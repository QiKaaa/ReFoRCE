"""
Schema解析器 - 解析final_algorithm_competition.txt并按表划分
"""
import re
from typing import Dict, List


class SchemaParser:
    """解析数据库Schema文件"""
    
    def __init__(self, schema_file_path: str):
        """
        初始化Schema解析器
        
        Args:
            schema_file_path: Schema文件路径（如M-schema/final_algorithm_competition.txt）
        """
        self.schema_file_path = schema_file_path
        self.db_id = None
        self.tables = {}  # {table_name: table_schema_chunk}
        self._parse_schema()
    
    def _parse_schema(self):
        """解析Schema文件"""
        with open(self.schema_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取DB_ID
        db_id_match = re.search(r'【DB_ID】\s*(\S+)', content)
        if db_id_match:
            self.db_id = db_id_match.group(1)
        
        # 按表分割
        # 匹配模式: # Table: table_name, description\n[...]
        table_pattern = r'# Table:\s*([^,\n]+)(?:,\s*([^\n]*))?\n\[(.*?)\n\]'
        
        matches = re.finditer(table_pattern, content, re.DOTALL)
        
        for match in matches:
            table_name = match.group(1).strip()
            description = match.group(2).strip() if match.group(2) else ""
            columns_block = match.group(3).strip()
            
            # 解析列信息
            columns = self._parse_columns(columns_block)
            
            # 构建表的schema chunk
            table_chunk = self._build_table_chunk(table_name, description, columns)
            
            self.tables[table_name] = {
                'description': description,
                'columns': columns,
                'chunk': table_chunk
            }
    
    def _parse_columns(self, columns_block: str) -> List[Dict]:
        """解析列信息"""
        columns = []
        # 匹配模式: (column_name:TYPE, description, Examples: [...])
        col_pattern = r'\(([^:]+):([^,]+),\s*([^,]*?)(?:,\s*Examples:\s*\[([^\]]*)\])?\)'
        
        matches = re.finditer(col_pattern, columns_block)
        
        for match in matches:
            column_name = match.group(1).strip()
            data_type = match.group(2).strip()
            description = match.group(3).strip()
            examples = match.group(4).strip() if match.group(4) else ""
            
            columns.append({
                'name': column_name,
                'type': data_type,
                'description': description,
                'examples': examples
            })
        
        return columns
    
    def _build_table_chunk(self, table_name: str, description: str, columns: List[Dict]) -> str:
        """构建表的Schema文本块"""
        chunk = f"Table: {table_name}\n"
        if description:
            chunk += f"Description: {description}\n"
        chunk += "Columns:\n"
        
        for col in columns:
            chunk += f"  - {col['name']} ({col['type']})"
            if col['description']:
                chunk += f": {col['description']}"
            if col['examples']:
                chunk += f" [Examples: {col['examples']}]"
            chunk += "\n"
        
        chunk += "-" * 80 + "\n"
        return chunk
    
    def get_table_chunk(self, table_name: str) -> str:
        """获取指定表的Schema块"""
        if table_name in self.tables:
            return self.tables[table_name]['chunk']
        else:
            return f"# Table {table_name} not found in schema\n"
    
    def get_tables_chunks(self, table_list: List[str]) -> str:
        """
        根据table_list获取相关表的Schema
        
        Args:
            table_list: 表名列表
            
        Returns:
            str: 合并的Schema文本
        """
        chunks = []
        
        # 添加数据库信息
        if self.db_id:
            chunks.append(f"Database: {self.db_id}\n")
            chunks.append("=" * 80 + "\n\n")
        
        # 添加相关表的Schema
        for table_name in table_list:
            chunk = self.get_table_chunk(table_name)
            chunks.append(chunk)
        
        return "\n".join(chunks)
    
    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        return list(self.tables.keys())
    
    def get_full_schema(self) -> str:
        """获取完整Schema"""
        return self.get_tables_chunks(self.get_all_tables())


if __name__ == "__main__":
    # 测试代码
    schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
    parser = SchemaParser(schema_path)
    
    print(f"数据库ID: {parser.db_id}")
    print(f"表数量: {len(parser.tables)}")
    print(f"表名列表: {parser.get_all_tables()[:5]}...")  # 显示前5个
    
    # 测试获取特定表的Schema
    test_tables = ["dim_argothek_gplayerid2qqwxid_df", "dim_argothek_seasondate_df"]
    schema_text = parser.get_tables_chunks(test_tables)
    print("\n" + "="*80)
    print("示例Schema提取:")
    print(schema_text)
