"""
ReFoRCE StarRocks版演示脚本
快速演示如何使用各个组件
"""

def demo_schema_parser():
    """演示Schema解析器"""
    print("=" * 80)
    print("演示1: Schema解析器")
    print("=" * 80)
    
    from schema_parser import SchemaParser
    
    # 初始化
    schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
    parser = SchemaParser(schema_path)
    
    print(f"✓ 数据库: {parser.db_id}")
    print(f"✓ 表数量: {len(parser.tables)}")
    print(f"✓ 表列表: {parser.get_all_tables()[:3]}...\n")
    
    # 获取单个表的Schema
    table_name = parser.get_all_tables()[0]
    chunk = parser.get_table_chunk(table_name)
    print(f"示例表 '{table_name}' 的Schema:")
    print(chunk[:300] + "...\n")
    
    # 获取多个表的Schema
    table_list = parser.get_all_tables()[:2]
    schema_text = parser.get_tables_chunks(table_list)
    print(f"获取 {len(table_list)} 个表的Schema，总长度: {len(schema_text)} 字符\n")


def demo_data_loader():
    """演示数据加载器"""
    print("=" * 80)
    print("演示2: 数据加载器")
    print("=" * 80)
    
    from data_loader import DatasetLoader
    
    # 加载数据
    dataset_path = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
    loader = DatasetLoader(dataset_path)
    
    # 统计信息
    stats = loader.get_statistics()
    print(f"✓ 总问题数: {stats['total_examples']}")
    print(f"✓ 复杂度分布: {stats['complexity_distribution']}")
    print(f"✓ 涉及表数: {stats['total_unique_tables']}\n")
    
    # 获取第一个示例
    first_ex = loader.get_all_examples()[0]
    print(f"示例问题:")
    print(f"  SQL ID: {first_ex['sql_id']}")
    print(f"  Question: {first_ex['question'][:100]}...")
    print(f"  Tables: {first_ex['table_list']}")
    print(f"  Complexity: {first_ex['复杂度']}\n")
    
    # 按复杂度过滤
    simple_questions = loader.filter_by_complexity("简单")
    print(f"✓ 简单题目数量: {len(simple_questions)}\n")


def demo_sql_connection():
    """演示StarRocks连接"""
    print("=" * 80)
    print("演示3: StarRocks数据库连接")
    print("=" * 80)
    
    from sql_starrocks import SqlEnvStarRocks
    
    try:
        # 初始化SQL环境
        sql_env = SqlEnvStarRocks(
            host="localhost",
            port=9030,
            user="root",
            password="",
            database="final_algorithm_competition"
        )
        
        print("✓ SQL环境初始化成功\n")
        
        # 测试简单查询
        test_query = "SHOW TABLES"
        print(f"执行查询: {test_query}")
        result = sql_env.execute_sql_api(
            test_query,
            ex_id="demo",
            api="starrocks",
            timeout=10
        )
        
        if isinstance(result, dict) and result.get("status") == "error":
            print(f"✗ 查询失败: {result['error_msg']}")
            print("\n提示: 请确保StarRocks正在运行且数据库存在")
        else:
            print(f"✓ 查询成功!")
            print(f"结果预览:\n{result[:200]}...\n")
        
        # 关闭连接
        sql_env.close_db()
        
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("\n请检查:")
        print("  1. StarRocks是否运行: ps aux | grep starrocks")
        print("  2. 端口9030是否可访问")
        print("  3. 数据库final_algorithm_competition是否存在\n")


def demo_prompt_generation():
    """演示Prompt生成"""
    print("=" * 80)
    print("演示4: StarRocks Prompt生成")
    print("=" * 80)
    
    from prompt_starrocks import PromptsStarRocks
    from schema_parser import SchemaParser
    from data_loader import DatasetLoader
    
    # 初始化组件
    prompt_gen = PromptsStarRocks()
    schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
    dataset_path = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
    
    parser = SchemaParser(schema_path)
    loader = DatasetLoader(dataset_path)
    
    # 获取第一个问题
    example = loader.get_all_examples()[0]
    question = example['question']
    table_list = example['table_list']
    knowledge = example.get('knowledge', '')
    
    # 获取相关表的Schema
    table_info = parser.get_tables_chunks(table_list)
    if knowledge:
        table_info += f"\n\nDomain Knowledge:\n{knowledge}\n"
    
    # 生成Prompt
    table_struct = f"Available tables: {', '.join(table_list)}"
    prompt = prompt_gen.get_self_refine_prompt(
        table_info=table_info,
        task=question,
        pre_info=None,
        question=question,
        api="starrocks",
        format_csv=None,
        table_struct=table_struct
    )
    
    print(f"✓ 为问题 '{example['sql_id']}' 生成的Prompt长度: {len(prompt)} 字符")
    print(f"\nPrompt预览:")
    print(prompt[:500] + "...\n")
    
    # 显示StarRocks特定提示
    print("StarRocks日期函数提示:")
    print(prompt_gen.get_starrocks_date_functions()[:200] + "...\n")


def demo_complete_workflow():
    """演示完整工作流"""
    print("=" * 80)
    print("演示5: 完整工作流（不执行SQL）")
    print("=" * 80)
    
    from schema_parser import SchemaParser
    from data_loader import DatasetLoader
    from prompt_starrocks import PromptsStarRocks
    
    # 1. 加载数据
    print("Step 1: 加载数据集...")
    loader = DatasetLoader("E:/Project/track3_2/final_for_student/data/final_dataset_example.json")
    example = loader.get_all_examples()[0]
    print(f"  ✓ 选择问题: {example['sql_id']}\n")
    
    # 2. 解析Schema
    print("Step 2: 解析Schema...")
    parser = SchemaParser("E:/Project/track3_2/M-schema/final_algorithm_competition.txt")
    print(f"  ✓ 加载了 {len(parser.tables)} 个表定义\n")
    
    # 3. 获取相关表Schema
    print("Step 3: 根据table_list获取相关Schema...")
    table_list = example['table_list']
    table_info = parser.get_tables_chunks(table_list)
    print(f"  ✓ 获取了 {len(table_list)} 个表的Schema")
    print(f"  ✓ Schema总长度: {len(table_info)} 字符\n")
    
    # 4. 添加领域知识
    print("Step 4: 添加领域知识...")
    knowledge = example.get('knowledge', '')
    if knowledge:
        table_info += f"\n\nDomain Knowledge:\n{knowledge}\n"
        print(f"  ✓ 添加了 {len(knowledge)} 字符的领域知识\n")
    else:
        print(f"  - 无额外领域知识\n")
    
    # 5. 生成Prompt
    print("Step 5: 生成Prompt...")
    prompt_gen = PromptsStarRocks()
    table_struct = f"Available tables: {', '.join(table_list)}"
    prompt = prompt_gen.get_self_refine_prompt(
        table_info=table_info,
        task=example['question'],
        pre_info=None,
        question=example['question'],
        api="starrocks",
        format_csv=None,
        table_struct=table_struct
    )
    print(f"  ✓ 生成的Prompt长度: {len(prompt)} 字符\n")
    
    # 6. 总结
    print("Step 6: 准备完成!")
    print(f"  • 问题ID: {example['sql_id']}")
    print(f"  • 问题文本: {example['question'][:60]}...")
    print(f"  • 涉及表数: {len(table_list)}")
    print(f"  • 复杂度: {example['复杂度']}")
    print(f"  • 最终Prompt大小: {len(prompt)} 字符")
    print("\n  → 现在可以将Prompt发送给LLM生成SQL了！\n")


def main():
    """主函数"""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  ReFoRCE StarRocks版 - 功能演示".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print("\n")
    
    demos = [
        ("Schema解析器", demo_schema_parser),
        ("数据加载器", demo_data_loader),
        ("StarRocks连接", demo_sql_connection),
        ("Prompt生成", demo_prompt_generation),
        ("完整工作流", demo_complete_workflow),
    ]
    
    for i, (name, func) in enumerate(demos, 1):
        try:
            func()
        except Exception as e:
            print(f"\n✗ {name}演示失败: {e}")
            import traceback
            traceback.print_exc()
            print()
        
        if i < len(demos):
            input("按Enter继续下一个演示...")
            print("\n")
    
    print("=" * 80)
    print("演示完成！")
    print("=" * 80)
    print("\n下一步:")
    print("  1. 运行环境测试: python test_starrocks_setup.py")
    print("  2. 查看快速启动: QUICKSTART_STARROCKS.md")
    print("  3. 运行完整程序: python run_starrocks.py --max_questions 1\n")


if __name__ == "__main__":
    main()
