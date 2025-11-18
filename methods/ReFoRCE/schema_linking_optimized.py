"""
优化的 Schema Linking 方案 (基于 LLM)
专为 final_algorithm_competition 数据集设计

特点:
1. 使用标注的 table_list 确定相关表
2. 使用 LLM 分析每个表的列,选择相关列
3. 输出 M-schema 格式的精简 schema
"""

import os
import json
import csv
import re
import sys
from typing import Dict, List, Set, Tuple, Optional
from tqdm import tqdm
import argparse

# 导入 GPT Chat
from chat import GPTChat

# 设置 CSV 字段大小限制 (处理 Windows 平台的限制)
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)


# LLM Prompt for Schema Linking
SCHEMA_LINKING_PROMPT = """You are performing column-level schema linking for SQL generation.

Given:
1. Question: The user's question that needs to be answered
2. Knowledge: Domain-specific knowledge and constraints
3. All Table Schemas: Complete schemas of all relevant tables in M-schema format

Your task:
Analyze which columns from each table are relevant to answer the question, considering the knowledge constraints and table relationships.

Rules:
1. Select ALL columns that might be needed (including filter columns, join columns, and output columns)
2. Always keep ID fields and date/time fields
3. Consider both direct usage and indirect usage (e.g., for JOINs)
4. Consider relationships between tables when selecting columns
5. Return the selected columns in the EXACT same format as shown in the table schemas

Please respond ONLY with a JSON code block:
```json
{{
    "think": "Brief reasoning about which columns are relevant and why, including table relationships",
    "tables": {{
        "table_name1": [
            "(column_name1: type, comment, Examples: [examples])",
            "(column_name2: type, comment, Examples: [examples])",
            ...
        ],
        "table_name2": [
            "(column_name1: type, comment, Examples: [examples])",
            ...
        ]
    }}
}}
```

Important: Copy the column definition EXACTLY as it appears in the table schema, including the parentheses, colon, comma, and examples.

---

Question: {question}

Knowledge: {knowledge}

All Table Schemas:
{all_table_schemas}

Please analyze and return the selected columns for each table in the JSON format above.
"""


class OptimizedSchemaLinker:
    """优化的 Schema Linking 类 (基于 LLM)"""
    
    def __init__(self, schema_file: str, chat_session: Optional[GPTChat] = None):
        """
        初始化
        Args:
            schema_file: schema 文件路径 (如 final_algorithm_competition.txt)
            chat_session: GPT Chat 会话 (可选)
        """
        self.schema_file = schema_file
        self.all_tables = {}  # {table_name: table_schema_text}
        self.chat_session = chat_session
        self._load_schema()
    
    def _load_schema(self):
        """从 schema 文件加载所有表的完整 schema 文本"""
        with open(self.schema_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析每个表的完整定义 (保持 M-schema 格式)
        # 找到所有表的起始位置
        table_starts = []
        for match in re.finditer(r'# Table: ([^,]+)', content):
            table_name = match.group(1).strip()
            start_pos = match.start()
            table_starts.append((table_name, start_pos))
        
        # 提取每个表的完整文本
        for i, (table_name, start_pos) in enumerate(table_starts):
            # 找到下一个表的开始位置或文件结束
            if i + 1 < len(table_starts):
                end_pos = table_starts[i + 1][1]
            else:
                end_pos = len(content)
            
            # 提取表的完整文本
            table_text = content[start_pos:end_pos].strip()
            self.all_tables[table_name] = table_text
        
        print(f"✓ 已加载 {len(self.all_tables)} 张表的 schema 信息")
    
    def _parse_llm_response(self, response: str) -> Dict[str, List[str]]:
        """
        解析 LLM 返回的多表列列表
        
        Args:
            response: LLM 的响应
            
        Returns:
            字典: {table_name: [列定义列表]}
        """
        try:
            # 提取 JSON code block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                return data.get('tables', {})
            else:
                print(f"警告: 无法从 LLM 响应中提取 JSON")
                return {}
        except Exception as e:
            print(f"警告: 解析 LLM 响应失败: {e}")
            return {}
    
    def link_schema(self, 
                   question: str, 
                   table_list: List[str], 
                   knowledge: str = "",
                   chat_session: Optional[GPTChat] = None) -> str:
        """
        执行 Schema Linking (使用 LLM 一次性分析所有表)
        
        Args:
            question: 问题文本
            table_list: 标注的相关表列表
            knowledge: knowledge 字段
            chat_session: GPT Chat 会话 (可选,如果不提供则使用初始化时的)
            
        Returns:
            M-schema 格式的精简 schema 文本
        """
        # 使用提供的 chat_session 或默认的
        session = chat_session or self.chat_session
        
        if session is None:
            raise ValueError("未提供 chat_session,请在初始化或调用时提供")
        
        # 收集所有相关表的 schema
        all_table_schemas = []
        valid_tables = []
        
        for table_name in table_list:
            if table_name not in self.all_tables:
                print(f"警告: 表 {table_name} 不在 schema 中")
                continue
            
            valid_tables.append(table_name)
            all_table_schemas.append(self.all_tables[table_name])
        
        if not valid_tables:
            print("警告: 没有有效的表")
            return ""
        
        # 合并所有表的 schema
        combined_schemas = "\n\n".join(all_table_schemas)
        
        # 构建 prompt (一次性给所有表)
        prompt = SCHEMA_LINKING_PROMPT.format(
            question=question,
            knowledge=knowledge if knowledge else "None",
            all_table_schemas=combined_schemas
        )
        
        try:
            # 调用 LLM (一次性处理所有表)
            response = session.get_response(prompt)
            # print(f"🔮 LLM Schema Linking 响应:\n{response}")
            
            # 解析响应
            tables_columns = self._parse_llm_response(response)
            
            if not tables_columns:
                # 如果 LLM 没有返回结果,使用完整 schema
                print(f"警告: LLM 响应为空,使用完整 schema")
                return combined_schemas
            
            # 重建每个表的 M-schema 格式
            linked_tables = []
            
            for table_name in valid_tables:
                if table_name not in tables_columns:
                    # 如果 LLM 没有返回这个表的列,使用完整表
                    print(f"警告: {table_name} 未在 LLM 响应中,使用完整表")
                    linked_tables.append(self.all_tables[table_name])
                    continue
                
                selected_columns = tables_columns[table_name]
                
                if not selected_columns:
                    # 如果这个表的列列表为空,使用完整表
                    print(f"警告: {table_name} 的列列表为空,使用完整表")
                    linked_tables.append(self.all_tables[table_name])
                    continue
                
                # 提取表头
                table_schema = self.all_tables[table_name]
                table_header_match = re.search(r'# Table: [^,\n]+,[^\n]+', table_schema)
                if table_header_match:
                    table_header = table_header_match.group(0)
                else:
                    table_header = f"# Table: {table_name}, (描述未找到)"
                
                # 构建精简的表定义
                linked_table = f"{table_header}\n[\n"
                for col_def in selected_columns:
                    linked_table += f"{col_def},\n"
                
                # 移除最后一个逗号
                if linked_table.endswith(',\n'):
                    linked_table = linked_table[:-2] + '\n'
                
                linked_table += "]\n"
                linked_tables.append(linked_table)
            
            # 合并所有表
            return "\n".join(linked_tables)
                    
        except Exception as e:
            print(f"错误: Schema Linking 时出错: {e}")
            import traceback
            traceback.print_exc()
            # 出错时使用完整 schema
            return combined_schemas
    
    def format_schema_prompt(self, linked_schema_text: str) -> str:
        """
        格式化 schema 文本 (已经是 M-schema 格式,直接返回)
        
        Args:
            linked_schema_text: link_schema() 的返回结果
            
        Returns:
            格式化的 schema 字符串 (与输入相同)
        """
        return linked_schema_text


def process_dataset(dataset_path: str, 
                    schema_file: str, 
                    output_dir: str,
                    model: str = "deepseek-chat",
                    azure: bool = False):
    """
    处理整个数据集
    
    Args:
        dataset_path: 数据集 JSON 文件路径
        schema_file: schema 文件路径
        output_dir: 输出目录
        model: LLM 模型名称
        azure: 是否使用 Azure
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载数据集
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # 创建 linker
    linker = OptimizedSchemaLinker(schema_file)
    
    # 创建 chat session
    chat_session = GPTChat(azure=azure, model=model, temperature=0)
    
    # 处理每个样本
    results = []
    
    for example in tqdm(dataset, desc="Processing examples"):
        sql_id = example['sql_id']
        question = example['question']
        table_list = example['table_list']
        knowledge = example.get('knowledge', '')
        
        print(f"处理: {sql_id}")
        
        # 执行 schema linking
        linked_schema = linker.link_schema(
            question=question,
            table_list=table_list,
            knowledge=knowledge,
            chat_session=chat_session
        )
        
        # 保存结果
        result = {
            'sql_id': sql_id,
            'question': question,
            'knowledge': knowledge,
            'table_list': table_list,
            'linked_schema': linked_schema,
            '复杂度': example.get('复杂度', '')
        }
        
        results.append(result)
        
        # 保存单个样本的 schema
        with open(os.path.join(output_dir, f"{sql_id}_schema.txt"), 'w', encoding='utf-8') as f:
            f.write(linked_schema)
    
    # 保存所有结果
    with open(os.path.join(output_dir, 'schema_linking_results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成! 结果保存到: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='优化的 Schema Linking (基于 LLM)')
    parser.add_argument('--dataset', type=str, 
                       default='e:/Project/track3_2/final_for_student/data/final_dataset_example.json',
                       help='数据集路径')
    parser.add_argument('--schema', type=str,
                       default='e:/Project/track3_2/M-schema/final_algorithm_competition.txt',
                       help='Schema 文件路径')
    parser.add_argument('--output', type=str,
                       default='e:/Project/track3_2/output/schema_linking',
                       help='输出目录')
    parser.add_argument('--model', type=str, default='deepseek-chat',
                       help='LLM 模型名称')
    parser.add_argument('--azure', action='store_true',
                       help='使用 Azure OpenAI')
    
    args = parser.parse_args()
    
    process_dataset(
        dataset_path=args.dataset,
        schema_file=args.schema,
        output_dir=args.output,
        model=args.model,
        azure=args.azure
    )


if __name__ == '__main__':
    main()
