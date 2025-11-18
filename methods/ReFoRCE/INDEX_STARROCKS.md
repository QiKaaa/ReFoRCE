# 📚 StarRocks版ReFoRCE文档索引

欢迎使用StarRocks适配版ReFoRCE！本索引帮助你快速找到所需文档。

---

## 🚀 快速开始

### 我是新手，从哪里开始？
1. **[快速启动指南 (QUICKSTART_STARROCKS.md)](QUICKSTART_STARROCKS.md)** ⭐
   - 5分钟快速启动
   - 环境配置步骤
   - 测试运行示例

### 我想了解完整功能？
2. **[完整使用文档 (README_STARROCKS.md)](README_STARROCKS.md)**
   - 详细参数说明
   - 运行模式介绍
   - 常见问题解答

### 我想了解改造细节？
3. **[改造总结 (STARROCKS_ADAPTATION_SUMMARY.md)](../STARROCKS_ADAPTATION_SUMMARY.md)**
   - 改造概览
   - 核心改造点
   - 技术对比

---

## 📁 文件结构

### 🔧 核心代码文件

| 文件 | 功能 | 何时使用 |
|------|------|----------|
| `sql_starrocks.py` | StarRocks SQL执行引擎 | 理解SQL执行逻辑 |
| `schema_parser.py` | Schema文件解析器 | 理解Schema处理 |
| `data_loader.py` | 数据集加载器 | 理解数据加载 |
| `prompt_starrocks.py` | StarRocks方言Prompt | 理解Prompt生成 |
| `run_starrocks.py` | 主运行脚本 | 运行完整程序 |

### 📝 配置文件

| 文件 | 用途 | 何时修改 |
|------|------|----------|
| `requirements_starrocks.txt` | Python依赖 | 安装依赖时 |
| `run_starrocks.sh` | Bash启动脚本 | Linux/Mac运行 |
| `run_starrocks.ps1` | PowerShell启动脚本 | Windows运行 |

### 🧪 测试和演示

| 文件 | 功能 | 何时运行 |
|------|------|----------|
| `test_starrocks_setup.py` | 环境验证测试 | 初次配置后 |
| `demo.py` | 功能演示脚本 | 了解各组件 |

### 📖 文档文件

| 文件 | 内容 | 适合人群 |
|------|------|----------|
| `INDEX_STARROCKS.md` | 本文档 | 所有人 |
| `QUICKSTART_STARROCKS.md` | 快速启动 | 新手 |
| `README_STARROCKS.md` | 完整文档 | 所有人 |
| `STARROCKS_ADAPTATION_SUMMARY.md` | 改造总结 | 开发者 |

---

## 🎯 按任务查找

### 我想...

#### 安装和配置
- **安装依赖** → [QUICKSTART - Step 2](QUICKSTART_STARROCKS.md#step-2-安装依赖使用uv超快)
- **配置数据库** → [QUICKSTART - Step 2](QUICKSTART_STARROCKS.md#step-2-配置数据库)
- **设置API Key** → [QUICKSTART - Step 4](QUICKSTART_STARROCKS.md#step-4-设置api-key)
- **验证环境** → [QUICKSTART - Step 3](QUICKSTART_STARROCKS.md#step-3-验证环境)

#### 运行程序
- **第一次运行** → [QUICKSTART - Step 5](QUICKSTART_STARROCKS.md#step-5-测试运行1个问题)
- **选择运行模式** → [QUICKSTART - 运行模式选择](QUICKSTART_STARROCKS.md#🎯-运行模式选择)
- **按复杂度运行** → [QUICKSTART - 按复杂度运行](QUICKSTART_STARROCKS.md#📊-按复杂度运行)
- **调试参数** → [README - 参数说明](README_STARROCKS.md#📊-参数说明)

#### 理解原理
- **Schema如何解析** → [schema_parser.py](schema_parser.py)
- **数据如何加载** → [data_loader.py](data_loader.py)
- **SQL如何执行** → [sql_starrocks.py](sql_starrocks.py)
- **Prompt如何生成** → [prompt_starrocks.py](prompt_starrocks.py)
- **工作流程** → [SUMMARY - 工作流程对比](../STARROCKS_ADAPTATION_SUMMARY.md#🔄-工作流程对比)

#### 解决问题
- **环境测试失败** → [README - 常见问题](README_STARROCKS.md#🐛-常见问题)
- **数据库连接失败** → [QUICKSTART - 问题1](QUICKSTART_STARROCKS.md#问题1-数据库连接失败)
- **API超时** → [QUICKSTART - 问题2](QUICKSTART_STARROCKS.md#问题2-api超时)
- **内存不足** → [QUICKSTART - 问题3](QUICKSTART_STARROCKS.md#问题3-内存不足)
- **Schema解析错误** → [QUICKSTART - 问题4](QUICKSTART_STARROCKS.md#问题4-schema解析错误)

#### 优化性能
- **降低成本** → [QUICKSTART - 省钱模式](QUICKSTART_STARROCKS.md#省钱模式使用mini模型)
- **提高准确率** → [QUICKSTART - 高精度模式](QUICKSTART_STARROCKS.md#高精度模式)
- **加快速度** → [QUICKSTART - 快速模式](QUICKSTART_STARROCKS.md#⚡-快速模式)
- **并发控制** → [README - 性能考虑](README_STARROCKS.md#📈-性能考虑)

---

## 🔍 按角色查找

### 👨‍💻 开发者
推荐阅读顺序：
1. [改造总结](../STARROCKS_ADAPTATION_SUMMARY.md) - 了解改造细节
2. 核心代码文件 - 理解实现
3. [完整文档](README_STARROCKS.md) - 掌握所有功能

关键文件：
- `sql_starrocks.py` - SQL执行引擎
- `schema_parser.py` - Schema解析
- `run_starrocks.py` - 主流程

### 👨‍🎓 研究者
推荐阅读顺序：
1. [原ReFoRCE论文](https://arxiv.org/pdf/2502.00675)
2. [改造总结](../STARROCKS_ADAPTATION_SUMMARY.md) - 对比原实现
3. `prompt_starrocks.py` - 理解Prompt设计

关键概念：
- 自我精化机制
- 列探索策略
- 投票共识算法

### 👨‍💼 数据分析师
推荐阅读顺序：
1. [快速启动](QUICKSTART_STARROCKS.md) - 快速上手
2. [完整文档](README_STARROCKS.md) - 深入了解
3. 运行示例 - 实际使用

关键功能：
- 按复杂度过滤
- 批量处理
- 结果导出

---

## 📚 学习路径

### 🌱 入门（第1天）
1. ✅ 阅读 [快速启动指南](QUICKSTART_STARROCKS.md)
2. ✅ 运行 `python test_starrocks_setup.py`
3. ✅ 运行 `python demo.py`
4. ✅ 测试1个问题：`python run_starrocks.py --max_questions 1`

### 🌿 进阶（第2-3天）
1. ✅ 尝试不同运行模式
2. ✅ 阅读 [完整文档](README_STARROCKS.md)
3. ✅ 理解各个模块的代码
4. ✅ 处理简单/中等复杂度问题

### 🌳 精通（第4-5天）
1. ✅ 阅读 [改造总结](../STARROCKS_ADAPTATION_SUMMARY.md)
2. ✅ 调优参数，提高准确率
3. ✅ 处理复杂问题
4. ✅ 批量处理全部数据集

---

## 🎓 常用命令速查

### 环境管理
```powershell
# 创建环境
uv venv --python 3.10

# 激活环境
.\.venv\Scripts\Activate.ps1

# 安装依赖
uv pip install -r requirements_starrocks.txt

# 测试环境
python test_starrocks_setup.py
```

### 运行程序
```powershell
# 测试运行
python run_starrocks.py --max_questions 1 --num_workers 1

# 基础运行
python run_starrocks.py --generation_model gpt-4o --do_self_refinement

# 完整运行
python run_starrocks.py --do_column_exploration --do_vote --num_votes 3

# 按复杂度
python run_starrocks.py --filter_complexity "简单"
```

### 查看结果
```powershell
# 查看SQL
cat output/starrocks-log/sql_1/result.sql

# 查看结果
cat output/starrocks-log/sql_1/result.csv

# 查看日志
cat output/starrocks-log/sql_1/log.log
```

---

## 🔗 外部资源

### 原项目
- [ReFoRCE GitHub](https://github.com/xlang-ai/Spider2)
- [ReFoRCE 论文](https://arxiv.org/pdf/2502.00675)
- [ReFoRCE 博客](https://hao-ai-lab.github.io/blogs/reforce/)

### 数据库
- [StarRocks 官方文档](https://docs.starrocks.io/)
- [StarRocks SQL参考](https://docs.starrocks.io/sql-reference/sql-statements/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

### LLM
- [OpenAI API 文档](https://platform.openai.com/docs/)
- [Azure OpenAI 文档](https://learn.microsoft.com/azure/ai-services/openai/)

---

## 💡 提示和技巧

### 快速查找
- 使用 `Ctrl+F` 在文档中搜索关键词
- 文件名包含功能描述，便于定位
- 代码注释详细，可直接阅读源码

### 获取帮助
```powershell
# 查看所有参数
python run_starrocks.py --help

# 运行演示了解组件
python demo.py

# 运行测试验证环境
python test_starrocks_setup.py
```

### 调试技巧
1. 先运行1个问题测试
2. 查看详细日志 `log.log`
3. 逐步增加复杂度
4. 使用 `--num_workers 1` 避免并发问题

---

## 📞 支持

遇到问题？查看这些资源：
1. [常见问题 - README](README_STARROCKS.md#🐛-常见问题)
2. [快速修复 - QUICKSTART](QUICKSTART_STARROCKS.md#🐛-常见问题快速修复)
3. [改造总结 - 已知限制](../STARROCKS_ADAPTATION_SUMMARY.md#🚧-已知限制)

---

**最后更新**: 2025-01-18  
**版本**: 1.0  
**维护者**: AI Assistant

祝使用愉快！🎉
