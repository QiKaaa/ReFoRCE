# 并行Schema Linking线程安全修复

## 🐛 问题描述

### 问题1: API调用参数错误
```
ERROR: BaseChat.get_model_response_txt() takes 2 positional arguments but 3 were given
```

**原因**: `get_model_response_txt()` 只接受一个 `prompt` 参数,但代码传了 `system_prompt` 和 `user_prompt` 两个参数。

### 问题2: 线程竞态条件
两个并行解析器(MACSQLCoTParse 和 RSLSQLBiDirParse)共享同一个 `chat_session`,导致:
- System prompt 互相覆盖
- 消息历史混乱
- 并发修改冲突

---

## ✅ 解决方案

### 1. 修正API调用方式

**修改前**:
```python
# ❌ 错误: 传递两个参数
chat_session.clear_messages()
response = chat_session.get_model_response_txt(system_prompt, user_prompt)
```

**修改后**:
```python
# ✅ 正确: 分两步设置
chat_session.clear_messages()                    # 清空历史
chat_session.set_system_prompt(system_prompt)   # 设置system prompt
response = chat_session.get_model_response_txt(user_prompt)  # 发送user prompt
```

**涉及方法**:
- `_call_macsql_parser()` (line 165-167)
- `_call_rslsql_parser()` (line 249-251, 273-276)

---

### 2. 解决线程竞态问题

**修改前**:
```python
# ❌ 错误: 共享chat_session导致竞态
if chat_session:
    chat_macsql = chat_session  # 直接使用传入的session
    chat_rslsql = GPTChat(...)  # 只为第二个解析器创建新session
```

**修改后**:
```python
# ✅ 正确: 为每个解析器创建独立session
if chat_session:
    # 提取配置参数
    azure = chat_session.azure if hasattr(chat_session, 'azure') else False
    model = chat_session.model if hasattr(chat_session, 'model') else "deepseek-chat"
    
    # 为两个解析器分别创建独立的session
    chat_macsql = GPTChat(azure, model)
    chat_rslsql = GPTChat(azure, model)
else:
    # 默认配置
    chat_macsql = GPTChat(False, "deepseek-chat")
    chat_rslsql = GPTChat(False, "deepseek-chat")

logger.info("[Parallel] Created independent chat sessions for each parser")
```

**涉及方法**:
- `link_schema()` (line 632-641)

---

## 🔧 技术细节

### Chat Session独立性保证

每个解析器拥有:
1. **独立的消息历史** (`messages` 列表)
2. **独立的system prompt** (通过 `set_system_prompt()` 设置)
3. **独立的API调用上下文** (不会相互干扰)

### 执行流程

```
link_schema()
├── 创建独立的chat_macsql session
├── 创建独立的chat_rslsql session
├── ThreadPoolExecutor并行执行:
│   ├── Thread 1: _call_macsql_parser(chat_macsql)
│   │   ├── clear_messages()
│   │   ├── set_system_prompt(macsql_system)
│   │   └── get_model_response_txt(macsql_user)
│   │
│   └── Thread 2: _call_rslsql_parser(chat_rslsql)
│       ├── Step 1: 表选择
│       │   ├── clear_messages()
│       │   ├── set_system_prompt(rslsql_table_system)
│       │   └── get_model_response_txt(rslsql_table_user)
│       │
│       └── Step 2: SQL生成
│           ├── clear_messages()
│           ├── set_system_prompt(rslsql_sql_system)
│           └── get_model_response_txt(rslsql_sql_user)
│
└── 合并结果
```

---

## 📊 影响范围

### 修改文件
1. `parallel_schema_linker.py`
   - `_call_macsql_parser()` - API调用方式
   - `_call_rslsql_parser()` - API调用方式
   - `link_schema()` - Chat session创建逻辑

2. `chat.py`
   - 新增 `clear_messages()` 方法 (支持保留system prompt)

### 向后兼容性
- ✅ 完全向后兼容
- ✅ 不影响现有代码逻辑
- ✅ 只修复了并发安全问题

---

## 🧪 测试验证

### 测试场景
```bash
# 并行Schema Linking投票模式
python run_starrocks.py \
  --do_schema_linking_vote \
  --do_vote \
  --num_votes 3 \
  --max_questions 1
```

### 预期行为
1. 两个解析器并行执行,互不干扰
2. 每个解析器使用正确的system prompt
3. 没有竞态条件错误
4. 正确合并两个解析器的结果

### 日志验证
```
[Parallel] Created independent chat sessions for each parser
[MACSQLCoTParse] Starting...
[RSLSQLBiDirParse] Starting...
[Parallel] MACSQLCoTParse completed
[Parallel] RSLSQLBiDirParse completed
[Merge] Starting result merge...
[Merge] Result: X tables, Y columns
```

---

## 📝 关键要点

### System Prompt设置最佳实践

1. **分离设置**:
   ```python
   chat_session.set_system_prompt(system_prompt)  # 先设置system
   response = chat_session.get_model_response_txt(user_prompt)  # 再发送user
   ```

2. **每次对话前清空**:
   ```python
   chat_session.clear_messages()  # 避免历史消息干扰
   chat_session.set_system_prompt(...)
   ```

3. **并发场景隔离**:
   - 每个线程使用独立的 `GPTChat` 实例
   - 避免共享 `chat_session` 对象

### 线程安全原则

1. **不可变共享**: Schema数据(只读)可以共享
2. **状态隔离**: Chat session(有状态)必须隔离
3. **结果合并**: 在所有线程完成后进行

---

## 🎯 总结

通过以下两个关键修复,确保了并行Schema Linking的线程安全性:

1. ✅ **API调用修复**: 正确使用 `set_system_prompt()` + `get_model_response_txt()`
2. ✅ **线程隔离**: 为每个解析器创建独立的chat session

这确保了:
- 无竞态条件
- System prompt正确隔离
- 并行执行稳定可靠
- 结果合并准确无误
