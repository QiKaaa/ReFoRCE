"""
清理输出目录脚本
"""
import os
import shutil

output_dir = "output/starrocks-log"

if os.path.exists(output_dir):
    print(f"🗑️  清理输出目录: {output_dir}")
    shutil.rmtree(output_dir)
    print("✅ 清理完成")
else:
    print(f"ℹ️  输出目录不存在: {output_dir}")

# 重新创建空目录
os.makedirs(output_dir, exist_ok=True)
print(f"✅ 创建新的输出目录: {output_dir}")
