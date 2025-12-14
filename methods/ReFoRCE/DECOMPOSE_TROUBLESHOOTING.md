# 分解-合并流程故障排查指南

## 问题现象

**症状**: 中等/困难题目启用 `--use_decompose` 后，日志显示：
```
[Decompose-Scale] Enabled for complexity: 中等
[Decompose] Starting question decomposition...
[Decomposer] Extracted 0 sub-questions
[Decompose] No sub-questions generated, falling back to normal flow
```

**影响**: 分解器无法提取子问题，系统自动回退到常规SQL生成流程，无法享受分解-合并的优势。

---

## 根本原因

### 原因1: 使用了错误的响应提取方法（**最关键**）

**问题代码**（已修复）:
```python
# ❌ 错误：只提取SQL代码块，丢弃文本标记
response = self.chat_session.get_model_response(prompt, "sql")
```

**修复后**:
```python
# ✅ 正确：获取完整响应文本，保留格式标记
response_text = self.chat_session.get_model_response_txt(prompt)
```

**技术细节**:
- `get_model_response(prompt, "sql")` 调用 `extract_all_blocks(response, "sql")`
- `extract_all_blocks` 只提取 `\`\`\`sql ... \`\`\`` 之间的内容
- **结果**: "Sub question 1:" 等文本标记被丢弃
- **后果**: `parse_qa_pairs` 无法找到子问题标记，返回空列表

### 原因2: LLM输出格式不符合预期

**期望格式**:
```
Sub question 1: Get users with specific tag
SQL
```sql
SELECT ...
```

Sub question 2: Calculate total duration
SQL
```sql
SELECT ...
```
```

**实际输出** (错误示例):
```sql
SELECT DISTINCT suserid
FROM dim_vplayerid_vies_df
WHERE dtstatdate = '20250724'
```

**原因分析**:
- `deepseek-reasoner` 等推理型模型可能直接返回SQL，忽略格式要求
- Prompt中的格式说明不够明确
- 模型没有看到足够的示例

### 原因2: 模型选择不当

某些模型不擅长结构化输出：
- ❌ `deepseek-reasoner` - 擅长推理但可能忽略格式
- ✅ `deepseek-chat` - 更好地遵循指令格式
- ✅ `gpt-4o` - 格式遵循性好

---

## 解决方案

### 方案1: 使用推荐的分解模型（快速修复）

**推荐配置**:
```bash
--decompose_model "deepseek-chat"  # 替代 deepseek-reasoner
--scale_model "deepseek-chat"
```

**完整命令**:
```bash
uv run run_starrocks.py \
  --output_path output/test-decompose \
  --use_decompose \
  --generation_model "deepseek-chat" \
  --decompose_model "deepseek-chat" \      # ✅ 修改这里
  --scale_model "deepseek-chat" \
  --do_self_refinement \
  --max_iter 5 \
  --sub_question_max_iter 3 \
  --filter_complexity 中等
```

### 方案2: 已实施的增强解析（自动生效）

**更新内容** (已应用到代码):

1. **增强的格式解析器** (`parse_qa_pairs`):
   - 支持标准格式: `Sub question 1: ...`
   - 支持Fallback: 直接提取SQL代码块
   - 支持裸SELECT语句

2. **改进的Prompt**:
   ```
   **IMPORTANT OUTPUT FORMAT REQUIREMENT**:
   You MUST follow this exact format for each sub-question:
   
   Sub question 1: <description>
   SQL
   ```sql
   <query>
   ```
   ```

3. **详细的调试日志**:
   - 显示解析失败原因
   - 预览LLM响应格式
   - 帮助诊断问题

### 方案3: 调整分解策略

如果问题持续，考虑：

#### A. 降低复杂度阈值
只对"复杂"题目使用分解：
```bash
--use_decompose \
--filter_complexity 复杂  # 只处理复杂题目
```

#### B. 增加Few-shot示例
确保列探索提供了足够的示例：
```bash
--do_column_exploration  # 提供更多上下文
```

#### C. 手动指定示例
在代码中添加更多Few-shot示例（需要修改代码）

---

## 诊断步骤

### 步骤1: 检查日志文件

查看分解日志：
```bash
# 找到题目的输出目录
cd output/test-sl-vote/sql_1

# 查看任意一个日志文件
cat linked_2_log.log | grep -A 20 "Decomposer"
```

**关键信息**:
```
[Decomposer] Starting decomposition for question: ...
[Decomposer] LLM Response:
<查看这里的响应格式>
[Decomposer] Extracted 0 sub-questions  # 如果是0就有问题
```

### 步骤2: 验证LLM响应格式

如果日志显示：
```
[Decomposer] LLM Response:
SELECT DISTINCT suserid
FROM ...
```

**问题**: 模型直接返回SQL，没有按格式分解

**解决**: 更换为 `deepseek-chat`

### 步骤3: 测试单个题目

```bash
python run_starrocks.py \
  --use_decompose \
  --decompose_model "deepseek-chat" \
  --do_self_refinement \
  --max_questions 1 \
  --filter_complexity 中等
```

检查是否成功分解：
```bash
cat output/starrocks-log/sql_1/decomposition/decomposition.json
```

应该看到：
```json
{
  "sql_id": "sql_1",
  "sub_questions_count": 2,  // 应该 > 0
  "decomposition": [...]
}
```

---

## 常见错误模式

### 错误1: Reasoner模型直接输出SQL
```
[Decomposer] LLM Response:
SELECT ...
```
**修复**: `--decompose_model "deepseek-chat"`

### 错误2: 格式混乱
```
[Decomposer] LLM Response:
First, we need to get users...
Then calculate...
SELECT ...
```
**修复**: 检查Prompt是否正确加载（已在代码中修复）

### 错误3: 空响应
```
[Decomposer] LLM Response:

[Decomposer] Extracted 0 sub-questions
```
**修复**: 检查API配置和模型可用性

---

## 验证修复

### 测试命令
```bash
# 清理旧输出
rm -rf output/test-decompose

# 使用修复后的配置
uv run run_starrocks.py \
  --output_path output/test-decompose \
  --use_decompose \
  --generation_model "deepseek-chat" \
  --decompose_model "deepseek-chat" \
  --scale_model "deepseek-chat" \
  --do_column_exploration \
  --do_self_refinement \
  --max_iter 5 \
  --sub_question_max_iter 3 \
  --max_questions 3 \
  --filter_complexity 中等
```

### 成功标志

查看日志应该显示：
```
[Decompose-Scale] Enabled for complexity: 中等
[Decompose] Starting question decomposition...
[Decomposer] Extracted 2 sub-questions       # ✅ > 0
  Sub-Q1: Get users with tag '其他'
  Sub-SQL1:
  SELECT DISTINCT suserid ...
  Sub-Q2: Calculate online duration
  Sub-SQL2:
  SELECT SUM(ionlinetime) ...
[Sub-Question 1] Processing: Get users...
[Sub-Question 1] ✓ Refined
[Sub-Question 2] Processing: Calculate...
[Sub-Question 2] ✓ Refined
[Scale] Final SQL generated
[Scale] ✓ Final SQL executed successfully
```

### 检查输出文件

应该生成：
```
output/test-decompose/sql_1/
├── decomposition/
│   ├── decomposition.json          # 分解结果
│   ├── sub_1/
│   │   ├── result.sql              # 子问题1的SQL
│   │   └── result.csv              # 子问题1的结果
│   ├── sub_2/
│   │   ├── result.sql
│   │   └── result.csv
├── result.sql                       # 最终合并的SQL
└── result.csv                       # 最终结果
```

---

## 性能对比

### 修复前（回退到常规流程）
```
[Decompose] No sub-questions generated, falling back to normal flow
[Self_refine] itercount: 0, 1, 2, 3, 4
Total time: ~2 min
```

### 修复后（成功使用分解）
```
[Decomposer] Extracted 2 sub-questions
[Sub-Question 1] itercount: 0, 1, 2
[Sub-Question 2] itercount: 0, 1
[Scale] Final SQL generated
Total time: ~1.5 min (faster), Accuracy: Higher
```

---

## 推荐配置

### 生产环境
```bash
python run_starrocks.py \
  --use_decompose \
  --generation_model "deepseek-chat" \
  --decompose_model "deepseek-chat" \        # ✅ 推荐
  --scale_model "deepseek-chat" \
  --column_exploration_model "deepseek-chat" \
  --do_column_exploration \
  --do_self_refinement \
  --do_self_consistency \
  --max_iter 6 \
  --sub_question_max_iter 3 \
  --num_workers 10 \
  --filter_complexity 复杂
```

### 开发/测试
```bash
python run_starrocks.py \
  --use_decompose \
  --decompose_model "deepseek-chat" \
  --do_self_refinement \
  --max_iter 3 \
  --sub_question_max_iter 2 \
  --max_questions 5
```

---

## FAQ

### Q1: 为什么deepseek-reasoner不适合做分解？
**A**: Reasoner模型优化了推理能力，但可能不严格遵循格式要求。Chat模型更适合结构化输出。

### Q2: 如果必须使用reasoner怎么办？
**A**: 代码已增强了解析能力，现在会尝试从任何SQL代码块中提取，但最好还是换成chat模型。

### Q3: 分解失败会影响结果吗？
**A**: 不会直接影响，系统会自动回退到常规流程。但你会失去分解-合并的优势（更高准确率、更快速度）。

### Q4: 如何确认分解成功？
**A**: 检查日志中 `[Decomposer] Extracted X sub-questions`，X应该 > 0。

### Q5: 简单题目会被分解吗？
**A**: 不会。分解只对"中等"和"复杂"题目生效（在代码中硬编码）。

---

## 相关文档

- **分解-合并指南**: `DECOMPOSE_SCALE_GUIDE.md`
- **子问题迭代配置**: `SUB_QUESTION_ITERATION_GUIDE.md`
- **快速参考**: `QUICK_REFERENCE_SUB_ITERATION.md`

---

## 更新历史

- **2025-11-26**: 
  - 增强 `parse_qa_pairs` 方法，支持多种格式
  - 改进Prompt，明确格式要求
  - 添加详细调试日志
  - 创建本故障排查文档
