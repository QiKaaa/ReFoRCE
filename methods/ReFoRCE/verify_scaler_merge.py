"""
验证Scaler功能合并是否成功
"""

import sys
import os

def verify_imports():
    """验证导入"""
    print("=" * 60)
    print("1. 验证agent.py可以导入")
    print("=" * 60)
    
    try:
        from agent import REFORCE
        print("✅ agent.py 导入成功")
        
        # 检查新增的方法
        methods = [
            'format_sub_questions',
            'scale_sql',
            '_extract_sql_from_response',
            'generate_multiple_sql_candidates',
            'refine_final_sql'
        ]
        
        print("\n检查新增方法:")
        for method in methods:
            if hasattr(REFORCE, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} - 未找到")
                return False
        
        # 检查类属性
        attrs = ['SCALE_TEMPLATE_STARROCKS', 'FALLBACK_TEMPLATE']
        print("\n检查类属性:")
        for attr in attrs:
            if hasattr(REFORCE, attr):
                print(f"  ✅ {attr}")
            else:
                print(f"  ❌ {attr} - 未找到")
                return False
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
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
        
        # 检查是否移除了导入
        if 'from scaler_starrocks import StarRocksScaler' in content:
            print("❌ 仍然有scaler_starrocks的导入")
            return False
        else:
            print("✅ scaler_starrocks导入已移除")
        
        # 检查是否有scaler.的调用
        if 'scaler.' in content:
            print("❌ 仍然有scaler.的调用")
            return False
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
        
        return True
        
    except FileNotFoundError:
        print("❌ run_starrocks.py 未找到")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Scaler功能合并验证")
    print("=" * 60)
    
    results = []
    
    # 1. 验证导入
    results.append(verify_imports())
    
    # 2. 验证文件删除
    results.append(verify_scaler_deleted())
    
    # 3. 验证调用修改
    results.append(verify_run_starrocks())
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    if all(results):
        print("✅ 所有验证通过！Scaler功能已成功合并到agent.py")
        print("\n下一步:")
        print("1. 运行实际测试确认分解-合并流程")
        print("2. 检查投票机制是否需要完善")
        return 0
    else:
        print("❌ 部分验证失败，请检查上述错误")
        return 1

if __name__ == '__main__':
    sys.exit(main())
