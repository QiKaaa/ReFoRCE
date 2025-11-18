# 📋 环境配置说明

## 核心变更

**重要**: 数据库配置现在**仅**从 `.env` 文件中读取，不再支持命令行参数。

---

## 快速配置（3步）

### Step 1: 复制模板

```powershell
cd E:\Project\track3_2\ReFoRCE\methods\ReFoRCE
cp .env.example .env
```

### Step 2: 编辑 `.env` 文件

```powershell
notepad .env
```

填入配置：

```env
# ----- API Key 配置 -----
OPENAI_API_KEY=sk-proj-your-real-api-key-here

# ----- StarRocks 数据库配置 -----
DB_HOST=localhost
DB_PORT=9030
DB_USER=root
DB_PASSWORD=
DB_NAME=final_algorithm_competition
```

### Step 3: 运行程序

```powershell
# 程序会自动从 .env 读取配置
python run_starrocks.py --generation_model gpt-4o
```

---

## 配置项说明

### API Key 配置

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 | - | 是* |
| `AZURE_ENDPOINT` | Azure OpenAI端点 | - | 是* |
| `AZURE_OPENAI_KEY` | Azure OpenAI密钥 | - | 是* |
| `DS_API_KEY` | DeepSeek API密钥 | - | 否 |

> *注意: `OPENAI_API_KEY` 和 `AZURE_*` 二选一

### 数据库配置

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `DB_HOST` | StarRocks主机地址 | `localhost` | 否 |
| `DB_PORT` | StarRocks端口 | `9030` | 否 |
| `DB_USER` | 数据库用户名 | `root` | 否 |
| `DB_PASSWORD` | 数据库密码 | `""` | 否 |
| `DB_NAME` | 数据库名称 | `final_algorithm_competition` | 否 |

---

## 使用示例

### 场景 1: 本地 StarRocks + OpenAI

`.env` 文件：
```env
OPENAI_API_KEY=sk-proj-abc123...

DB_HOST=localhost
DB_PORT=9030
DB_USER=root
DB_PASSWORD=
DB_NAME=final_algorithm_competition
```

运行：
```powershell
python run_starrocks.py --generation_model gpt-4o
```

### 场景 2: 远程 StarRocks + Azure OpenAI

`.env` 文件：
```env
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-azure-key

DB_HOST=192.168.1.100
DB_PORT=9030
DB_USER=admin
DB_PASSWORD=your_password
DB_NAME=final_algorithm_competition
```

运行：
```powershell
python run_starrocks.py --azure --generation_model gpt-4o
```

### 场景 3: 本地测试环境

`.env` 文件：
```env
OPENAI_API_KEY=sk-test-key

DB_HOST=127.0.0.1
DB_PORT=9030
DB_USER=root
DB_PASSWORD=
DB_NAME=test_database
```

运行：
```powershell
python run_starrocks.py --max_questions 1
```

---

## 验证配置

运行测试脚本检查配置是否正确：

```powershell
python test_starrocks_setup.py
```

输出示例：
```
✓ 环境变量检查
  OpenAI Key: sk-proj-xxx...
  
✓ 数据库配置
  Host: localhost:9030
  Database: final_algorithm_competition
  User: root
  
✓ StarRocks 连接测试
  连接成功！
  
✓ Schema 文件检查
  找到 45 个表
  
🎉 所有测试通过！
```

---

## 常见问题

### Q1: 为什么要用 .env 而不是命令行参数？

**A:** 
- ✅ **安全性**: 避免密码出现在命令历史中
- ✅ **便捷性**: 一次配置，多次使用
- ✅ **团队协作**: 统一配置方式
- ✅ **版本控制**: `.env` 可以被 `.gitignore` 排除

### Q2: .env 文件不生效怎么办？

**A:** 检查以下几点：
1. 文件名必须是 `.env`（不是 `.env.txt`）
2. 文件必须在 `methods/ReFoRCE/` 目录下
3. 确保安装了 `python-dotenv`：
   ```powershell
   uv pip install python-dotenv
   ```
4. 查看程序开头是否有：
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### Q3: 如何在不同环境间切换？

**A:** 创建多个配置文件：

```powershell
# 开发环境
cp .env.example .env.dev
# 编辑 .env.dev

# 生产环境
cp .env.example .env.prod
# 编辑 .env.prod

# 使用时复制对应文件
cp .env.dev .env  # 使用开发环境
cp .env.prod .env # 使用生产环境
```

### Q4: 数据库密码包含特殊字符怎么办？

**A:** 直接填写即可，无需转义：

```env
# 正确 ✓
DB_PASSWORD=P@ssw0rd!#$

# 不需要引号或转义
```

### Q5: 如何检查当前使用的配置？

**A:** 运行程序时会输出配置信息：

```powershell
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Host:', os.getenv('DB_HOST')); print('Port:', os.getenv('DB_PORT'))"
```

---

## 安全建议

### ✅ 应该做的

1. **添加 .env 到 .gitignore**
   ```gitignore
   .env
   .env.local
   .env.*.local
   ```

2. **使用 .env.example 作为模板**
   - 提交 `.env.example` 到版本控制
   - 不包含真实的密钥

3. **定期轮换密钥**
   - API Key 每 3-6 个月更换一次
   - 数据库密码定期修改

4. **限制文件权限**（Linux/Mac）
   ```bash
   chmod 600 .env
   ```

### ❌ 不应该做的

1. ❌ 提交 `.env` 到 Git
2. ❌ 在代码中硬编码密钥
3. ❌ 共享包含真实密钥的配置文件
4. ❌ 在公共场合展示配置内容

---

## 配置文件对比

### 旧方式（命令行参数）❌

```powershell
python run_starrocks.py `
  --db_host localhost `
  --db_port 9030 `
  --db_user root `
  --db_password "secret" `  # 密码暴露在命令行！
  --db_name final_algorithm_competition
```

问题：
- 密码出现在命令历史
- 参数过多，容易出错
- 每次运行都要输入

### 新方式（.env 文件）✅

`.env`:
```env
DB_HOST=localhost
DB_PORT=9030
DB_USER=root
DB_PASSWORD=secret
DB_NAME=final_algorithm_competition
```

运行：
```powershell
python run_starrocks.py  # 简洁！
```

优势：
- ✅ 密码安全存储
- ✅ 一次配置，多次使用
- ✅ 易于管理和切换环境

---

## 完整配置示例

创建一个完整的 `.env` 文件：

```env
# ========================================
# ReFoRCE StarRocks 环境配置
# ========================================

# ----- API Key 配置 -----
# 使用 OpenAI
OPENAI_API_KEY=sk-proj-your-key-here

# 或使用 Azure OpenAI（取消注释）
# AZURE_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_KEY=your-azure-key-here

# 或使用 DeepSeek（取消注释）
# DS_API_KEY=your-deepseek-key-here

# ----- StarRocks 数据库配置 -----
DB_HOST=localhost
DB_PORT=9030
DB_USER=root
DB_PASSWORD=
DB_NAME=final_algorithm_competition

# ----- 可选：代理配置 -----
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080

# ----- 可选：日志配置 -----
# LOG_LEVEL=INFO
# LOG_FILE=app.log
```

---

需要帮助？查看 `START_HERE.md` 了解快速上手流程！
