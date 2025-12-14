# 子问题迭代次数参数更新摘要

## 更新概述

新增`--sub_question_max_iter`参数，用于独立控制分解-合并流程中子问题SQL的迭代次数。

## 修改文件

### 1. `run_starrocks.py`
**位置**: 参数解析部分（第835行左右）

**修改内容**:
```python
# 新增参数
parser.add_argument('--sub_question_max_iter', type=int, default=3,
                   help="子问题的最大迭代次数（默认3，通常比主问题的max_iter更小）")

# 同时更新max_iter的help文本
parser.add_argument('--max_iter', type=int, default=5, help="主问题的最大迭代次数")
```

### 2. `agent.py`
**位置**: `process_sub_question_sql`方法

**修改内容**:
```python
# 在self-refinement部分添加
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

## 参数说明

| 参数名 | 类型 | 默认值 | 作用范围 | 说明 |
|--------|------|--------|----------|------|
| `--max_iter` | int | 5 | 主问题 | 常规流程或最终SQL的迭代次数 |
| `--sub_question_max_iter` | int | 3 | 子问题 | 分解流程中每个子问题的迭代次数 |

## 使用示例

### 基础用法
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 5 \
  --sub_question_max_iter 2
```

### 快速测试模式
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 3 \
  --sub_question_max_iter 1 \
  --max_questions 5
```

### 高精度模式
```bash
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --max_iter 8 \
  --sub_question_max_iter 5 \
  --do_column_exploration \
  --do_self_consistency
```

## 设计理念

### 为什么需要独立的迭代参数？

1. **效率优化**: 子问题通常比主问题简单，不需要太多迭代
2. **成本控制**: 减少不必要的API调用
3. **灵活性**: 允许用户根据不同场景调整迭代策略

### 默认值选择（3）

- 主问题默认5次，子问题默认3次
- 约60%的迭代比例
- 平衡了精度和效率

## 日志输出示例

启用该参数后，日志中会显示：

```
[Sub-SQL 1] Processing sub-question: 获取平均SAT优秀率
[Sub-SQL 1] Using sub_question_max_iter=2
[Sub-SQL 1] Applying self-refinement
itercount: 0
itercount: 1
Total iteration counts: 2
[Sub-SQL 1] Processing complete
```

## 向后兼容性

- **兼容**: 如果不设置`--sub_question_max_iter`，使用默认值3
- **无副作用**: 对不使用`--use_decompose`的场景无影响

## 性能影响

### 时间节省（估算）

假设一个复杂题目分解为3个子问题：

| 配置 | 主问题迭代 | 子问题迭代 | 总迭代次数 | 时间估算 |
|------|-----------|-----------|-----------|---------|
| **旧方式** | 5 | 5 | 3×5=15 | 基线 |
| **新方式(默认)** | 5 | 3 | 3×3=9 | -40% |
| **快速模式** | 5 | 1 | 3×1=3 | -80% |

## 测试建议

### 1. 验证参数生效
```bash
# 运行并检查日志
python run_starrocks.py \
  --use_decompose \
  --do_self_refinement \
  --sub_question_max_iter 2 \
  --max_questions 1

# 查看日志文件
cat output/starrocks-log/{sql_id}/decomposition/sub_1/log.log | grep "sub_question_max_iter"
```

### 2. 对比不同迭代次数的效果
```bash
# 配置A: 子问题迭代1次
python run_starrocks.py --sub_question_max_iter 1 --filter_complexity 中等 --max_questions 10

# 配置B: 子问题迭代3次（默认）
python run_starrocks.py --sub_question_max_iter 3 --filter_complexity 中等 --max_questions 10

# 配置C: 子问题迭代5次
python run_starrocks.py --sub_question_max_iter 5 --filter_complexity 中等 --max_questions 10

# 对比准确率和耗时
```

## 相关文档

- **详细指南**: `SUB_QUESTION_ITERATION_GUIDE.md`
- **分解-合并总指南**: `DECOMPOSE_SCALE_GUIDE.md`
- **实现总结**: `IMPLEMENTATION_SUMMARY.md`

## 注意事项

1. **最小值建议**: 建议至少设置为1，设置为0会导致跳过迭代
2. **与主问题的关系**: 通常设置为`max_iter`的50%-70%
3. **日志监控**: 通过日志观察实际迭代次数，及时调整参数

## 更新时间

- **日期**: 2025-11-26
- **版本**: v1.0
- **修改者**: AI Assistant
