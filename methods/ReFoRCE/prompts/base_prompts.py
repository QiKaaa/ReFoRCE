"""
基础 Prompt 管理器
将原有 Prompt 重构为 System/User 格式
"""

from typing import Optional, Dict, Any


class BasePromptManager:
    """基础 Prompt 管理器 - System/User 分离格式"""
    
    def __init__(self, domain_knowledge: str = None):
        """
        初始化基础Prompt管理器
        
        Args:
            domain_knowledge: 业务领域通用知识（可选）
        """
        self.domain_knowledge = domain_knowledge
    
    # ==================== 工具方法 ====================
    
    def get_condition_onmit_tables(self):
        """获取需要避免的表省略注释"""
        return [
            "-- Include all", "-- Omit", "-- Continue", "-- Union all", 
            "-- ...", "-- List all", "-- Replace this", "-- Each table", "-- Add other"
        ]
    
    # ==================== System Prompts ====================
    
    def get_exploration_system_prompt(self, api: str) -> str:
        """
        列探索的 System Prompt
        定义角色和基本规则
        """
        system_prompt = f"""You are an expert SQL data analyst specialized in {api} database.

Your role: Generate exploratory SQL queries to understand the data distribution and column values before answering complex questions.

Core Rules:
1. Generate at most 10 simple SELECT queries
2. Each query must be different and focus on understanding data values
3. Use DISTINCT and LIMIT to avoid large result sets
4. DO NOT query about SCHEMA or data types
5. DO NOT output the final answer
6. Only write SELECT queries for data exploration

Output Format:
Each query must be in a code block with description:
```sql
-- Description: [What you're exploring]
SELECT DISTINCT column_name FROM table_name LIMIT 10;
```

{self._get_dialect_nested_rules(api)}

Remember: Focus on exploring actual data values, not schema structure."""
        
        # ✨ 添加业务领域知识
        if self.domain_knowledge:
            system_prompt += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**CRITICAL: BUSINESS DOMAIN KNOWLEDGE**
You MUST strictly follow these business rules when exploring data:

{self.domain_knowledge}

When exploring, verify:
1. Data follows these business constraints
2. No violations of domain rules
3. Use these rules to guide exploration focus
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return system_prompt
    
    def get_self_refine_system_prompt(self, api: str, table_struct: str) -> str:
        """
        SQL生成/精化的 System Prompt
        定义SQL生成的核心规则
        """
        system_prompt = f"""You are an expert {api} SQL developer with deep knowledge of database optimization and query design.

Your role: Generate accurate, efficient SQL queries based on natural language questions and database schema.

Core Capabilities:
1. Understand complex database schemas and relationships
2. Write optimized {api} SQL queries
3. Handle date/time operations correctly
4. Apply proper aggregations and window functions
5. Use appropriate JOINs and subqueries

SQL Dialect Rules:
{self._get_dialect_basic_rules(api)}

{self._get_dialect_list_tables_rules(table_struct, api)}

{self._get_dialect_nested_rules(api)}

{self._get_dialect_string_matching_rules(api)}

Output Requirements:
1. Generate ONLY ONE complete SQL query
2. Output in code block format:
```sql
-- Your SQL query here
```

Quality Standards:
- Accuracy: Query must return exactly what's asked
- Efficiency: Use optimal query patterns
- Clarity: Include comments for complex logic
- Completeness: Handle NULL values and edge cases

{self._get_decimal_places_rule()}

Remember: Your knowledge is based on the database schema provided, not external knowledge."""
        
        # ✨ 添加业务领域知识
        if self.domain_knowledge:
            system_prompt += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**CRITICAL: BUSINESS DOMAIN KNOWLEDGE**
You MUST strictly follow these business rules when generating SQL:

{self.domain_knowledge}

SQL Generation Requirements:
1. Apply ALL domain constraints in WHERE clauses
2. Use specified column values for filtering
3. Follow business logic patterns exactly
4. Verify results align with domain expectations
5. If business rule conflicts with question, prioritize business rule
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return system_prompt
    
    def get_self_consistency_system_prompt(self) -> str:
        """
        自我一致性检查的 System Prompt
        """
        system_prompt = """You are an expert SQL query validator and reviewer.

Your role: Review SQL queries for correctness, completeness, and alignment with the task requirements.

Review Checklist:
1. Does the query answer the exact question asked?
2. Are all required columns included in SELECT?
3. Are WHERE conditions correctly applied?
4. Are JOINs properly structured?
5. Are aggregations and GROUP BY correct?
6. Are date/time operations handled properly?
7. Are NULL values handled appropriately?
8. Does the output match the required format?

Decision Process:
- If the query is correct: Output the same SQL without changes
- If issues found: Provide the corrected SQL with brief explanation

Output Format:
```sql
-- Your final SQL query (corrected or unchanged)
```

Remember: Focus on correctness and task alignment, not over-optimization."""
        
        return system_prompt
    
    def get_format_analysis_system_prompt(self) -> str:
        """
        格式分析的 System Prompt
        """
        system_prompt = """You are an expert at analyzing SQL task requirements and defining output formats.

Your role: Analyze natural language questions and determine the expected output format (columns, data types, structure).

Analysis Process:
1. Identify what information is requested
2. Determine required columns (both explicit and implicit)
3. Infer appropriate data types
4. Define output structure

Output Format:
Provide the answer format in CSV-like structure:
```csv
column1_name,column2_name
column1_type:data_type,column2_type:data_type
...
```

Rules:
- When asked "which products", include both product_name and product_id
- When asked "top N", ensure proper ordering is implied
- Specify data types (str, int, float, date, etc.)
- Keep format simple and clear

Example:
Question: "Which users have the highest scores?"
Format:
```csv
user_name,user_id,score
user_name:str,user_id:int,score:float
```

Remember: Focus on what the question implicitly requires, not just what's explicitly stated."""
        
        return system_prompt
    
    # ==================== User Prompts ====================
    
    def get_exploration_user_prompt(self, table_info: str, question: str, table_struct: str) -> str:
        """
        列探索的 User Prompt
        提供具体任务和数据
        """
        user_prompt = f"""Database Schema:
{table_info}

Available Tables: {table_struct}

Task Question:
{question}

Please generate exploratory SQL queries to understand the data in columns relevant to this question."""
        
        return user_prompt
    
    def get_self_refine_user_prompt(
        self, 
        table_info: str, 
        question: str,
        pre_info: Optional[str] = None,
        format_csv: Optional[str] = None,
        table_struct: str = ""
    ) -> str:
        """
        SQL生成的 User Prompt
        """
        user_prompt = f"""Database Schema:
{table_info}
"""
        
        if pre_info:
            user_prompt += f"""
Column Exploration Results (Few-shot Examples):
{pre_info}

{'-' * 80}
"""
        
        user_prompt += f"""
Task Question:
{question}

Available Tables: {table_struct}
"""
        
        if format_csv:
            user_prompt += f"""
Expected Output Format:
{format_csv}
"""
        
        user_prompt += """
Please generate ONE complete SQL query to answer this question."""
        
        return user_prompt
    
    def get_self_consistency_user_prompt(
        self, 
        task: str, 
        current_sql: str, 
        current_result: str,
        format_csv: Optional[str] = None
    ) -> str:
        """
        自我一致性检查的 User Prompt
        """
        user_prompt = f"""Original Task:
{task}

Current SQL Query:
{current_sql}

Current Query Result:
{current_result}
"""
        
        if format_csv:
            user_prompt += f"""
Required Output Format:
{format_csv}
"""
        
        user_prompt += """
Please review:
1. Does this query correctly answer the task?
2. Does the result match the required format?
3. Are there any logical errors?

If correct, output the same SQL. If not, provide the corrected SQL."""
        
        return user_prompt
    
    def get_format_analysis_user_prompt(self, question: str) -> str:
        """
        格式分析的 User Prompt
        """
        user_prompt = f"""Question:
{question}

Please analyze this question and provide the expected output format in CSV structure."""
        
        return user_prompt
    
    def get_error_correction_user_prompt(self, sql: str, error: str) -> str:
        """
        错误修正的 User Prompt
        """
        user_prompt = f"""The following SQL query has an error:

```sql
{sql}
```

Error Message:
{error}

Please analyze the error and provide the corrected SQL query. Include your thinking process briefly."""
        
        return user_prompt
    
    def get_exploration_refine_prompt(self, sql: str, corrected_sql: str, sqls: list, res: str) -> str:
        """
        探索阶段批量修正其他SQL的 User Prompt
        当一个SQL被修正后，用于指导修正其他类似的SQL
        
        Args:
            sql: 原始错误的SQL
            corrected_sql: 修正后的SQL
            sqls: 需要检查和修正的其他SQL列表
            res: 修正后SQL的执行结果
        """
        user_prompt = f"""```sql
{sql}
``` 
was corrected to:
```sql
{corrected_sql}
```

And the result is:
{res}

Please correct other sqls based on results if they have similar errors. Otherwise don't modify the SQL. 

SQLs to check: {sqls}

For each SQL, answer in ```sql
--Description: 
``` format."""
        
        return user_prompt
    
    # ==================== 内部辅助方法 ====================
    
    def _get_dialect_basic_rules(self, api: str) -> str:
        """获取基本SQL方言规则"""
        if api == "snowflake":
            return """Snowflake SQL Syntax:
- Use double quotes for column names: SELECT "COLUMN_NAME"
- Format: SELECT "COLUMN" FROM DATABASE.SCHEMA.TABLE
- All identifiers are case-sensitive when quoted"""
        
        elif api == "bigquery":
            return """BigQuery SQL Syntax:
- Use backticks for identifiers: SELECT `column_name`
- Format: SELECT `column` FROM `project.dataset.table`
- Supports standard SQL with extensions"""
        
        elif api == "sqlite":
            return """SQLite SQL Syntax:
- Use double quotes for special identifiers: SELECT "column_name"
- Format: SELECT DISTINCT "column" FROM "table"
- Case-insensitive by default"""
        
        elif api == "starrocks":
            return """StarRocks SQL Syntax:
- MySQL-compatible syntax
- Use backticks for identifiers (optional): SELECT `column`
- Format: SELECT column FROM database.table
- Supports standard SQL"""
        
        else:
            return f"{api} SQL syntax (standard SQL conventions apply)"
    
    def _get_dialect_list_tables_rules(self, table_struct: str, api: str) -> str:
        """获取表联合操作规则"""
        if api == "snowflake":
            return f"""UNION Operations (Snowflake):
- List ALL tables explicitly, never use comments like {self.get_condition_onmit_tables()} to omit tables
- Union first, then filter: SELECT "col1", "col2" FROM (TABLE1 UNION ALL TABLE2) WHERE ...
- DON'T write: (SELECT FROM TABLE1 WHERE ...) UNION ALL (SELECT FROM TABLE2 WHERE ...)
- Available tables: {table_struct}"""
        
        elif api == "bigquery":
            return """UNION Operations (BigQuery):
- For tables with similar prefix, use wildcard: FROM `project.dataset.prefix*`
- Filter by suffix: WHERE _TABLE_SUFFIX IN ('suffix1', 'suffix2')
- Avoid manual listing when wildcard applies"""
        
        elif api == "starrocks":
            return f"""UNION Operations (StarRocks):
- Use UNION ALL for better performance (if duplicates acceptable)
- List all tables explicitly
- Example: SELECT col1, col2 FROM table1 UNION ALL SELECT col1, col2 FROM table2
- Available tables: {table_struct}"""
        
        else:
            return ""
    
    def _get_dialect_nested_rules(self, api: str) -> str:
        """获取嵌套数据处理规则"""
        if api == "snowflake":
            return """Nested Data (Snowflake):
- JSON extraction: SELECT f.value::VARIANT:"key"::STRING FROM table, LATERAL FLATTEN(input => t."json_col") f
- First inspect structure if unknown: SELECT f.value FROM table, LATERAL FLATTEN(input => t."column") f"""
        
        elif api == "bigquery":
            return """Nested Data (BigQuery):
- JSON extraction: JSON_EXTRACT_SCALAR(f.value, "$.key")
- UNNEST arrays: FROM table, UNNEST(JSON_EXTRACT_ARRAY(t."column")) AS f
- Inspect unknown structures first"""
        
        elif api == "sqlite":
            return """Nested Data (SQLite):
- JSON extraction: json_extract(f.value, '$.key')
- Iterate JSON: FROM table, json_each(t."column") AS f"""
        
        elif api == "starrocks":
            return """Nested Data (StarRocks):
- JSON: get_json_string(column, '$.key'), get_json_int(column, '$.key')
- Arrays: array_length(), array_contains()
- Example: SELECT get_json_string(json_col, '$.name') FROM table"""
        
        else:
            return ""
    
    def _get_dialect_string_matching_rules(self, api: str) -> str:
        """获取字符串匹配规则"""
        if api == "snowflake":
            return """String Matching (Snowflake):
- Fuzzy search: WHERE str ILIKE "%target%"
- Replace spaces with %: WHERE str ILIKE "%meat%lovers%"
- Case-insensitive by default with ILIKE"""
        
        elif api == "bigquery":
            return """String Matching (BigQuery):
- Fuzzy search: WHERE LOWER(str) LIKE LOWER('%target%')
- Case-insensitive comparison recommended"""
        
        elif api == "sqlite":
            return """String Matching (SQLite):
- Fuzzy search: WHERE str LIKE '%target%'
- Case-sensitive: WHERE str LIKE '%target%' COLLATE BINARY"""
        
        elif api == "starrocks":
            return """String Matching (StarRocks):
- Fuzzy search: WHERE column LIKE '%pattern%'
- Exact match: WHERE column = 'value'
- Regular expressions: WHERE column REGEXP 'pattern'
- Chinese characters supported: WHERE name LIKE '%张%'"""
        
        else:
            return ""
    
    def _get_decimal_places_rule(self) -> str:
        """获取小数位数规则"""
        return """Decimal Precision:
- If task doesn't specify decimal places, retain 4 decimal places
- Use ROUND(value, 4) or CAST for precision control"""
    
    # ==================== 兼容旧接口的方法 ====================
    
    def get_exploration_prompt(self, api: str, table_struct: str) -> str:
        """兼容旧接口 - 返回 system prompt"""
        return self.get_exploration_system_prompt(api)
    
    def get_self_refine_prompt(
        self, 
        table_info: str, 
        task: str,
        pre_info: Optional[str], 
        question: str, 
        api: str, 
        format_csv: Optional[str], 
        table_struct: str, 
        omnisql_format_pth: Optional[str] = None
    ) -> str:
        """兼容旧接口 - 返回组合后的 prompt"""
        # 如果使用 omnisql 格式,保持原有逻辑
        if omnisql_format_pth:
            if task == "lite":
                from ..prompt import omni_sql_input_prompt_template
                return omni_sql_input_prompt_template.format(
                    db_engine="SQLite",
                    db_details=table_info,
                    question=question
                )
            elif task in ["BIRD", "spider"]:
                ce = "Some few-shot examples after column exploration may be helpful:\n" + pre_info if pre_info else ""
                return table_info + "\n" + ce
        
        # 组合 system + user prompt
        system = self.get_self_refine_system_prompt(api, table_struct)
        user = self.get_self_refine_user_prompt(table_info, question, pre_info, format_csv, table_struct)
        
        return f"{system}\n\n{user}"
    
    def get_self_consistency_prompt(self, task: str, format_csv: Optional[str]) -> str:
        """兼容旧接口"""
        system = self.get_self_consistency_system_prompt()
        return system
    
    def get_format_prompt(self) -> str:
        """兼容旧接口"""
        return self.get_format_analysis_system_prompt()
    
    def get_exploration_refine_prompt(self, sql: str, corrected_sql: str, sqls: list, res: str) -> str:
        """
        探索阶段SQL修正后的批量优化prompt
        用于根据一个SQL的修正结果，优化其他待执行的SQL
        """
        return f"""```sql
{sql}``` is corrected to ```sql
{corrected_sql}```. And the result is: 
{res}

Please correct other sqls based on results if they have similar errors. Otherwise don't modify the SQL. 
SQLs: {sqls}. 
For each SQL, answer in ```sql
--Description: 
``` format.
"""
    
    def get_exploration_self_correct_prompt(self, sql: str, error: str) -> str:
        """兼容旧接口"""
        return self.get_error_correction_user_prompt(sql, error)
    
    def get_prompt_decimal_places(self) -> str:
        """兼容旧接口"""
        return self._get_decimal_places_rule()
    
    def get_prompt_dialect_basic(self, api: str) -> str:
        """兼容旧接口"""
        return self._get_dialect_basic_rules(api)
    
    def get_prompt_dialect_nested(self, api: str) -> str:
        """兼容旧接口"""
        return self._get_dialect_nested_rules(api)
    
    def get_prompt_dialect_string_matching(self, api: str) -> str:
        """兼容旧接口"""
        return self._get_dialect_string_matching_rules(api)
    
    def get_prompt_dialect_list_all_tables(self, table_struct: str, api: str) -> str:
        """兼容旧接口"""
        return self._get_dialect_list_tables_rules(table_struct, api)
    
    def get_self_refine_prompt_on_error(self, error_message: str, current_sql: str, question: str) -> str:
        """
        生成错误修正的 User Prompt
        用于在 SQL 执行出现错误时引导 LLM 修正
        
        Args:
            error_message: 错误信息
            current_sql: 当前的 SQL 查询
            question: 原始问题
            
        Returns:
            str: User prompt 用于错误修正
        """
        return f"""An error occurred during SQL execution:

**Error:** {error_message}

**Current SQL:**
```sql
{current_sql}
```

**Original Question:** {question}

Please analyze the error and generate a corrected SQL query. Consider:
1. What caused this error?
2. How can the SQL be fixed while maintaining the original intent?
3. Are there any logical issues in the current query?

Output the corrected SQL in the following format:
```sql
-- Your corrected SQL here
```"""
