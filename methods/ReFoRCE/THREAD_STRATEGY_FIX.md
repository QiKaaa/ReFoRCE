# 线程策略修复报告

## 问题描述

### 原始问题
观察 `linked_7_log.log` 发现，单个线程内部生成了3个候选SQL：
```
2025-11-27 02:41:39 - Thread-19 (execute_single_question) - INFO - [Scaler] Generated 3 unique SQL candidates
```

这违背了"一个线程一个SQL"的设计原则，导致：
1. **重复生成**：每个线程都生成3个SQL，导致资源浪费
2. **投票混乱**：线程内部试图进行投票，但应该在所有线程完成后统一投票
3. **文件命名冲突**：多个候选使用相同的前缀，导致覆盖

### 原始流程（错误）
```
启动3个线程（linked_0, linked_1, linked_2）
  ↓
每个线程调用 generate_multiple_sql_candidates(num_candidates=3)
  ↓
每个线程内部生成3个SQL候选
  ↓
每个线程尝试内部投票（但被移除了）
  ↓
总共生成 3×3 = 9 个SQL候选 ❌
```

---

## 解决方案

### 核心修改

**修改文件**: `run_starrocks.py` (第271-347行)

**设计原则**：
1. ✅ **一个线程一个SQL**：每个线程只生成1个SQL候选
2. ✅ **策略差异化**：根据线程编号选择不同策略（每3个中有1个使用fallback）
3. ✅ **自我精化**：生成后对SQL进行self-refinement优化
4. ✅ **统一投票**：所有线程完成后在外层统一投票

### 修改后流程（正确）
```
启动3个线程（linked_0, linked_1, linked_2）
  ↓
linked_0: scale_sql(use_fallback=False) → refine_final_sql() → decompose_linked_0_result.sql
linked_1: scale_sql(use_fallback=False) → refine_final_sql() → decompose_linked_1_result.sql
linked_2: scale_sql(use_fallback=True)  → refine_final_sql() → decompose_linked_2_result.sql ⭐
  ↓
等待所有线程完成
  ↓
统一收集所有 *_result.sql 文件并投票
  ↓
生成最终 result.sql ✅
```

---

## 代码对比

### 修改前（错误）
```python
# 每个线程生成多个候选
if args.do_vote and args.use_decompose:
    final_sqls = agent.generate_multiple_sql_candidates(
        question=question,
        schema=table_info,
        qa_pairs=refined_qa_pairs,
        num_candidates=args.num_votes,  # 生成3个 ❌
        chat_session=chat_session_scale,
        logger=logger
    )
    
    # 对每个候选进行处理
    for i, final_sql in enumerate(final_sqls):
        vote_csv_path = os.path.join(search_directory, f"{file_prefix}_{i}_result.csv")
        vote_sql_path = os.path.join(search_directory, f"{file_prefix}_{i}_result.sql")
        # ... refinement ...
    
    # 尝试在线程内部投票 ❌
    agent_format_temp.vote_result(...)
```

### 修改后（正确）
```python
# 每个线程只生成1个候选
if args.do_vote and args.use_decompose:
    # 1. 根据线程编号决定策略
    thread_index = 0
    if thread_prefix:
        parts = thread_prefix.split('_')
        if len(parts) > 1 and parts[1].isdigit():
            thread_index = int(parts[1])
    
    # 每3个线程中有1个使用fallback
    use_fallback = (thread_index % 3 == 2)
    
    logger.info(f"[Scale] Thread {thread_prefix}: Using {'fallback' if use_fallback else 'normal'} strategy")
    
    # 2. 生成单个SQL候选
    final_sql = agent.scale_sql(
        question=question,
        schema=table_info,
        qa_pairs=refined_qa_pairs,
        use_fallback=use_fallback,  # 根据线程策略 ✅
        chat_session=chat_session_scale,
        logger=logger
    )
    
    # 3. 确定文件前缀
    if thread_prefix:
        prefix_parts = thread_prefix.split('_')
        if prefix_parts[0] in ['linked', 'original']:
            file_prefix = f"decompose_{thread_prefix}"  # decompose_linked_0 ✅
    
    # 4. 保存文件路径
    vote_csv_path = os.path.join(search_directory, f"{file_prefix}_result.csv")
    vote_sql_path = os.path.join(search_directory, f"{file_prefix}_result.sql")
    
    # 5. 对生成的SQL进行self-refinement
    final_sql = agent.refine_final_sql(
        initial_sql=final_sql,
        question=question,
        schema=table_info,
        max_iter=args.final_sql_max_iter if hasattr(args, 'final_sql_max_iter') else 3,
        sql_id=f"{sql_id}_{thread_prefix}",
        csv_save_path=vote_csv_path,
        sql_save_path=vote_sql_path,
        chat_session=chat_session_scale,
        logger=logger
    )
    
    # 6. 不在线程内部投票，等待外层统一投票 ✅
    logger.info(f"[Decompose-Vote] Generated 1 candidate with prefix '{file_prefix}'")
```

---

## 策略分配规则

### Fallback策略使用规则
```python
use_fallback = (thread_index % 3 == 2)
```

### 策略分配表
| Thread Prefix | Thread Index | Use Fallback | Strategy  | File Name                    |
|---------------|--------------|--------------|-----------|------------------------------|
| `linked_0`    | 0            | False        | Normal    | `decompose_linked_0_result.sql` |
| `linked_1`    | 1            | False        | Normal    | `decompose_linked_1_result.sql` |
| `linked_2`    | 2            | **True**     | **Fallback** | `decompose_linked_2_result.sql` ⭐ |
| `linked_3`    | 3            | False        | Normal    | `decompose_linked_3_result.sql` |
| `linked_4`    | 4            | False        | Normal    | `decompose_linked_4_result.sql` |
| `linked_5`    | 5            | **True**     | **Fallback** | `decompose_linked_5_result.sql` ⭐ |
| `original_0`  | 0            | False        | Normal    | `decompose_original_0_result.sql` |
| `original_1`  | 1            | False        | Normal    | `decompose_original_1_result.sql` |
| `original_2`  | 2            | **True**     | **Fallback** | `decompose_original_2_result.sql` ⭐ |

---

## 验证测试

### 测试脚本
运行 `test_thread_strategy.py` 验证：
```bash
cd e:\Project\track3_2\ReFoRCE\methods\ReFoRCE
python test_thread_strategy.py
```

### 测试结果
```
============================================================
测试: 线程策略选择
============================================================

线程策略分配:
Thread Prefix        Index    Fallback   Strategy
------------------------------------------------------------
✓ linked_0             0        False      normal
✓ linked_1             1        False      normal
✓ linked_2             2        True       fallback  ⭐
✓ linked_3             3        False      normal
✓ linked_4             4        False      normal
✓ linked_5             5        True       fallback  ⭐
✓ original_0           0        False      normal
✓ original_1           1        False      normal
✓ original_2           2        True       fallback  ⭐

✓ 策略选择验证完成
```

---

## 期望效果

### 运行时输出（每个线程）
```
[Scale] Thread linked_0: Using normal strategy
[Scale] SQL candidate generated and refined successfully
[Decompose-Vote] Generated 1 candidate with prefix 'decompose_linked_0'
```

```
[Scale] Thread linked_2: Using fallback strategy  ⭐
[Scale] SQL candidate generated and refined successfully
[Decompose-Vote] Generated 1 candidate with prefix 'decompose_linked_2'
```

### 生成的文件
```
output/test-sl-vote/sql_1/
├── decompose_linked_0_result.sql   (Normal策略)
├── decompose_linked_0_result.csv
├── decompose_linked_1_result.sql   (Normal策略)
├── decompose_linked_1_result.csv
├── decompose_linked_2_result.sql   (Fallback策略) ⭐
├── decompose_linked_2_result.csv
└── result.sql                      (投票后的最终结果)
```

### 外层统一投票
```
✓ 收集到 3 个候选SQL文件，开始统一投票...
  • decompose_linked_0_result.sql
  • decompose_linked_1_result.sql
  • decompose_linked_2_result.sql
[投票完成] 最佳候选: decompose_linked_1_result.sql
```

---

## 总结

### ✅ 修复内容
1. **删除线程内部的多候选生成**：每个线程从生成3个SQL改为生成1个SQL
2. **实现策略差异化**：根据线程编号自动选择Normal或Fallback策略
3. **添加自我精化**：每个生成的SQL都经过self-refinement优化
4. **移除线程内投票**：等待所有线程完成后在外层统一投票
5. **优化文件命名**：使用完整的线程前缀（如 `decompose_linked_0`）

### ✅ 遵循原则
- ✅ 一个线程一个SQL
- ✅ 策略多样性（每3个中有1个使用fallback）
- ✅ 自我精化提升质量
- ✅ 统一投票选择最佳

### ✅ 测试验证
- ✅ 策略选择逻辑正确（test_thread_strategy.py）
- ✅ 文件命名规则正确
- ✅ 无语法错误（linter检查通过）

---

## 下一步

1. **运行实际测试**：
   ```bash
   cd e:\Project\track3_2\ReFoRCE\methods\ReFoRCE
   python run_starrocks.py --do_vote --do_schema_linking_vote --num_votes 3 ...
   ```

2. **验证输出**：
   - 每个线程只生成1个SQL文件
   - 文件命名正确（`decompose_linked_X_result.sql`）
   - 日志显示正确的策略选择
   - 最终生成 `result.sql`（投票结果）

3. **监控效果**：
   - 生成速度（应该更快，因为减少了重复生成）
   - SQL质量（通过self-refinement优化）
   - 投票准确性（在所有候选中选择最佳）
