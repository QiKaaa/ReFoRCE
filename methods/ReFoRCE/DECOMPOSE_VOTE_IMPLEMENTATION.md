# 分解-合并流程投票机制完整实现文档

## 📋 概述

本文档详细说明了如何在分解-合并（Decompose-Scale）流程中实现完整的投票机制，解决之前"生成多个候选SQL但没有投票选择最佳结果"的问题。

---

## 🎯 问题背景

### 之前的问题
在启用 `args.do_vote and args.use_decompose` 时：
- ✅ **已实现**：生成多个SQL候选（`decompose_0_result.sql`, `decompose_1_result.sql`, ...）
- ✅ **已实现**：对每个候选进行refinement优化
- ✅ **已实现**：保存每个候选的SQL和CSV
- ❌ **缺失**：没有调用 `vote_result()` 进行投票
- ❌ **缺失**：没有生成最终的 `result.sql` 和 `result.csv`

### 影响
- 问题如 `sql_14` 显示 "empty results"
- 虽然有 `decompose_0_result.sql` 等候选，但没有最终结果文件

---

## ✨ 完整实现方案

### 1. 核心流程图

```
分解-合并投票流程 (args.do_vote=True, args.use_decompose=True)
│
├─ 1️⃣ 问题分解 (Decompose)
│   └─ 生成子问题和子SQL: [(sub_q1, sub_sql1), (sub_q2, sub_sql2), ...]
│
├─ 2️⃣ 子问题处理 (Process Sub-Questions)
│   ├─ 对每个子SQL应用self-refinement
│   └─ 生成精炼后的QA对: [(sub_q1, refined_sql1), ...]
│
├─ 3️⃣ 生成多个候选SQL (Generate Candidates)
│   ├─ 调用 agent.generate_multiple_sql_candidates()
│   └─ 生成 num_votes 个候选SQL
│
├─ 4️⃣ 处理每个候选 (Process Candidates)
│   ├─ 构建 decompose_sql_paths 字典记录映射
│   │   decompose_sql_paths = {
│   │       "decompose_0_result.sql": "decompose_0_result.csv",
│   │       "decompose_1_result.sql": "decompose_1_result.csv",
│   │       ...
│   │   }
│   │
│   └─ 对每个候选:
│       ├─ 如果启用 do_final_sql_refinement:
│       │   └─ 调用 agent.refine_final_sql() 迭代优化
│       └─ 否则:
│           └─ 直接执行SQL并保存
│
└─ 5️⃣ 投票选择最佳SQL (Vote) ⭐ 新增！
    ├─ 检查有效候选: valid_candidates = [decompose_*_result.sql]
    ├─ 构建投票用table_info（包含knowledge）
    └─ 调用 agent_format.vote_result()
        ├─ 比较所有候选的CSV结果
        ├─ 找出执行结果相同的SQL（投票）
        ├─ 如果有平票，使用model_vote（LLM投票）
        └─ 生成最终: result.sql + result.csv ✅
```

---

## 💻 代码实现

### 核心代码片段（run_starrocks.py）

```python
# ===== 投票模式：生成多个候选 =====
if args.do_vote and args.use_decompose:
    final_sqls = agent.generate_multiple_sql_candidates(
        question=question,
        schema=table_info,
        qa_pairs=refined_qa_pairs,
        evidence=knowledge if knowledge else "",
        schema_links="",
        few_shot_examples=pre_info if pre_info else "",
        num_candidates=args.num_votes if hasattr(args, 'num_votes') else 3,
        chat_session=chat_session_scale,
        logger=logger
    )
    
    logger.info(f"[Scale] Generated {len(final_sqls)} SQL candidates for voting")
    
    # ✨ 构建投票所需的sql_paths字典
    decompose_sql_paths = {}
    
    # 执行并保存每个候选SQL
    for i, final_sql in enumerate(final_sqls):
        vote_csv_path = os.path.join(search_directory, f"decompose_{i}_result.csv")
        vote_sql_path = os.path.join(search_directory, f"decompose_{i}_result.sql")
        
        # 记录SQL-CSV映射
        decompose_sql_paths[f"decompose_{i}_result.sql"] = f"decompose_{i}_result.csv"
        
        # 对候选进行refinement或直接执行
        if args.do_final_sql_refinement:
            # ... refinement逻辑 ...
        else:
            # ... 直接执行逻辑 ...
    
    # ✨ 执行投票选择最佳SQL
    logger.info("[Decompose-Vote] Starting voting for decompose-scale candidates")
    
    # 检查有效候选
    valid_candidates = [f for f in os.listdir(search_directory) 
                       if f.startswith('decompose_') and f.endswith('_result.sql')]
    
    if valid_candidates:
        # 构建包含knowledge的table_info
        table_info_for_vote = table_info
        if knowledge:
            table_info_for_vote += f"\n\nDomain Knowledge:\n{knowledge}"
        
        # 调用投票
        agent_format.vote_result(
            search_directory=search_directory,
            args=args,
            sql_paths=decompose_sql_paths,
            table_info=table_info_for_vote,
            task=question,
            knowledge=knowledge
        )
        
        logger.info("[Decompose-Vote] Voting completed")
    else:
        logger.warning("[Decompose-Vote] No valid candidates found, skipping voting")
```

---

## 📊 投票机制详解

### vote_result() 方法工作原理

**位置**: `agent.py` 的 `REFORCE.vote_result()` 方法

**核心逻辑**:

```python
def vote_result(self, search_directory, args, sql_paths, table_info, task, knowledge=None):
    """
    投票选择最佳SQL
    
    Args:
        search_directory: 输出目录
        args: 命令行参数
        sql_paths: SQL-CSV映射字典
        table_info: Schema信息
        task: 问题文本
        knowledge: 领域知识
    """
    
    # 1️⃣ 比较所有候选的CSV结果
    #    找出执行结果相同的SQL（self-consistency）
    result = {}
    for key, value in sql_paths.items():
        if os.path.exists(value):
            same_ans = 0
            # 与其他所有CSV比较
            for other_csv in all_csv_files:
                if compare_pandas_table(current_csv, other_csv):
                    same_ans += 1
            result[key] = same_ans  # 投票数
    
    # 2️⃣ 找出票数最多的SQL
    sorted_dict = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
    first_key = next(iter(sorted_dict))  # 获胜者
    
    # 3️⃣ 处理平票情况
    max_vote = max(vote_counts)
    num_with_max_vote = vote_counts.count(max_vote)
    has_tie = num_with_max_vote > (max_vote + 1)
    
    if has_tie and args.model_vote:
        # 使用LLM进行二次投票
        self.model_vote(result, sql_paths, search_directory, args, table_info, task, knowledge)
        return
    
    # 4️⃣ 复制获胜SQL为最终结果
    shutil.copy2(
        os.path.join(search_directory, first_key),           # decompose_0_result.sql
        os.path.join(search_directory, "result.sql")         # result.sql
    )
    shutil.copy2(
        os.path.join(search_directory, sql_paths[first_key]), # decompose_0_result.csv
        os.path.join(search_directory, "result.csv")          # result.csv
    )
```

---

## 🔧 参数配置

### 启用分解-合并投票的参数组合

```python
# 必需参数
--do_vote                      # 启用投票模式
--use_decompose                # 启用问题分解
--num_votes 3                  # 生成3个候选SQL

# 可选参数（推荐）
--do_final_sql_refinement      # 对候选SQL进行refinement
--final_sql_max_iter 3         # Refinement最大迭代次数
--model_vote                   # 平票时使用LLM投票
--model_vote gpt-4             # 投票使用的LLM模型

# 分解相关参数
--decompose_model gpt-4        # 问题分解使用的模型
--scale_model gpt-4            # SQL合并使用的模型
```

### 示例命令

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
    --generation_model gpt-4
```

---

## 📁 输出文件结构

### 分解-合并投票模式的完整输出

```
output/test-decompose-vote/sql_14/
├── decomposition/                      # 分解结果目录
│   ├── decomposition.json             # 子问题JSON
│   ├── sub_1/                         # 子问题1
│   │   ├── result.sql
│   │   └── result.csv
│   ├── sub_2/                         # 子问题2
│   │   ├── result.sql
│   │   └── result.csv
│   └── ...
├── decompose_0_result.sql             # 候选SQL #0
├── decompose_0_result.csv             # 候选结果 #0
├── decompose_1_result.sql             # 候选SQL #1
├── decompose_1_result.csv             # 候选结果 #1
├── decompose_2_result.sql             # 候选SQL #2
├── decompose_2_result.csv             # 候选结果 #2
├── result.sql                         # ✅ 最终SQL（投票选出）
├── result.csv                         # ✅ 最终结果（投票选出）
└── vote.log                           # 投票日志
```

---

## 🎯 投票决策流程

```
投票决策树
│
├─ 情况1: 有候选SQL的结果完全相同
│   ├─ 票数最高的有1个 → 直接选择该SQL
│   └─ 票数最高的有多个（平票）
│       ├─ args.model_vote=True → 使用LLM投票
│       └─ args.model_vote=False → 随机选择或跳过
│
├─ 情况2: 所有候选SQL结果都不同
│   ├─ args.model_vote=True → 使用LLM投票
│   └─ args.model_vote=False
│       ├─ args.final_choose=True → 选择第一个
│       └─ 否则 → 不生成result.sql
│
└─ 情况3: 没有有效的候选SQL
    └─ 记录警告，不生成result.sql
```

---

## 🔍 LLM投票（model_vote）详解

### 触发条件
- 启用 `args.model_vote=True`
- 且满足以下之一:
  - 所有候选SQL结果都不相同
  - 多个候选SQL获得最高票数（平票）

### 投票Prompt结构

```python
prompt = f"""
You are given DB info, task and candidate SQLs and their results. 
Choose the most correct one based on database info:
{table_info}

The task is: {task}

**Important Domain Knowledge:**
{knowledge}
Please strictly follow the domain knowledge rules when evaluating the SQL queries.

Here are some candidate sqls and answers:

SQL file name: decompose_0_result.sql
[SQL内容]
CSV file name: decompose_0_result.csv
[CSV内容]

SQL file name: decompose_1_result.sql
[SQL内容]
CSV file name: decompose_1_result.csv
[CSV内容]

...

Compare the SQL and results of each answer, think step by step and choose one SQL as the correct answer.
Output thinking process and the name of sql in ```plaintext
xxx.sql``` format.

Your reasoning step should be:
1. Exclude unreasonable results.
2. Check results if aligning with task description.
3. Analyze SQL if aligning with task description.

For results with null or zero values, they tend to be wrong answer.
"""
```

### LLM投票流程

1. **构建Prompt**: 包含所有候选SQL和结果
2. **调用LLM**: 使用 `args.model_vote` 指定的模型
3. **解析响应**: 提取选择的SQL文件名
4. **执行验证**: 重新执行选中的SQL确保可行
5. **保存结果**: 将选中的SQL保存为 `result.sql`

---

## 📈 性能和成本优化

### 优化策略

1. **缓存列探索结果**
   - 投票模式下只执行一次列探索
   - 所有候选共享 `pre_info`
   
2. **并行生成候选**（可选，暂未实现）
   ```python
   # 可以使用多线程并行生成候选SQL
   with ThreadPoolExecutor(max_workers=num_candidates) as executor:
       futures = [executor.submit(agent.scale_sql, ...) for _ in range(num_candidates)]
       final_sqls = [f.result() for f in futures]
   ```

3. **提前终止无效候选**
   - 如果候选SQL执行失败，不记录到 `decompose_sql_paths`
   - 减少无效投票项

4. **选择性refinement**
   ```python
   # 只对票数较高的候选进行refinement
   if vote_count >= threshold:
       refined_sql = agent.refine_final_sql(...)
   ```

---

## 🐛 常见问题和解决方案

### Q1: 投票后仍然没有 `result.sql`

**可能原因**:
- 所有候选SQL执行失败
- 没有启用 `args.model_vote` 且结果全不同

**解决方案**:
```python
# 启用model_vote
--model_vote

# 或启用final_choose（选择第一个有效候选）
--final_choose
```

---

### Q2: 投票选择了错误的SQL

**可能原因**:
- 多个错误SQL生成了相同的错误结果
- 领域知识没有正确传递到投票逻辑

**解决方案**:
```python
# 确保knowledge参数正确传递
agent_format.vote_result(
    ...,
    knowledge=knowledge  # ✅ 必须传递
)

# 启用LLM投票进行二次验证
--model_vote
```

---

### Q3: 投票耗时过长

**可能原因**:
- 候选数量过多（`num_votes` 过大）
- 每个候选的refinement迭代次数过多

**解决方案**:
```python
# 减少候选数量
--num_votes 3  # 推荐值

# 减少refinement迭代次数
--final_sql_max_iter 2

# 或者禁用refinement，直接投票
# 不加 --do_final_sql_refinement
```

---

## ✅ 验证清单

在部署分解-合并投票机制前，请确认：

- [ ] `decompose_sql_paths` 字典已构建
- [ ] `decompose_sql_paths` 正确记录了所有候选的SQL-CSV映射
- [ ] 调用 `agent_format.vote_result()` 且传递了所有必需参数
- [ ] `knowledge` 参数正确传递到投票逻辑
- [ ] 投票逻辑在 `if args.do_vote and args.use_decompose:` 分支内
- [ ] 投票前检查了 `valid_candidates`
- [ ] 日志中有 `[Decompose-Vote]` 标记
- [ ] 生成了最终的 `result.sql` 和 `result.csv`

### 自动验证脚本

运行以下命令进行自动验证：

```bash
python verify_decompose_vote.py
```

---

## 📚 相关文档

- [SCALER_MIGRATION.md](SCALER_MIGRATION.md) - Scaler功能合并说明
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - 整体重构总结
- [run_starrocks.py](run_starrocks.py) - 主执行脚本

---

## 🎉 总结

通过以上实现，分解-合并流程现在具备了完整的投票机制：

1. ✅ **生成多个候选SQL** - `generate_multiple_sql_candidates()`
2. ✅ **Refinement优化** - `refine_final_sql()`
3. ✅ **投票选择** - `vote_result()`
4. ✅ **LLM二次投票** - `model_vote()` （可选）
5. ✅ **生成最终结果** - `result.sql` + `result.csv`

这使得分解-合并流程在处理复杂问题时更加稳健，能够通过投票机制选出最可能正确的SQL！

---

**最后更新**: 2025-11-26  
**版本**: v1.0  
**作者**: AI Agent
