# 分解-合并投票机制快速上手指南

## 🚀 快速开始

### 1. 最简配置（推荐用于测试）

```bash
python run_starrocks.py \
    --data_path ../dataset/test_dataset.json \
    --output_path ./output/test-decompose-vote \
    --do_vote \
    --use_decompose \
    --num_votes 3 \
    --model_vote \
    --generation_model gpt-4
```

### 2. 完整配置（推荐用于生产）

```bash
python run_starrocks.py \
    --data_path ../dataset/test_dataset.json \
    --output_path ./output/test-decompose-vote \
    --do_vote \
    --use_decompose \
    --num_votes 3 \
    --do_final_sql_refinement \
    --final_sql_max_iter 3 \
    --model_vote \
    --generation_model gpt-4 \
    --decompose_model gpt-4 \
    --scale_model gpt-4
```

---

## 📋 关键参数说明

| 参数 | 作用 | 推荐值 | 必需 |
|-----|------|--------|------|
| `--do_vote` | 启用投票模式 | - | ✅ |
| `--use_decompose` | 启用问题分解 | - | ✅ |
| `--num_votes` | 生成候选SQL数量 | 3 | ✅ |
| `--model_vote` | 启用LLM投票 | - | ⭐ 强烈推荐 |
| `--do_final_sql_refinement` | 对候选SQL进行refinement | - | 推荐 |
| `--final_sql_max_iter` | Refinement最大迭代次数 | 3 | 可选 |

---

## 📊 工作流程

```
1. 问题分解 → 2. 生成子SQL → 3. 合并为多个候选 → 4. 投票选择最佳 → 5. 生成result.sql
```

---

## 🎯 适用场景

### ✅ 适合使用分解-合并投票

- 中等或复杂的SQL问题（`complexity in ['中等', '复杂']`）
- 问题可以分解为多个子问题
- 需要高准确率，可以接受更长的生成时间

### ❌ 不适合使用

- 简单的单表查询
- 实时性要求高的场景
- 资源受限的环境（会调用更多LLM）

---

## 📁 输出结果

运行后会生成：

```
output/test-decompose-vote/sql_14/
├── decomposition/              # 分解结果
│   ├── sub_1/result.sql
│   └── sub_2/result.sql
├── decompose_0_result.sql      # 候选1
├── decompose_1_result.sql      # 候选2
├── decompose_2_result.sql      # 候选3
├── result.sql                  # ✅ 最终结果（投票选出）
└── result.csv                  # ✅ 最终结果数据
```

---

## 🐛 故障排查

### 问题：没有生成 result.sql

**可能原因1**: 所有候选SQL执行失败
```bash
# 解决：检查日志中的错误信息
cat output/test-decompose-vote/sql_14/log.log
```

**可能原因2**: 所有候选结果都不同，且未启用model_vote
```bash
# 解决：添加 --model_vote 参数
--model_vote
```

### 问题：投票选择了错误的SQL

**可能原因**: 多个错误SQL生成了相同的错误结果

```bash
# 解决：启用LLM投票进行二次验证
--model_vote --model_vote gpt-4
```

---

## ✅ 验证投票机制

运行验证脚本确认投票机制已正确实现：

```bash
cd e:\Project\track3_2\ReFoRCE\methods\ReFoRCE
python verify_decompose_vote.py
```

预期输出：
```
✅ 所有检查通过！分解-合并流程的投票机制已正确实现
```

---

## 📚 更多信息

- 详细实现文档：[DECOMPOSE_VOTE_IMPLEMENTATION.md](DECOMPOSE_VOTE_IMPLEMENTATION.md)
- 投票逻辑测试：`python test_decompose_vote_logic.py`
- 代码实现：`run_starrocks.py` (第272-340行)

---

**最后更新**: 2025-11-26
