# 子问题迭代参数 - 快速参考

## 🎯 核心参数

```bash
--sub_question_max_iter <数字>
```

**作用**: 控制分解流程中每个子问题的SQL迭代优化次数  
**默认值**: `3`  
**适用场景**: 启用 `--use_decompose` 时

---

## 📋 快速配置表

| 场景 | 命令 |
|------|------|
| **快速测试** | `--sub_question_max_iter 1` |
| **日常开发** | `--sub_question_max_iter 2` 或 `--sub_question_max_iter 3` (默认) |
| **高精度** | `--sub_question_max_iter 5` |

---

## 🔧 常用组合

### 1. 快速测试模式
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 3 \
  --sub_question_max_iter 1 \
  --max_questions 5
```

### 2. 平衡模式（推荐）
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --do_column_exploration \
  --max_iter 5 \
  --sub_question_max_iter 3
```

### 3. 高精度模式
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --do_column_exploration \
  --do_self_consistency \
  --max_iter 8 \
  --sub_question_max_iter 5
```

---

## 📊 参数对比

| 参数 | 主问题 | 子问题 |
|------|--------|--------|
| 参数名 | `--max_iter` | `--sub_question_max_iter` |
| 默认值 | 5 | 3 |
| 推荐范围 | 3-10 | 1-5 |

---

## ⚡ 性能对比

**假设**: 1个主问题分解为3个子问题

| 配置 | 子问题迭代 | 总迭代 | 时间节省 |
|------|-----------|--------|---------|
| 旧方式 | 5 | 15次 | 基线 |
| 默认 | 3 | 9次 | ⚡ 40% |
| 快速 | 1 | 3次 | ⚡⚡ 80% |

---

## 🎓 设置建议

### 按题目复杂度

```bash
# 中等复杂度
--max_iter 5 --sub_question_max_iter 2

# 高复杂度
--max_iter 6 --sub_question_max_iter 3
```

### 按时间预算

```bash
# 时间充足
--max_iter 8 --sub_question_max_iter 5

# 时间受限
--max_iter 3 --sub_question_max_iter 1
```

---

## 📝 日志检查

查看子问题实际迭代次数：

```bash
# 查看子问题日志
cat output/starrocks-log/{sql_id}/decomposition/sub_1/log.log | grep "itercount"

# 输出示例：
# [Sub-SQL 1] Using sub_question_max_iter=3
# itercount: 0
# itercount: 1
# itercount: 2
# Total iteration counts: 3
```

---

## ⚠️ 注意事项

1. ✅ 建议子问题迭代 = 主问题迭代 × 50%-70%
2. ✅ 最小值建议设为 1（不要设为0）
3. ✅ 观察日志，如果经常达到上限可增加数值
4. ❌ 不启用 `--use_decompose` 时此参数无效

---

## 🔍 调试命令

### 测试单个题目
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --sub_question_max_iter 2 \
  --max_questions 1 \
  --filter_complexity 复杂
```

### 对比不同配置
```bash
# 配置A
python run_starrocks.py --sub_question_max_iter 1 --output_path output/test_iter1

# 配置B
python run_starrocks.py --sub_question_max_iter 3 --output_path output/test_iter3

# 配置C
python run_starrocks.py --sub_question_max_iter 5 --output_path output/test_iter5
```

---

## 📚 完整文档

- 详细指南: `SUB_QUESTION_ITERATION_GUIDE.md`
- 更新摘要: `SUB_QUESTION_ITERATION_UPDATE.md`
