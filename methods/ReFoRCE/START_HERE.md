# 🚀 快速开始 - 仅需 3 步！

## Step 1: 安装环境（Python 3.12）

```powershell
# 进入项目目录
cd E:\Project\track3_2\ReFoRCE\methods\ReFoRCE

# 创建虚拟环境（使用 Python 3.12）
uv venv --python 3.12

# 激活环境
.\.venv\Scripts\Activate.ps1

# 安装依赖
uv pip install -r requirements_starrocks.txt
```

---

## Step 2: 配置 API Key 和数据库

**方式 A：使用 .env 文件（强烈推荐）**

```powershell
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 文件
notepad .env

# 3. 填入配置（示例）
```

`.env` 文件内容示例：
```env
# API Key
OPENAI_API_KEY=sk-proj-your-real-key-here

# StarRocks 数据库（会自动从这里读取，无需命令行参数）
DB_HOST=localhost
DB_PORT=9030
DB_USER=root
DB_PASSWORD=
DB_NAME=final_algorithm_competition
```

**方式 B：使用配置脚本**

1. 编辑 `set_env.ps1`，填入你的 API Key：

```powershell
# 打开文件编辑
notepad set_env.ps1

# 将这行：
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# 改为你的真实 Key：
$env:OPENAI_API_KEY = "sk-proj-xxxxxxxxxxxxx"
```

2. 运行配置脚本：

```powershell
.\set_env.ps1
```

**注意**: 数据库配置只能通过 `.env` 文件设置，不再支持命令行参数。

---

## Step 3: 运行测试

```powershell
# 验证配置（推荐先运行）
python check_config.py

# 测试环境
python test_starrocks_setup.py

# 测试运行（1个问题）
python run_starrocks.py `
  --max_questions 1 `
  --generation_model gpt-4o `
  --do_self_refinement
```

---

## 🎯 完整运行示例

### 基础模式（快速）

```powershell
python run_starrocks.py `
  --generation_model gpt-4o `
  --do_self_refinement `
  --max_questions 5
```

### 高精度模式

```powershell
python run_starrocks.py `
  --generation_model gpt-4o `
  --column_exploration_model gpt-4o `
  --do_column_exploration `
  --do_self_refinement `
  --do_vote `
  --num_votes 3
```

### 省钱模式（使用 mini 模型）

```powershell
python run_starrocks.py `
  --generation_model gpt-4o-mini `
  --do_self_refinement `
  --max_questions 10
```

---

## 📖 详细文档

- **API Key 配置详解**: `CONFIG_EXAMPLE.md`
- **完整功能指南**: `QUICKSTART_STARROCKS.md`
- **技术文档**: `README_STARROCKS.md`

---

## ⚠️ 常见问题

**Q: 提示 "API Key not found"**

A: 检查环境变量：
```powershell
echo $env:OPENAI_API_KEY
```

**Q: 如何使用 Azure OpenAI？**

A: 设置 Azure 变量并加上 `--azure` 参数：
```powershell
$env:AZURE_ENDPOINT = "https://xxx.openai.azure.com/"
$env:AZURE_OPENAI_KEY = "your-key"
python run_starrocks.py --azure --generation_model gpt-4o
```

**Q: 数据库连接失败？**

A: 检查 StarRocks 是否运行：
```powershell
netstat -an | findstr 9030
```

---

## 🎉 成功后

查看结果：
```powershell
# 生成的 SQL
cat output/starrocks-log/sql_1/result.sql

# 执行结果
cat output/starrocks-log/sql_1/result.csv

# 详细日志
cat output/starrocks-log/sql_1/log.log
```

---

**需要帮助？** 查看 `CONFIG_EXAMPLE.md` 了解更多配置方式！
