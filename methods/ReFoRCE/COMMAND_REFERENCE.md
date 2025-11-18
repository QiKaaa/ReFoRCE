# 命令参考快查

## 🚀 常用命令

### 基础运行

```bash
# 处理单个问题（测试）
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --max_questions 1 \
  --num_workers 1 \
  --do_self_refinement

# 处理多个问题（并行）
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --max_questions 10 \
  --num_workers 4 \
  --do_self_refinement

# 处理所有问题
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --num_workers 8 \
  --do_self_refinement
```

### 高级选项

```bash
# 启用列探索
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --column_exploration_model gpt-4o \
  --do_column_exploration \
  --do_self_refinement

# 启用投票机制（生成多个SQL并投票选择最佳）
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --do_vote \
  --num_votes 3 \
  --model_vote gpt-4o

# 按复杂度过滤
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --filter_complexity 简单 \
  --do_self_refinement

# 重新运行（覆盖现有结果）
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --rerun \
  --do_self_refinement

# 强制覆盖未完成的任务
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --overwrite_unfinished \
  --do_self_refinement
```

## 🛠️ 工具命令

```bash
# 清理输出目录
python clean_output.py

# 验证配置
python check_config.py

# 调试运行
python debug_run.py

# 诊断问题
python diagnose_no_output.py

# 测试数据库连接
python test_starrocks_setup.py

# 安装依赖
uv pip install -r requirements_starrocks.txt
```

## 📋 参数说明

### 模型参数
- `--generation_model`: SQL生成模型（推荐: `deepseek-reasoner`, `gpt-4o`）
- `--column_exploration_model`: 列探索模型
- `--format_model`: 格式化模型
- `--model_vote`: 投票模型
- `--azure`: 使用 Azure OpenAI

### 功能开关
- `--do_self_refinement`: 启用自我精化（推荐）
- `--do_column_exploration`: 启用列探索
- `--do_vote`: 启用投票机制
- `--do_format_restriction`: 启用格式限制
- `--do_self_consistency`: 启用自我一致性

### 运行参数
- `--max_iter`: 最大迭代次数（默认: 5）
- `--temperature`: 采样温度（默认: 1.0）
- `--num_votes`: 投票次数（默认: 3）
- `--num_workers`: 并行worker数量（默认: 4）
- `--early_stop`: 启用早停

### 数据过滤
- `--filter_complexity`: 按复杂度过滤（简单/中等/复杂）
- `--max_questions`: 限制处理的问题数量

### 其他选项
- `--rerun`: 重新运行
- `--revote`: 重新投票
- `--overwrite_unfinished`: 覆盖未完成的
- `--random_vote_for_tie`: 平局时随机投票
- `--final_choose`: 最终选择
- `--save_all_results`: 保存所有结果

## 🎯 推荐配置

### 快速测试
```bash
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --max_questions 3 \
  --num_workers 1 \
  --do_self_refinement
```

### 高质量生成
```bash
uv run python run_starrocks.py \
  --generation_model gpt-4o \
  --do_column_exploration \
  --column_exploration_model gpt-4o \
  --do_self_refinement \
  --max_iter 10 \
  --num_workers 4
```

### 最佳平衡
```bash
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --do_self_refinement \
  --max_iter 5 \
  --num_workers 8
```

### 投票模式（最高准确率）
```bash
uv run python run_starrocks.py \
  --generation_model deepseek-reasoner \
  --do_vote \
  --num_votes 5 \
  --model_vote gpt-4o \
  --num_workers 2
```

## 📊 输出结构

```
output/starrocks-log/
├── sql_1/
│   ├── log.log       # 详细执行日志
│   ├── result.sql    # 生成的SQL查询
│   └── result.csv    # 执行结果
├── sql_2/
│   └── ...
└── ...
```

## ⚠️ 常见问题

### 问题：程序无输出
**解决**:
```bash
python clean_output.py && \
uv run python run_starrocks.py --generation_model deepseek-reasoner --max_questions 1
```

### 问题：依赖缺失
**解决**:
```bash
uv pip install -r requirements_starrocks.txt
```

### 问题：API Key错误
**解决**:
```bash
# 检查.env文件
cat .env | grep API_KEY

# 或验证配置
python check_config.py
```

### 问题：文件被占用
**解决**:
- 关闭所有文本编辑器
- 或使用 `--overwrite_unfinished`

## 📚 相关文档

- [快速开始](QUICKSTART_STARROCKS.md)
- [环境配置](ENV_CONFIG.md)
- [故障排查](TROUBLESHOOTING.md)
- [成功报告](SUCCESS_REPORT.md)
