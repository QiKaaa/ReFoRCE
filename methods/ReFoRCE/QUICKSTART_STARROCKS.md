# 🚀 StarRocks版ReFoRCE快速启动指南

## 📋 前置条件检查清单

- [ ] Python 3.10+ 已安装
- [ ] StarRocks 数据库已启动（localhost:9030）
- [ ] `final_algorithm_competition` 数据库已创建
- [ ] OpenAI API Key 或 Azure OpenAI 已配置

## ⚡ 5分钟快速启动

### Step 1: 进入项目目录
```powershell
cd E:\Project\track3_2\ReFoRCE\methods\ReFoRCE
```

### Step 2: 安装依赖（使用uv，超快！）
```powershell
# 安装uv（如果还没有）
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 创建虚拟环境并安装依赖（使用 Python 3.12）
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements_starrocks.txt
```

### Step 3: 验证环境
```powershell
python test_starrocks_setup.py
```

如果看到 `🎉 所有测试通过！`，继续下一步。

### Step 4: 设置API Key
```powershell
# 方式1: OpenAI
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# 方式2: Azure OpenAI
$env:AZURE_ENDPOINT = "https://your-resource.openai.azure.com/"
$env:AZURE_OPENAI_KEY = "your-azure-key-here"
```

### Step 5: 测试运行（1个问题）
```powershell
python run_starrocks.py `
  --dataset_path "E:/Project/track3_2/final_for_student/data/final_dataset_example.json" `
  --schema_path "E:/Project/track3_2/M-schema/final_algorithm_competition.txt" `
  --output_path "output/test" `
  --generation_model "gpt-4o" `
  --do_self_refinement `
  --max_questions 1 `
  --num_workers 1
```

### Step 6: 查看结果
```powershell
# 查看生成的SQL
cat output/test/sql_1/result.sql

# 查看执行结果
cat output/test/sql_1/result.csv

# 查看详细日志
cat output/test/sql_1/log.log
```

## 🎯 运行模式选择

### 🚀 Schema Linking模式 (推荐新手✨)
```powershell
python run_starrocks.py `
  --use_schema_linking `
  --generation_model "gpt-4o" `
  --do_self_refinement `
  --max_iter 5 `
  --num_workers 1
```
- ⏱️ 时间：约3-5分钟/题
- 💰 成本：中等 (显著减少token)
- 🎯 准确度：高
- ✨ 特性：LLM一次性分析所有表,智能列选择

### ⭐ Schema Linking投票模式 (最推荐)
```powershell
python run_starrocks.py `
  --do_schema_linking_vote `
  --do_vote `
  --generation_model "gpt-4o" `
  --num_votes 3 `
  --random_vote_for_tie `
  --max_iter 5 `
  --num_workers 1
```
- ⏱️ 时间：约8-12分钟/题
- 💰 成本：中高
- 🎯 准确度：最高 (双路径验证)
- ✨ 特性：原始+Linked双重保障

### 🐢 慢速但准确（列探索）
```powershell
python run_starrocks.py `
  --generation_model "gpt-4o" `
  --column_exploration_model "gpt-4o" `
  --do_column_exploration `
  --do_self_refinement `
  --do_self_consistency `
  --max_iter 5 `
  --num_workers 1
```
- ⏱️ 时间：约5-10分钟/题
- 💰 成本：高
- 🎯 准确度：最高

### ⚡ 快速模式
```powershell
python run_starrocks.py `
  --generation_model "gpt-4o-mini" `
  --do_self_refinement `
  --max_iter 3 `
  --num_workers 4
```
- ⏱️ 时间：约1-2分钟/题
- 💰 成本：低
- 🎯 准确度：中等

### 🏆 完整模式（生产环境）
```powershell
python run_starrocks.py `
  --generation_model "gpt-4o" `
  --column_exploration_model "gpt-4o" `
  --do_column_exploration `
  --do_self_refinement `
  --do_self_consistency `
  --do_vote `
  --num_votes 3 `
  --random_vote_for_tie `
  --max_iter 5 `
  --num_workers 2
```
- ⏱️ 时间：约15-20分钟/题
- 💰 成本：最高
- 🎯 准确度：最高（投票机制）

## 📊 按复杂度运行

### 只运行简单题目
```powershell
python run_starrocks.py `
  --filter_complexity "简单" `
  --generation_model "gpt-4o" `
  --do_self_refinement `
  --num_workers 2
```

### 只运行中等题目
```powershell
python run_starrocks.py `
  --filter_complexity "中等" `
  --generation_model "gpt-4o" `
  --column_exploration_model "gpt-4o" `
  --do_column_exploration `
  --do_self_refinement `
  --num_workers 2
```

### 只运行复杂题目
```powershell
python run_starrocks.py `
  --filter_complexity "复杂" `
  --generation_model "gpt-4o" `
  --column_exploration_model "gpt-4o" `
  --do_column_exploration `
  --do_self_refinement `
  --do_vote `
  --num_votes 3 `
  --max_iter 8 `
  --num_workers 1
```

## 🔧 常用参数组合

### 🌟 Schema Linking快速测试 (推荐)
```powershell
python run_starrocks.py `
  --use_schema_linking `
  --max_questions 3 `
  --num_workers 1 `
  --generation_model "gpt-4o"
```

### 调试模式（测试3题）
```powershell
python run_starrocks.py `
  --max_questions 3 `
  --num_workers 1 `
  --generation_model "gpt-4o-mini"
```

### 省钱模式（使用mini模型）
```powershell
python run_starrocks.py `
  --generation_model "gpt-4o-mini" `
  --column_exploration_model "gpt-4o-mini" `
  --format_model "gpt-4o-mini" `
  --do_column_exploration `
  --do_self_refinement `
  --temperature 0.5
```
**注意**: `--do_column_exploration` 会根据题目复杂度自动决定是否执行列探索：
- 简单题：不执行（节省时间和成本）
- 中等/复杂题：执行（提高准确率）

### 高精度模式 (Schema Linking + 投票)
```powershell
python run_starrocks.py `
  --do_schema_linking_vote `
  --do_vote `
  --generation_model "gpt-4o" `
  --num_votes 5 `
  --temperature 0.3 `
  --num_workers 1
```

### 原高精度模式 (列探索 + 投票)
```powershell
python run_starrocks.py `
  --generation_model "o1-preview" `
  --column_exploration_model "gpt-4o" `
  --do_column_exploration `
  --do_self_refinement `
  --do_vote `
  --num_votes 5 `
  --temperature 0.3
```

## 📁 输出目录结构

```
output/
└── starrocks-log/
    ├── sql_1/
    │   ├── result.sql       ← 最终SQL（如果投票通过）
    │   ├── result.csv       ← 执行结果
    │   ├── log.log          ← 完整日志
    │   ├── 0result.sql      ← 候选SQL 1
    │   ├── 0result.csv      ← 候选结果 1
    │   ├── 0log.log         ← 候选日志 1
    │   ├── 1result.sql      ← 候选SQL 2
    │   ├── 1result.csv      ← 候选结果 2
    │   ├── 1log.log         ← 候选日志 2
    │   ├── 2result.sql      ← 候选SQL 3
    │   ├── 2result.csv      ← 候选结果 3
    │   └── 2log.log         ← 候选日志 3
    ├── sql_2/
    │   └── ...
    └── ...
```

**Schema Linking投票模式输出**:
```
sql_1/
├── original_0_result.sql    ┐
├── original_1_result.sql    ├─ 原始Schema路径
├── original_2_result.sql    ┘
├── linked_0_result.sql      ┐
├── linked_1_result.sql      ├─ Linked Schema路径
├── linked_2_result.sql      ┘
├── result.sql              ← 投票后最终结果 ⭐
└── result.csv
```
    │   ├── 2result.csv      ← 候选结果 3
    │   └── 2log.log         ← 候选日志 3
    ├── sql_2/
    │   └── ...
    └── ...
```

## 🐛 常见问题快速修复

### 问题1: 数据库连接失败
```powershell
# 检查StarRocks是否运行
netstat -an | findstr 9030

# 测试连接
mysql -h localhost -P 9030 -u root -e "SHOW DATABASES;"
```

### 问题2: API超时
```powershell
# 降低并发数
python run_starrocks.py --num_workers 1

# 或增加温度降低思考时间
python run_starrocks.py --temperature 1.5
```

### 问题3: 内存不足
```powershell
# 分批处理
python run_starrocks.py --max_questions 10
# 处理完后继续下10个
python run_starrocks.py --max_questions 20 --rerun
```

### 问题4: Schema解析错误
```powershell
# 验证Schema文件
python -c "from schema_parser import SchemaParser; p = SchemaParser('E:/Project/track3_2/M-schema/final_algorithm_competition.txt'); print(len(p.tables))"
```

### 问题5: Schema Linking输出为空
```powershell
# 检查LLM响应日志
grep "🔮 LLM Schema Linking" output/starrocks-log/sql_1/log.log -A 100

# 可能原因:
# 1. LLM返回格式不正确 -> 检查日志中的JSON
# 2. table_list为空 -> 检查数据集标注
# 3. API超时 -> 降低并发或切换模型
```

## 📈 性能优化建议

### CPU密集型（本地模型）
```powershell
--num_workers 8  # 使用更多CPU核心
```

### API密集型（云端模型）
```powershell
--num_workers 2  # 避免超过API速率限制
```

### 内存优化
```powershell
--max_questions 5  # 每次处理少量问题
```

## 🎓 学习路径

1. **第一天**：运行Schema Linking测试，理解基本流程
   ```powershell
   python run_starrocks.py --use_schema_linking --max_questions 1
   ```
2. **第二天**：尝试投票模式，对比结果
   ```powershell
   python run_starrocks.py --do_schema_linking_vote --do_vote --max_questions 3
   ```
3. **第三天**：调优参数，提升准确率
4. **第四天**：处理全部数据集

## 💡 高级技巧

### 使用配置文件
创建 `config.json`:
```json
{
  "dataset_path": "E:/Project/track3_2/final_for_student/data/final_dataset_example.json",
  "schema_path": "E:/Project/track3_2/M-schema/final_algorithm_competition.txt",
  "db_host": "localhost",
  "db_port": 9030,
  "generation_model": "gpt-4o",
  "do_self_refinement": true,
  "max_iter": 5
}
```

### 批量重跑失败的题目
```powershell
# 找出没有result.sql的题目
$failed = Get-ChildItem output/starrocks-log -Directory | Where-Object { -not (Test-Path "$($_.FullName)/result.sql") }

# 只重跑这些题目（需要修改脚本）
```

### 并行运行不同复杂度
```powershell
# Terminal 1
python run_starrocks.py --filter_complexity "简单" --output_path "output/simple"

# Terminal 2
python run_starrocks.py --filter_complexity "中等" --output_path "output/medium"

# Terminal 3
python run_starrocks.py --filter_complexity "复杂" --output_path "output/complex"
```

## 🎉 完成后

1. **检查结果完整性**
   ```powershell
   # 统计成功生成的SQL
   (Get-ChildItem output/starrocks-log -Directory | Where-Object { Test-Path "$($_.FullName)/result.sql" }).Count
   ```

2. **分析Schema Linking效果**
   ```powershell
   # 查看token节省情况
   grep "Optimized schema generated" output/starrocks-log/*/log.log
   ```

3. **对比投票结果**
   ```powershell
   # 查看linked vs original的胜率
   grep "vote.log" output/starrocks-log/*/
   ```

4. **导出最终SQL和结果**

祝你好运！🚀

---

## 💡 Schema Linking核心优势

✅ **一次LLM调用**: 同时分析所有相关表  
✅ **智能JOIN**: 理解表关系,保留关联列  
✅ **大幅节省Token**: 平均减少60-80%的schema token  
✅ **保持准确率**: 通过投票模式验证
