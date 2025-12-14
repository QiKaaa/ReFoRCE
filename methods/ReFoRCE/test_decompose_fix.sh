#!/bin/bash
# =========================================
# 测试分解功能修复 - Linux/Mac脚本
# =========================================

echo "========================================"
echo "分解-合并功能修复测试"
echo "========================================"
echo ""

# 清理旧输出
echo "[1/3] 清理旧测试输出..."
rm -rf output/test-decompose-fixed
echo "   ✓ 清理完成"
echo ""

# 运行测试 - 使用修复后的配置
echo "[2/3] 运行分解测试（使用 deepseek-chat 作为分解模型）..."
echo "   配置:"
echo "   - 分解模型: deepseek-chat （修复前: deepseek-reasoner）"
echo "   - 只测试3个中等难度题目"
echo "   - 启用详细日志"
echo ""

uv run run_starrocks.py \
  --output_path output/test-decompose-fixed \
  --use_decompose \
  --generation_model "deepseek-chat" \
  --decompose_model "deepseek-chat" \
  --scale_model "deepseek-chat" \
  --column_exploration_model "deepseek-chat" \
  --do_column_exploration \
  --do_self_refinement \
  --max_iter 5 \
  --sub_question_max_iter 3 \
  --max_questions 3 \
  --filter_complexity 中等 \
  --num_workers 3

echo ""
echo "[3/3] 检查结果..."
echo ""

# 检查是否成功生成分解文件
found_decomposition=0
for dir in output/test-decompose-fixed/sql_*/; do
    if [ -f "${dir}decomposition/decomposition.json" ]; then
        echo "✓ 找到分解结果: ${dir}decomposition/decomposition.json"
        found_decomposition=1
        
        # 显示分解的子问题数量
        grep "sub_questions_count" "${dir}decomposition/decomposition.json"
    fi
done

echo ""
if [ $found_decomposition -eq 1 ]; then
    echo "========================================"
    echo "✅ 测试成功！分解功能正常工作"
    echo "========================================"
    echo ""
    echo "详细日志位置:"
    find output/test-decompose-fixed -name "*.log" -type f
else
    echo "========================================"
    echo "⚠️ 未找到分解结果文件"
    echo "========================================"
    echo "请检查日志文件以诊断问题"
    echo ""
    echo "日志位置:"
    find output/test-decompose-fixed -name "*.log" -type f
fi

echo ""
