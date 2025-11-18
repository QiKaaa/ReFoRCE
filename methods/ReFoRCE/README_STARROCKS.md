# ReFoRCE for StarRocks

这是 ReFoRCE 项目的 StarRocks 适配版本，专门用于处理 `final_dataset_example.json` 中的 Text-to-SQL 任务。

## 🎯 改造要点

### 1. **数据源适配**
- ✅ 使用 SQLAlchemy 连接 StarRocks 数据库
- ✅ 支持 `localhost:9030` 默认配置
- ✅ 数据库名：`final_algorithm_competition`

### 2. **Schema管理**
- ✅ 解析 `M-schema/final_algorithm_competition.txt`
- ✅ 按数据表进行 chunk 划分
- ✅ 根据 `table_list` 动态获取相关表的 Schema
- ✅ **LLM-based Schema Linking**: 一次性分析所有相关表，智能选择列

### 3. **SQL方言**
- ✅ StarRocks 方言支持（MySQL兼容语法）
- ✅ 日期函数、聚合函数、窗口函数提示
- ✅ JSON/ARRAY 数据类型处理

## 📁 新增文件

```
methods/ReFoRCE/
├── sql_starrocks.py               # StarRocks SQL执行引擎
├── schema_parser.py               # Schema文件解析器
├── schema_linking_optimized.py    # LLM-based Schema Linking (优化版)
├── data_loader.py                 # 数据集加载器
├── prompt_starrocks.py            # StarRocks方言Prompt
├── run_starrocks.py               # 主运行脚本
├── run_starrocks.sh               # Bash启动脚本
├── run_starrocks.ps1              # PowerShell启动脚本
├── requirements_starrocks.txt     # 依赖文件
└── README_STARROCKS.md            # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

使用 **uv**（推荐）：
```powershell
cd E:\Project\track3_2\ReFoRCE\methods\ReFoRCE

# 创建虚拟环境
uv venv --python 3.10

# 激活环境
.\.venv\Scripts\Activate.ps1

# 安装依赖
uv pip install -r requirements_starrocks.txt
```

使用 **pip**：
```powershell
pip install -r requirements_starrocks.txt
```

### 2. 配置数据库

确保 StarRocks 数据库正在运行：
```sql
-- 检查连接
mysql -h localhost -P 9030 -u root

-- 验证数据库
SHOW DATABASES;
USE final_algorithm_competition;
SHOW TABLES;
```

### 3. 设置 API Key

```powershell
# OpenAI
$env:OPENAI_API_KEY = "sk-..."

# 或 Azure OpenAI
$env:AZURE_ENDPOINT = "https://your-resource.openai.azure.com/"
$env:AZURE_OPENAI_KEY = "your-key"
```

### 4. 测试运行

先运行3个问题测试：
```powershell
python run_starrocks.py `
  --dataset_path "E:/Project/track3_2/final_for_student/data/final_dataset_example.json" `
  --schema_path "E:/Project/track3_2/M-schema/final_algorithm_competition.txt" `
  --output_path "output/test" `
  --db_host "localhost" `
  --db_port 9030 `
  --db_user "root" `
  --db_password "" `
  --db_name "final_algorithm_competition" `
  --generation_model "gpt-4o" `
  --do_self_refinement `
  --max_questions 3 `
  --num_workers 1
```

### 5. 完整运行

使用PowerShell脚本：
```powershell
# 编辑 run_starrocks.ps1 配置API Key

# 运行
.\run_starrocks.ps1
```

## 🔧 运行模式

### 模式1: 基础模式
```powershell
python run_starrocks.py \
  --generation_model gpt-4o \
  --do_self_refinement \
  --max_iter 5
```
- ✅ 自我精化
- ❌ 列探索
- ❌ 投票

### 模式2: Schema Linking模式 (新增✨)
```powershell
python run_starrocks.py \
  --use_schema_linking \
  --generation_model gpt-4o \
  --do_self_refinement \
  --max_iter 5
```
- ✅ LLM智能列选择（一次性分析所有表）
- ✅ 显著减少prompt token
- ✅ 保持准确率
- ✅ 自我精化

### 模式3: Schema Linking投票模式 (推荐⭐)
```powershell
python run_starrocks.py \
  --do_schema_linking_vote \
  --do_vote \
  --generation_model gpt-4o \
  --num_votes 3 \
  --random_vote_for_tie \
  --max_iter 5
```
- ✅ 原始Schema + Linked Schema 双路径
- ✅ 投票选择最优SQL
- ✅ 最高准确率
- ✅ 成本略高但效果最佳

### 模式4: 列探索模式
```powershell
python run_starrocks.py \
  --generation_model gpt-4o \
  --column_exploration_model gpt-4o \
  --do_column_exploration \
  --do_self_refinement \
  --do_self_consistency \
  --max_iter 5
```
- ✅ 自我精化
- ✅ 列探索
- ✅ 自我一致性
- ❌ 投票

### 模式5: 完整模式
```powershell
python run_starrocks.py \
  --generation_model gpt-4o \
  --column_exploration_model gpt-4o \
  --do_column_exploration \
  --do_self_refinement \
  --do_self_consistency \
  --do_vote \
  --num_votes 3 \
  --random_vote_for_tie \
  --max_iter 5 \
  --num_workers 4
```
- ✅ 自我精化
- ✅ 列探索
- ✅ 自我一致性
- ✅ 投票（3次）

## 📊 参数说明

### 数据源参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--dataset_path` | final_dataset_example.json | 数据集路径 |
| `--schema_path` | final_algorithm_competition.txt | Schema文件路径 |
| `--db_host` | localhost | StarRocks主机 |
| `--db_port` | 9030 | StarRocks端口 |
| `--db_user` | root | 数据库用户名 |
| `--db_password` | "" | 数据库密码 |
| `--db_name` | final_algorithm_competition | 数据库名 |

### 模型参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--generation_model` | gpt-4o | SQL生成模型 |
| `--column_exploration_model` | gpt-4o | 列探索模型 |
| `--format_model` | gpt-4o | 格式化模型 |
| `--azure` | False | 使用Azure OpenAI |
| `--temperature` | 1.0 | 采样温度 |

### 功能开关
| 参数 | 说明 |
|------|------|
| `--do_column_exploration` | 启用列探索 |
| `--do_self_refinement` | 启用自我精化 |
| `--do_self_consistency` | 启用自我一致性检查 |
| `--do_vote` | 启用投票机制 |
| `--do_format_restriction` | 启用格式限制 |
| `--use_schema_linking` | 启用Schema Linking (单独使用) |
| `--do_schema_linking_vote` | 启用Schema Linking投票模式 |

### 运行控制
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max_iter` | 5 | 最大迭代次数 |
| `--num_votes` | 3 | 投票次数 |
| `--num_workers` | 4 | 并行worker数 |
| `--max_questions` | None | 限制问题数（测试用） |
| `--filter_complexity` | None | 过滤复杂度（简单/中等/复杂） |

## 📝 输出结果

运行后会在 `output/` 目录生成：

```
output/starrocks-log/
├── sql_1/
│   ├── result.sql      # 最终SQL
│   ├── result.csv      # 执行结果
│   ├── log.log         # 详细日志
│   ├── 0result.sql     # 投票候选1
│   ├── 1result.sql     # 投票候选2
│   └── 2result.sql     # 投票候选3
├── sql_2/
│   └── ...
└── ...
```

## 🧪 测试模块

单独测试各个模块：

### 测试Schema解析器
```python
python schema_parser.py
```

### 测试数据加载器
```python
python data_loader.py
```

### 测试StarRocks连接
```python
from sql_starrocks import SqlEnvStarRocks

sql_env = SqlEnvStarRocks(
    host="localhost",
    port=9030,
    user="root",
    database="final_algorithm_competition"
)

result = sql_env.execute_sql_api(
    "SELECT * FROM dim_argothek_gplayerid2qqwxid_df LIMIT 5",
    ex_id="test",
    api="starrocks"
)

print(result)
sql_env.close_db()
```

## ⚠️ 注意事项

### 1. 数据库连接
- 确保 StarRocks 服务正在运行
- 检查端口 9030 未被占用
- 验证数据库和表已正确创建

### 2. API限制
- GPT-4o 有速率限制，建议降低 `--num_workers`
- 使用 Azure 时可提高并发数
- 复杂问题建议增加 `--max_iter`

### 3. 内存使用
- 大规模运行时注意内存消耗
- 可通过 `--max_questions` 分批处理
- 使用 `--filter_complexity` 分类处理

### 4. 日期格式
- final_dataset中的日期格式为 YYYYMMDD（如20250702）
- StarRocks查询时需要正确转换
- 使用 `STR_TO_DATE()` 或 `DATE_FORMAT()` 函数

## 🐛 常见问题

### Q1: 连接 StarRocks 失败
```
A: 检查：
1. StarRocks是否启动: ps aux | grep starrocks
2. 端口是否正确: netstat -an | grep 9030
3. 用户名密码是否正确
```

### Q2: Schema解析失败
```
A: 确保 M-schema/final_algorithm_competition.txt 格式正确
   每个表应该有:
   # Table: table_name, description
   [(column:TYPE, desc, Examples: [...])...]
```

### Q3: 投票结果为空
```
A: 可能原因：
1. 所有候选SQL都失败 -> 检查日志
2. 结果完全不同 -> 降低temperature
3. 添加 --random_vote_for_tie 参数
```

### Q4: 内存不足
```
A: 优化措施：
1. 减少 --num_workers
2. 添加 --max_questions 限制
3. 使用 --filter_complexity 分批处理
```

## 📚 相关文档

- [原始ReFoRCE论文](https://arxiv.org/pdf/2502.00675)
- [StarRocks官方文档](https://docs.starrocks.io/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

遵循原 ReFoRCE 项目许可证
