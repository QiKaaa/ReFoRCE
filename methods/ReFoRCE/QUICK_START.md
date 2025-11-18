# Schema Linking 快速开始指南

## 🚀 5分钟上手

### 1️⃣ 测试单个问题

```bash
cd e:/Project/track3_2/ReFoRCE/methods/ReFoRCE

python run_starrocks.py \
  --use_schema_linking \
  --max_questions 1 \
  --generation_model gpt-4o \
  --azure
```

**预期输出**:
```
Loading dataset...
Loading schema...
Initializing Schema Linker...
  ✓ Schema Linker ready with 84 tables

Processing: sql_1
  🔮 LLM Schema Linking 响应: (一次性分析所有相关表)
  [Schema Linking] Optimized schema generated with 19 columns
  ✓ sql_1 completed in 1 min

✓ 所有问题处理完成！
```

---

### 2️⃣ 使用投票模式 (推荐)

```bash
python run_starrocks.py \
  --do_vote \
  --do_schema_linking_vote \
  --num_votes 3 \
  --max_questions 5 \
  --generation_model gpt-4o \
  --azure
```

**说明**: 
- 每个问题生成 6 个 SQL (3个原始 + 3个linked)
- 投票选择最优结果

---

### 3️⃣ 批量处理

```bash
python run_starrocks.py \
  --do_schema_linking_vote \
  --do_vote \
  --num_votes 3 \
  --num_workers 8 \
  --generation_model gpt-4o \
  --azure
```

**说明**: 使用 8 个并行 worker 处理所有问题

---

## 📋 核心参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--use_schema_linking` | 直接使用 SL | False |
| `--do_schema_linking_vote` | SL 投票模式 | False |
| `--num_votes` | 投票次数 | 3 |
| `--max_questions` | 限制问题数 | None |
| `--num_workers` | 并行数 | 4 |

---

## 🎯 三种模式对比

| 模式 | 命令 | 优势 | 劣势 |
|------|------|------|------|
| **SL 单独** | `--use_schema_linking` | 快速,省钱,一次LLM调用 | 准确率可能略低 |
| **SL 投票** ⭐ | `--do_schema_linking_vote --do_vote` | 准确率高,双路径验证 | 成本略高 |
| **原始** | (无参数) | 基线 | Token 多 |

---

## 📊 输出查看

### 检查结果

```bash
# 查看生成的 SQL
cat output/starrocks-log/sql_1/result.sql

# 查看日志 (Schema Linking 部分)
cat output/starrocks-log/sql_1/log.log | grep "Schema Linking" -A 5

# 对比原始和 Linked Schema
cat output/starrocks-log/sql_1/original_0_log.log | grep "Table Info" -A 20
cat output/starrocks-log/sql_1/linked_0_log.log | grep "Table Info" -A 20
```

### 投票模式输出结构

```
sql_1/
├── original_0_result.sql    ┐
├── original_1_result.sql    ├─ 原始 Schema
├── original_2_result.sql    ┘
├── linked_0_result.sql      ┐
├── linked_1_result.sql      ├─ Linked Schema
├── linked_2_result.sql      ┘
├── result.sql              ← 最终结果 ⭐
├── result.csv
└── vote.log                ← 投票日志
```

---

## 💡 常用命令

### 测试脚本

```bash
# Windows
test_schema_linking_integration.bat

# Linux/Mac
./test_schema_linking_integration.sh
```

### 手动对比

```bash
# 1. 运行原始方法
python run_starrocks.py --output_path output/original --max_questions 1

# 2. 运行 Schema Linking
python run_starrocks.py --use_schema_linking --output_path output/linked --max_questions 1

# 3. 对比结果
diff output/original/sql_1/result.sql output/linked/sql_1/result.sql
```

---

## 🐛 常见问题

### Q: 如何查看 Schema Linking 工作流程?

```bash
# 查看LLM分析日志
grep "🔮 LLM Schema Linking" output/starrocks-log/sql_1/log.log -A 50

# 查看选择的列统计
grep "Optimized schema generated" output/starrocks-log/sql_1/log.log
```

输出示例: 
```
🔮 LLM Schema Linking 响应:
```json
{
  "think": "需要用户信息表的ID和时间字段...",
  "tables": {
    "user_table": ["(user_id: BIGINT, ...)"],
    "order_table": ["(order_id: BIGINT, ...)"]
  }
}
```
[Schema Linking] Optimized schema generated with 19 columns
```

---

### Q: Schema Linking 是逐表还是批量处理?

**答**: 现在是**一次性处理所有相关表** (优化后)
- ✅ **更高效**: 从N次LLM调用降至1次
- ✅ **更准确**: LLM可同时看到所有表,理解JOIN关系
- ✅ **更省钱**: 减少API调用次数

---

### Q: 如何查看 Schema 压缩效果?

```bash
grep "Optimized schema generated" output/starrocks-log/sql_1/log.log
```

---

### Q: 投票模式生成了多少个 SQL?

```bash
ls output/starrocks-log/sql_1/*.sql | wc -l
```

输出: `7` (6个候选 + 1个最终结果)

---

### Q: 如何调整 Schema Linking 行为?

**现在不需要调整参数** - LLM会一次性分析所有表并智能选择列。

如果需要调试，可查看 `schema_linking_optimized.py` 中的 `SCHEMA_LINKING_PROMPT`。

关键优势:
- 自动考虑表关系
- 保留JOIN所需列
- 保留ID和时间字段

---

## 📚 更多信息

- **完整文档**: `SCHEMA_LINKING_INTEGRATION.md`
- **实现细节**: `INTEGRATION_SUMMARY.md`
- **原理说明**: `SCHEMA_LINKING_GUIDE.md`

---

## 🎁 推荐配置

### 快速测试

```bash
python run_starrocks.py \
  --use_schema_linking \
  --max_questions 10 \
  --generation_model gpt-4o-mini
```

### 生产环境

```bash
python run_starrocks.py \
  --do_vote \
  --do_schema_linking_vote \
  --num_votes 3 \
  --num_workers 8 \
  --generation_model gpt-4o \
  --azure
```

### 最高准确率

```bash
python run_starrocks.py \
  --do_column_exploration \
  --do_vote \
  --do_schema_linking_vote \
  --num_votes 5 \
  --generation_model gpt-4o \
  --azure
```

---

**开始使用吧! 🚀**
