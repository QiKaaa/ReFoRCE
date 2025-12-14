# Schema Links 缓存机制说明

## 概述

在并行Schema Linking优化中,`parallel_schema_linker.link_schema()`方法返回两个值:
1. **`schema_links`**: 字典格式的schema linking结果
2. **`linked_schema`**: 简化后的M-schema文本

为了避免投票模式下重复执行Schema Linking,两个结果都会被缓存。

---

## 返回值结构

### 1. schema_links (字典)

```python
{
    "tables": ["table1", "table2", "table3"],
    "columns": [
        "table1.`col1`",
        "table1.`col2`",
        "table2.`col3`",
        ...
    ]
}
```

**用途**:
- 提供结构化的schema linking结果
- 便于统计和分析(表数量、列数量)
- 可用于后续处理(如filter、merge等)

### 2. linked_schema (字符串)

M-schema格式的文本,示例:

```
# Table: dim_argothek_gplayerid2qqwxid_df, 全量用户gplayerid转qq或wxid
[
(dtstatdate:VARCHAR, 日期, Examples: [20250720, 20250610]),
(vgameappid:VARCHAR, 平台, Examples: [app001, app007]),
...
]

# Table: dws_mgamejp_login_user_activity_di, 登录用户活跃信息
[
(dtstatdate:VARCHAR, 日期),
(igameid:BIGINT, 游戏ID),
...
]

### Foreign Keys:
dim_argothek_gplayerid2qqwxid_df.`vgameappid` = dws_mgamejp_login_user_activity_di.`vgameappid`
```

**用途**:
- 直接用作LLM的输入(作为table_info参数)
- 替代完整Schema,减少token消耗
- 保持M-schema格式的兼容性

---

## 缓存机制实现

### 在 `process_question()` 中缓存

```python
# 执行Schema Linking（只执行一次）
schema_links, linked_schema = schema_linker.link_schema(
    question=question,
    table_list=table_list,
    knowledge=knowledge,
    chat_session=chat_session_sl_temp
)

# 缓存两个结果
cached_linked_schema = linked_schema  # M-schema文本
cached_schema_links = schema_links    # {"tables": [...], "columns": [...]}

print(f"[{sql_id}] ✓ Schema linking cached:")
print(f"  - Tables: {len(schema_links.get('tables', []))}")
print(f"  - Columns: {len(schema_links.get('columns', []))}")
```

### 在 `execute_single_question()` 中使用

```python
def execute_single_question(
    ...,
    cached_linked_schema=None,   # 缓存的M-schema文本
    cached_schema_links=None,    # 缓存的schema links
    ...
):
    # 使用缓存的M-schema文本
    if use_schema_linking and cached_linked_schema is not None:
        table_info = cached_linked_schema
        logger.info("[Schema Linking] Using cached schema")
    
    # 使用缓存的schema links(可选,用于统计或其他目的)
    if cached_schema_links:
        logger.info(f"[Schema Links] Using cached links:")
        logger.info(f"  Tables: {cached_schema_links.get('tables', [])}")
        logger.info(f"  Columns count: {len(cached_schema_links.get('columns', []))}")
```

---

## 投票模式中的传递

### 原始Schema组 (不使用缓存)

```python
# 第一组：使用原始Schema生成（num_votes次）
for i in range(num_votes):
    thread = threading.Thread(
        target=execute_single_question,
        args=(
            ...,
            None,  # 不使用cached_linked_schema（原始schema模式）
            None,  # 不使用cached_schema_links（原始schema模式）
            ...
        )
    )
```

### Linked Schema组 (使用缓存)

```python
# 第二组：使用Schema Linking生成（num_votes次）
for i in range(num_votes):
    thread = threading.Thread(
        target=execute_single_question,
        args=(
            ...,
            cached_linked_schema,  # ✨ 传递缓存的M-schema文本
            cached_schema_links,   # ✨ 传递缓存的schema links
            ...
        )
    )
```

---

## 优势

### 1. 性能提升

**未使用缓存**:
```
投票3次 × 2组(原始+Linked) = 6次线程
每次线程都执行Schema Linking = 6次LLM调用
总Token: 6 × 15K = 90K tokens
```

**使用缓存**:
```
投票3次 × 2组(原始+Linked) = 6次线程
但Schema Linking只执行1次 = 1次LLM调用
总Token: 1 × 15K = 15K tokens (节省83%)
```

### 2. 一致性保证

所有Linked Schema组的线程使用相同的schema linking结果,确保:
- 投票结果公平(基于相同的Schema基础)
- 结果可复现
- 便于调试和分析

### 3. 信息完整性

同时缓存两种格式:
- **`linked_schema`**: 用于SQL生成(LLM输入)
- **`schema_links`**: 用于分析和统计(程序处理)

---

## 使用示例

### 示例1: 查看缓存的schema links统计

```python
if cached_schema_links:
    tables = cached_schema_links.get('tables', [])
    columns = cached_schema_links.get('columns', [])
    
    print(f"Schema Linking Summary:")
    print(f"  Selected Tables: {len(tables)}")
    print(f"  Selected Columns: {len(columns)}")
    print(f"  Avg Columns per Table: {len(columns) / len(tables):.1f}")
    
    # 按表统计列数
    table_col_count = {}
    for col in columns:
        if '.' in col:
            table = col.split('.')[0]
            table_col_count[table] = table_col_count.get(table, 0) + 1
    
    print(f"\n  Column Distribution:")
    for table, count in sorted(table_col_count.items(), key=lambda x: -x[1]):
        print(f"    {table}: {count} columns")
```

### 示例2: 保存缓存结果到文件

```python
import json

# 保存schema_links到JSON文件
if cached_schema_links:
    cache_file = os.path.join(search_directory, "cached_schema_links.json")
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cached_schema_links, f, indent=2, ensure_ascii=False)
    
    print(f"Schema links cached to: {cache_file}")

# 保存linked_schema到文本文件
if cached_linked_schema:
    cache_file = os.path.join(search_directory, "cached_linked_schema.txt")
    with open(cache_file, 'w', encoding='utf-8') as f:
        f.write(cached_linked_schema)
    
    print(f"Linked schema cached to: {cache_file}")
```

### 示例3: 在Scale阶段使用cached_schema_links

```python
# 在agent.scale_sql()中可以利用schema_links信息
if cached_schema_links:
    # 提取相关表信息传递给Scale模块
    relevant_tables = cached_schema_links.get('tables', [])
    relevant_columns = cached_schema_links.get('columns', [])
    
    # 构造额外的schema_links参数
    schema_links_str = f"Relevant Tables: {', '.join(relevant_tables)}\n"
    schema_links_str += f"Relevant Columns: {', '.join(relevant_columns[:20])}..."  # 只显示前20列
    
    final_sql = agent.scale_sql(
        question=question,
        schema=table_info,  # 使用cached_linked_schema
        qa_pairs=refined_qa_pairs,
        evidence=knowledge,
        schema_links=schema_links_str,  # 传递schema links信息
        ...
    )
```

---

## 调试技巧

### 查看缓存是否生效

在日志中搜索关键词:

```bash
# 缓存创建
grep "Schema linking cached" output/*/log.log

# 缓存使用
grep "Using cached schema" output/*/log.log
grep "Using cached links" output/*/log.log
```

### 验证缓存一致性

```python
# 在投票完成后,验证所有linked线程使用的是相同的schema
linked_schemas = []
for i in range(num_votes):
    log_file = f"linked_{i}_log.log"
    with open(os.path.join(search_directory, log_file), 'r') as f:
        content = f.read()
        if "[Table Info]" in content:
            start = content.find("[Table Info]")
            end = content.find("[Table Info]", start + 1)
            schema = content[start:end]
            linked_schemas.append(schema)

# 验证所有schema相同
assert all(s == linked_schemas[0] for s in linked_schemas), "Schema缓存不一致!"
print("✓ All linked schemas are identical (cache working correctly)")
```

---

## 总结

通过同时缓存`schema_links`和`linked_schema`两个结果:

✅ **性能**: 节省83%的Schema Linking调用成本  
✅ **一致性**: 确保投票模式下所有线程使用相同的Schema  
✅ **灵活性**: 提供结构化和文本两种格式,适应不同使用场景  
✅ **可观测**: 便于统计、分析和调试  

这是并行Schema Linking优化的重要组成部分!
