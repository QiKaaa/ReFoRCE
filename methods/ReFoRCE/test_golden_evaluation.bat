@echo off
REM 测试金标准SQL评估功能
REM 只处理有golden_sql=true的题目

echo ========================================
echo Golden SQL Evaluation Test
echo ========================================
echo.

REM 设置环境变量
set OPENAI_API_KEY=your-api-key-here
set AZURE_ENDPOINT=your-azure-endpoint-here
set AZURE_OPENAI_KEY=your-azure-key-here

REM 运行评估 (只处理3个golden题目)
uv run python run_starrocks.py ^
  --dataset_path "e:/Project/track3_2/final_for_student/data/final_dataset_example.json" ^
  --schema_path "e:/Project/track3_2/M-schema/final_algorithm_competition.txt" ^
  --output_path "output/golden_test" ^
  --generation_model "gpt-4o" ^
  --do_self_refinement ^
  --enable_golden_evaluation ^
  --max_questions 5 ^
  --num_workers 1

echo.
echo ========================================
echo Test completed!
echo Check output/golden_test/ for results
echo ========================================
pause
