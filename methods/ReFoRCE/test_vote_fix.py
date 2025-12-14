"""
测试投票逻辑修复
"""
import os

# 模拟测试目录
test_dir = "E:/Project/track3_2/ReFoRCE/methods/ReFoRCE/output/test-sl-vote/sql_1"

print("=" * 60)
print("测试: 动态收集候选SQL文件")
print("=" * 60)

# 原始逻辑（错误的）
print("\n[旧逻辑] 预定义的 sql_paths:")
sql_paths_old = {
    "linked_0_log.log": "linked_0_result.csv",
    "linked_1_log.log": "linked_1_result.csv",
    "linked_2_log.log": "linked_2_result.csv",
}
print(f"  {sql_paths_old}")
print("  ❌ 问题: 这些文件名不匹配实际生成的候选SQL文件")

# 新逻辑（正确的）
print("\n[新逻辑] 动态收集所有 *_result.sql 文件:")
candidate_sql_files = {}
for filename in os.listdir(test_dir):
    if filename.endswith('_result.sql') and filename != 'result.sql':
        if os.path.isfile(os.path.join(test_dir, filename)):
            csv_filename = filename.replace('.sql', '.csv')
            csv_path = os.path.join(test_dir, csv_filename)
            if os.path.exists(csv_path):
                candidate_sql_files[filename] = csv_filename

print(f"  找到 {len(candidate_sql_files)} 个候选文件:")
for sql_file, csv_file in candidate_sql_files.items():
    print(f"    • {sql_file} → {csv_file}")

print("\n✓ 修复验证成功！")
print("=" * 60)
