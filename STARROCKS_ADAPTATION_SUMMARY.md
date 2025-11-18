# ReFoRCE StarRocks适配总结

## 📝 改造概览

本文档总结了将 ReFoRCE 项目适配到 StarRocks 数据库和 `final_dataset_example.json` 数据集的所有改造工作。

---

## 🎯 改造目标

1. ✅ **数据源**：从 Snowflake/BigQuery/SQLite 迁移到 **StarRocks**
2. ✅ **连接方式**：使用 **SQLAlchemy** 连接 `localhost:9030`
3. ✅ **Schema管理**：解析 `M-schema/final_algorithm_competition.txt`
4. ✅ **Schema链接**：根据 `table_list` 动态获取相关表
5. ✅ **SQL方言**：适配 **StarRocks** 语法（MySQL兼容）

---

## 📦 新增文件清单

### 核心功能模块
| 文件名 | 功能 | 行数 |
|--------|------|------|
| `sql_starrocks.py` | StarRocks SQL执行引擎（替代 sql.py） | ~180 |
| `schema_parser.py` | 解析并管理Schema文件 | ~150 |
| `data_loader.py` | 加载final_dataset_example.json | ~100 |
| `prompt_starrocks.py` | StarRocks方言Prompt模板 | ~200 |
| `run_starrocks.py` | 主运行脚本（适配新数据集） | ~450 |

### 配置和脚本
| 文件名 | 功能 |
|--------|------|
| `requirements_starrocks.txt` | StarRocks版依赖清单 |
| `run_starrocks.sh` | Bash启动脚本 |
| `run_starrocks.ps1` | PowerShell启动脚本 |
| `test_starrocks_setup.py` | 环境验证测试脚本 |

### 文档
| 文件名 | 内容 |
|--------|------|
| `README_STARROCKS.md` | 完整使用文档 |
| `QUICKSTART_STARROCKS.md` | 快速启动指南 |
| `STARROCKS_ADAPTATION_SUMMARY.md` | 本总结文档 |

**总计**：12个新文件，约1400行代码

---

## 🔧 核心改造点

### 1. SQL执行引擎 (`sql_starrocks.py`)

**原有实现**：
```python
# 原sql.py支持3种数据库
- BigQuery: google.cloud.bigquery
- Snowflake: snowflake.connector
- SQLite: sqlite3
```

**新实现**：
```python
class SqlEnvStarRocks:
    def __init__(self, host="localhost", port=9030, ...):
        # 使用SQLAlchemy统一接口
        connection_string = f"starrocks://{user}:{password}@{host}:{port}/{database}"
        self.engine = create_engine(connection_string)
    
    def execute_sql_api(self, sql_query, ...):
        # 兼容原有接口
        with self.engine.connect() as connection:
            result = connection.execute(text(sql_query))
            # 处理结果...
```

**关键特性**：
- ✅ 兼容原有 `execute_sql_api` 接口
- ✅ 支持超时控制（`func_timeout`）
- ✅ 统一错误处理
- ✅ CSV格式输出

---

### 2. Schema解析器 (`schema_parser.py`)

**挑战**：
- Schema文件格式特殊（非标准DDL）
- 需要按表分块
- 需要根据table_list动态组装

**解决方案**：
```python
class SchemaParser:
    def _parse_schema(self):
        # 正则提取表信息
        table_pattern = r'# Table:\s*([^,\n]+)(?:,\s*([^\n]*))?\n\[(.*?)\n\]'
        
    def get_tables_chunks(self, table_list):
        # 根据table_list组装Schema
        chunks = []
        for table_name in table_list:
            chunk = self.get_table_chunk(table_name)
            chunks.append(chunk)
        return "\n".join(chunks)
```

**输入格式**：
```
# Table: dim_argothek_gplayerid2qqwxid_df, 全量用户gplayerid转qq或wxid
[
(dtstatdate:VARCHAR, 日期, Examples: [20250720, 20250610]),
(vgameappid:VARCHAR, 平台, Examples: [app001, app007]),
...
]
```

**输出格式**：
```
Table: dim_argothek_gplayerid2qqwxid_df
Description: 全量用户gplayerid转qq或wxid
Columns:
  - dtstatdate (VARCHAR): 日期 [Examples: 20250720, 20250610]
  - vgameappid (VARCHAR): 平台 [Examples: app001, app007]
  ...
```

---

### 3. 数据加载器 (`data_loader.py`)

**功能**：
- 加载 `final_dataset_example.json`
- 提供统计信息
- 支持按复杂度过滤

**核心方法**：
```python
class DatasetLoader:
    def get_questions_dict(self):
        # 兼容原有task_dict格式
        return {ex['sql_id']: ex['question'] for ex in self.data}
    
    def filter_by_complexity(self, complexity):
        # 按复杂度过滤
        return [ex for ex in self.data if ex.get('复杂度') == complexity]
```

**数据格式**：
```json
{
    "sql_id": "sql_1",
    "question": "统计2025.07.24的手游全量用户...",
    "复杂度": "中等",
    "table_list": ["dws_mgamejp_login_user_activity_di", ...],
    "knowledge": "竞品业务：sgamecode in (...)"
}
```

---

### 4. StarRocks方言Prompt (`prompt_starrocks.py`)

**新增特性**：

#### 日期函数提示
```python
def get_starrocks_date_functions(self):
    return """StarRocks Date Functions:
    - DATE_FORMAT(date, format): Format date as string
    - STR_TO_DATE(str, format): Convert string to date
    - DATEDIFF(date1, date2): Calculate days between dates
    - Common format: '%Y%m%d' for YYYYMMDD
    """
```

#### 聚合函数提示
```python
def get_starrocks_aggregation_tips(self):
    return """StarRocks Aggregation Tips:
    - COUNT(DISTINCT column) for unique count
    - GROUP_CONCAT(column SEPARATOR ',')
    - BITMAP functions: bitmap_union(), bitmap_count()
    - HLL functions for cardinality estimation
    """
```

#### 窗口函数提示
```python
def get_starrocks_window_functions(self):
    return """StarRocks Window Functions:
    - ROW_NUMBER() OVER (PARTITION BY col ORDER BY col)
    - RANK() / DENSE_RANK()
    - LEAD() / LAG()
    """
```

---

### 5. 主运行脚本 (`run_starrocks.py`)

**核心改造**：

#### 原有流程
```python
# 1. 从jsonl加载数据
dictionaries, task_dict = get_dictionary(db_path, task)

# 2. 从prompts.txt读取Schema
table_info = get_table_info(db_path, sql_data, api)

# 3. 连接特定数据库
if api == "snowflake":
    sql_env.start_db_sf(ex_id)
```

#### 新流程
```python
# 1. 从JSON加载数据
loader = DatasetLoader(args.dataset_path)
examples_dict = loader.get_example_dict()

# 2. 解析Schema文件
schema_parser = SchemaParser(args.schema_path)

# 3. 根据table_list获取Schema
table_info = schema_parser.get_tables_chunks(table_list)

# 4. 连接StarRocks
sql_env = SqlEnvStarRocks(host=args.db_host, port=args.db_port, ...)

# 5. 添加领域知识
if knowledge:
    table_info += f"\n\nDomain Knowledge:\n{knowledge}\n"
```

---

## 🔄 工作流程对比

### 原有ReFoRCE流程
```
1. 读取spider2-snow.jsonl
2. 遍历examples_snow目录
3. 读取每个example的prompts.txt
4. 连接Snowflake/BigQuery
5. 执行SQL并保存结果
```

### StarRocks适配流程
```
1. 读取final_dataset_example.json
2. 解析M-schema/final_algorithm_competition.txt
3. 根据table_list动态组装Schema
4. 添加knowledge到context
5. 连接StarRocks (localhost:9030)
6. 执行SQL并保存结果
```

---

## 📊 功能对比

| 功能 | 原ReFoRCE | StarRocks版 | 状态 |
|------|-----------|-------------|------|
| 列探索 | ✅ | ✅ | 完全兼容 |
| 自我精化 | ✅ | ✅ | 完全兼容 |
| 自我一致性 | ✅ | ✅ | 完全兼容 |
| 投票机制 | ✅ | ✅ | 完全兼容 |
| Schema链接 | LLM/规则 | 基于table_list | 改进 |
| 多方言支持 | 3种 | StarRocks | 新增 |
| 领域知识 | 无 | knowledge字段 | 新增 |
| 复杂度过滤 | 无 | 简单/中等/复杂 | 新增 |

---

## 🎯 使用示例

### 基础运行
```powershell
python run_starrocks.py `
  --dataset_path "final_dataset_example.json" `
  --schema_path "final_algorithm_competition.txt" `
  --db_host "localhost" `
  --generation_model "gpt-4o" `
  --do_self_refinement
```

### 完整模式
```powershell
python run_starrocks.py `
  --dataset_path "final_dataset_example.json" `
  --schema_path "final_algorithm_competition.txt" `
  --db_host "localhost" `
  --generation_model "gpt-4o" `
  --column_exploration_model "gpt-4o" `
  --do_column_exploration `
  --do_self_refinement `
  --do_vote `
  --num_votes 3 `
  --max_iter 5
```

### 按复杂度运行
```powershell
# 简单题目
python run_starrocks.py --filter_complexity "简单"

# 中等题目
python run_starrocks.py --filter_complexity "中等"

# 复杂题目
python run_starrocks.py --filter_complexity "复杂" --max_iter 8
```

---

## 🧪 测试验证

### 环境测试
```powershell
python test_starrocks_setup.py
```

**测试项**：
1. ✅ 依赖导入检查
2. ✅ 自定义模块加载
3. ✅ 数据集加载验证
4. ✅ Schema解析验证
5. ✅ 数据库连接测试
6. ✅ API Key配置检查

### 单模块测试
```powershell
# Schema解析器
python schema_parser.py

# 数据加载器
python data_loader.py

# Prompt模板
python prompt_starrocks.py
```

---

## 📈 性能考虑

### 并发控制
- **API限制**：GPT-4o 建议 `--num_workers 2-4`
- **本地限制**：内存消耗建议 `--max_questions 10-20`
- **数据库**：StarRocks并发能力强，无需特别限制

### 成本估算
- **简单题目**：约 5-10K tokens × $0.005 = $0.025-0.05/题
- **中等题目**：约 15-30K tokens × $0.005 = $0.075-0.15/题
- **复杂题目**：约 30-60K tokens × $0.005 = $0.15-0.30/题

**总成本估算**（假设20个题目）：
- 基础模式：$0.5 - $1
- 列探索模式：$1 - $2
- 完整投票模式：$3 - $6

---

## 🔍 与原项目的关键差异

### 1. Schema来源
| 原项目 | StarRocks版 |
|--------|-------------|
| 从数据库INFORMATION_SCHEMA获取 | 从txt文件解析 |
| 实时查询 | 预先加载 |
| 自动发现所有表 | 根据table_list过滤 |

### 2. Schema链接
| 原项目 | StarRocks版 |
|--------|-------------|
| LLM判断相关性 | 直接使用table_list |
| 可能有误判 | 100%准确 |
| 需要额外API调用 | 零成本 |

### 3. 领域知识
| 原项目 | StarRocks版 |
|--------|-------------|
| 可选external knowledge | 必需knowledge字段 |
| 人工添加 | 数据集内置 |

---

## 🎓 技术亮点

1. **兼容性设计**：保持原有Agent接口不变
2. **模块化架构**：每个组件可独立测试
3. **灵活配置**：支持多种运行模式
4. **错误处理**：完善的超时和异常处理
5. **文档完善**：详细的使用指南和示例

---

## 🚧 已知限制

1. **Schema格式**：仅支持特定格式的txt文件
2. **数据库**：仅支持StarRocks（可扩展）
3. **投票机制**：平局时需要额外LLM调用
4. **内存**：大规模运行需要充足内存

---

## 🔮 未来改进方向

1. **多数据库支持**：扩展到ClickHouse、Doris等
2. **Schema自动发现**：从数据库自动获取Schema
3. **增量更新**：支持只处理新增/失败的题目
4. **结果分析**：自动统计准确率和失败原因
5. **GUI界面**：提供可视化配置和监控

---

## 📚 参考资料

- [ReFoRCE原论文](https://arxiv.org/pdf/2502.00675)
- [StarRocks文档](https://docs.starrocks.io/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)

---

## 👥 贡献者

改造工作由AI助手完成，基于以下输入：
- 原ReFoRCE项目代码
- final_dataset_example.json数据集
- M-schema/final_algorithm_competition.txt

---

## 📄 许可证

遵循原ReFoRCE项目许可证

---

**最后更新时间**：2025-01-18
