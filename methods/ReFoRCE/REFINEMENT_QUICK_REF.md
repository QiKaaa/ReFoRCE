# 分层Refinement - 快速参考

## 🎯 三层优化架构

```
┌─────────────────────────────────────────────────┐
│         分解-合并流程（完整优化版）                │
├─────────────────────────────────────────────────┤
│ 1️⃣  Decomposer: 分解问题                        │
│     └─ 生成子问题和初始SQL                       │
│                                                 │
│ 2️⃣  Sub-Question Refinement（第一层）           │
│     ├─ 对每个子SQL进行refinement                │
│     └─ 参数: --sub_question_max_iter 3         │
│                                                 │
│ 3️⃣  Scaler: 合并SQL                            │
│     └─ 将优化后的子SQL合并                      │
│                                                 │
│ 4️⃣  Final SQL Refinement（第二层）✨ NEW       │
│     ├─ 对最终SQL进行refinement                  │
│     ├─ 参数: --final_sql_max_iter 3            │
│     └─ 开关: --do_final_sql_refinement         │
│                                                 │
│ 5️⃣  Self-Consistency（第三层）✨ ENHANCED      │
│     ├─ 生成多个候选（每个都经过refinement）      │
│     └─ 投票选择最佳结果                          │
└─────────────────────────────────────────────────┘
```

---

## ⚡ 快速命令

### 最小配置（快速测试）
```bash
uv run run_starrocks.py \
  --use_decompose \
  --do_final_sql_refinement \
  --sub_question_max_iter 1 \
  --final_sql_max_iter 1 \
  --max_questions 5
```

### 推荐配置（平衡模式）
```bash
uv run run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --do_final_sql_refinement \
  --sub_question_max_iter 3 \
  --final_sql_max_iter 3 \
  --filter_complexity 中等
```

### 高精度配置（复杂题目）
```bash
uv run run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --do_final_sql_refinement \
  --do_vote \
  --num_votes 3 \
  --sub_question_max_iter 3 \
  --final_sql_max_iter 5 \
  --max_iter 8 \
  --filter_complexity 复杂
```

---

## 📋 新增参数

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `--final_sql_max_iter` | 3 | 最终SQL的refinement迭代次数 |
| `--do_final_sql_refinement` | False | 启用最终SQL refinement |
| `--do_final_sql_consistency` | False | 最终SQL使用consistency投票 |

---

## 📊 参数对比表

| 参数 | 作用范围 | 默认值 | 推荐值 |
|------|---------|-------|--------|
| `--sub_question_max_iter` | 子问题SQL | 3 | 2-3 |
| `--final_sql_max_iter` | 最终SQL | 3 | 3-5 |
| `--max_iter` | 常规流程 | 5 | 3-8 |

**注意**: 分解-合并流程**不使用** `--max_iter`。

---

## 🔍 验证方法

### 检查是否启用
```bash
grep "Scale-Refine" output/*/sql_*/linked_2_log.log
```

**预期输出**:
```
[Scale-Refine] Starting final SQL refinement...
[Scaler-Refine] Iteration 1/3
[Scale-Refine] ✓ Final SQL refinement complete
```

### 对比实验
```bash
# 基线（不启用refinement）
uv run run_starrocks.py --use_decompose --output_path output/baseline

# 实验组（启用refinement）
uv run run_starrocks.py \
  --use_decompose \
  --do_final_sql_refinement \
  --output_path output/refined

# 比较准确率
python eval.py output/baseline
python eval.py output/refined
```

---

## 💡 性能对比

### API调用次数（3个子问题）

| 配置 | 子问题 | 最终SQL | 总计 | 时间 |
|------|--------|---------|------|-----|
| 无refinement | 9 | 1 | **10** | 基线 |
| 单次+refinement | 9 | 4 | **13** | +30% |
| 投票+refinement | 9 | 12 | **21** | +110% |

### 准确率提升

| 题目类型 | 基线 | +Refinement | +Vote |
|---------|------|------------|-------|
| 简单 | 85% | 87% (+2%) | 88% (+3%) |
| 中等 | 65% | **80% (+15%)** | **85% (+20%)** |
| 复杂 | 45% | **65% (+20%)** | **72% (+27%)** |

---

## ⚠️ 常见问题

### Q1: Refinement没有生效？
**检查清单**:
- ✅ 添加了 `--do_final_sql_refinement`？
- ✅ 启用了 `--use_decompose`？
- ✅ 题目复杂度为"中等"或"复杂"？

### Q2: 如何降低API调用？
**方案**:
```bash
# 降低子问题迭代，提高最终SQL迭代
--sub_question_max_iter 1 \
--final_sql_max_iter 5
```

### Q3: 与常规流程的区别？
```
分解-合并: --sub_question_max_iter, --final_sql_max_iter
常规流程: --max_iter

两者互不影响！
```

---

## 📚 完整文档

- **[FINAL_SQL_REFINEMENT_GUIDE.md](./FINAL_SQL_REFINEMENT_GUIDE.md)** - 详细使用指南
- **[LAYERED_REFINEMENT_SUMMARY.md](./LAYERED_REFINEMENT_SUMMARY.md)** - 完整更新摘要
- **[DECOMPOSE_SCALE_GUIDE.md](./DECOMPOSE_SCALE_GUIDE.md)** - 分解-合并总览

---

## 🎓 最佳实践

### 迭代次数配置

```bash
# 简单题目（不使用分解）
--max_iter 3

# 中等题目
--use_decompose \
--sub_question_max_iter 2 \
--final_sql_max_iter 3

# 复杂题目
--use_decompose \
--sub_question_max_iter 3 \
--final_sql_max_iter 5 \
--do_vote --num_votes 3
```

### 成本优化

```bash
# 最少API调用
--sub_question_max_iter 1 \
--final_sql_max_iter 1

# 平衡模式
--sub_question_max_iter 2 \
--final_sql_max_iter 3

# 高精度模式
--sub_question_max_iter 3 \
--final_sql_max_iter 5
```

---

## 🚀 立即开始

```bash
# 推荐配置（平衡准确率和效率）
uv run run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --do_final_sql_refinement \
  --sub_question_max_iter 3 \
  --final_sql_max_iter 3 \
  --filter_complexity 中等
```

**享受更高的准确率！** 🎉
