"""
Prompt 重构验证脚本
验证新的 prompt 管理器是否正常工作
"""

def test_imports():
    """测试导入"""
    print("=" * 60)
    print("测试 1: 导入检查")
    print("=" * 60)
    
    try:
        from prompts import StarRocksPromptManager, BasePromptManager, SchemaLinkingPromptManager
        print("✅ 所有管理器导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_instantiation():
    """测试实例化"""
    print("\n" + "=" * 60)
    print("测试 2: 实例化检查")
    print("=" * 60)
    
    from prompts import StarRocksPromptManager, BasePromptManager, SchemaLinkingPromptManager
    
    try:
        base_mgr = BasePromptManager()
        print("✅ BasePromptManager 实例化成功")
        
        sr_mgr = StarRocksPromptManager()
        print("✅ StarRocksPromptManager 实例化成功")
        
        sl_mgr = SchemaLinkingPromptManager()
        print("✅ SchemaLinkingPromptManager 实例化成功")
        
        return True
    except Exception as e:
        print(f"❌ 实例化失败: {e}")
        return False


def test_system_user_separation():
    """测试 System/User 分离"""
    print("\n" + "=" * 60)
    print("测试 3: System/User Prompt 分离")
    print("=" * 60)
    
    from prompts import StarRocksPromptManager
    
    mgr = StarRocksPromptManager()
    
    # 测试 exploration prompt
    system = mgr.get_exploration_system_prompt(api="starrocks")
    user = mgr.get_exploration_user_prompt(
        table_info="test_table", 
        question="测试问题", 
        table_struct="schema"
    )
    
    print(f"✅ Exploration System Prompt 长度: {len(system)}")
    print(f"✅ Exploration User Prompt 长度: {len(user)}")
    
    # 测试 self_refine prompt
    system = mgr.get_self_refine_system_prompt(api="starrocks", table_struct="schema")
    user = mgr.get_self_refine_user_prompt(
        table_info="test", 
        question="测试", 
        pre_info="", 
        format_csv=None, 
        table_struct="schema"
    )
    
    print(f"✅ Self-Refine System Prompt 长度: {len(system)}")
    print(f"✅ Self-Refine User Prompt 长度: {len(user)}")
    
    return True


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "=" * 60)
    print("测试 4: 向后兼容性")
    print("=" * 60)
    
    from prompts import StarRocksPromptManager
    
    mgr = StarRocksPromptManager()
    
    # 测试旧方法仍然可用
    prompt = mgr.get_exploration_prompt(api="starrocks", table_struct="schema")
    print(f"✅ get_exploration_prompt() 仍然可用, 长度: {len(prompt)}")
    
    prompt = mgr.get_self_refine_prompt(
        table_info="test",
        task="",  # task 参数
        pre_info="", 
        question="测试",
        api="starrocks",
        format_csv=None,
        table_struct="schema"
    )
    print(f"✅ get_self_refine_prompt() 仍然可用, 长度: {len(prompt)}")
    
    return True


def test_schema_linking():
    """测试 Schema Linking Prompt"""
    print("\n" + "=" * 60)
    print("测试 5: Schema Linking Prompt")
    print("=" * 60)
    
    from prompts import SchemaLinkingPromptManager
    
    mgr = SchemaLinkingPromptManager()
    
    system = mgr.get_schema_linking_system_prompt()
    print(f"✅ Schema Linking System Prompt 长度: {len(system)}")
    
    user = mgr.get_schema_linking_user_prompt(
        question="测试问题",
        knowledge="测试知识",
        all_table_schemas="# Table: test\n[...]"
    )
    print(f"✅ Schema Linking User Prompt 长度: {len(user)}")
    
    prompt = mgr.get_schema_linking_prompt(
        question="测试问题",
        knowledge="测试知识",
        all_table_schemas="# Table: test\n[...]"
    )
    print(f"✅ Schema Linking 组合 Prompt 长度: {len(prompt)}")
    
    return True


def test_method_coverage():
    """测试方法覆盖率"""
    print("\n" + "=" * 60)
    print("测试 6: 方法覆盖率")
    print("=" * 60)
    
    from prompts import StarRocksPromptManager
    
    mgr = StarRocksPromptManager()
    
    required_methods = [
        'get_exploration_system_prompt',
        'get_exploration_user_prompt',
        'get_exploration_prompt',
        'get_self_refine_system_prompt',
        'get_self_refine_user_prompt',
        'get_self_refine_prompt',
        'get_self_consistency_system_prompt',
        'get_self_consistency_user_prompt',
        'get_self_consistency_prompt',
        'get_format_analysis_system_prompt',
        'get_format_analysis_user_prompt',
        'get_format_prompt',
    ]
    
    missing_methods = []
    for method in required_methods:
        if not hasattr(mgr, method):
            missing_methods.append(method)
        else:
            print(f"  ✅ {method}")
    
    if missing_methods:
        print(f"\n❌ 缺少方法: {', '.join(missing_methods)}")
        return False
    else:
        print(f"\n✅ 所有 {len(required_methods)} 个必需方法都存在")
        return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Prompt 重构验证测试")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_instantiation,
        test_system_user_separation,
        test_backward_compatibility,
        test_schema_linking,
        test_method_coverage,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过! Prompt 重构成功!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
