# 🔄 配置方式变更说明

## 重要变更

从 `.env` 文件中读取数据库配置，不再使用命令行参数。

---

## 变更对比

### ❌ 旧方式（已废弃）

```powershell
python run_starrocks.py `
  --db_host localhost `
  --db_port 9030 `
  --db_user root `
  --db_password "mypassword" `
  --db_name final_algorithm_competition `
  --generation_model gpt-4o
```

**问题**：
- 密码暴露在命令行历史
- 参数繁多，容易出错
- 不便于团队协作

### ✅ 新方式（推荐）

**1. 配置 `.env` 文件：**

```env
# API Key
OPENAI_API_KEY=sk-proj-your-key

# 数据库配置
DB_HOST=localhost
DB_PORT=9030
DB_USER=root
DB_PASSWORD=mypassword
DB_NAME=final_algorithm_competition
```

**2. 运行命令：**

```powershell
python run_starrocks.py --generation_model gpt-4o
```

**优势**：
- ✅ 密码安全存储
- ✅ 命令简洁清晰
- ✅ 易于环境切换
- ✅ 符合最佳实践

---

## 迁移指南

### Step 1: 创建 `.env` 文件

```powershell
cd E:\Project\track3_2\ReFoRCE\methods\ReFoRCE
cp .env.example .env
```

### Step 2: 填写配置

编辑 `.env` 文件：

```env
# 必填：API Key
OPENAI_API_KEY=your-real-api-key

# 可选：数据库配置（如果使用默认值可以不填）
DB_HOST=localhost
DB_PORT=9030
DB_USER=root
DB_PASSWORD=
DB_NAME=final_algorithm_competition
```

### Step 3: 验证配置

```powershell
python check_config.py
```

### Step 4: 更新启动脚本

**旧脚本：**
```powershell
python run_starrocks.py `
  --db_host localhost `
  --db_port 9030 `
  --db_user root `
  --db_name final_algorithm_competition
```

**新脚本：**
```powershell
# 数据库配置会自动从 .env 读取
python run_starrocks.py
```

---

## 配置项映射

| 旧参数（命令行） | 新参数（.env） | 默认值 |
|-----------------|---------------|--------|
| `--db_host` | `DB_HOST` | `localhost` |
| `--db_port` | `DB_PORT` | `9030` |
| `--db_user` | `DB_USER` | `root` |
| `--db_password` | `DB_PASSWORD` | `""` |
| `--db_name` | `DB_NAME` | `final_algorithm_competition` |

---

## 常见问题

### Q1: 我还能用命令行参数吗？

**A:** 不能。数据库配置**仅**从 `.env` 文件读取。这是为了提高安全性和便捷性。

### Q2: 如果我不创建 .env 文件会怎样？

**A:** 程序会使用默认值：
- `DB_HOST=localhost`
- `DB_PORT=9030`
- `DB_USER=root`
- `DB_PASSWORD=`（空）
- `DB_NAME=final_algorithm_competition`

### Q3: 我可以在不同项目间共享 .env 吗？

**A:** 不推荐。每个项目应该有自己的 `.env` 文件。但你可以：
```powershell
# 复制配置
cp project1/.env project2/.env
```

### Q4: .env 文件会被提交到 Git 吗？

**A:** 不会。`.env` 已被添加到 `.gitignore`，确保密码不会泄露。

### Q5: 如何在多个环境间切换？

**A:** 创建多个配置文件：
```powershell
# 创建环境配置
.env.dev      # 开发环境
.env.test     # 测试环境
.env.prod     # 生产环境

# 使用时复制
cp .env.dev .env    # 切换到开发环境
cp .env.prod .env   # 切换到生产环境
```

---

## 升级检查清单

- [ ] 创建 `.env` 文件
- [ ] 从旧脚本中复制数据库配置到 `.env`
- [ ] 添加 API Key 到 `.env`
- [ ] 运行 `python check_config.py` 验证配置
- [ ] 更新启动脚本，移除数据库相关参数
- [ ] 测试运行 `python run_starrocks.py --max_questions 1`
- [ ] 确认 `.env` 已被 `.gitignore` 排除

---

## 受影响的文件

### 修改的文件

1. **`run_starrocks.py`**
   - 移除命令行参数：`--db_host`, `--db_port`, `--db_user`, `--db_password`, `--db_name`
   - 从环境变量读取配置：`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

2. **`requirements_starrocks.txt`**
   - 新增依赖：`python-dotenv`

3. **`.gitignore`**
   - 排除 `.env` 文件

### 新增的文件

1. **`.env.example`** - 配置模板
2. **`ENV_CONFIG.md`** - 配置详解
3. **`check_config.py`** - 配置验证脚本
4. **`CHANGELOG_ENV.md`** - 变更说明（本文件）

### 更新的文档

1. **`START_HERE.md`** - 更新快速开始流程
2. **`QUICKSTART_STARROCKS.md`** - 更新启动指南
3. **`CONFIG_EXAMPLE.md`** - 更新配置说明

---

## 技术细节

### 实现原理

```python
# run_starrocks.py

from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 获取配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '9030')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'final_algorithm_competition')
}

# 使用配置
sql_env = SqlEnvStarRocks(
    host=DB_CONFIG['host'],
    port=DB_CONFIG['port'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password'],
    database=DB_CONFIG['database']
)
```

### 优先级

1. `.env` 文件中的值
2. 操作系统环境变量
3. 代码中的默认值

---

## 回滚方案

如果需要回滚到旧版本：

```bash
git checkout HEAD~1 run_starrocks.py
```

但**不推荐**回滚，新方式更安全、更便捷。

---

## 获取帮助

- **配置问题**: 查看 `ENV_CONFIG.md`
- **快速开始**: 查看 `START_HERE.md`
- **验证配置**: 运行 `python check_config.py`

---

更新日期: 2025-11-18
