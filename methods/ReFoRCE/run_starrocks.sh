#!/bin/bash
# StarRocks版ReFoRCE启动脚本

# 设置API Key
export OPENAI_API_KEY="your-openai-api-key"
# 或使用Azure
# export AZURE_ENDPOINT="your-azure-endpoint"
# export AZURE_OPENAI_KEY="your-azure-key"

# 基本配置
DATASET_PATH="E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
SCHEMA_PATH="E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
OUTPUT_PATH="output/starrocks-log"

# StarRocks数据库配置
DB_HOST="localhost"
DB_PORT=9030
DB_USER="root"
DB_PASSWORD=""
DB_NAME="final_algorithm_competition"

# 模型配置
MODEL="gpt-4o"
# 使用Azure时添加 --azure 参数

# 运行模式1: 基础运行（无列探索，无投票）
echo "模式1: 基础运行"
python run_starrocks.py \
  --dataset_path "$DATASET_PATH" \
  --schema_path "$SCHEMA_PATH" \
  --output_path "$OUTPUT_PATH/basic" \
  --db_host "$DB_HOST" \
  --db_port "$DB_PORT" \
  --db_user "$DB_USER" \
  --db_password "$DB_PASSWORD" \
  --db_name "$DB_NAME" \
  --generation_model "$MODEL" \
  --do_self_refinement \
  --max_iter 5 \
  --num_workers 4

# 运行模式2: 列探索 + 自我精化
echo "模式2: 列探索 + 自我精化"
python run_starrocks.py \
  --dataset_path "$DATASET_PATH" \
  --schema_path "$SCHEMA_PATH" \
  --output_path "$OUTPUT_PATH/with_exploration" \
  --db_host "$DB_HOST" \
  --db_port "$DB_PORT" \
  --db_user "$DB_USER" \
  --db_password "$DB_PASSWORD" \
  --db_name "$DB_NAME" \
  --generation_model "$MODEL" \
  --column_exploration_model "$MODEL" \
  --do_column_exploration \
  --do_self_refinement \
  --do_self_consistency \
  --max_iter 5 \
  --num_workers 4

# 运行模式3: 完整模式（列探索 + 投票）
echo "模式3: 完整模式（列探索 + 投票）"
python run_starrocks.py \
  --dataset_path "$DATASET_PATH" \
  --schema_path "$SCHEMA_PATH" \
  --output_path "$OUTPUT_PATH/full" \
  --db_host "$DB_HOST" \
  --db_port "$DB_PORT" \
  --db_user "$DB_USER" \
  --db_password "$DB_PASSWORD" \
  --db_name "$DB_NAME" \
  --generation_model "$MODEL" \
  --column_exploration_model "$MODEL" \
  --do_column_exploration \
  --do_self_refinement \
  --do_self_consistency \
  --do_vote \
  --num_votes 3 \
  --random_vote_for_tie \
  --max_iter 5 \
  --num_workers 2

echo "✓ 所有模式运行完成！"
