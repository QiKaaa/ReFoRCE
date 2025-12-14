"""
并行Schema Linking测试脚本
用于验证ParallelSchemaLinker功能
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from parallel_schema_linker import ParallelSchemaLinker
from chat import GPTChat


def test_basic_usage():
    """测试基本用法"""
    print("="*60)
    print("测试1: 基本用法")
    print("="*60)
    
    # 初始化Linker
    schema_file = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
    linker = ParallelSchemaLinker(schema_file=schema_file)
    
    print(f"✓ 已加载Schema: {len(linker.all_tables)} 个表")
    print(f"✓ 外键数量: {len(linker.foreign_keys.split('\\n'))}")
    
    # 测试问题
    question = "统计2025年7月24日手游全量用户中的竞品游戏活跃用户数"
    table_list = [
        "dim_argothek_gplayerid2qqwxid_df",
        "dws_mgamejp_login_user_activity_di"
    ]
    knowledge = "竞品游戏: sgamecode in ('initiatived', 'jordass')"
    
    print(f"\\n问题: {question}")
    print(f"相关表: {table_list}")
    print(f"领域知识: {knowledge}")
    
    # 创建Chat会话
    chat = GPTChat(
        azure=False,
        model="deepseek-chat",
        temperature=0
    )
    
    print("\\n开始执行并行Schema Linking...")
    
    # 执行Schema Linking
    linked_schema = linker.link_schema(
        question=question,
        table_list=table_list,
        knowledge=knowledge,
        chat_session=chat
    )
    
    print("\\n" + "="*60)
    print("生成的简化Schema:")
    print("="*60)
    print(linked_schema)
    print("="*60)
    
    # 验证结果
    assert linked_schema, "生成的Schema不能为空"
    assert "# Table:" in linked_schema, "Schema应包含表定义"
    
    print("\\n✓ 测试通过！")


def test_internal_methods():
    """测试内部方法"""
    print("\\n" + "="*60)
    print("测试2: 内部方法")
    print("="*60)
    
    schema_file = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
    linker = ParallelSchemaLinker(schema_file=schema_file)
    
    # 测试_parse_all_tables
    print(f"\\n表数量: {len(linker.all_tables)}")
    print(f"前5个表: {linker.all_tables[:5]}")
    
    # 测试_parse_table_schemas
    first_table = linker.all_tables[0]
    print(f"\\n第一个表: {first_table}")
    print(f"Schema片段长度: {len(linker.table_schemas.get(first_table, ''))}")
    
    # 测试_extract_foreign_keys
    print(f"\\n外键信息:")
    print(linker.foreign_keys[:200] + "...")
    
    # 测试_get_filtered_schema
    test_tables = linker.all_tables[:3]
    filtered = linker._get_filtered_schema(test_tables)
    print(f"\\n过滤后Schema长度: {len(filtered)}")
    
    print("\\n✓ 内部方法测试通过！")


def test_merge_results():
    """测试结果合并逻辑"""
    print("\\n" + "="*60)
    print("测试3: 结果合并")
    print("="*60)
    
    schema_file = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
    linker = ParallelSchemaLinker(schema_file=schema_file)
    
    # 模拟MACSQLCoTParse结果
    macsql_result = {
        "tables": ["table1", "table2"],
        "columns": {
            "table1": ["col1", "col2"],
            "table2": ["col3"]
        }
    }
    
    # 模拟RSLSQLBiDirParse结果
    rslsql_result = {
        "tables": ["table2", "table3"],
        "columns": [
            "table2.`col3`",
            "table2.`col4`",
            "table3.`col5`"
        ]
    }
    
    print("\\nMACSQLCoTParse结果:")
    print(macsql_result)
    print("\\nRSLSQLBiDirParse结果:")
    print(rslsql_result)
    
    # 合并
    merged = linker.merge_results(macsql_result, rslsql_result)
    
    print("\\n合并后结果:")
    print(merged)
    
    # 验证
    assert len(merged["tables"]) == 3, "应合并为3个表"
    assert "table1" in merged["tables"], "应包含table1"
    assert "table2" in merged["tables"], "应包含table2"
    assert "table3" in merged["tables"], "应包含table3"
    
    assert len(merged["columns"]) >= 5, "至少应有5个列"
    
    print("\\n✓ 合并测试通过！")


def test_json_extraction():
    """测试JSON提取功能"""
    print("\\n" + "="*60)
    print("测试4: JSON提取")
    print("="*60)
    
    schema_file = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
    linker = ParallelSchemaLinker(schema_file=schema_file)
    
    # 测试不同格式的JSON
    test_cases = [
        # 带```json标记
        ('```json\\n{"tables": ["t1", "t2"]}\\n```', True),
        # 带```标记
        ('```\\n{"tables": ["t1"]}\\n```', True),
        # 纯JSON
        ('{"tables": ["t1", "t2", "t3"]}', True),
        # 嵌套JSON
        ('Some text {"tables": ["t1"], "columns": {"t1": ["c1"]}} more text', True),
        # 无效JSON
        ('No JSON here', False),
    ]
    
    for i, (text, should_succeed) in enumerate(test_cases, 1):
        print(f"\\n测试用例 {i}:")
        print(f"输入: {text[:50]}...")
        
        result = linker._extract_json_from_text(text)
        
        if should_succeed:
            assert result is not None, f"用例{i}应成功提取JSON"
            print(f"✓ 成功提取: {result}")
        else:
            assert result is None, f"用例{i}不应提取到JSON"
            print(f"✓ 正确识别为无效JSON")
    
    print("\\n✓ JSON提取测试通过！")


def main():
    """运行所有测试"""
    print("\\n" + "🧪 " + "="*58)
    print("  ParallelSchemaLinker 测试套件")
    print("="*60 + "\\n")
    
    try:
        # 测试2-4不需要API Key
        test_internal_methods()
        test_merge_results()
        test_json_extraction()
        
        # 测试1需要API Key
        if os.getenv('OPENAI_API_KEY'):
            test_basic_usage()
        else:
            print("\\n⚠️  跳过测试1（需要OPENAI_API_KEY）")
        
        print("\\n" + "🎉 " + "="*58)
        print("  所有测试通过！")
        print("="*60)
        
    except Exception as e:
        print(f"\\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
