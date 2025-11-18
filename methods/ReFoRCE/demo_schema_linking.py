"""
Schema Linking 演示脚本
展示如何使用优化的 Schema Linking 方案
"""

from schema_linking_optimized import OptimizedSchemaLinker
import json

def demo_single_example():
    """演示单个样本的处理"""
    
    print("="*80)
    print("Schema Linking 优化方案演示")
    print("="*80)
    
    # 初始化 linker
    print("\n📚 加载 Schema...")
    linker = OptimizedSchemaLinker(
        schema_file='e:/Project/track3_2/M-schema/final_algorithm_competition.txt'
    )
    
    # 示例问题
    example = {
        "sql_id": "sql_1",
        "question": """统计2025.07.24的手游全量用户且标签为其他,在竞品业务下2025.05.30-2025.07.24的在线时长。
输出:suserid、sgamecode、ionlinetime""",
        "table_list": [
            "dws_mgamejp_login_user_activity_di",
            "dim_vplayerid_vies_df"
        ],
        "knowledge": """竞品业务:
sgamecode in ("initiatived","jordass","esports","allianceforce","strategy","playzone","su")
saccounttype = "-100" -- 账号体系,取-100表示汇总
and suseridtype in ("qq","wxid") -- 用户类型
and splattype = "-100" -- 平台类型
and splat = "-100" -- 平台,写死为-100"""
    }
    
    print(f"\n📋 处理问题: {example['sql_id']}")
    print(f"问题: {example['question'][:50]}...")
    print(f"涉及表数: {len(example['table_list'])}")
    
    # 执行 schema linking
    print("\n🔗 执行 Schema Linking...")
    linked_schema = linker.link_schema(
        question=example['question'],
        table_list=example['table_list'],
        knowledge=example['knowledge'],
        max_examples=3
    )
    
    # 统计信息
    print("\n📊 压缩效果:")
    for table_name, table_info in linked_schema.items():
        original_cols = len(linker.all_tables[table_name]['columns'])
        filtered_cols = len(table_info['columns'])
        compression = (1 - filtered_cols / original_cols) * 100
        
        print(f"  {table_name}:")
        print(f"    原始列数: {original_cols}")
        print(f"    保留列数: {filtered_cols}")
        print(f"    压缩比: {compression:.1f}%")
        print(f"    保留的列: {', '.join(table_info['columns'][:5])}...")
    
    # 格式化输出
    print("\n📝 生成的 Schema Prompt:")
    print("-"*80)
    schema_prompt = linker.format_schema_prompt(linked_schema)
    print(schema_prompt[:500])
    print("... (省略)")
    print("-"*80)
    
    # 保存结果
    output_file = 'e:/Project/track3_2/output/schema_linking/demo_result.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(schema_prompt)
    print(f"\n💾 完整结果已保存到: {output_file}")
    
    return linked_schema


def demo_batch_processing():
    """演示批量处理"""
    
    print("\n"+"="*80)
    print("批量处理演示")
    print("="*80)
    
    # 加载数据集
    dataset_path = 'e:/Project/track3_2/final_for_student/data/final_dataset_example.json'
    print(f"\n📂 加载数据集: {dataset_path}")
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    print(f"总样本数: {len(dataset)}")
    
    # 统计不同复杂度的样本
    complexity_count = {}
    for ex in dataset:
        complexity = ex.get('复杂度', '未知')
        complexity_count[complexity] = complexity_count.get(complexity, 0) + 1
    
    print(f"\n复杂度分布:")
    for complexity, count in sorted(complexity_count.items()):
        print(f"  {complexity}: {count} 个")
    
    # 初始化 linker
    linker = OptimizedSchemaLinker(
        schema_file='e:/Project/track3_2/M-schema/final_algorithm_competition.txt'
    )
    
    # 随机选择几个样本展示
    import random
    sample_examples = random.sample(dataset, min(5, len(dataset)))
    
    print(f"\n🎲 随机选择 {len(sample_examples)} 个样本展示:")
    print("-"*80)
    
    total_cols_before = 0
    total_cols_after = 0
    
    for i, example in enumerate(sample_examples, 1):
        linked_schema = linker.link_schema(
            question=example['question'],
            table_list=example['table_list'],
            knowledge=example.get('knowledge', ''),
            max_examples=3
        )
        
        cols_before = sum(
            len(linker.all_tables[t]['columns']) 
            for t in example['table_list'] 
            if t in linker.all_tables
        )
        cols_after = sum(len(t['columns']) for t in linked_schema.values())
        
        total_cols_before += cols_before
        total_cols_after += cols_after
        
        print(f"\n{i}. {example['sql_id']} ({example.get('复杂度', '未知')})")
        print(f"   表数: {len(example['table_list'])}")
        print(f"   列数: {cols_before} → {cols_after} (压缩 {(1-cols_after/cols_before)*100:.1f}%)")
        print(f"   问题: {example['question'][:60]}...")
    
    print("\n" + "="*80)
    print(f"总体压缩比: {(1-total_cols_after/total_cols_before)*100:.1f}%")
    print(f"列数: {total_cols_before} → {total_cols_after}")


def demo_comparison():
    """演示优化前后对比"""
    
    print("\n"+"="*80)
    print("优化前后对比")
    print("="*80)
    
    linker = OptimizedSchemaLinker(
        schema_file='e:/Project/track3_2/M-schema/final_algorithm_competition.txt'
    )
    
    # 选择一个示例
    example = {
        "question": "统计网吧玩家的活跃数据",
        "table_list": ["dws_argothek_oss_login_di"],
        "knowledge": "iloginway in (1,10,11,12) and inetbarlevel > 0"
    }
    
    table_name = example['table_list'][0]
    
    # 优化前: 所有列
    print(f"\n📊 表: {table_name}")
    original_cols = linker.all_tables[table_name]['columns']
    print(f"\n✗ 优化前 ({len(original_cols)} 列):")
    print(f"  {', '.join(original_cols)}")
    
    # 优化后: 筛选的列
    linked_schema = linker.link_schema(
        question=example['question'],
        table_list=example['table_list'],
        knowledge=example['knowledge'],
        max_examples=3
    )
    
    filtered_cols = linked_schema[table_name]['columns']
    print(f"\n✓ 优化后 ({len(filtered_cols)} 列):")
    print(f"  {', '.join(filtered_cols)}")
    
    # 分析保留/剔除的列
    removed_cols = set(original_cols) - set(filtered_cols)
    print(f"\n❌ 剔除的列 ({len(removed_cols)}):")
    print(f"  {', '.join(list(removed_cols)[:10])}...")
    
    print(f"\n💡 压缩比: {len(filtered_cols)/len(original_cols)*100:.1f}%")
    
    # 估算 token 节省
    token_before = len(' '.join(original_cols)) * 1.3  # 粗略估算
    token_after = len(' '.join(filtered_cols)) * 1.3
    print(f"💰 Token 节省: ~{token_before:.0f} → ~{token_after:.0f} ({(1-token_after/token_before)*100:.1f}% ⬇️)")


if __name__ == '__main__':
    # 运行演示
    print("\n🚀 开始演示...\n")
    
    # 1. 单个样本处理
    demo_single_example()
    
    # 2. 批量处理
    demo_batch_processing()
    
    # 3. 优化对比
    demo_comparison()
    
    print("\n✅ 演示完成!")
    print("\n📚 详细说明请查看: SCHEMA_LINKING_GUIDE.md")
    print("📊 效果对比请查看: output/schema_linking/COMPARISON.md")
