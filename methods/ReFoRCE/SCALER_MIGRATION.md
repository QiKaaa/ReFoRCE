# Scaler功能合并说明

## 概述
将`scaler_starrocks.py`的SQL合并（Scaler）功能合并到`agent.py`中统一管理。

## 迁移时间
2025-11-26

## 修改内容

### 1. 删除文件
- `scaler_starrocks.py` - 已删除，功能合并到`agent.py`

### 2. agent.py - 新增方法

#### 类属性
- `SCALE_TEMPLATE_STARROCKS` - SQL合并模板
- `FALLBACK_TEMPLATE` - 简化模板（无子问题时使用）

#### 新增方法

**`format_sub_questions(qa_pairs)`**
- 功能：格式化子问题和SQL为Prompt输入
- 参数：`qa_pairs` - [(sub_question, sub_sql), ...]
- 返回：格式化的字符串

**`scale_sql(question, schema, qa_pairs, ...)`**
- 功能：执行SQL合并（将子问题SQL合并为最终SQL）
- 参数：
  - `question` - 原始问题
  - `schema` - 数据库Schema
  - `qa_pairs` - 子问题和SQL对
  - `evidence` - 领域知识
  - `schema_links` - Schema Linking结果
  - `few_shot_examples` - 列探索示例
  - `use_fallback` - 是否使用简化模板
  - `chat_session` - GPT会话（可选，默认使用self.chat_session）
  - `logger` - 日志记录器
- 返回：合并后的最终SQL

**`_extract_sql_from_response(response)`**
- 功能：从LLM响应中提取SQL
- 参数：`response` - LLM响应（str或list）
- 返回：提取的SQL语句

**`generate_multiple_sql_candidates(question, schema, qa_pairs, ...)`**
- 功能：生成多个SQL候选（用于投票机制）
- 参数：与`scale_sql`类似，增加`num_candidates`
- 返回：SQL候选列表

**`refine_final_sql(initial_sql, question, schema, ...)`**
- 功能：对最终合并SQL进行self-refinement迭代优化
- 参数：
  - `initial_sql` - 初始合并SQL
  - `question` - 原始问题
  - `schema` - 数据库Schema
  - `evidence` - 领域知识
  - `schema_links` - Schema Linking结果
  - `max_iter` - 最大迭代次数
  - `sql_id` - SQL标识符
  - `csv_save_path` - CSV保存路径
  - `sql_save_path` - SQL保存路径
  - `table_struct` - 表结构信息
  - `chat_session` - GPT会话（可选）
  - `logger` - 日志记录器
- 返回：优化后的SQL

### 3. run_starrocks.py - 调用修改

#### 移除导入
```python
# 删除
from scaler_starrocks import StarRocksScaler
```

#### 修改调用方式

**原代码（已删除）：**
```python
scaler = StarRocksScaler(
    chat_session=GPTChat(...),
    azure=args.azure,
    model=args.scale_model,
    prompt_class=prompt_manager
)

final_sqls = scaler.generate_multiple_candidates(...)
final_sql = scaler.scale(...)
final_sql = scaler.refine_final_sql(...)
```

**新代码：**
```python
# 创建专用于SQL合并的chat session
chat_session_scale = GPTChat(
    args.azure, 
    args.scale_model if hasattr(args, 'scale_model') else args.generation_model
)

# 直接使用agent的方法
final_sqls = agent.generate_multiple_sql_candidates(..., chat_session=chat_session_scale)
final_sql = agent.scale_sql(..., chat_session=chat_session_scale)
final_sql = agent.refine_final_sql(..., chat_session=chat_session_scale)
```

## 优势

### 1. 代码统一管理
- 所有SQL相关操作（exploration、self_refine、scale）都在`REFORCE`类中
- 减少代码重复，便于维护

### 2. 共享资源
- 共享`sql_env`、`api`、`sqlite_path`等资源
- 共享`prompt_class`进行统一的Prompt管理

### 3. 简化调用
- 不需要额外创建`StarRocksScaler`实例
- 参数传递更简洁（自动使用agent的sql_env等）

### 4. 一致性
- 与`self_refine`、`process_sub_question_sql`等方法风格一致
- 使用相同的错误处理和日志记录模式

## 兼容性

### API兼容性
所有原`StarRocksScaler`的方法签名保持兼容：
- `scale()` → `scale_sql()`（名称调整避免与动词scale混淆）
- `generate_multiple_candidates()` → `generate_multiple_sql_candidates()`
- `refine_final_sql()` → `refine_final_sql()`（保持不变）

### 参数变化
- 移除了`sql_env`、`api`、`sqlite_path`等参数（自动使用agent的属性）
- 新增`chat_session`参数（可选，默认使用self.chat_session）

## 使用示例

### 单次合并模式
```python
final_sql = agent.scale_sql(
    question=question,
    schema=table_info,
    qa_pairs=refined_qa_pairs,
    evidence=knowledge,
    schema_links="",
    few_shot_examples=pre_info,
    use_fallback=False,
    chat_session=chat_session_scale,
    logger=logger
)
```

### 投票模式
```python
# 生成多个候选
final_sqls = agent.generate_multiple_sql_candidates(
    question=question,
    schema=table_info,
    qa_pairs=refined_qa_pairs,
    evidence=knowledge,
    num_candidates=3,
    chat_session=chat_session_scale,
    logger=logger
)

# 对每个候选进行refinement
for i, final_sql in enumerate(final_sqls):
    refined_sql = agent.refine_final_sql(
        initial_sql=final_sql,
        question=question,
        schema=table_info,
        max_iter=3,
        sql_id=f"decompose_{i}",
        csv_save_path=vote_csv_path,
        sql_save_path=vote_sql_path,
        table_struct=table_struct,
        chat_session=chat_session_scale,
        logger=logger
    )
```

## 注意事项

1. **chat_session参数**：需要为SQL合并创建独立的chat_session，避免与exploration和self_refine的会话混淆

2. **日志记录**：所有Scaler操作的日志前缀为`[Scaler]`或`[Scaler-Refine]`

3. **错误处理**：继承了`self_refine`的错误处理逻辑（early stop、empty result检查等）

4. **文件保存**：使用agent的`csv_max_len`、`empty_result`等配置

## 测试建议

1. 验证分解-合并流程是否正常工作
2. 检查投票机制是否正确生成和选择候选SQL
3. 确认refinement迭代逻辑与原实现一致
4. 测试各种复杂度的问题（简单、中等、复杂）

## 相关文件

- `agent.py` - 合并后的主文件
- `run_starrocks.py` - 使用Scaler功能的主脚本
- `decomposer_starrocks.py` - 问题分解模块（仍然独立）
- `scaler_starrocks.py` - **已删除**
