# StarRocks适配故障排查指南

## 问题：程序运行后没有输出

### 症状
运行 `run_starrocks.py` 后，程序显示"处理完成"但输出目录为空或只有空的子目录。

### 根本原因

#### 1. `get_api_name` 函数不支持 StarRocks 命名格式
**位置**: `utils.py` 第166-174行

**问题**: 原函数只支持以下前缀：
- `sf` → snowflake
- `local` → sqlite  
- `bq` 或 `ga` → bigquery

我们的数据集使用 `sql_1`, `sql_2` 等命名，导致抛出 `NotImplementedError`。

**修复**:
```python
def get_api_name(sql_data):
    if sql_data.startswith("sf"):
        return "snowflake"
    elif sql_data.startswith("local"):
        return "sqlite"
    elif sql_data.startswith("bq") or sql_data.startswith("ga"):
        return "bigquery"
    elif sql_data.startswith("sql"):  # 添加 StarRocks 支持
        return "starrocks"
    else:
        raise NotImplementedError(f"Invalid file name: {sql_data}")
```

#### 2. 缺少必需的命令行参数
**位置**: `run_starrocks.py` 参数定义部分

**问题**: `agent.py` 中的 `self_refine()` 和 `gen()` 方法需要 `args.omnisql_format_pth` 参数。

**修复**: 在 `run_starrocks.py` 中添加：
```python
parser.add_argument('--omnisql_format_pth', type=str, default=None,
                   help="OmniSQL格式路径（可选）")
```

### 诊断步骤

1. **运行诊断脚本**:
   ```bash
   python diagnose_no_output.py
   ```

2. **检查输出目录**:
   ```bash
   ls -R output/starrocks-log/
   ```

3. **查看现有文件**:
   如果看到 `result.sql` 存在，说明程序已经成功运行过。

### 解决方案

#### 方案 1: 清理后重新运行（推荐）
```bash
python clean_output.py
uv run python run_starrocks.py --generation_model deepseek-reasoner --max_questions 1 --num_workers 1 --do_self_refinement
```

#### 方案 2: 强制覆盖未完成的任务
```bash
uv run python run_starrocks.py --generation_model deepseek-reasoner --max_questions 1 --num_workers 1 --do_self_refinement --overwrite_unfinished
```

#### 方案 3: 重新运行所有任务
```bash
uv run python run_starrocks.py --generation_model deepseek-reasoner --max_questions 1 --num_workers 1 --do_self_refinement --rerun
```

### 常见错误

#### 错误 1: `ModuleNotFoundError: No module named 'sqlglot'`
**原因**: 依赖未安装或未使用 `uv run`

**解决**:
```bash
uv pip install -r requirements_starrocks.txt
# 或使用 uv run
uv run python run_starrocks.py ...
```

#### 错误 2: `PermissionError: [WinError 32]`
**原因**: log.log 文件被其他程序占用（通常是文本编辑器或日志查看器）

**解决**:
- 关闭所有打开该文件的程序
- 或使用 `--overwrite_unfinished` 参数

#### 错误 3: 程序运行但无输出
**原因**: 异常被 ThreadPoolExecutor 吞没

**解决**: 查看修改后的代码，异常现在会被捕获并打印。

### 验证成功

成功运行后，应该看到以下文件：
```
output/starrocks-log/sql_1/
├── log.log           # 详细日志
├── result.sql        # 生成的SQL查询
└── result.csv        # 执行结果
```

**示例输出**:
```sql
-- result.sql
SELECT 
    a.suserid,
    a.sgamecode,
    SUM(a.ionlinetime) AS ionlinetime
FROM final_algorithm_competition.dws_mgamejp_login_user_activity_di a
INNER JOIN final_algorithm_competition.dim_vplayerid_vies_df b 
    ON a.suserid = b.suserid 
    AND a.suseridtype = b.suserid_type
WHERE b.dtstatdate = '20250724'
    AND b.itag = '其他'
    AND a.dtstatdate BETWEEN 20250530 AND 20250724
    ...
GROUP BY a.suserid, a.sgamecode
```

### 调试技巧

1. **添加调试输出**: 在关键位置添加 `print(f"[DEBUG] ...")`
2. **捕获异常**: 使用 try-except 包装可疑代码
3. **检查日志**: 查看 `log.log` 文件了解详细执行过程
4. **单步测试**: 使用 `--max_questions 1` 限制测试范围

### 性能优化

- **并行处理**: 根据CPU核心数调整 `--num_workers`
- **批量处理**: 移除 `--max_questions` 参数处理所有问题
- **模型选择**: 使用更快的模型（如 `gpt-4o-mini`）进行测试

## 相关文档

- [快速开始指南](QUICKSTART_STARROCKS.md)
- [环境配置说明](ENV_CONFIG.md)
- [README](README_STARROCKS.md)
