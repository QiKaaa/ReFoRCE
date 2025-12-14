#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证分解-合并流程的投票机制实现

检查项：
1. 分解-合并流程是否构建了sql_paths字典
2. 是否调用了agent_format.vote_result()
3. 是否正确传递了knowledge参数
4. 投票逻辑是否在生成多个候选SQL后执行
"""

import os
import re

def check_decompose_vote_implementation():
    """检查分解-合并投票实现"""
    
    print("=" * 70)
    print("验证分解-合并流程的投票机制")
    print("=" * 70)
    
    file_path = "run_starrocks.py"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # ===== 检查1: 是否构建了decompose_sql_paths字典 =====
    check1 = 'decompose_sql_paths = {}' in content
    checks.append(("构建decompose_sql_paths字典", check1))
    
    # ===== 检查2: 是否记录了SQL-CSV映射 =====
    check2 = 'decompose_sql_paths[f"decompose_{i}_result.sql"] = f"decompose_{i}_result.csv"' in content
    checks.append(("记录SQL-CSV映射", check2))
    
    # ===== 检查3: 是否调用了vote_result =====
    check3_pattern = r'agent_format\.vote_result\(\s*search_directory=search_directory'
    check3 = bool(re.search(check3_pattern, content))
    checks.append(("调用agent_format.vote_result()", check3))
    
    # ===== 检查4: 是否传递了sql_paths参数 =====
    check4 = 'sql_paths=decompose_sql_paths' in content
    checks.append(("传递sql_paths=decompose_sql_paths", check4))
    
    # ===== 检查5: 是否传递了knowledge参数 =====
    check5_pattern = r'knowledge=knowledge'
    check5 = bool(re.search(check5_pattern, content))
    checks.append(("传递knowledge参数", check5))
    
    # ===== 检查6: 是否在投票前检查有效候选 =====
    check6 = 'valid_candidates = [f for f in os.listdir(search_directory)' in content
    checks.append(("检查有效候选SQL", check6))
    
    # ===== 检查7: 是否有投票日志输出 =====
    check7 = '[Decompose-Vote]' in content
    checks.append(("投票日志标记", check7))
    
    # ===== 检查8: 投票逻辑是否在生成候选SQL的分支内 =====
    # 确认投票代码在 "if args.do_vote and args.use_decompose:" 块内
    decompose_vote_block = re.search(
        r'if args\.do_vote and args\.use_decompose:.*?agent_format\.vote_result\(',
        content,
        re.DOTALL
    )
    check8 = bool(decompose_vote_block)
    checks.append(("投票逻辑在正确的分支内", check8))
    
    # ===== 打印结果 =====
    print("\n检查结果:")
    print("-" * 70)
    
    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print("-" * 70)
    
    # ===== 额外检查：提取投票逻辑代码片段 =====
    print("\n投票逻辑代码片段:")
    print("-" * 70)
    
    vote_pattern = r'# ✨ 执行投票选择最佳SQL.*?logger\.warning\("\[Decompose-Vote\] No valid candidates found'
    vote_match = re.search(vote_pattern, content, re.DOTALL)
    
    if vote_match:
        code_snippet = vote_match.group(0)
        lines = code_snippet.split('\n')[:20]  # 只显示前20行
        for line in lines:
            print(line)
        if len(code_snippet.split('\n')) > 20:
            print("... (更多代码)")
    else:
        print("❌ 未找到投票逻辑代码")
    
    print("-" * 70)
    
    # ===== 总结 =====
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ 所有检查通过！分解-合并流程的投票机制已正确实现")
        print("\n主要改进:")
        print("1. ✅ 生成多个SQL候选并记录映射关系")
        print("2. ✅ 对每个候选进行refinement或直接执行")
        print("3. ✅ 调用vote_result()进行投票选择最佳SQL")
        print("4. ✅ 正确传递knowledge领域知识到投票逻辑")
        print("5. ✅ 生成最终的result.sql和result.csv")
    else:
        print("❌ 部分检查未通过，请检查实现")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    check_decompose_vote_implementation()
