"""
StarRocks方言的Prompt模板 - 继承并扩展原有的Prompts类
"""
from prompt import Prompts


class PromptsStarRocks(Prompts):
    """StarRocks方言的Prompt模板"""
    
    def __init__(self):
        super().__init__()
    
    def get_prompt_dialect_basic(self, api="starrocks"):
        """StarRocks基本SQL格式提示"""
        if api == "starrocks":
            return """```sql
SELECT column_name FROM database.table_name WHERE ... 
``` 
(StarRocks使用MySQL兼容语法，列名和表名可用反引号包裹)"""
        else:
            return super().get_prompt_dialect_basic(api)
    
    def get_prompt_dialect_string_matching(self, api="starrocks"):
        """StarRocks字符串匹配提示"""
        if api == "starrocks":
            return """For string matching in StarRocks, use LIKE with wildcards:
- Use WHERE column LIKE '%pattern%' for case-insensitive fuzzy matching
- For exact matching, use WHERE column = 'exact_value'
- StarRocks supports regular expressions with REGEXP operator
- Example: WHERE name LIKE '%张%' for Chinese characters\n"""
        else:
            return super().get_prompt_dialect_string_matching(api)
    
    def get_prompt_dialect_nested(self, api="starrocks"):
        """StarRocks嵌套数据处理提示"""
        if api == "starrocks":
            return """For JSON data in StarRocks:
- Use get_json_string(column, '$.key') to extract JSON string values
- Use get_json_int(column, '$.key') to extract JSON integer values
- Use get_json_double(column, '$.key') to extract JSON double values
- Example: SELECT get_json_string(json_col, '$.name') FROM table;
For ARRAY types:
- Use array functions like array_length(), array_contains()
- Example: SELECT array_contains(tags, 'important') FROM table;\n"""
        else:
            return super().get_prompt_dialect_nested(api)
    
    def get_prompt_dialect_list_all_tables(self, table_struct, api="starrocks"):
        """StarRocks表联合提示"""
        if api == "starrocks":
            return f"""When performing UNION operations, list all tables explicitly:
- Use UNION ALL for better performance if duplicates are acceptable
- Example: SELECT col1, col2 FROM table1 UNION ALL SELECT col1, col2 FROM table2
- Avoid using comments like {self.get_condition_onmit_tables()} to omit tables
- Available tables: {table_struct}\n"""
        else:
            return super().get_prompt_dialect_list_all_tables(table_struct, api)
    
    def get_starrocks_date_functions(self):
        """StarRocks日期函数提示"""
        return """StarRocks Date Functions:
- DATE_FORMAT(date, format): Format date as string
- STR_TO_DATE(str, format): Convert string to date
- DATEDIFF(date1, date2): Calculate days between dates
- DATE_ADD(date, INTERVAL n DAY/MONTH/YEAR): Add interval to date
- DATE_SUB(date, INTERVAL n DAY/MONTH/YEAR): Subtract interval from date
- NOW(): Current datetime
- CURDATE(): Current date
- Common format: '%Y%m%d' for YYYYMMDD, '%Y-%m-%d' for YYYY-MM-DD\n"""
    
    def get_starrocks_aggregation_tips(self):
        """StarRocks聚合函数提示"""
        return """StarRocks Aggregation Tips:
- Use COUNT(DISTINCT column) for unique count
- Use GROUP_CONCAT(column SEPARATOR ',') to concatenate strings
- Use PERCENTILE_APPROX(column, percentile) for approximate percentiles
- BITMAP functions: bitmap_union(), bitmap_count(), bitmap_contains()
- HLL functions: hll_union_agg(), hll_cardinality() for large cardinality estimation\n"""
    
    def get_starrocks_window_functions(self):
        """StarRocks窗口函数提示"""
        return """StarRocks Window Functions:
- ROW_NUMBER() OVER (PARTITION BY col ORDER BY col)
- RANK() / DENSE_RANK() for ranking
- LEAD() / LAG() for accessing adjacent rows
- FIRST_VALUE() / LAST_VALUE() for first/last values in window
- Example: SELECT ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales DESC) as rank FROM table;\n"""
    
    def get_exploration_prompt(self, api, table_struct):
        """StarRocks探索性查询提示"""
        exploration_prompt = f"""Write at most 10 StarRocks SQL queries in format like:
```sql
-- Description: Check distinct values in column_name
SELECT DISTINCT column_name FROM table_name LIMIT 10;
```
to understand the data in related columns.\n"""
        
        exploration_prompt += "Each query should be different. Focus on SELECT queries only. Use DISTINCT and LIMIT.\n"
        exploration_prompt += "Don't query about SCHEMA or data types. Try to explore actual data values.\n"
        exploration_prompt += "Write annotations to describe each SQL in format: ```sql\\n-- Description: ...\\n```\n\n"
        
        # StarRocks特定提示
        exploration_prompt += self.get_prompt_dialect_nested(api)
        exploration_prompt += self.get_starrocks_date_functions()
        
        return exploration_prompt
    
    def get_self_refine_prompt(self, table_info, task, pre_info, question, api, 
                              format_csv, table_struct, omnisql_format_pth=None):
        """StarRocks自我精化提示"""
        
        refine_prompt = f"Database Schema:\n{table_info}\n\n"
        
        # 添加列探索结果
        if pre_info:
            refine_prompt += "Column Exploration Examples (helpful context):\n"
            refine_prompt += pre_info + "\n"
            refine_prompt += "-" * 80 + "\n\n"
        
        # 任务描述
        refine_prompt += f"Task: {question}\n\n"
        refine_prompt += f"Please think step by step and write ONE complete SQL query in StarRocks dialect.\n"
        refine_prompt += f"Output format: ```sql\\n-- Your SQL query\\n```\n\n"
        
        # 基本语法示例
        refine_prompt += f"SQL Usage Example:\n{self.get_prompt_dialect_basic(api)}\n\n"
        
        # 答案格式要求
        if format_csv:
            refine_prompt += f"Expected answer format: {format_csv}\n\n"
        
        # 提示技巧
        refine_prompt += "Important Tips:\n"
        refine_prompt += self.get_prompt_dialect_list_all_tables(table_struct, api)
        refine_prompt += self.get_starrocks_date_functions()
        refine_prompt += self.get_prompt_decimal_places()
        refine_prompt += "\n"
        
        # 常见错误避免
        refine_prompt += "Common Mistakes to Avoid:\n"
        refine_prompt += "- Always use proper date format conversion (DATE_FORMAT or STR_TO_DATE)\n"
        refine_prompt += "- When filtering by date strings like '20250702', ensure proper comparison\n"
        refine_prompt += "- Use COUNT(DISTINCT ...) for unique counting\n"
        refine_prompt += "- Remember to handle NULL values appropriately\n"
        
        return refine_prompt


if __name__ == "__main__":
    # 测试
    prompt = PromptsStarRocks()
    print("StarRocks基本语法:")
    print(prompt.get_prompt_dialect_basic("starrocks"))
    print("\n日期函数:")
    print(prompt.get_starrocks_date_functions())
