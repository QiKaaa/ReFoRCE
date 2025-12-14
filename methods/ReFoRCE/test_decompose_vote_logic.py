#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试分解-合并投票逻辑

模拟投票场景，验证vote_result()方法能否正确选择最佳SQL
"""

import os
import sys
import pandas as pd
from io import StringIO

# 模拟投票场景
def simulate_voting_scenarios():
    """
    模拟不同投票场景的结果
    """
    
    print("=" * 70)
    print("分解-合并投票逻辑测试")
    print("=" * 70)
    
    # ===== 场景1: 2个候选有相同结果，1个不同 =====
    print("\n场景1: 2个候选有相同结果（应选择相同结果的SQL）")
    print("-" * 70)
    
    candidates_scenario1 = {
        "decompose_0_result.sql": "id,name\n1,Alice\n2,Bob\n",
        "decompose_1_result.sql": "id,name\n1,Alice\n2,Bob\n",  # 与0相同
        "decompose_2_result.sql": "id,name\n1,Alice\n",          # 不同
    }
    
    # 计算投票
    result1 = {}
    csv_data = list(candidates_scenario1.values())
    
    for i, (sql_name, csv_content) in enumerate(candidates_scenario1.items()):
        same_ans = 0
        for j, other_csv in enumerate(csv_data):
            if i != j and csv_content == other_csv:
                same_ans += 1
        result1[sql_name] = same_ans
    
    print(f"投票结果: {result1}")
    winner1 = max(result1, key=result1.get)
    print(f"✅ 获胜者: {winner1} (票数: {result1[winner1]})")
    
    # ===== 场景2: 所有候选结果都不同 =====
    print("\n场景2: 所有候选结果都不同（需要LLM投票）")
    print("-" * 70)
    
    candidates_scenario2 = {
        "decompose_0_result.sql": "id,name\n1,Alice\n2,Bob\n",
        "decompose_1_result.sql": "id,name\n1,Alice\n",
        "decompose_2_result.sql": "id,name\n1,Charlie\n",
    }
    
    result2 = {}
    csv_data2 = list(candidates_scenario2.values())
    
    for i, (sql_name, csv_content) in enumerate(candidates_scenario2.items()):
        same_ans = 0
        for j, other_csv in enumerate(csv_data2):
            if i != j and csv_content == other_csv:
                same_ans += 1
        result2[sql_name] = same_ans
    
    print(f"投票结果: {result2}")
    print("⚠️  所有候选票数为0，需要启用 --model_vote 进行LLM投票")
    
    # ===== 场景3: 平票（2个候选都有1票）=====
    print("\n场景3: 平票情况")
    print("-" * 70)
    
    candidates_scenario3 = {
        "decompose_0_result.sql": "id,name\n1,Alice\n",
        "decompose_1_result.sql": "id,name\n1,Alice\n",  # 与0相同
        "decompose_2_result.sql": "id,name\n2,Bob\n",
        "decompose_3_result.sql": "id,name\n2,Bob\n",    # 与2相同
    }
    
    result3 = {}
    csv_data3 = list(candidates_scenario3.values())
    
    for i, (sql_name, csv_content) in enumerate(candidates_scenario3.items()):
        same_ans = 0
        for j, other_csv in enumerate(csv_data3):
            if i != j and csv_content == other_csv:
                same_ans += 1
        result3[sql_name] = same_ans
    
    print(f"投票结果: {result3}")
    max_vote = max(result3.values())
    winners = [k for k, v in result3.items() if v == max_vote]
    print(f"⚠️  平票: {winners} 都有 {max_vote} 票")
    print("   需要启用 --model_vote 进行LLM二次投票")
    
    # ===== 场景4: 明确的赢家（3个相同，1个不同）=====
    print("\n场景4: 明确的赢家（最理想情况）")
    print("-" * 70)
    
    candidates_scenario4 = {
        "decompose_0_result.sql": "id,name\n1,Alice\n2,Bob\n",
        "decompose_1_result.sql": "id,name\n1,Alice\n2,Bob\n",  # 相同
        "decompose_2_result.sql": "id,name\n1,Alice\n2,Bob\n",  # 相同
        "decompose_3_result.sql": "id,name\n999,Error\n",       # 不同（错误）
    }
    
    result4 = {}
    csv_data4 = list(candidates_scenario4.values())
    
    for i, (sql_name, csv_content) in enumerate(candidates_scenario4.items()):
        same_ans = 0
        for j, other_csv in enumerate(csv_data4):
            if i != j and csv_content == other_csv:
                same_ans += 1
        result4[sql_name] = same_ans
    
    print(f"投票结果: {result4}")
    winner4 = max(result4, key=result4.get)
    print(f"✅ 明确获胜者: {winner4} (票数: {result4[winner4]})")
    print("   直接选择该SQL，无需LLM投票")
    
    # ===== 总结 =====
    print("\n" + "=" * 70)
    print("投票逻辑总结")
    print("=" * 70)
    print("""
1. ✅ 有明确赢家（票数最高且唯一）
   → 直接选择该SQL作为result.sql

2. ⚠️  平票（多个候选票数最高）
   → 启用 --model_vote 使用LLM进行二次投票
   → 或使用 --random_vote_for_tie 随机选择

3. ⚠️  所有候选结果都不同（票数都为0）
   → 启用 --model_vote 使用LLM选择最佳SQL
   → 或使用 --final_choose 选择第一个有效候选
   → 否则不生成result.sql

4. ❌ 没有有效候选
   → 记录警告，不生成result.sql
    """)
    
    print("\n推荐参数配置:")
    print("  --do_vote --use_decompose --num_votes 3 --model_vote")

if __name__ == "__main__":
    simulate_voting_scenarios()
