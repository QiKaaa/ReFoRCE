# 🐛 线程文件名冲突修复报告

## 问题描述

用户报告：**所有线程的结果都写入一个文件里了**

## 🔍 问题分析

### 1. **观察到的现象**

在 `output/test-sl-vote/sql_1/` 目录下，只有一个文件：
```
decompose_result.csv
decompose_result.sql
```

而期望应该有3个不同的文件（对应3个线程）：
```
decompose_linked_0_result.csv / .sql
decompose_linked_1_result.csv / .sql
decompose_linked_2_result.csv / .sql
```

### 2. **根本原因**

在 `run_starrocks.py` 中，启动线程时**没有传递 `thread_prefix` 参数**，导致所有线程都使用默认值 `""`，最终生成相同的文件名。

**问题代码**（第607-628行）：

```python
thread = threading.Thread(
    target=execute_single_question,
    args=(
        sql_id, question, table_list, knowledge,
        schema_parser, args,
        csv_save_pathi, log_pathi, sql_save_pathi,
        search_directory, format_csv,
        schema_linker, True,
        complexity,
        cached_exploration_result,
        cached_linked_schema,
        prompt_manager  # ❌ 缺少 thread_prefix 参数
    )
)
```

### 3. **文件命名逻辑**

在 `execute_single_question` 函数中（第311-320行）：

```python
if thread_prefix:
    prefix_parts = thread_prefix.split('_')
    if prefix_parts[0] in ['linked', 'original']:
        file_prefix = f"decompose_{thread_prefix}"  # 例如: decompose_linked_0
    else:
        file_prefix = f"decompose_{thread_prefix}"
else:
    file_prefix = "decompose"  # ❌ 所有线程都用这个默认值！

vote_csv_path = os.path.join(search_directory, f"{file_prefix}_result.csv")
vote_sql_path = os.path.join(search_directory, f"{file_prefix}_result.sql")
```

**结果**：由于 `thread_prefix=""` （默认值），所有线程生成的文件名都是：
- `decompose_result.csv`
- `decompose_result.sql`

→ 后面的线程覆盖了前面线程的结果！

---

## ✅ 修复方案

### 修复位置1：Schema Linking投票模式（第607-628行）

**修复前**：
```python
thread = threading.Thread(
    target=execute_single_question,
    args=(
        ...,
        prompt_manager  # ❌ 缺少参数
    )
)
```

**修复后**：
```python
thread = threading.Thread(
    target=execute_single_question,
    args=(
        ...,
        prompt_manager,  # ✨ 添加prompt_manager
        f"linked_{i}"  # ✨ 传递线程前缀
    )
)
```

### 修复位置2：原始Schema线程（第581-603行，已注释）

**修复前**：
```python
#     thread = threading.Thread(
#         target=execute_single_question,
#         args=(
#             ...,
#             prompt_manager  # ❌ 缺少参数
#         )
#     )
```

**修复后**：
```python
#     thread = threading.Thread(
#         target=execute_single_question,
#         args=(
#             ...,
#             prompt_manager,  # ✨ 添加prompt_manager
#             f"original_{i}"  # ✨ 传递线程前缀
#         )
#     )
```

### 修复位置3：原始投票模式（第631-653行）

**修复前**：
```python
thread = threading.Thread(
    target=execute_single_question,
    args=(
        ...,
        prompt_manager  # ❌ 缺少参数
    )
)
```

**修复后**：
```python
thread = threading.Thread(
    target=execute_single_question,
    args=(
        ...,
        prompt_manager,  # ✨ 添加prompt_manager
        f"vote_{i}"  # ✨ 传递线程前缀
    )
)
```

### 修复位置4：非投票模式（第680-695行）

**修复前**：
```python
execute_single_question(
    ...,
    prompt_manager  # ❌ 缺少参数
)
```

**修复后**：
```python
execute_single_question(
    ...,
    prompt_manager,  # ✨ 添加prompt_manager
    ""  # ✨ 非投票模式不需要线程前缀
)
```

---

## 📊 修复后的文件命名

### Schema Linking投票模式（num_votes=3）

| 线程编号 | thread_prefix | 生成的文件名 |
|---------|--------------|-------------|
| Thread 0 | `"linked_0"` | `decompose_linked_0_result.csv/sql` |
| Thread 1 | `"linked_1"` | `decompose_linked_1_result.csv/sql` |
| Thread 2 | `"linked_2"` | `decompose_linked_2_result.csv/sql` |

### 原始投票模式（num_votes=3）

| 线程编号 | thread_prefix | 生成的文件名 |
|---------|--------------|-------------|
| Thread 0 | `"vote_0"` | `decompose_vote_0_result.csv/sql` |
| Thread 1 | `"vote_1"` | `decompose_vote_1_result.csv/sql` |
| Thread 2 | `"vote_2"` | `decompose_vote_2_result.csv/sql` |

### 非投票模式

| thread_prefix | 生成的文件名 |
|--------------|-------------|
| `""` | `result.csv/sql` (直接使用默认名称) |

---

## ✅ 验证检查

- ✅ **语法检查**：无linter错误
- ✅ **所有调用点已修复**：
  - Schema Linking投票模式 ✅
  - 原始Schema线程（注释部分）✅
  - 原始投票模式 ✅
  - 非投票模式 ✅

---

## 🎯 预期效果

**修复前（错误）**：
```
output/test-sl-vote/sql_1/
├── decompose_result.csv  ❌ (被覆盖3次)
└── decompose_result.sql  ❌ (被覆盖3次)
```

**修复后（正确）**：
```
output/test-sl-vote/sql_1/
├── decompose_linked_0_result.csv  ✅
├── decompose_linked_0_result.sql  ✅
├── decompose_linked_1_result.csv  ✅
├── decompose_linked_1_result.sql  ✅
├── decompose_linked_2_result.csv  ✅
└── decompose_linked_2_result.sql  ✅
```

投票阶段可以正确收集所有候选并选择最佳SQL！

---

## 🔄 完整的工作流程（修复后）

```
启动3个linked线程
  ↓
Thread 0: thread_prefix="linked_0" → decompose_linked_0_result.sql ✅
Thread 1: thread_prefix="linked_1" → decompose_linked_1_result.sql ✅
Thread 2: thread_prefix="linked_2" → decompose_linked_2_result.sql ✅
  ↓
等待所有线程完成
  ↓
动态收集：
  - decompose_linked_0_result.sql
  - decompose_linked_1_result.sql
  - decompose_linked_2_result.sql
  ↓
统一投票选择最佳SQL
  ↓
生成最终 result.sql ✅
```
