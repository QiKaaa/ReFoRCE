# Prompt 管理器迁移指南

## 概述

本次重构将所有 prompt 从分散的字符串和旧类迁移到统一的 **System/User Prompt** 格式管理器。

---

## ✅ 已完成的迁移

### 1. 核心文件

| 文件 | 旧导入 | 新导入 | 状态 |
|------|--------|--------|------|
| `run_starrocks.py` | `from prompt_starrocks import PromptsStarRocks` | `from prompts.starrocks_prompts import StarRocksPromptManager` | ✅ |
| `agent.py` | `from prompt import Prompts` | `from prompts.base_prompts import BasePromptManager` | ✅ |
| `schema_linking_optimized.py` | 硬编码 `SCHEMA_LINKING_PROMPT` | `from prompts.schema_linking_prompts import SchemaLinkingPromptManager` | ✅ |

### 2. 类型签名更新

```python
# agent.py 旧版
def __init__(self, ..., prompt_class: Type[Prompts], ...)

# agent.py 新版
def __init__(self, ..., prompt_class: Union[Type[BasePromptManager], BasePromptManager], ...)
```

### 3. 实例化更新

```python
# run_starrocks.py 旧版
prompt_all = PromptsStarRocks()

# run_starrocks.py 新版
prompt_all = StarRocksPromptManager()
```

---

## 📦 新的 Prompt 管理器结构

```
prompts/
├── __init__.py                    # 包初始化,导出所有管理器
├── base_prompts.py               # 基础 Prompt 管理器 (原 prompt.py)
├── starrocks_prompts.py          # StarRocks 特化管理器 (原 prompt_starrocks.py)
├── schema_linking_prompts.py     # Schema Linking 管理器
├── README.md                     # 使用文档
├── examples.py                   # 使用示例
└── MIGRATION_GUIDE.md            # 本文档
```

---

## 🔄 迁移步骤 (对于其他文件)

### 步骤 1: 更新导入

**旧代码**:
```python
from prompt import Prompts
from prompt_starrocks import PromptsStarRocks
```

**新代码**:
```python
from prompts.base_prompts import BasePromptManager
from prompts.starrocks_prompts import StarRocksPromptManager
```

### 步骤 2: 更新实例化

**旧代码**:
```python
prompt_gen = PromptsStarRocks()
```

**新代码**:
```python
prompt_gen = StarRocksPromptManager()
```

### 步骤 3: 使用新的 System/User 分离模式 (可选)

**旧模式** (一次性 prompt):
```python
prompt = prompt_gen.get_self_refine_prompt(
    table_info, question, pre_info, format_csv, table_struct
)
chat.get_response(prompt)
```

**新模式** (System/User 分离):
```python
# 方式 1: 分别获取
system = prompt_gen.get_self_refine_system_prompt(api="starrocks", table_struct=table_struct)
user = prompt_gen.get_self_refine_user_prompt(table_info, question, pre_info, format_csv, table_struct)

chat.set_system_prompt(system)
response = chat.get_response(user)

# 方式 2: 组合获取 (兼容旧代码)
prompt = prompt_gen.get_self_refine_prompt(
    table_info, question, pre_info, format_csv, table_struct
)
chat.get_response(prompt)
```

---

## 🆕 新特性

### 1. System Prompt 复用

```python
# 一次设置,多次使用
chat.set_system_prompt(prompt_gen.get_self_refine_system_prompt(api="starrocks"))

for question in questions:
    user_prompt = prompt_gen.get_self_refine_user_prompt(...)
    response = chat.get_response(user_prompt)
```

### 2. 更清晰的职责分离

- **System Prompt**: 定义 LLM 的角色、规则、输出格式
- **User Prompt**: 提供具体的输入数据和问题

### 3. 更易于维护

- 所有 prompt 集中在 `prompts/` 目录
- 每个功能模块有独立的管理器
- 统一的接口规范

---

## 🔍 验证迁移

### 检查 1: 导入是否正确

```python
# 在 Python 中测试
from prompts.starrocks_prompts import StarRocksPromptManager
prompt_mgr = StarRocksPromptManager()
print(prompt_mgr)  # 应该成功打印
```

### 检查 2: 旧功能是否保留

```python
# 所有旧方法仍然可用 (兼容模式)
prompt = prompt_mgr.get_exploration_prompt(api="starrocks", table_struct="...")
print(len(prompt) > 0)  # 应该为 True
```

### 检查 3: 新功能是否可用

```python
# 新的 system/user 分离模式
system = prompt_mgr.get_exploration_system_prompt(api="starrocks")
user = prompt_mgr.get_exploration_user_prompt(table_info="...", question="...", table_struct="...")
print(len(system) > 0 and len(user) > 0)  # 应该为 True
```

---

## ⚠️ 注意事项

### 1. 保持向后兼容

所有旧的 `get_xxx_prompt()` 方法仍然保留并正常工作。你可以：
- **渐进式迁移**: 先更新导入,后续再逐步使用 system/user 分离模式
- **快速迁移**: 只更新导入和实例化,不改变调用方式

### 2. 类型提示

如果使用类型提示,记得更新:
```python
from typing import Union, Type
from prompts.base_prompts import BasePromptManager

def my_function(prompt_class: Union[Type[BasePromptManager], BasePromptManager]):
    ...
```

### 3. Schema Linking 特殊处理

`OptimizedSchemaLinker` 类现在内部使用 `SchemaLinkingPromptManager`:
```python
# 旧代码 (硬编码)
prompt = SCHEMA_LINKING_PROMPT.format(question=..., knowledge=..., all_table_schemas=...)

# 新代码 (使用管理器)
self.prompt_manager = SchemaLinkingPromptManager()
prompt = self.prompt_manager.get_schema_linking_prompt(question, knowledge, all_table_schemas)
```

---

## 📝 待迁移文件 (可选)

以下文件目前仍使用旧的导入,但不影响主流程:

| 文件 | 是否影响主流程 | 优先级 |
|------|---------------|--------|
| `run.py` | ❌ (legacy) | 低 |
| `demo.py` | ❌ (示例文件) | 低 |
| `prompt_starrocks.py` | ❌ (已被取代) | 可删除 |
| `prompt.py` | ❌ (已被取代) | 可删除 |

---

## ✅ 完成检查清单

- [✅] 更新 `run_starrocks.py` 的导入
- [✅] 更新 `agent.py` 的类型签名
- [✅] 更新 `schema_linking_optimized.py` 使用 prompt 管理器
- [✅] 创建 `prompts/` 包和所有管理器
- [✅] 编写文档和示例
- [✅] 验证 linter 无错误
- [ ] 运行测试确保功能正常 (用户测试)
- [ ] (可选) 删除旧文件 `prompt.py` 和 `prompt_starrocks.py`

---

## 🚀 下一步建议

1. **运行现有测试**: 确保迁移没有破坏功能
   ```bash
   uv run run_starrocks.py --max_questions 1 ...
   ```

2. **逐步使用新特性**: 在新代码中使用 system/user 分离模式

3. **清理旧代码**: 确认无问题后删除 `prompt.py` 和 `prompt_starrocks.py`

4. **更新其他文件**: 如果需要,迁移 `demo.py` 等示例文件

---

## 📚 相关文档

- [Prompts README](./README.md) - 详细使用指南
- [Examples](./examples.py) - 代码示例
- [Base Prompts](./base_prompts.py) - 基础管理器源码
- [StarRocks Prompts](./starrocks_prompts.py) - StarRocks管理器源码
- [Schema Linking Prompts](./schema_linking_prompts.py) - Schema Linking管理器源码
