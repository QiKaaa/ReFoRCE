"""
测试StarRocks环境配置
运行此脚本验证所有组件是否正常工作
"""
import sys
import os

def test_imports():
    """测试导入"""
    print("=" * 80)
    print("测试1: 检查依赖导入")
    print("=" * 80)
    
    try:
        import sqlalchemy
        print("✓ SQLAlchemy:", sqlalchemy.__version__)
    except ImportError as e:
        print("✗ SQLAlchemy导入失败:", e)
        return False
    
    try:
        import pandas
        print("✓ Pandas:", pandas.__version__)
    except ImportError as e:
        print("✗ Pandas导入失败:", e)
        return False
    
    try:
        import openai
        print("✓ OpenAI:", openai.__version__)
    except ImportError as e:
        print("✗ OpenAI导入失败:", e)
        return False
    
    try:
        from starrocks import starrocks
        print("✓ StarRocks客户端已安装")
    except ImportError:
        print("⚠ StarRocks客户端未安装（使用SQLAlchemy连接）")
    
    print("\n✓ 所有核心依赖导入成功\n")
    return True


def test_custom_modules():
    """测试自定义模块"""
    print("=" * 80)
    print("测试2: 检查自定义模块")
    print("=" * 80)
    
    try:
        from sql_starrocks import SqlEnvStarRocks
        print("✓ sql_starrocks.py")
    except Exception as e:
        print("✗ sql_starrocks.py:", e)
        return False
    
    try:
        from schema_parser import SchemaParser
        print("✓ schema_parser.py")
    except Exception as e:
        print("✗ schema_parser.py:", e)
        return False
    
    try:
        from data_loader import DatasetLoader
        print("✓ data_loader.py")
    except Exception as e:
        print("✗ data_loader.py:", e)
        return False
    
    try:
        from prompt_starrocks import PromptsStarRocks
        print("✓ prompt_starrocks.py")
    except Exception as e:
        print("✗ prompt_starrocks.py:", e)
        return False
    
    print("\n✓ 所有自定义模块加载成功\n")
    return True


def test_dataset_loading():
    """测试数据集加载"""
    print("=" * 80)
    print("测试3: 加载数据集")
    print("=" * 80)
    
    try:
        from data_loader import DatasetLoader
        
        dataset_path = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
        
        if not os.path.exists(dataset_path):
            print(f"✗ 数据集文件不存在: {dataset_path}")
            return False
        
        loader = DatasetLoader(dataset_path)
        stats = loader.get_statistics()
        
        print(f"✓ 数据集加载成功")
        print(f"  - 总问题数: {stats['total_examples']}")
        print(f"  - 复杂度分布: {stats['complexity_distribution']}")
        print(f"  - 涉及表数: {stats['total_unique_tables']}")
        
        # 显示第一个示例
        first_ex = loader.get_all_examples()[0]
        print(f"\n  示例问题:")
        print(f"  - ID: {first_ex['sql_id']}")
        print(f"  - Question: {first_ex['question'][:80]}...")
        print(f"  - Tables: {first_ex['table_list'][:3]}...")
        
        print("\n✓ 数据集测试通过\n")
        return True
        
    except Exception as e:
        print(f"✗ 数据集加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_parsing():
    """测试Schema解析"""
    print("=" * 80)
    print("测试4: 解析Schema")
    print("=" * 80)
    
    try:
        from schema_parser import SchemaParser
        
        schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
        
        if not os.path.exists(schema_path):
            print(f"✗ Schema文件不存在: {schema_path}")
            return False
        
        parser = SchemaParser(schema_path)
        
        print(f"✓ Schema解析成功")
        print(f"  - 数据库ID: {parser.db_id}")
        print(f"  - 表数量: {len(parser.tables)}")
        print(f"  - 前5个表: {parser.get_all_tables()[:5]}")
        
        # 测试获取特定表
        test_table = parser.get_all_tables()[0]
        chunk = parser.get_table_chunk(test_table)
        print(f"\n  示例表Schema片段:")
        print("  " + chunk.split('\n')[0])
        print(f"  ... (共{len(chunk.split(chr(10)))}行)")
        
        print("\n✓ Schema解析测试通过\n")
        return True
        
    except Exception as e:
        print(f"✗ Schema解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_connection():
    """测试数据库连接"""
    print("=" * 80)
    print("测试5: 连接StarRocks数据库")
    print("=" * 80)
    
    try:
        from sql_starrocks import SqlEnvStarRocks
        
        sql_env = SqlEnvStarRocks(
            host="localhost",
            port=9030,
            user="root",
            password="",
            database="final_algorithm_competition"
        )
        
        print("✓ SQL环境初始化成功")
        
        # 尝试简单查询
        test_query = "SHOW TABLES"
        result = sql_env.execute_sql_api(
            test_query,
            ex_id="test",
            api="starrocks",
            timeout=10
        )
        
        if isinstance(result, dict) and result.get("status") == "error":
            print(f"✗ 数据库查询失败: {result['error_msg']}")
            print("\n  可能原因:")
            print("  1. StarRocks服务未启动")
            print("  2. 端口9030未开放")
            print("  3. 数据库名称错误")
            print("  4. 用户权限不足")
            return False
        
        print(f"✓ 数据库连接成功")
        print(f"  - 查询结果: {result[:100]}...")
        
        sql_env.close_db()
        print("\n✓ 数据库连接测试通过\n")
        return True
        
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        print("\n  请检查:")
        print("  1. StarRocks是否运行: ps aux | grep starrocks")
        print("  2. 端口是否正确: netstat -an | grep 9030")
        print("  3. 数据库是否存在: mysql -h localhost -P 9030 -u root")
        import traceback
        traceback.print_exc()
        return False


def test_api_key():
    """测试API Key配置"""
    print("=" * 80)
    print("测试6: 检查API Key")
    print("=" * 80)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    azure_key = os.getenv("AZURE_OPENAI_KEY")
    azure_endpoint = os.getenv("AZURE_ENDPOINT")
    
    if openai_key:
        print(f"✓ OPENAI_API_KEY 已设置: {openai_key[:10]}...")
    elif azure_key and azure_endpoint:
        print(f"✓ Azure OpenAI 已配置")
        print(f"  - Endpoint: {azure_endpoint}")
        print(f"  - Key: {azure_key[:10]}...")
    else:
        print("✗ 未找到API Key配置")
        print("\n  请设置环境变量:")
        print("  PowerShell: $env:OPENAI_API_KEY = 'sk-...'")
        print("  或 Azure: $env:AZURE_OPENAI_KEY = '...'")
        return False
    
    print("\n✓ API Key配置检查通过\n")
    return True


def main():
    """运行所有测试"""
    print("\n")
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "  StarRocks版ReFoRCE环境测试".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print("\n")
    
    tests = [
        ("依赖导入", test_imports),
        ("自定义模块", test_custom_modules),
        ("数据集加载", test_dataset_loading),
        ("Schema解析", test_schema_parsing),
        ("数据库连接", test_database_connection),
        ("API Key配置", test_api_key),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name}测试异常: {e}\n")
            results.append((name, False))
    
    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{name:20s} {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print("-" * 80)
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！可以开始运行ReFoRCE了。")
        print("\n快速开始:")
        print("  python run_starrocks.py --max_questions 1 --num_workers 1")
        return 0
    else:
        print("\n⚠️  部分测试失败，请修复后再运行。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
