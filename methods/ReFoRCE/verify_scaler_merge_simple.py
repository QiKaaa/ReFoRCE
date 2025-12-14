"""
简化验证：直接检查代码而不导入
"""

import os
import re

def verify_agent_methods():
    """验证agent.py包含所需方法"""
    print("=" * 60)
    print("1. 验证agent.py包含新增方法")
    print("=" * 60)
    
    try:
        with open('agent.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查新增的方法
        methods = [
            'def format_sub_questions',
            'def scale_sql',
            'def _extract_sql_from_response',
            'def generate_multiple_sql_candidates',
            'def refine_final_sql'
        ]
        
        print("\n检查新增方法:")
        all_found = True
        for method in methods:
            if method in content:
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} - 未找到")
                all_found = False
        
        # 检查类属性
        attrs = ['SCALE_TEMPLATE_STARROCKS', 'FALLBACK_TEMPLATE']
        print("\n检查类属性:")
        for attr in attrs:
            if attr in content:
                print(f"  ✅ {attr}")
            else:
                print(f"  ❌ {attr} - 未找到")
                all_found = False
        
        return all_found
        
    except FileNotFoundError:
        print("❌ agent.py 未找到")
        return False

def verify_scaler_deleted():
    """验证scaler_starrocks.py已删除"""
    print("\n" + "=" * 60)
    print("2. 验证scaler_starrocks.py已删除")
    print("=" * 60)
    
    scaler_path = "scaler_starrocks.py"
    if os.path.exists(scaler_path):
        print(f"❌ {scaler_path} 仍然存在")
        return False
    else:
        print(f"✅ {scaler_path} 已成功删除")
        return True

def verify_run_starrocks():
    """验证run_starrocks.py的修改"""
    print("\n" + "=" * 60)
    print("3. 验证run_starrocks.py的修改")
    print("=" * 60)
    
    try:
        with open('run_starrocks.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_good = True
        
        # 检查是否移除了导入
        if 'from scaler_starrocks import StarRocksScaler' in content:
            print("❌ 仍然有scaler_starrocks的导入")
            all_good = False
        else:
            print("✅ scaler_starrocks导入已移除")
        
        # 检查是否有scaler.的调用（排除注释）
        scaler_calls = re.findall(r'^[^#]*scaler\.', content, re.MULTILINE)
        if scaler_calls:
            print(f"❌ 仍然有{len(scaler_calls)}处scaler.的调用")
            all_good = False
        else:
            print("✅ 无scaler.的直接调用")
        
        # 检查是否使用了agent的方法
        checks = [
            ('agent.scale_sql(', 'scale_sql调用'),
            ('agent.generate_multiple_sql_candidates(', '生成候选SQL调用'),
            ('agent.refine_final_sql(', 'refinement调用'),
            ('chat_session_scale', '独立的scale chat session')
        ]
        
        print("\n检查新调用方式:")
        for pattern, desc in checks:
            if pattern in content:
                print(f"  ✅ {desc}")
            else:
                print(f"  ⚠️  {desc} - 未找到（可能未启用该功能）")
        
        # 统计agent方法调用
        agent_scale_calls = len(re.findall(r'agent\.scale_sql\(', content))
        agent_candidates_calls = len(re.findall(r'agent\.generate_multiple_sql_candidates\(', content))
        agent_refine_calls = len(re.findall(r'agent\.refine_final_sql\(', content))
        
        print(f"\n方法调用统计:")
        print(f"  - agent.scale_sql(): {agent_scale_calls}次")
        print(f"  - agent.generate_multiple_sql_candidates(): {agent_candidates_calls}次")
        print(f"  - agent.refine_final_sql(): {agent_refine_calls}次")
        
        return all_good
        
    except FileNotFoundError:
        print("❌ run_starrocks.py 未找到")
        return False

def check_documentation():
    """检查文档"""
    print("\n" + "=" * 60)
    print("4. 检查文档")
    print("=" * 60)
    
    docs = [
        'SCALER_MIGRATION.md',
        'REFACTORING_SUMMARY.md'
    ]
    
    all_exist = True
    for doc in docs:
        if os.path.exists(doc):
            print(f"  ✅ {doc}")
        else:
            print(f"  ❌ {doc} - 未找到")
            all_exist = False
    
    return all_exist

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Scaler功能合并验证（简化版）")
    print("=" * 60)
    
    results = []
    
    # 1. 验证agent.py
    results.append(verify_agent_methods())
    
    # 2. 验证文件删除
    results.append(verify_scaler_deleted())
    
    # 3. 验证调用修改
    results.append(verify_run_starrocks())
    
    # 4. 检查文档
    results.append(check_documentation())
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n通过: {passed}/{total}")
    
    if all(results):
        print("\n✅ 所有验证通过！Scaler功能已成功合并到agent.py")
        print("\n✨ 改进内容:")
        print("  1. SQL合并功能统一在REFORCE类中管理")
        print("  2. 删除了独立的scaler_starrocks.py文件")
        print("  3. run_starrocks.py已更新为使用agent方法")
        print("  4. 创建了完整的迁移文档")
        print("\n📋 下一步:")
        print("  1. 运行实际测试确认分解-合并流程")
        print("  2. 检查投票机制是否需要完善")
        print("  3. 验证所有复杂度的问题都能正确处理")
        return 0
    else:
        print("\n❌ 部分验证失败，请检查上述错误")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
