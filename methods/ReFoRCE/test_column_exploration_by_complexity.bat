@echo off
REM 测试列探索的复杂度自动判断功能
REM 当--do_column_exploration启用时:
REM   - 简单题: 不开启列探索
REM   - 中等/复杂题: 开启列探索

echo ====================================
echo 测试列探索的复杂度自动判断
echo ====================================
echo.

REM 设置Python路径（根据实际情况修改）
set PYTHON=python

REM 测试1: 启用列探索参数，系统会根据复杂度自动判断
echo [测试1] 启用列探索参数 (会根据题目复杂度自动判断是否真正开启)
echo   - 简单题: 不会执行列探索
echo   - 中等题: 执行列探索
echo   - 复杂题: 执行列探索
echo.

%PYTHON% run_starrocks.py ^
  --dataset_path "E:/Project/track3_2/final_for_student/data/final_dataset_example.json" ^
  --schema_path "E:/Project/track3_2/M-schema/final_algorithm_competition.txt" ^
  --output_path "output/test_column_exploration" ^
  --generation_model "deepseek-chat" ^
  --column_exploration_model "deepseek-chat" ^
  --do_column_exploration ^
  --do_self_refinement ^
  --max_questions 3 ^
  --num_workers 1

echo.
echo ====================================
echo 测试完成！
echo ====================================
echo.
echo 请检查输出日志文件，确认:
echo   1. 简单题的日志中没有 "[Column Exploration] Enabled" 信息
echo   2. 中等/复杂题的日志中有 "[Column Exploration] Enabled for complexity: 中等/复杂" 信息
echo.

pause
