# StarRocks版ReFoRCE启动脚本 (PowerShell)

# 设置API Key
$env:OPENAI_API_KEY = "your-openai-api-key"
# 或使用Azure
# $env:AZURE_ENDPOINT = "your-azure-endpoint"
# $env:AZURE_OPENAI_KEY = "your-azure-key"

# 基本配置
$DATASET_PATH = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
$SCHEMA_PATH = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
$OUTPUT_PATH = "output/starrocks-log"

# StarRocks数据库配置
$DB_HOST = "localhost"
$DB_PORT = 9030
$DB_USER = "root"
$DB_PASSWORD = ""
$DB_NAME = "final_algorithm_competition"

# 模型配置
$MODEL = "gpt-4o"

# 运行模式1: 基础运行（测试少量问题）
Write-Host "模式1: 基础测试（前3个问题）" -ForegroundColor Green
python run_starrocks.py `
  --dataset_path $DATASET_PATH `
  --schema_path $SCHEMA_PATH `
  --output_path "$OUTPUT_PATH/test" `
  --db_host $DB_HOST `
  --db_port $DB_PORT `
  --db_user $DB_USER `
  --db_password $DB_PASSWORD `
  --db_name $DB_NAME `
  --generation_model $MODEL `
  --do_self_refinement `
  --max_iter 3 `
  --num_workers 1 `
  --max_questions 3

# 运行模式2: 列探索 + 自我精化（简单题目）
Write-Host "`n模式2: 简单题目（列探索 + 自我精化）" -ForegroundColor Green
python run_starrocks.py `
  --dataset_path $DATASET_PATH `
  --schema_path $SCHEMA_PATH `
  --output_path "$OUTPUT_PATH/simple" `
  --db_host $DB_HOST `
  --db_port $DB_PORT `
  --db_user $DB_USER `
  --db_password $DB_PASSWORD `
  --db_name $DB_NAME `
  --generation_model $MODEL `
  --column_exploration_model $MODEL `
  --do_column_exploration `
  --do_self_refinement `
  --do_self_consistency `
  --filter_complexity "简单" `
  --max_iter 5 `
  --num_workers 2

# 运行模式3: 完整模式（所有题目）
Write-Host "`n模式3: 完整运行（所有题目，带投票）" -ForegroundColor Green
python run_starrocks.py `
  --dataset_path $DATASET_PATH `
  --schema_path $SCHEMA_PATH `
  --output_path "$OUTPUT_PATH/full" `
  --db_host $DB_HOST `
  --db_port $DB_PORT `
  --db_user $DB_USER `
  --db_password $DB_PASSWORD `
  --db_name $DB_NAME `
  --generation_model $MODEL `
  --column_exploration_model $MODEL `
  --do_column_exploration `
  --do_self_refinement `
  --do_self_consistency `
  --do_vote `
  --num_votes 3 `
  --random_vote_for_tie `
  --max_iter 5 `
  --num_workers 4

Write-Host "`n✓ 所有模式运行完成！" -ForegroundColor Cyan
