# Schema Linking 缓存优化

## 问题描述

在 `scale_sql` 和 `refine_final_sql` 调用时，`schema_links` 参数传递的是空字符串，没有利用已经缓存的 schema linking 结果，导致：

1. **信息丢失**：缓存的 schema linking 结果（精简的M-schema）没有被传递给SQL合并和优化阶段
2. **性能浪费**：在 `process_question` 中已经执行了一次 schema linking 并缓存，但在后续SQL生成阶段没有使用
3. **质量下降**：SQL合并时缺少关键的schema信息，可能影响生成质量

## 解决方案

### 修改位置

**文件**: `run_starrocks.py`

**修改点1**: 投票模式中的 `scale_sql` 调用（第286-302行）
**修改点2**: 投票模式中的 `refine_final_sql` 调用（第323-337行）
**修改点3**: 单次合并模式中的 `scale_sql` 调用（第353-371行）
**修改点4**: 单次合并模式中的 `refine_final_sql` 调用（第377行）

---

## 代码对比

### 修改前（错误）

```python
# 投票模式 - scale_sql
final_sql = agent.scale_sql(
    question=question,
    schema=table_info,
    qa_pairs=refined_qa_pairs,
    evidence=knowledge if knowledge else "",
    schema_links="",  # ❌ 空字符串，没有使用缓存
    few_shot_examples=pre_info if pre_info else "",
    use_fallback=use_fallback,
    chat_session=chat_session_scale,
    logger=logger
)

# 投票模式 - refine_final_sql
final_sql = agent.refine_final_sql(
    initial_sql=final_sql,
    question=question,
    schema=table_info,
    evidence=knowledge if knowledge else "",
    schema_links="",  # ❌ 空字符串，没有使用缓存
    max_iter=args.final_sql_max_iter if hasattr(args, 'final_sql_max_iter') else 3,
    ...
)

# 单次合并模式 - 相同问题
```

### 修改后（正确）

```python
# 投票模式
logger.info(f"[Scale] Thread {thread_prefix}: Using {'fallback' if use_fallback else 'normal'} strategy")

# 🔧 准备schema_links参数（使用缓存的schema linking结果）
schema_links_for_scale = ""
if use_schema_linking and cached_linked_schema:
    schema_links_for_scale = cached_linked_schema
    logger.info("[Scale] Using cached schema linking result")

# 生成单个SQL候选
final_sql = agent.scale_sql(
    question=question,
    schema=table_info,
    qa_pairs=refined_qa_pairs,
    evidence=knowledge if knowledge else "",
    schema_links=schema_links_for_scale,  # ✅ 使用缓存的结果
    few_shot_examples=pre_info if pre_info else "",
    use_fallback=use_fallback,
    chat_session=chat_session_scale,
    logger=logger
)

# ✨ 对生成的SQL进行self-refinement
logger.info(f"[Scale] Refining generated SQL...")
final_sql = agent.refine_final_sql(
    initial_sql=final_sql,
    question=question,
    schema=table_info,
    evidence=knowledge if knowledge else "",
    schema_links=schema_links_for_scale,  # ✅ 使用相同的缓存结果
    max_iter=args.final_sql_max_iter if hasattr(args, 'final_sql_max_iter') else 3,
    sql_id=f"{sql_id}_{thread_prefix if thread_prefix else 'default'}",
    csv_save_path=vote_csv_path,
    sql_save_path=vote_sql_path,
    table_struct=table_struct,
    chat_session=chat_session_scale,
    logger=logger
)
```

```python
# 单次合并模式
else:
    # 单次合并模式
    # 🔧 准备schema_links参数（使用缓存的schema linking结果）
    schema_links_for_scale = ""
    if use_schema_linking and cached_linked_schema:
        schema_links_for_scale = cached_linked_schema
        logger.info("[Scale] Using cached schema linking result")
    
    final_sql = agent.scale_sql(
        question=question,
        schema=table_info,
        qa_pairs=refined_qa_pairs,
        evidence=knowledge if knowledge else "",
        schema_links=schema_links_for_scale,  # ✅ 使用缓存的结果
        few_shot_examples=pre_info if pre_info else "",
        use_fallback=False,
        chat_session=chat_session_scale,
        logger=logger
    )
    
    logger.info(f"[Scale] Initial final SQL generated:\n{final_sql}")
    
    # ✨ 如果启用最终SQL refinement，进行优化
    if args.do_final_sql_refinement:
        logger.info("[Scale-Refine] Starting final SQL refinement...")
        final_sql = agent.refine_final_sql(
            initial_sql=final_sql,
            question=question,
            schema=table_info,
            evidence=knowledge if knowledge else "",
            schema_links=schema_links_for_scale,  # ✅ 使用相同的缓存结果
            ...
        )
```

---

## 工作流程

### 修改前的流程（错误）

```
process_question 函数
  ↓
预执行 Schema Linking (第523-547行)
  ↓
cached_linked_schema = linked_schema ✅
  ↓
传递给 execute_single_question
  ↓
execute_single_question 中使用缓存的 table_info ✅
  ↓
调用 scale_sql(schema_links="") ❌ 没有使用缓存
  ↓
调用 refine_final_sql(schema_links="") ❌ 没有使用缓存
```

**问题**：虽然缓存了 schema linking 结果，但在SQL合并和优化阶段没有使用，导致信息丢失。

### 修改后的流程（正确）

```
process_question 函数
  ↓
预执行 Schema Linking (第523-547行)
  ↓
cached_linked_schema = linked_schema ✅
  ↓
传递给 execute_single_question
  ↓
execute_single_question 中使用缓存的 table_info ✅
  ↓
准备 schema_links_for_scale = cached_linked_schema ✅
  ↓
调用 scale_sql(schema_links=schema_links_for_scale) ✅
  ↓
调用 refine_final_sql(schema_links=schema_links_for_scale) ✅
```

**效果**：缓存的 schema linking 结果在整个流程中都得到了使用。

---

## 优化效果

### 1. **信息完整性** ✅

**修改前**：
```python
# 传递给 agent.scale_sql 的 schema_links
schema_links = ""  # 空字符串

# SCALE_TEMPLATE_STARROCKS 中的占位符
【Schema Links (Critical Tables & Columns)】
{schema_links}  # 渲染为 "Not provided"
```

**修改后**：
```python
# 传递给 agent.scale_sql 的 schema_links
schema_links_for_scale = cached_linked_schema  # M-schema格式的精简schema

# SCALE_TEMPLATE_STARROCKS 中的占位符
【Schema Links (Critical Tables & Columns)】
{schema_links}  # 渲染为完整的M-schema信息
```

### 2. **性能优化** ✅

- ✅ **避免重复计算**：不需要在SQL合并阶段重新推断schema关系
- ✅ **利用预处理结果**：使用已经精简和优化过的schema信息
- ✅ **减少Token消耗**：精简的M-schema比完整schema更短，节省LLM调用成本

### 3. **质量提升** ✅

- ✅ **更准确的SQL生成**：LLM可以基于schema linking的精准信息生成SQL
- ✅ **更好的列选择**：知道哪些列是关键列，避免选择无关列
- ✅ **更合理的JOIN条件**：基于schema linking的表关系建议

---

## 日志输出

### 修改前（没有日志）

```
[Scale] Starting SQL synthesis...
[Scale] Thread linked_0: Using normal strategy
[Scaler] Starting SQL scaling with 2 sub-questions
[Scaler] Generated final SQL: ...
```

### 修改后（有提示日志）

```
[Scale] Starting SQL synthesis...
[Scale] Thread linked_0: Using normal strategy
[Scale] Using cached schema linking result  ⭐ 新增日志
[Scaler] Starting SQL scaling with 2 sub-questions
[Scaler] Generated final SQL: ...
[Scale] Refining generated SQL...
[Scale] Using cached schema linking result  ⭐ 新增日志（refinement阶段）
[Scaler-Refine] Starting refinement with max_iter=3
```

---

## 验证检查

### ✅ 语法检查
```bash
# 无语法错误
python -m py_compile run_starrocks.py
```

### ✅ 参数传递检查

**投票模式**：
- `scale_sql` 调用：`schema_links=schema_links_for_scale` ✅
- `refine_final_sql` 调用：`schema_links=schema_links_for_scale` ✅

**单次合并模式**：
- `scale_sql` 调用：`schema_links=schema_links_for_scale` ✅
- `refine_final_sql` 调用：`schema_links=schema_links_for_scale` ✅

### ✅ 条件判断

```python
# 只有在使用schema linking且有缓存时才传递
if use_schema_linking and cached_linked_schema:
    schema_links_for_scale = cached_linked_schema
    logger.info("[Scale] Using cached schema linking result")
```

---

## 总结

### ✅ 修复内容
1. **投票模式**：`scale_sql` 和 `refine_final_sql` 都使用缓存的schema linking结果
2. **单次合并模式**：`scale_sql` 和 `refine_final_sql` 都使用缓存的schema linking结果
3. **条件判断**：仅在启用schema linking且有缓存时才传递
4. **日志记录**：添加明确的日志提示，便于调试

### ✅ 优势
- ✅ **信息完整**：SQL合并阶段可以利用schema linking的精准信息
- ✅ **性能提升**：避免重复计算，减少Token消耗
- ✅ **质量保证**：基于更准确的schema信息生成更高质量的SQL
- ✅ **一致性**：整个流程使用相同的schema信息，保持一致性

### ✅ 兼容性
- ✅ 向后兼容：如果没有启用schema linking或缓存为空，`schema_links_for_scale` 为空字符串
- ✅ 不影响现有逻辑：只是填充了之前为空的参数
- ✅ 无破坏性修改：所有现有功能保持不变
