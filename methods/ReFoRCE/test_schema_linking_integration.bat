@echo off
REM Schema Linking 集成测试脚本 (Windows) - UV 环境

echo ======================================
echo Schema Linking 集成测试 (UV 环境)
echo ======================================

REM 设置路径（使用绝对路径）
set DATASET_PATH=e:/Project/track3_2/final_for_student/data/final_dataset_example.json
set SCHEMA_PATH=e:/Project/track3_2/M-schema/final_algorithm_competition.txt

REM 测试1: 仅使用 Schema Linking (1个问题)
echo.
echo 测试1: 仅使用 Schema Linking 模式
echo --------------------------------------
uv run run_starrocks.py ^
  --dataset_path %DATASET_PATH% ^
  --schema_path %SCHEMA_PATH% ^
  --output_path output/test-sl-only ^
  --use_schema_linking ^
  --max_questions 1 ^
  --generation_model deepseek-chat ^
  --overwrite_unfinished

echo.
echo ✓ 测试1完成
echo.

REM 测试2: Schema Linking 投票模式 (1个问题)
echo 测试2: Schema Linking 投票模式
echo --------------------------------------
uv run run_starrocks.py ^
  --dataset_path %DATASET_PATH% ^
  --schema_path %SCHEMA_PATH% ^
  --output_path output/test-sl-vote ^
  --do_vote ^
  --do_schema_linking_vote ^
  --num_votes 2 ^
  --max_questions 1 ^
  --generation_model deepseek-chat ^
  --overwrite_unfinished

echo.
echo ✓ 测试2完成
echo.

REM 测试3: 对比测试
echo 测试3: 对比测试
echo --------------------------------------
echo 3.1 原始 Schema
uv run run_starrocks.py ^
  --dataset_path %DATASET_PATH% ^
  --schema_path %SCHEMA_PATH% ^
  --output_path output/test-original ^
  --max_questions 1 ^
  --generation_model deepseek-chat ^
  --overwrite_unfinished

echo.
echo 3.2 Schema Linking
uv run run_starrocks.py ^
  --dataset_path %DATASET_PATH% ^
  --schema_path %SCHEMA_PATH% ^
  --output_path output/test-linked ^
  --use_schema_linking ^
  --max_questions 1 ^
  --generation_model deepseek-chat ^
  --overwrite_unfinished

echo.
echo ✓ 测试3完成
echo.

REM 分析结果
echo ======================================
echo 测试完成，结果分析：
echo ======================================
echo.
echo 输出目录：
echo   - output/test-sl-only/   (Schema Linking 单独模式)
echo   - output/test-sl-vote/   (Schema Linking 投票模式)
echo   - output/test-original/  (原始 Schema)
echo   - output/test-linked/    (Schema Linking)
echo.
echo ✅ 所有测试完成！
pause
