# 🔍 变量作用域验证报告

## 问题背景

用户质疑：`cached_linked_schema` 是局部变量，可以直接在 `scale_sql` 和 `refine_final_sql` 调用中使用吗？

## ✅ 验证结果：完全正确

### 1. **变量定义位置**

`cached_linked_schema` 是 `execute_single_question` 函数的**函数参数**（不是内部定义的局部变量）：

```python
def execute_single_question(
    sql_id, question, table_list, knowledge, 
    schema_parser, args, 
    csv_save_path, log_save_path, sql_save_path, 
    search_directory, format_csv,
    schema_linker=None, use_schema_linking=False,
    complexity='unknown',
    cached_exploration_result=None,
    cached_linked_schema=None,  # ✅ 作为函数参数传入
    prompt_manager=None,
    thread_prefix=""
):
```

**文件**: `run_starrocks.py`  
**位置**: 第43-54行

### 2. **作用域范围**

由于 `cached_linked_schema` 是**函数参数**，它在整个 `execute_single_question` 函数体内都是可访问的：

```
execute_single_question() 函数作用域
├── cached_linked_schema (参数，整个函数内可访问)
├── ... (其他逻辑)
├── if use_schema_linking and cached_linked_schema:  ✅ 第291行（可访问）
├── if use_decompose_scale:
│   ├── agent.scale_sql(schema_links=schema_links_for_scale)  ✅ 第301行（可访问）
│   └── agent.refine_final_sql(schema_links=schema_links_for_scale)  ✅ 第336行（可访问）
└── else:
    ├── agent.scale_sql(schema_links=schema_links_for_scale)  ✅ 第367行（可访问）
    └── agent.refine_final_sql(schema_links=schema_links_for_scale)  ✅ 第383行（可访问）
```

### 3. **使用方式**

#### 步骤1：检查缓存是否存在

```python
# 🔧 准备schema_links参数（使用缓存的schema linking结果）
schema_links_for_scale = ""
if use_schema_linking and cached_linked_schema:
    schema_links_for_scale = cached_linked_schema
    logger.info("[Scale] Using cached schema linking result")
```

**位置**: 第289-292行 / 第355-358行

#### 步骤2：传递给 `scale_sql`

```python
final_sql = agent.scale_sql(
    question=question,
    schema=table_info,
    qa_pairs=refined_qa_pairs,
    evidence=knowledge if knowledge else "",
    schema_links=schema_links_for_scale,  # ✨ 使用缓存的结果
    few_shot_examples=pre_info if pre_info else "",
    use_fallback=use_fallback,
    chat_session=chat_session_scale,
    logger=logger
)
```

**位置**: 第295-305行 / 第361-371行

#### 步骤3：传递给 `refine_final_sql`

```python
final_sql = agent.refine_final_sql(
    initial_sql=final_sql,
    question=question,
    schema=table_info,
    evidence=knowledge if knowledge else "",
    schema_links=schema_links_for_scale,  # ✨ 使用相同的缓存结果
    max_iter=args.final_sql_max_iter if hasattr(args, 'final_sql_max_iter') else 3,
    sql_id=f"{sql_id}_{thread_prefix if thread_prefix else 'default'}",
    csv_save_path=vote_csv_path,
    sql_save_path=vote_sql_path,
    table_struct=table_struct,
    chat_session=chat_session_scale,
    logger=logger
)
```

**位置**: 第331-343行 / 第377-390行

### 4. **缓存传递链路**

```
process_question()
  ↓
  预执行 Schema Linking（一次）
  ↓
  cached_linked_schema = 结果
  ↓
  启动多个线程：
    thread_0: execute_single_question(cached_linked_schema=缓存)
    thread_1: execute_single_question(cached_linked_schema=缓存)
    thread_2: execute_single_question(cached_linked_schema=缓存)
  ↓
  每个线程内部：
    ├── schema_links_for_scale = cached_linked_schema
    ├── agent.scale_sql(schema_links=schema_links_for_scale)
    └── agent.refine_final_sql(schema_links=schema_links_for_scale)
```

### 5. **修复的Bug**

在第377-390行发现了一个重复参数Bug：

**修复前**：
```python
agent.refine_final_sql(
    schema_links=schema_links_for_scale,  # ✅ 正确
    schema_links="",  # ❌ 重复参数！
    ...
)
```

**修复后**：
```python
agent.refine_final_sql(
    schema_links=schema_links_for_scale,  # ✅ 正确
    ...
)
```

## ✅ 结论

1. **作用域正确**：`cached_linked_schema` 作为函数参数，在整个函数内都可访问 ✅
2. **使用方式正确**：通过中间变量 `schema_links_for_scale` 安全传递 ✅
3. **空值处理正确**：如果缓存为空，使用空字符串 `""` 作为默认值 ✅
4. **Bug已修复**：移除了重复的 `schema_links` 参数 ✅

---

## 📊 完整使用统计

| 使用位置 | 行号 | 调用函数 | 传递方式 |
|---------|------|---------|---------|
| 投票模式-Scale | 301 | `agent.scale_sql()` | `schema_links=schema_links_for_scale` |
| 投票模式-Refine | 336 | `agent.refine_final_sql()` | `schema_links=schema_links_for_scale` |
| 单次模式-Scale | 367 | `agent.scale_sql()` | `schema_links=schema_links_for_scale` |
| 单次模式-Refine | 383 | `agent.refine_final_sql()` | `schema_links=schema_links_for_scale` |

所有使用位置都在 `execute_single_question` 函数作用域内，**完全合法**！✅
