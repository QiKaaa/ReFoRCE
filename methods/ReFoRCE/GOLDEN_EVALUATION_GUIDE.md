# 金标准SQL评估功能指南

## 📋 功能说明

本功能为 `final_dataset_example.json` 中标注了 `golden_sql: true` 的题目提供自动评估功能，对比生成的SQL结果与金标准SQL结果是否一致。

---

## 🎯 功能特点

1. ✅ **自动识别**: 自动识别数据集中 `golden_sql: true` 的题目
2. ✅ **自动执行**: 自动执行金标准SQL并保存结果
3. ✅ **智能对比**: 对比生成结果与金标准结果（忽略行顺序）
4. ✅ **详细报告**: 为每个题目生成详细评估报告
5. ✅ **总结统计**: 生成整体评估总结报告，包含准确率统计

---

## 🚀 使用方法

### 1. 基础使用

```bash
python run_starrocks.py \
  --enable_golden_evaluation \
  --generation_model gpt-4o \
  --do_self_refinement
```

### 2. 只评估金标准题目

```bash
# 使用max_questions限制处理前几个题目
python run_starrocks.py \
  --enable_golden_evaluation \
  --max_questions 10 \
  --generation_model gpt-4o
```

### 3. 结合Schema Linking评估

```bash
python run_starrocks.py \
  --enable_golden_evaluation \
  --use_schema_linking \
  --generation_model gpt-4o \
  --do_self_refinement
```

### 4. 投票模式 + 评估

```bash
python run_starrocks.py \
  --enable_golden_evaluation \
  --do_vote \
  --num_votes 3 \
  --generation_model gpt-4o
```

---

## 📊 输出文件

### 每个题目的评估报告

```
output/
└── sql_30/
    ├── result.sql              ← 生成的SQL
    ├── result.csv              ← 生成的结果
    ├── golden.sql              ← 金标准SQL
    ├── golden_result.csv       ← 金标准结果
    └── evaluation_report.txt   ← 评估报告 ⭐
```

**evaluation_report.txt** 示例:
```
Golden SQL Evaluation Report
============================================================

SQL ID: sql_30
Evaluation Time: 2025-01-18 14:30:00

Golden Result:
  Rows: 150
  Columns: 4
  Column Names: ['月份', '主玩玩法', '主玩人数', '总参与人数']

Generated Result:
  Rows: 150
  Columns: 4
  Column Names: ['月份', '主玩玩法', '主玩人数', '总参与人数']

Comparison:
  Shape Match: ✅ Yes
  Content Match (ignore order): ✅ Yes

🎉 Result: PASS - Results are identical!
```

### 总结报告

```
output/
└── golden_evaluation_summary.txt  ← 总结报告 ⭐
```

**golden_evaluation_summary.txt** 示例:
```
Golden SQL Evaluation Summary
============================================================

Generated: 2025-01-18 14:35:00

Total Golden SQL Questions: 15
Evaluated: 15
Not Evaluated: 0

Results Breakdown:
  ✅ PASS (Identical):   12 (80.0% of evaluated)
  ⚠️  PARTIAL (Shape OK): 2 (13.3% of evaluated)
  ❌ FAIL (Different):   1 (6.7% of evaluated)

Accuracy (PASS only): 80.00%

PASSED Questions (12):
  ✅ sql_28
  ✅ sql_29
  ✅ sql_30
  ...

PARTIAL Questions (2):
  ⚠️  sql_31
  ⚠️  sql_35

FAILED Questions (1):
  ❌ sql_40
```

---

## 📈 评估标准

### ✅ PASS (通过)
- 行数相同
- 列数相同
- 列名相同
- 数据内容完全一致（忽略行顺序）

### ⚠️ PARTIAL (部分通过)
- 行数和列数相同
- 列名相同
- 但数据内容有差异

### ❌ FAIL (失败)
- 行数或列数不同
- 列名不同
- 结构完全不同

---

## 🔧 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--enable_golden_evaluation` | 启用金标准SQL评估 | False |
| `--max_questions` | 限制处理的题目数（测试用） | None |
| `--generation_model` | SQL生成模型 | gpt-4o |

---

## 💡 使用场景

### 场景1: 开发调试
```bash
# 快速测试前3个金标准题目
python run_starrocks.py \
  --enable_golden_evaluation \
  --max_questions 3 \
  --num_workers 1
```

### 场景2: 评估新方法
```bash
# 评估Schema Linking的效果
python run_starrocks.py \
  --enable_golden_evaluation \
  --use_schema_linking \
  --do_self_refinement
```

### 场景3: 完整评估
```bash
# 处理所有题目并评估
python run_starrocks.py \
  --enable_golden_evaluation \
  --do_vote \
  --num_votes 3 \
  --generation_model gpt-4o \
  --num_workers 4
```

---

## 🐛 常见问题

### Q: 为什么有些题目没有评估报告?

A: 可能原因:
1. 该题目不是金标准题目（`golden_sql != true`）
2. SQL生成失败，没有 `result.csv`
3. 金标准SQL执行失败

### Q: PARTIAL 和 FAIL 的区别?

A: 
- **PARTIAL**: 结构正确但数据有差异（可能是计算精度、排序等问题）
- **FAIL**: 结构完全不同（列数/行数/列名不匹配）

### Q: 如何只评估特定题目?

A: 使用 `--max_questions` 限制处理前N个题目，或修改数据集JSON文件。

---

## 📝 注意事项

1. ⚠️ **数据库连接**: 确保StarRocks数据库正在运行
2. ⚠️ **金标准SQL**: 确保数据集中的SQL语法正确
3. ⚠️ **执行时间**: 金标准SQL可能执行较慢，请耐心等待
4. ⚠️ **内存占用**: 大结果集可能占用较多内存

---

## 🎉 快速开始

运行测试脚本:
```bash
# Windows
test_golden_evaluation.bat

# Linux/Mac
chmod +x test_golden_evaluation.sh
./test_golden_evaluation.sh
```

查看评估结果:
```bash
cat output/golden_test/golden_evaluation_summary.txt
```

---

**祝你使用愉快！🚀**
