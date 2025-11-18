# 🔧 API Key 配置指南

## 方式 1：环境变量（推荐）

### Windows PowerShell

```powershell
# OpenAI API
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# 或者 Azure OpenAI
$env:AZURE_ENDPOINT = "https://your-resource.openai.azure.com/"
$env:AZURE_OPENAI_KEY = "your-azure-key-here"
```

### Linux/Mac Bash

```bash
# OpenAI API
export OPENAI_API_KEY="sk-your-api-key-here"

# 或者 Azure OpenAI
export AZURE_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_KEY="your-azure-key-here"
```

### 持久化配置（Windows）

创建 `set_env.ps1` 文件：

```powershell
# set_env.ps1 - API Key配置
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# 或者使用 Azure
# $env:AZURE_ENDPOINT = "https://your-resource.openai.azure.com/"
# $env:AZURE_OPENAI_KEY = "your-azure-key-here"

Write-Host "✓ API Key 已设置" -ForegroundColor Green
```

每次运行前执行：
```powershell
.\set_env.ps1
python run_starrocks.py --generation_model gpt-4o
```

---

## 方式 2：`.env` 文件

创建 `.env` 文件在 `methods/ReFoRCE/` 目录下：

```env
# .env - API密钥配置文件
# 请勿提交此文件到Git！

# OpenAI 配置
OPENAI_API_KEY=sk-your-api-key-here

# 或者 Azure OpenAI 配置
# AZURE_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_KEY=your-azure-key-here

# DeepSeek 配置（可选）
# DS_API_KEY=your-deepseek-key-here
```

然后安装 `python-dotenv`：

```powershell
uv pip install python-dotenv
```

在 `run_starrocks.py` 开头添加：

```python
from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件
```

---

## 方式 3：系统环境变量（Windows）

### 临时设置（当前会话）

```powershell
$env:OPENAI_API_KEY = "sk-your-key"
```

### 永久设置（所有会话）

```powershell
# 为当前用户永久设置
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-your-key', 'User')

# 或使用 GUI
# 1. Win+R 输入：sysdm.cpl
# 2. "高级" → "环境变量"
# 3. 在"用户变量"下点击"新建"
# 4. 变量名：OPENAI_API_KEY
# 5. 变量值：sk-your-api-key-here
```

---

## 方式 4：配置文件

创建 `config.json`：

```json
{
  "api_config": {
    "provider": "openai",
    "openai_api_key": "sk-your-key-here",
    "azure_endpoint": "https://your-resource.openai.azure.com/",
    "azure_api_key": "your-azure-key-here"
  },
  "db_config": {
    "host": "localhost",
    "port": 9030,
    "user": "root",
    "password": "",
    "database": "final_algorithm_competition"
  },
  "model_config": {
    "generation_model": "gpt-4o",
    "column_exploration_model": "gpt-4o",
    "temperature": 1.0
  }
}
```

然后修改脚本加载配置（需要自己实现加载逻辑）。

---

## 验证配置

运行测试脚本检查 API Key 是否正确配置：

```powershell
# 测试环境变量
python -c "import os; print('OpenAI Key:', os.getenv('OPENAI_API_KEY')[:10] + '...' if os.getenv('OPENAI_API_KEY') else 'Not Set')"

# 测试连接
python test_starrocks_setup.py
```

---

## 安全建议

1. **不要提交 API Key 到 Git**

   添加到 `.gitignore`：
   ```
   .env
   config.json
   set_env.ps1
   *_credential.json
   ```

2. **使用项目级环境变量**

   推荐在项目目录下创建 `.env` 而不是系统级设置

3. **定期轮换密钥**

   建议每 3-6 个月更换一次 API Key

4. **使用环境隔离**

   开发、测试、生产使用不同的 API Key

---

## 快速启动完整示例

```powershell
# 1. 进入项目目录
cd E:\Project\track3_2\ReFoRCE\methods\ReFoRCE

# 2. 创建虚拟环境（Python 3.12）
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1

# 3. 安装依赖
uv pip install -r requirements_starrocks.txt

# 4. 设置 API Key
$env:OPENAI_API_KEY = "sk-your-actual-key-here"

# 5. 验证配置
python test_starrocks_setup.py

# 6. 运行测试
python run_starrocks.py --max_questions 1 --generation_model gpt-4o
```

---

## 常见问题

### Q: 提示 "API Key not found"

**A:** 检查环境变量是否设置：
```powershell
echo $env:OPENAI_API_KEY
```

### Q: Azure OpenAI 如何配置？

**A:** 需要同时设置两个变量：
```powershell
$env:AZURE_ENDPOINT = "https://xxx.openai.azure.com/"
$env:AZURE_OPENAI_KEY = "your-key"
```
然后运行时加上 `--azure` 参数：
```powershell
python run_starrocks.py --azure --generation_model gpt-4o
```

### Q: DeepSeek 如何配置？

**A:** 设置 DS_API_KEY 并使用对应模型：
```powershell
$env:DS_API_KEY = "your-deepseek-key"
python run_starrocks.py --generation_model deepseek-reasoner
```

### Q: 多个项目共享 API Key？

**A:** 使用系统级环境变量或创建全局 `.env` 文件，然后在每个项目中加载。

---

## 推荐配置方案

**日常开发**：使用 `.env` 文件（方便切换）  
**CI/CD**：使用环境变量（安全）  
**团队协作**：使用 `config.example.json` 模板（不含真实密钥）

创建 `config.example.json` 模板：
```json
{
  "api_config": {
    "provider": "openai",
    "openai_api_key": "YOUR_KEY_HERE",
    "azure_endpoint": "YOUR_ENDPOINT_HERE",
    "azure_api_key": "YOUR_KEY_HERE"
  }
}
```

团队成员复制后重命名为 `config.json` 并填入真实密钥。
