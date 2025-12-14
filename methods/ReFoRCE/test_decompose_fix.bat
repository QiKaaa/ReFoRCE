@echo off
REM =========================================
REM 测试分解功能修复 - Windows批处理脚本
REM =========================================

echo ========================================
echo 分解-合并功能修复测试
echo ========================================
echo.

REM 清理旧输出
echo [1/3] 清理旧测试输出...
if exist output\test-decompose-fixed rmdir /s /q output\test-decompose-fixed
echo    ✓ 清理完成
echo.

REM 运行测试 - 使用修复后的配置
echo [2/3] 运行分解测试（使用 deepseek-chat 作为分解模型）...
echo    配置:
echo    - 分解模型: deepseek-chat （修复前: deepseek-reasoner）
echo    - 只测试3个中等难度题目
echo    - 启用详细日志
echo.

uv run run_starrocks.py ^
  --output_path output/test-decompose-fixed ^
  --use_decompose ^
  --generation_model "deepseek-chat" ^
  --decompose_model "deepseek-chat" ^
  --scale_model "deepseek-chat" ^
  --column_exploration_model "deepseek-chat" ^
  --do_column_exploration ^
  --do_self_refinement ^
  --max_iter 5 ^
  --sub_question_max_iter 3 ^
  --max_questions 3 ^
  --filter_complexity 中等 ^
  --num_workers 3

echo.
echo [3/3] 检查结果...
echo.

REM 检查是否成功生成分解文件
set found_decomposition=0
for /d %%D in (output\test-decompose-fixed\sql_*) do (
    if exist "%%D\decomposition\decomposition.json" (
        echo ✓ 找到分解结果: %%D\decomposition\decomposition.json
        set found_decomposition=1
        
        REM 显示分解的子问题数量
        findstr /C:"sub_questions_count" "%%D\decomposition\decomposition.json"
    )
)

echo.
if %found_decomposition%==1 (
    echo ========================================
    echo ✅ 测试成功！分解功能正常工作
    echo ========================================
    echo.
    echo 详细日志位置:
    dir /b /s output\test-decompose-fixed\*.log
) else (
    echo ========================================
    echo ⚠️ 未找到分解结果文件
    echo ========================================
    echo 请检查日志文件以诊断问题
    echo.
    echo 日志位置:
    dir /b /s output\test-decompose-fixed\*.log
)

echo.
echo 按任意键退出...
pause > nul
