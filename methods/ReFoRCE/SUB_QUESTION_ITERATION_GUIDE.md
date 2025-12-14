# 子问题迭代次数控制指南

## 新增参数说明

### `--sub_question_max_iter`

**功能**: 控制分解-合并流程中子问题SQL的最大迭代次数

**默认值**: 3

**用途**: 
- 在启用`--use_decompose`时，对中等/困难题目进行问题分解后，每个子问题的SQL会经过self-refinement优化
- 子问题通常比主问题简单，因此可以使用更少的迭代次数，提高处理效率
- 独立于主问题的`--max_iter`参数

## 使用示例

### 示例1: 基础用法
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 5 \
  --sub_question_max_iter 2 \
  --filter_complexity 复杂
```

**说明**:
- 主问题迭代5次 (`--max_iter 5`)
- 子问题迭代2次 (`--sub_question_max_iter 2`)
- 只处理复杂题目

### 示例2: 高精度模式（更多迭代）
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 8 \
  --sub_question_max_iter 5 \
  --do_column_exploration \
  --filter_complexity 复杂
```

**说明**:
- 适用于需要高精度的场景
- 子问题也进行较多迭代（5次）

### 示例3: 快速测试模式（减少迭代）
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 3 \
  --sub_question_max_iter 1 \
  --max_questions 5
```

**说明**:
- 适用于快速测试
- 子问题只迭代1次
- 只处理前5个问题

### 示例4: 不设置子问题迭代（使用默认值）
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 5
```

**说明**:
- 如果不指定`--sub_question_max_iter`，将使用默认值3
- 主问题迭代5次

## 参数关系说明

| 参数 | 作用范围 | 默认值 | 说明 |
|------|---------|--------|------|
| `--max_iter` | 主问题 | 5 | 常规流程或最终SQL生成的迭代次数 |
| `--sub_question_max_iter` | 子问题 | 3 | 分解流程中每个子问题的迭代次数 |

## 设置建议

### 根据题目复杂度

| 复杂度 | 主问题迭代 | 子问题迭代 | 理由 |
|--------|-----------|-----------|------|
| 简单 | 3-5 | N/A | 简单题目不使用分解 |
| 中等 | 5-6 | 2-3 | 子问题相对简单 |
| 复杂 | 6-8 | 3-5 | 子问题可能也较复杂 |

### 根据使用场景

| 场景 | 主问题迭代 | 子问题迭代 | 总耗时估计 |
|------|-----------|-----------|-----------|
| **快速测试** | 2-3 | 1 | 低 |
| **常规开发** | 5 | 2-3 | 中 |
| **高精度生产** | 7-10 | 4-5 | 高 |
| **时间受限** | 3-4 | 1-2 | 低-中 |

## 工作流程示意

```
主问题 (复杂度: 复杂)
  ↓
[分解] → 子问题1, 子问题2, 子问题3
  ↓
[处理子问题1] → Self-Refinement (迭代 sub_question_max_iter 次)
[处理子问题2] → Self-Refinement (迭代 sub_question_max_iter 次)
[处理子问题3] → Self-Refinement (迭代 sub_question_max_iter 次)
  ↓
[合并] → 最终SQL
  ↓
[可选: 主问题Refinement] → (如果启用常规流程，迭代 max_iter 次)
```

## 性能优化建议

### 1. 平衡精度与效率
```bash
# 推荐配置（平衡模式）
--max_iter 5 \
--sub_question_max_iter 3
```

### 2. 极速模式（牺牲精度）
```bash
# 快速模式
--max_iter 3 \
--sub_question_max_iter 1 \
--early_stop
```

### 3. 高精度模式（牺牲速度）
```bash
# 高精度模式
--max_iter 10 \
--sub_question_max_iter 5 \
--do_self_consistency
```

## 调试技巧

### 查看子问题迭代日志
每个子问题的处理日志保存在:
```
output/starrocks-log/{sql_id}/decomposition/sub_{sub_id}/log.log
```

日志中会显示实际迭代次数:
```
[Sub-SQL 1] Using sub_question_max_iter=3
[Sub-SQL 1] Applying self-refinement
itercount: 0
itercount: 1
itercount: 2
Total iteration counts: 3
```

### 监控迭代效率
观察日志中的`itercount`，如果经常达到`max_iter`但结果仍不理想，考虑:
1. 增加`sub_question_max_iter`
2. 或检查子问题分解质量

## 常见问题

### Q1: 子问题和主问题能使用相同的迭代次数吗？
**A**: 可以，但通常不推荐。子问题一般更简单，使用更少的迭代次数可以节省时间。

```bash
# 可以这样设置（但可能浪费计算资源）
--max_iter 5 --sub_question_max_iter 5
```

### Q2: 如果不启用`--use_decompose`，`--sub_question_max_iter`会生效吗？
**A**: 不会。这个参数仅在分解-合并流程中使用。

### Q3: 子问题迭代太少会影响最终结果吗？
**A**: 可能会。建议至少设置为2-3次，以确保子问题SQL的质量。

### Q4: 如何确定最佳的迭代次数？
**A**: 
1. 从默认值开始（主问题5，子问题3）
2. 观察日志中的迭代轨迹
3. 如果经常在早期就成功，可以减少迭代次数
4. 如果经常达到上限但未成功，可以增加迭代次数

## 完整示例命令

### 生产环境推荐配置
```bash
python run_starrocks.py \
  --dataset_path E:/Project/track3_2/final_for_student/data/final_dataset_example.json \
  --schema_path E:/Project/track3_2/M-schema/final_algorithm_competition.txt \
  --output_path output/starrocks-log \
  --generation_model deepseek-chat \
  --column_exploration_model deepseek-chat \
  --decompose_model deepseek-chat \
  --scale_model deepseek-chat \
  --use_decompose \
  --do_column_exploration \
  --do_self_refinement \
  --do_self_consistency \
  --max_iter 6 \
  --sub_question_max_iter 3 \
  --early_stop \
  --num_workers 5 \
  --filter_complexity 复杂
```

## 实现细节

### 代码位置
- **参数定义**: `run_starrocks.py` 第835行左右
- **参数使用**: `agent.py` 的 `process_sub_question_sql` 方法

### 核心逻辑
```python
# agent.py - process_sub_question_sql方法
import copy
sub_args = copy.copy(args)

# 使用独立的迭代次数
if hasattr(args, 'sub_question_max_iter') and args.sub_question_max_iter is not None:
    sub_args.max_iter = args.sub_question_max_iter
    logger.info(f"[Sub-SQL {sub_id}] Using sub_question_max_iter={args.sub_question_max_iter}")
else:
    logger.info(f"[Sub-SQL {sub_id}] Using default max_iter={args.max_iter}")

# 调用self_refine时使用sub_args
self.self_refine(args=sub_args, ...)
```

## 更新日志

- **2025-11-26**: 新增`--sub_question_max_iter`参数，支持独立控制子问题迭代次数
