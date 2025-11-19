# 列探索和Schema Linking缓存优化总结

## 修改目的

对于数据集中的每个问题，只执行**一次**列探索和**一次**Schema Linking，之后的所有需要用到这两个输出的地方复用结果，避免重复调用LLM，提高效率和降低成本。

## 问题背景

在原始实现中，当启用投票模式时（如 `--num_votes 3`），每个问题会被执行多次：
- **列探索（Column Exploration）**: 每个线程都独立调用 `agent.exploration()`
- **Schema Linking**: 每个线程都独立调用 `schema_linker.link_schema()`

例如，投票模式下生成3次SQL，就会调用3次列探索和3次Schema Linking，造成：
- ❌ LLM调用次数增加3倍
- ❌ 执行时间增加
- ❌ API成本增加
- ❌ 结果可能不一致（LLM输出有随机性）

## 解决方案

### 核心思路

在 `process_question()` 函数中，**在启动投票线程之前**：
1. 预先执行一次列探索（如果需要）
2. 预先执行一次Schema Linking（如果需要）
3. 将结果缓存并传递给所有后续线程

### 代码修改

#### 1. 修改 `execute_single_question()` 函数签名

**文件**: `run_starrocks.py`  
**位置**: 第45行

添加两个新参数：
```python
def execute_single_question(
    sql_id, question, table_list, knowledge, 
    schema_parser, args, 
    csv_save_path, log_save_path, sql_save_path, 
    search_directory, format_csv,
    schema_linker=None, use_schema_linking=False,
    complexity='unknown',
    cached_exploration_result=None,  # ✨ 新增
    cached_linked_schema=None  # ✨ 新增
):
```

#### 2. Schema Linking使用缓存逻辑

**文件**: `run_starrocks.py`  
**位置**: 第91-114行

```python
if use_schema_linking and schema_linker:
    # ===== 使用缓存的Schema Linking结果（如果有）=====
    if cached_linked_schema is not None:
        table_info = cached_linked_schema
        logger.info("[Schema Linking] Using cached schema")
    else:
        # 没有缓存，执行Schema Linking
        logger.info("[Schema Linking] Generating optimized schema...")
        # ... 执行逻辑 ...
```

#### 3. 列探索使用缓存逻辑

**文件**: `run_starrocks.py`  
**位置**: 第184-200行

```python
# ===== 列探索（使用缓存机制）=====
if should_do_column_exploration:
    if cached_exploration_result is not None:
        pre_info, response_pre_txt = cached_exploration_result
        logger.info("[Column Exploration] Using cached exploration result")
        print(f"{sql_id}: Using cached column exploration")
    else:
        # 没有缓存，执行列探索
        pre_info, response_pre_txt, max_try = agent.exploration(...)
```

#### 4. 在 `process_question()` 中预执行并缓存

**文件**: `run_starrocks.py`  
**位置**: 第272-350行

##### 4.1 预执行列探索

```python
# ===== ✨ 预先执行一次列探索（如果需要）=====
cached_exploration_result = None

if args.do_column_exploration and complexity in ['中等', '复杂']:
    should_do_column_exploration = True
    print(f"[{sql_id}] Pre-executing column exploration...")
    
    # 创建临时环境
    chat_session_ex_temp = GPTChat(...)
    sql_env_temp = SqlEnvStarRocks(...)
    agent_temp = REFORCE(...)
    
    # 执行列探索（只执行一次）
    pre_info, response_pre_txt, max_try = agent_temp.exploration(...)
    
    # 缓存结果
    cached_exploration_result = (pre_info, response_pre_txt)
    print(f"[{sql_id}] ✓ Column exploration cached")
```

##### 4.2 预执行Schema Linking

```python
# ===== ✨ 预先执行一次Schema Linking（如果需要）=====
cached_linked_schema = None

if (args.do_schema_linking_vote or args.use_schema_linking) and schema_linker:
    print(f"[{sql_id}] Pre-executing schema linking...")
    
    # 创建临时chat session
    chat_session_sl_temp = GPTChat(...)
    
    # 执行Schema Linking（只执行一次）
    linked_schema = schema_linker.link_schema(...)
    
    # 缓存结果
    cached_linked_schema = linked_schema
    print(f"[{sql_id}] ✓ Schema linking cached")
```

##### 4.3 传递缓存给所有线程

**投票模式** - 原始Schema组：
```python
thread = threading.Thread(
    target=execute_single_question,
    args=(
        ...,
        cached_exploration_result,  # ✨ 传递缓存
        None  # 不使用cached_linked_schema
    )
)
```

**投票模式** - Schema Linking组：
```python
thread = threading.Thread(
    target=execute_single_question,
    args=(
        ...,
        cached_exploration_result,  # ✨ 传递缓存
        cached_linked_schema  # ✨ 传递缓存
    )
)
```

**非投票模式**：
```python
execute_single_question(
    ...,
    cached_exploration_result,  # ✨ 传递缓存
    cached_linked_schema  # ✨ 传递缓存
)
```

## 优化效果

### 性能提升

| 场景 | 原实现 | 优化后 | 提升 |
|------|--------|--------|------|
| **投票模式 (num_votes=3)** | 列探索×3次<br>Schema Linking×3次 | 列探索×1次<br>Schema Linking×1次 | **减少66%** LLM调用 |
| **Schema Linking投票 (num_votes=3)** | 列探索×6次<br>Schema Linking×3次 | 列探索×1次<br>Schema Linking×1次 | **减少83%** 列探索调用<br>**减少66%** Schema Linking调用 |
| **非投票模式** | 列探索×1次<br>Schema Linking×1次 | 列探索×1次<br>Schema Linking×1次 | 无变化（已是最优） |

### 一致性保证

✅ **结果一致性**: 所有投票候选使用相同的列探索和Schema Linking结果，避免LLM随机性导致的不一致

✅ **公平投票**: 确保所有候选SQL在相同的schema信息下生成，投票更公平

### 成本节约

假设：
- 列探索平均tokens: 5000 (input) + 2000 (output)
- Schema Linking平均tokens: 3000 (input) + 1500 (output)

**投票模式 (num_votes=3)** 节约：
- 列探索: 减少 `2 × (5000 + 2000) = 14,000 tokens`
- Schema Linking: 减少 `2 × (3000 + 1500) = 9,000 tokens`
- **总计**: 每个问题节约约 **23,000 tokens**

对于100个问题，节约约 **2,300,000 tokens** ≈ **节省成本60-80%**（列探索和Schema Linking部分）

## 兼容性

✅ **完全向后兼容**: 
- 新增参数有默认值 `None`
- 未传递缓存时，自动执行原逻辑
- 不影响现有功能

✅ **所有模式支持**:
- ✅ 投票模式 (`--do_vote`)
- ✅ Schema Linking投票 (`--do_schema_linking_vote`)
- ✅ 非投票模式（直接执行）
- ✅ 列探索按复杂度过滤

## 使用示例

### 启用投票+列探索+Schema Linking

```bash
python run_starrocks.py \
  --do_vote \
  --num_votes 3 \
  --do_column_exploration \
  --use_schema_linking \
  --output_path output/cached_test
```

**行为**:
- 每个问题只执行1次列探索（如果复杂度为中等/复杂）
- 每个问题只执行1次Schema Linking
- 3个投票候选复用相同结果

### 启用Schema Linking投票

```bash
python run_starrocks.py \
  --do_vote \
  --num_votes 3 \
  --do_schema_linking_vote \
  --do_column_exploration
```

**行为**:
- 每个问题只执行1次列探索
- 每个问题只执行1次Schema Linking
- 生成6个候选SQL（3个原始schema + 3个linked schema）
- 所有候选共享相同的列探索结果

## 注意事项

### 1. 临时文件清理

预执行阶段会创建临时日志文件（`temp_exploration.log`），不影响最终结果。

### 2. 数据库连接

预执行列探索时会创建临时数据库连接，执行完毕后自动关闭，避免连接泄漏。

### 3. 复杂度判断

列探索的预执行遵循原有逻辑：
- **简单**: 不执行列探索
- **中等/复杂**: 执行列探索

## 测试建议

### 1. 功能测试

```bash
# 测试投票模式缓存
python run_starrocks.py \
  --do_vote --num_votes 3 \
  --do_column_exploration \
  --max_questions 5

# 检查日志中是否出现 "Using cached"
```

### 2. 性能测试

```bash
# 对比优化前后的执行时间
time python run_starrocks.py --do_vote --num_votes 3 --max_questions 10
```

### 3. 结果验证

确认优化后的SQL质量没有下降（投票结果应该保持一致或更好）。

## 相关文件

- `run_starrocks.py`: 主要修改文件
- `agent.py`: `exploration()` 方法被调用
- `schema_linking_optimized.py`: `link_schema()` 方法被调用

## 版本历史

- **2025-11-19**: 初始实现，添加列探索和Schema Linking缓存机制

---

**总结**: 通过在问题级别预执行并缓存列探索和Schema Linking结果，成功将投票模式下的LLM调用次数减少60-80%，显著提高性能和降低成本，同时保证结果一致性。
