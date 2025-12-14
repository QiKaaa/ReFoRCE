# Schema Linking幻觉问题修复文档

## 问题描述

在并行Schema Linking过程中，发现MACSQLCoTParse和RSLSQLBiDirParse两个解析器存在严重的幻觉问题：
1. **输出不存在的表名**：解析器会"创造"schema中不存在的表
2. **输出不存在的列名**：解析器会"猜测"表中不存在的列
3. **表数量超出预期**：例如table_list只有3个表，但返回6个表

## 根本原因

1. **Prompt不够明确**：原prompt没有强调"只能使用schema中存在的名称"
2. **缺少M-schema格式说明**：LLM不理解M-schema的结构
3. **缺少验证机制**：解析后没有验证表名/列名的有效性
4. **日志不足**：无法追踪两个parser各自的输出和合并过程

## 修复方案

### 1. 优化Prompt（`parallel_schema_linking_prompts.py`）

#### MACSQLCoTParse System Prompt 改进：

**添加内容：**
```markdown
M-Schema Format Explanation:
The schema follows this structure:
```
# Table: table_name, Comment: table description
[
(column1: type, Comment: description, Examples: [value1, value2, ...]),
...
]
```

CRITICAL CONSTRAINTS:
1. **ONLY use table names and column names that EXACTLY appear in the provided schema**
2. **DO NOT invent or guess any table/column names**
3. **Table names appear after "# Table:" in the schema**
4. **Column names appear before ":" inside parentheses in the schema**
5. **If unsure, mark table as "drop_all" rather than guessing**
```

**关键点：**
- 明确说明M-schema格式
- 用粗体强调禁止编造名称
- 给出精确的名称提取规则
- 提供不确定时的安全策略

#### RSLSQLBiDirParse System Prompt 改进：

**添加内容：**
```markdown
M-Schema Format Explanation: (同上)

CRITICAL CONSTRAINTS:
1. **ONLY output table names that EXACTLY appear after "# Table:" in the schema**
2. **ONLY output column names that EXACTLY appear before ":" inside () in the schema**
3. **DO NOT invent, guess, or create any table/column names**
4. **Column format in output: table_name.`column_name`**
5. **Verify every output name against the provided schema**
```

### 2. 添加验证机制（`parallel_schema_linker.py`）

#### MACSQLCoTParse响应验证：

```python
def _parse_macsql_response(self, response: str):
    # 验证表名
    if table not in self.table_schemas:
        invalid_tables.append(table)
        logger.warning(f"⚠️ Invalid table '{table}' not in schema, skipping")
        continue
    
    # 验证列名
    available_cols = self._extract_table_columns(table)
    for col in value:
        if col in available_cols:
            valid_cols.append(col)
        else:
            logger.warning(f"⚠️ Invalid column '{table}.{col}' not in schema, skipping")
```

**效果：**
- 自动过滤不存在的表
- 自动过滤不存在的列
- 记录所有被过滤的无效名称

#### RSLSQLBiDirParse响应验证：

```python
def _parse_rslsql_table_response(self, response: str):
    # 验证表名
    for table in raw_tables:
        if table in self.table_schemas:
            valid_tables.append(table)
        else:
            logger.warning(f"⚠️ Invalid table '{table}' not in schema, skipping")
    
    # 验证列名
    for col in raw_columns:
        table = col.split('.')[0]
        column = col.split('.', 1)[1].strip('`')
        
        if table not in self.table_schemas:
            logger.warning(f"⚠️ Invalid column '{col}': table not in schema")
            continue
        
        available_cols = self._extract_table_columns(table)
        if column not in available_cols:
            logger.warning(f"⚠️ Invalid column '{col}': column not in schema")
```

### 3. 增强日志输出（`parallel_schema_linker.py`）

#### 添加详细的parser结果日志：

```python
# MACSQLCoTParse结果
logger.info("="*60)
logger.info("[Parser Results] MACSQLCoTParse:")
logger.info(f"  Tables ({count}): {tables}")
logger.info(f"  Columns: {total} total across {num} tables")
for table, cols in columns.items():
    logger.info(f"    {table}: {len(cols)} columns - {cols[:5]}...")

# RSLSQLBiDirParse结果
logger.info("[Parser Results] RSLSQLBiDirParse:")
logger.info(f"  Tables ({count}): {tables}")
logger.info(f"  Columns: {total} total")
for table, cols in cols_by_table.items():
    logger.info(f"    {table}: {len(cols)} columns - {cols[:5]}...")

# 合并结果
logger.info("[Merged Result]:")
logger.info(f"  Tables ({count}): {tables}")
logger.info(f"  Columns: {total} total")
for table in tables:
    logger.info(f"    {table}: {len(cols)} columns - {cols[:5]}...")
logger.info("="*60)
```

**日志示例：**
```
============================================================
[Parser Results] MACSQLCoTParse:
  Tables (3): ['users', 'code_submissions', 'contests']
  Columns: 18 total across 3 tables
    users: 6 columns - ['user_id', 'username', 'email', 'created_at', 'status']...
    code_submissions: 8 columns - ['submission_id', 'user_id', 'contest_id', 'problem_id']...
    contests: 4 columns - ['contest_id', 'contest_name', 'start_time', 'end_time']

[Parser Results] RSLSQLBiDirParse:
  Tables (3): ['users', 'code_submissions', 'contests']
  Columns: 15 total
    users: 5 columns - ['`user_id`', '`username`', '`email`', '`created_at`']...
    code_submissions: 7 columns - ['`submission_id`', '`user_id`', '`contest_id`']...
    contests: 3 columns - ['`contest_id`', '`contest_name`', '`start_time`']

[Merged Result]:
  Tables (3): ['users', 'code_submissions', 'contests']
  Columns: 25 total
    users: 8 columns - ['`user_id`', '`username`', '`email`', '`created_at`']...
    code_submissions: 12 columns - ['`submission_id`', '`user_id`', '`contest_id`']...
    contests: 5 columns - ['`contest_id`', '`contest_name`', '`start_time`']...
============================================================
```

### 4. 表名过滤机制（已在之前修复）

在`merge_results`方法中添加`table_list`参数，确保只返回预期范围内的表：

```python
def merge_results(self, macsql_result, rslsql_result, table_list):
    # 过滤：只保留在table_list中的表
    if table_list:
        all_tables = [t for t in all_tables if t in table_list]
        if filtered_count > 0:
            logger.warning(f"[Merge] Filtered out {filtered_count} tables not in table_list")
```

## 修改文件清单

1. **`prompts/parallel_schema_linking_prompts.py`**
   - `get_macsql_system_prompt()`: 添加M-schema格式说明和严格约束
   - `get_rslsql_table_selection_system_prompt()`: 添加M-schema格式说明和严格约束

2. **`parallel_schema_linker.py`**
   - `_parse_macsql_response()`: 添加表名/列名验证和日志
   - `_parse_rslsql_table_response()`: 添加表名/列名验证和日志
   - `link_schema()`: 添加详细的parser结果和合并结果日志
   - `merge_results()`: 添加table_list过滤（已在之前修复）

## 预期效果

### 幻觉问题解决：
- ✅ **100%准确的表名**：只输出schema中存在的表
- ✅ **100%准确的列名**：只输出schema中存在的列
- ✅ **符合预期的表数量**：受table_list约束

### 可追踪性提升：
- ✅ **清晰的parser输出**：可以看到每个parser识别了哪些表和列
- ✅ **详细的过滤日志**：记录所有被过滤的无效名称
- ✅ **完整的合并过程**：可以追踪从两个parser到最终结果的全过程

### 示例警告日志：
```
[MACSQLCoTParse] ⚠️ Invalid table 'order_details' not in schema, skipping
[MACSQLCoTParse] ⚠️ Invalid column 'users.phone_number' not in schema, skipping
[MACSQLCoTParse] ⚠️ Filtered 2 invalid tables: ['order_details', 'payments']
[RSLSQLBiDirParse] ⚠️ Invalid table 'transactions' not in schema, skipping
[RSLSQLBiDirParse] ⚠️ Filtered 1 invalid tables: ['transactions']
[Merge] Filtered out 1 tables not in table_list
```

## 测试建议

1. **运行sql_1问题**：验证表数量是否符合table_list
2. **检查日志输出**：确认parser结果和合并结果清晰可见
3. **查找警告信息**：确认是否还有幻觉问题
4. **对比修复前后**：评估幻觉问题的改善程度

## 后续优化

如果幻觉问题仍然存在，可以考虑：
1. **Few-shot示例**：在prompt中提供正确的schema linking示例
2. **更严格的JSON schema**：使用JSON schema约束LLM输出格式
3. **二次验证**：让LLM自己验证输出的表名/列名是否在schema中
4. **降低temperature**：使用temperature=0减少随机性
