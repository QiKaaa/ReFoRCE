## Prompts 包使用指南

### 📋 概述

这个包统一管理所有 Prompt，采用 **System/User Prompt 分离**的设计模式，提高可维护性和可扩展性。

---

### 🏗️ 架构设计

```
prompts/
├── __init__.py                    # 包入口
├── base_prompts.py                # 基础 Prompt 管理器
├── starrocks_prompts.py           # StarRocks 专用 Prompt
├── schema_linking_prompts.py      # Schema Linking Prompt
├── README.md                      # 本文档
└── examples.py                    # 使用示例
```

---

### 🎯 设计原则

#### 1. **System/User 分离**

**System Prompt**: 定义角色、规则、能力
- 设定AI的角色和专业能力
- 定义核心规则和约束
- 提供输出格式要求
- 不包含具体任务数据

**User Prompt**: 提供具体任务和数据
- 包含具体的问题
- 提供数据库 schema
- 包含领域知识
- 提供示例数据

#### 2. **向后兼容**

- 保留所有旧接口方法
- 新旧接口可以并存
- 逐步迁移，不破坏现有代码

#### 3. **模块化扩展**

- 基础类提供通用功能
- 子类扩展特定数据库
- 易于添加新数据库支持

---

### 📖 使用方法

#### 方法 1: 使用新接口（推荐）

```python
from prompts import StarRocksPromptManager

# 初始化
prompt_mgr = StarRocksPromptManager()

# 获取 System Prompt
system_prompt = prompt_mgr.get_self_refine_system_prompt(
    api="starrocks",
    table_struct="table1, table2, table3"
)

# 获取 User Prompt
user_prompt = prompt_mgr.get_self_refine_user_prompt(
    table_info="...",
    question="统计2025.07.24的用户数量",
    pre_info="...",  # 列探索结果
    format_csv="...",  # 输出格式
    table_struct="table1, table2"
)

# 组合使用（如果需要）
full_prompt = f"{system_prompt}\n\n{user_prompt}"
```

#### 方法 2: 使用兼容接口（无需修改现有代码）

```python
from prompts import StarRocksPromptManager

prompt_mgr = StarRocksPromptManager()

# 直接使用旧接口（内部自动组合 system + user）
prompt = prompt_mgr.get_self_refine_prompt(
    table_info="...",
    task="...",
    pre_info="...",
    question="...",
    api="starrocks",
    format_csv="...",
    table_struct="..."
)
```

#### 方法 3: Schema Linking

```python
from prompts import SchemaLinkingPromptManager

sl_prompt_mgr = SchemaLinkingPromptManager()

# 新接口
system = sl_prompt_mgr.get_schema_linking_system_prompt()
user = sl_prompt_mgr.get_schema_linking_user_prompt(
    question="...",
    knowledge="...",
    all_table_schemas="..."
)

# 或使用兼容接口
prompt = sl_prompt_mgr.get_schema_linking_prompt(
    question="...",
    knowledge="...",
    all_table_schemas="..."
)
```

---

### 🔧 与现有代码集成

#### 替换方案 1: 最小改动（推荐渐进式迁移）

在 `run_starrocks.py` 中：

```python
# 旧代码
from prompt_starrocks import PromptsStarRocks
prompt_all = PromptsStarRocks()

# 新代码（只需改一行）
from prompts import StarRocksPromptManager
prompt_all = StarRocksPromptManager()

# 其他代码无需修改，因为所有旧方法都保留了
```

#### 替换方案 2: 完全迁移（利用新特性）

```python
from prompts import StarRocksPromptManager

prompt_mgr = StarRocksPromptManager()

# 在 agent.py 中修改 chat 调用
# 旧方式
response = chat.get_response(combined_prompt)

# 新方式（分离 system/user）
chat.set_system_prompt(system_prompt)
response = chat.get_response(user_prompt)
```

---

### 📚 Prompt 类型说明

#### 1. **Exploration Prompt** (列探索)

**用途**: 生成探索性 SQL，了解数据分布

**System Prompt 内容**:
- 定义数据分析师角色
- 规定探索查询规则
- 提供 SQL 示例格式
- 列出可用函数

**User Prompt 内容**:
- 数据库 schema
- 具体问题
- 可用表列表

#### 2. **Self-Refine Prompt** (SQL 生成/精化)

**用途**: 生成最终 SQL 查询

**System Prompt 内容**:
- 定义 SQL 开发专家角色
- SQL 语法规则
- 函数使用指南
- 优化建议
- 输出格式要求

**User Prompt 内容**:
- 数据库 schema
- 具体问题
- 列探索结果（few-shot）
- 输出格式要求

#### 3. **Self-Consistency Prompt** (一致性检查)

**用途**: 验证 SQL 正确性

**System Prompt 内容**:
- 定义验证专家角色
- 检查清单
- 决策流程

**User Prompt 内容**:
- 原始任务
- 当前 SQL
- 执行结果
- 预期格式

#### 4. **Schema Linking Prompt** (Schema 链接)

**用途**: 选择相关列

**System Prompt 内容**:
- 定义 schema 分析专家角色
- 列选择规则
- JSON 输出格式

**User Prompt 内容**:
- 问题
- 领域知识
- 完整 schema

---

### 🎨 自定义 Prompt

#### 扩展新数据库

```python
from prompts.base_prompts import BasePromptManager

class PostgreSQLPromptManager(BasePromptManager):
    """PostgreSQL 专用 Prompt"""
    
    def get_self_refine_system_prompt(self, api="postgresql", table_struct=""):
        system_prompt = """You are a PostgreSQL expert...
        
        PostgreSQL Specific Features:
        - ARRAY operations
        - JSONB functions
        - Window functions
        - CTEs (WITH clauses)
        ...
        """
        return system_prompt
    
    def _get_dialect_basic_rules(self, api):
        if api == "postgresql":
            return """PostgreSQL Syntax:
            - Use double quotes for identifiers
            - LIMIT/OFFSET for pagination
            - RETURNING clause support
            """
        return super()._get_dialect_basic_rules(api)
```

#### 添加新 Prompt 类型

```python
class StarRocksPromptManager(BasePromptManager):
    
    def get_data_quality_check_system_prompt(self):
        """数据质量检查 System Prompt"""
        return """You are a data quality analyst...
        
        Check for:
        1. NULL values
        2. Duplicates
        3. Outliers
        4. Data consistency
        ...
        """
    
    def get_data_quality_check_user_prompt(self, table_name, columns):
        """数据质量检查 User Prompt"""
        return f"""Table: {table_name}
        Columns to check: {columns}
        
        Generate SQL queries to check data quality."""
```

---

### 🧪 测试

查看 `examples.py` 获取完整测试示例：

```bash
cd e:\Project\track3_2\ReFoRCE\methods\ReFoRCE
python -m prompts.examples
```

---

### 📊 对比：旧 vs 新

| 特性 | 旧设计 | 新设计 |
|------|--------|--------|
| **Prompt 组织** | 单一字符串 | System + User 分离 |
| **可读性** | 混合在一起 | 清晰的角色定义 |
| **可维护性** | 难以修改 | 模块化，易于扩展 |
| **复用性** | 低 | 高（System 可复用） |
| **测试性** | 难以单独测试 | 可分别测试 |
| **兼容性** | N/A | 完全向后兼容 |

---

### 🔄 迁移步骤

#### 阶段 1: 安装新包（已完成）
- ✅ 创建 `prompts/` 目录
- ✅ 实现基础类和 StarRocks 类
- ✅ 添加兼容接口

#### 阶段 2: 验证兼容性
```bash
# 运行现有测试，确保无破坏
python run_starrocks.py --max_questions 1
```

#### 阶段 3: 逐步迁移
```python
# 在新代码中使用新接口
from prompts import StarRocksPromptManager
prompt_mgr = StarRocksPromptManager()

# 旧代码继续使用兼容接口
prompt = prompt_mgr.get_self_refine_prompt(...)
```

#### 阶段 4: 完全迁移（可选）
- 更新 `agent.py` 使用新接口
- 更新 chat 类支持 system prompt
- 移除旧文件（`prompt.py`, `prompt_starrocks.py`）

---

### ❓ 常见问题

#### Q1: 新包会破坏现有代码吗？
**A**: 不会。所有旧方法都保留并且功能一致。

#### Q2: 必须立即迁移吗？
**A**: 不必须。可以渐进式迁移，新旧代码并存。

#### Q3: System/User 分离的好处是什么？
**A**: 
- System 定义角色和规则，可以复用
- User 提供具体数据，每次不同
- 更容易调试和优化
- 符合 OpenAI 等 API 的最佳实践

#### Q4: 如何添加新数据库支持？
**A**: 继承 `BasePromptManager`，重写方法即可。

#### Q5: 性能影响？
**A**: 无影响。Prompt 生成在内存中进行，耗时可忽略。

---

### 📝 最佳实践

1. **新项目**: 直接使用新接口
2. **现有项目**: 先替换 import，验证后再逐步迁移
3. **Prompt 优化**: 在新接口中调整更方便
4. **多数据库**: 使用基础类统一接口

---

### 🔗 相关文档

- [examples.py](examples.py) - 完整使用示例
- [base_prompts.py](base_prompts.py) - 基础类实现
- [starrocks_prompts.py](starrocks_prompts.py) - StarRocks 实现
- [schema_linking_prompts.py](schema_linking_prompts.py) - Schema Linking 实现

---

**更新时间**: 2025-01-18  
**版本**: v1.0.0
