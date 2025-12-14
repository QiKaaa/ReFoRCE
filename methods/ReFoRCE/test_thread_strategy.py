"""
测试线程策略选择逻辑
"""

def test_strategy_selection():
    print("=" * 60)
    print("测试: 线程策略选择")
    print("=" * 60)
    
    # 模拟不同的thread_prefix
    test_cases = [
        ("linked_0", 0, False, "normal"),
        ("linked_1", 1, False, "normal"),
        ("linked_2", 2, True, "fallback"),  # 每3个中的第3个
        ("linked_3", 3, False, "normal"),
        ("linked_4", 4, False, "normal"),
        ("linked_5", 5, True, "fallback"),  # 每3个中的第3个
        ("original_0", 0, False, "normal"),
        ("original_1", 1, False, "normal"),
        ("original_2", 2, True, "fallback"),
    ]
    
    print("\n线程策略分配:")
    print(f"{'Thread Prefix':<20} {'Index':<8} {'Fallback':<10} {'Strategy':<10}")
    print("-" * 60)
    
    for thread_prefix, expected_index, expected_fallback, expected_strategy in test_cases:
        # 提取线程编号
        thread_index = 0
        if thread_prefix:
            parts = thread_prefix.split('_')
            if len(parts) > 1 and parts[1].isdigit():
                thread_index = int(parts[1])
        
        # 每3个线程中有1个使用fallback
        use_fallback = (thread_index % 3 == 2)
        strategy = "fallback" if use_fallback else "normal"
        
        # 验证
        status = "✓" if (thread_index == expected_index and 
                        use_fallback == expected_fallback and 
                        strategy == expected_strategy) else "✗"
        
        print(f"{status} {thread_prefix:<20} {thread_index:<8} {use_fallback:<10} {strategy:<10}")
    
    print("\n" + "=" * 60)
    print("✓ 策略选择验证完成")
    print("=" * 60)
    
    # 测试文件命名
    print("\n" + "=" * 60)
    print("测试: 文件命名")
    print("=" * 60)
    
    test_prefixes = [
        ("linked_0", "decompose_linked_0"),
        ("linked_1", "decompose_linked_1"),
        ("linked_2", "decompose_linked_2"),
        ("original_0", "decompose_original_0"),
        ("original_1", "decompose_original_1"),
        ("original_2", "decompose_original_2"),
    ]
    
    print("\n文件前缀生成:")
    print(f"{'Thread Prefix':<20} {'File Prefix':<30}")
    print("-" * 60)
    
    for thread_prefix, expected_file_prefix in test_prefixes:
        # 生成文件前缀
        if thread_prefix:
            parts = thread_prefix.split('_')
            if parts[0] in ['linked', 'original']:
                file_prefix = f"decompose_{thread_prefix}"
            else:
                file_prefix = f"decompose_{thread_prefix}"
        else:
            file_prefix = "decompose"
        
        status = "✓" if file_prefix == expected_file_prefix else "✗"
        print(f"{status} {thread_prefix:<20} {file_prefix:<30}")
    
    print("\n✓ 文件命名验证完成")

if __name__ == "__main__":
    test_strategy_selection()
