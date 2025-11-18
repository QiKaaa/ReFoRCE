"""
优化的 Schema Linking 方案
专为 final_algorithm_competition 数据集设计

特点:
1. 直接使用标注的 table_list (零成本,100%准确)
2. 从 knowledge 字段提取列名
3. 从 question 字段匹配列名
4. 智能 Schema 压缩
"""

import os
import json
import csv
import re
import sys
from typing import Dict, List, Set, Tuple
from tqdm import tqdm
import argparse

# 设置 CSV 字段大小限制 (处理 Windows 平台的限制)
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)


class OptimizedSchemaLinker:
    """优化的 Schema Linking 类"""
    
    def __init__(self, schema_file: str):
        """
        初始化
        Args:
            schema_file: schema 文件路径 (如 final_algorithm_competition.txt)
        """
        self.schema_file = schema_file
        self.all_tables = {}  # {table_name: {columns: [...], descriptions: {...}}}
        self._load_schema()
    
    def _load_schema(self):
        """从 schema 文件加载所有表和列信息"""
        with open(self.schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析表定义
        table_pattern = r'# Table: ([^,]+),([^\n]+)\n\[(.*?)\n\]'
        matches = re.finditer(table_pattern, content, re.DOTALL)
        
        for match in matches:
            table_name = match.group(1).strip()
            table_desc = match.group(2).strip()
            columns_block = match.group(3)
            
            columns = []
            col_desc = {}
            
            # 解析列定义
            col_pattern = r'\(([^:]+):([^,]+),([^,\)]+)(?:, Examples: \[([^\]]*)\])?\)'
            for col_match in re.finditer(col_pattern, columns_block):
                col_name = col_match.group(1).strip()
                col_type = col_match.group(2).strip()
                col_comment = col_match.group(3).strip()
                examples = col_match.group(4) if col_match.group(4) else ""
                
                columns.append(col_name)
                col_desc[col_name] = {
                    'type': col_type,
                    'comment': col_comment,
                    'examples': examples
                }
            
            self.all_tables[table_name] = {
                'description': table_desc,
                'columns': columns,
                'column_details': col_desc
            }
        
        print(f"已加载 {len(self.all_tables)} 张表的 schema 信息")
    
    def extract_columns_from_knowledge(self, knowledge: str) -> Set[str]:
        """
        从 knowledge 字段提取相关列名
        
        Args:
            knowledge: knowledge 字符串
            
        Returns:
            提取到的列名集合
        """
        if not knowledge:
            return set()
        
        columns = set()
        
        # 提取条件中的列名 (如: sgamecode in (...), saccounttype = "...")
        # 匹配模式: 列名 后面跟 =, in, >, <, >= 等
        patterns = [
            r'\b([a-z_][a-z0-9_]*)\s*(?:=|in|>|<|>=|<=|!=)',  # 条件表达式
            r'\b([a-z_][a-z0-9_]*)\s*\(.*?\)',  # 函数调用
            r'sum\(([a-z_][a-z0-9_]*)\)',  # 聚合函数
            r'count\((?:distinct\s+)?([a-z_][a-z0-9_]*)\)',
            r'max\(([a-z_][a-z0-9_]*)\)',
            r'min\(([a-z_][a-z0-9_]*)\)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, knowledge, re.IGNORECASE):
                col_name = match.group(1).lower()
                # 过滤掉 SQL 关键字
                if col_name not in ['and', 'or', 'not', 'in', 'is', 'null', 'case', 'when', 'then', 'else', 'end']:
                    columns.add(col_name)
        
        return columns
    
    def extract_columns_from_question(self, question: str, table_columns: List[str]) -> Set[str]:
        """
        从问题中匹配列名
        
        Args:
            question: 问题文本
            table_columns: 表的所有列名
            
        Returns:
            匹配到的列名集合
        """
        matched_columns = set()
        question_lower = question.lower()
        
        for col in table_columns:
            col_lower = col.lower()
            # 如果列名在问题中出现
            if col_lower in question_lower:
                matched_columns.add(col)
        
        # 也可以根据列的注释匹配
        # 这里暂时简化处理
        
        return matched_columns
    
    def get_key_columns(self, table_name: str) -> Set[str]:
        """
        获取表的关键列 (主键、外键、时间字段等)
        
        Args:
            table_name: 表名
            
        Returns:
            关键列集合
        """
        if table_name not in self.all_tables:
            return set()
        
        key_columns = set()
        columns = self.all_tables[table_name]['column_details']
        
        for col_name, col_info in columns.items():
            col_lower = col_name.lower()
            comment_lower = col_info['comment'].lower()
            
            # 识别关键字段
            if any(keyword in col_lower for keyword in [
                'id', 'date', 'time', 'dt', 'key', 'userid', 'playerid',
                'vplayerid', 'gplayerid', 'suserid', 'iuserid', 'vroleid'
            ]):
                key_columns.add(col_name)
            
            # 识别日期/时间字段
            if any(keyword in comment_lower for keyword in [
                '日期', '时间', 'id', '标识', '主键', '外键'
            ]):
                key_columns.add(col_name)
        
        return key_columns
    
    def link_schema(self, 
                   question: str, 
                   table_list: List[str], 
                   knowledge: str = "",
                   max_examples: int = 3) -> Dict[str, Dict]:
        """
        执行 Schema Linking
        
        Args:
            question: 问题文本
            table_list: 标注的相关表列表
            knowledge: knowledge 字段
            max_examples: 每列最多保留的示例数
            
        Returns:
            {table_name: {columns: [...], column_details: {...}}}
        """
        linked_schema = {}
        
        # 从 knowledge 提取列名
        cols_from_knowledge = self.extract_columns_from_knowledge(knowledge)
        
        for table_name in table_list:
            if table_name not in self.all_tables:
                print(f"警告: 表 {table_name} 不在 schema 中")
                continue
            
            table_info = self.all_tables[table_name]
            
            # 从问题匹配列名
            cols_from_question = self.extract_columns_from_question(
                question, 
                table_info['columns']
            )
            
            # 获取关键列
            key_columns = self.get_key_columns(table_name)
            
            # 合并所有相关列
            relevant_columns = cols_from_knowledge | cols_from_question | key_columns
            
            # 如果没有找到任何相关列,保留所有列 (安全策略)
            if not relevant_columns:
                relevant_columns = set(table_info['columns'])
            
            # 构建压缩后的列信息
            compressed_cols = {}
            for col in relevant_columns:
                if col in table_info['column_details']:
                    col_detail = table_info['column_details'][col].copy()
                    # 限制示例数量
                    if col_detail['examples']:
                        examples = col_detail['examples'].split(', ')[:max_examples]
                        col_detail['examples'] = ', '.join(examples)
                    compressed_cols[col] = col_detail
            
            linked_schema[table_name] = {
                'description': table_info['description'],
                'columns': list(relevant_columns),
                'column_details': compressed_cols
            }
        
        return linked_schema
    
    def format_schema_prompt(self, linked_schema: Dict[str, Dict]) -> str:
        """
        将 linked schema 格式化为 prompt
        
        Args:
            linked_schema: link_schema() 的返回结果
            
        Returns:
            格式化的 schema 字符串
        """
        lines = []
        
        for table_name, table_info in linked_schema.items():
            lines.append(f"# Table: {table_name}, {table_info['description']}")
            lines.append("[")
            
            for col in table_info['columns']:
                if col in table_info['column_details']:
                    col_detail = table_info['column_details'][col]
                    examples_str = f", Examples: [{col_detail['examples']}]" if col_detail['examples'] else ""
                    lines.append(
                        f"({col}:{col_detail['type']}, {col_detail['comment']}{examples_str}),"
                    )
            
            # 移除最后一个逗号
            if lines[-1].endswith(','):
                lines[-1] = lines[-1][:-1]
            
            lines.append("]")
            lines.append("")
        
        return "\n".join(lines)


def process_dataset(dataset_path: str, 
                    schema_file: str, 
                    output_dir: str,
                    max_examples: int = 3):
    """
    处理整个数据集
    
    Args:
        dataset_path: 数据集 JSON 文件路径
        schema_file: schema 文件路径
        output_dir: 输出目录
        max_examples: 每列最多保留的示例数
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载数据集
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # 创建 linker
    linker = OptimizedSchemaLinker(schema_file)
    
    # 处理每个样本
    results = []
    
    for example in tqdm(dataset, desc="Processing examples"):
        sql_id = example['sql_id']
        question = example['question']
        table_list = example['table_list']
        knowledge = example.get('knowledge', '')
        
        # 执行 schema linking
        linked_schema = linker.link_schema(
            question=question,
            table_list=table_list,
            knowledge=knowledge,
            max_examples=max_examples
        )
        
        # 格式化为 prompt
        schema_prompt = linker.format_schema_prompt(linked_schema)
        
        # 保存结果
        result = {
            'sql_id': sql_id,
            'question': question,
            'knowledge': knowledge,
            'table_list': table_list,
            'linked_schema': linked_schema,
            'schema_prompt': schema_prompt,
            '复杂度': example.get('复杂度', '')
        }
        
        results.append(result)
        
        # 保存单个样本的 schema prompt
        with open(os.path.join(output_dir, f"{sql_id}_schema.txt"), 'w', encoding='utf-8') as f:
            f.write(schema_prompt)
    
    # 保存所有结果
    with open(os.path.join(output_dir, 'schema_linking_results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 统计信息
    print("\n=== Schema Linking 统计 ===")
    total_tables_before = sum(len(ex['table_list']) for ex in dataset)
    total_tables_after = sum(len(r['linked_schema']) for r in results)
    
    total_cols_before = 0
    total_cols_after = 0
    
    for result in results:
        for table in result['table_list']:
            if table in linker.all_tables:
                total_cols_before += len(linker.all_tables[table]['columns'])
        
        for table_info in result['linked_schema'].values():
            total_cols_after += len(table_info['columns'])
    
    print(f"样本数: {len(dataset)}")
    print(f"表数 (前): {total_tables_before}, (后): {total_tables_after}")
    print(f"列数 (前): {total_cols_before}, (后): {total_cols_after}")
    print(f"列压缩比: {total_cols_after / total_cols_before * 100:.1f}%")
    
    # 按复杂度统计
    complexity_stats = {}
    for result in results:
        complexity = result['复杂度']
        if complexity not in complexity_stats:
            complexity_stats[complexity] = {'count': 0, 'avg_tables': 0, 'avg_cols': 0}
        
        complexity_stats[complexity]['count'] += 1
        complexity_stats[complexity]['avg_tables'] += len(result['linked_schema'])
        complexity_stats[complexity]['avg_cols'] += sum(
            len(t['columns']) for t in result['linked_schema'].values()
        )
    
    print("\n按复杂度统计:")
    for complexity, stats in complexity_stats.items():
        count = stats['count']
        avg_tables = stats['avg_tables'] / count
        avg_cols = stats['avg_cols'] / count
        print(f"  {complexity}: {count}个, 平均 {avg_tables:.1f} 张表, {avg_cols:.1f} 列")


def main():
    parser = argparse.ArgumentParser(description='优化的 Schema Linking')
    parser.add_argument('--dataset', type=str, 
                       default='e:/Project/track3_2/final_for_student/data/final_dataset_example.json',
                       help='数据集路径')
    parser.add_argument('--schema', type=str,
                       default='e:/Project/track3_2/M-schema/final_algorithm_competition.txt',
                       help='Schema 文件路径')
    parser.add_argument('--output', type=str,
                       default='e:/Project/track3_2/output/schema_linking',
                       help='输出目录')
    parser.add_argument('--max_examples', type=int, default=3,
                       help='每列最多保留的示例数')
    
    args = parser.parse_args()
    
    process_dataset(
        dataset_path=args.dataset,
        schema_file=args.schema,
        output_dir=args.output,
        max_examples=args.max_examples
    )


if __name__ == '__main__':
    main()
