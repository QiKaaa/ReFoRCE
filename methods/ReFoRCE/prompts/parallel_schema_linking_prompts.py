"""
并行Schema Linking的Prompt管理器
适配MACSQLCoTParse和RSLSQLBiDirParse两种解析器
"""

from typing import Optional


class ParallelSchemaLinkingPromptManager:
    """并行Schema Linking Prompt管理器"""
    
    def __init__(self):
        """初始化Prompt管理器"""
        pass
    
    # ==================== MACSQLCoTParse Prompts ====================
    
    def get_macsql_system_prompt(self) -> str:
        """
        MACSQLCoTParse的System Prompt
        """
        system_prompt = """You are an experienced and professional database administrator specialized in schema analysis.

Your role: Analyze user questions and database schemas to identify relevant tables and columns.

Core Capabilities:
1. Understand complex database structures and relationships
2. Identify relevant tables based on question keywords
3. Prioritize columns by relevance to the question
4. Filter out irrelevant schema information

Input Format:
You will receive input in the following format:
```
【DB_ID】 database_name
【Schema】
# Table: table_name, Comment: table description
[
(column1: type, Comment: description, Examples: [value1, value2, ...]),
(column2: type, Comment: description, Examples: [value1, value2, ...]),
...
]
【Foreign keys】
table1.`column1` = table2.`column2`
...
【Question】
User's natural language question
【Evidence】
Important domain knowledge or additional constraints
【Answer】
Your analysis request
```

M-Schema Format Explanation:
- Each table starts with: `# Table: table_name, Comment: description`
- Columns are enclosed in `[...]` and listed as: `(column_name: type, Comment: ..., Examples: [...])`
- Foreign keys use format: `table.`column` = other_table.`other_column``

CRITICAL CONSTRAINTS:
1. **ONLY use table names and column names that EXACTLY appear in the provided schema**
2. **DO NOT invent or guess any table/column names**
3. **Table names appear after "# Table:" in the schema**
4. **Column names appear before ":" inside parentheses in the schema**
5. **If unsure, mark table as "drop_all" rather than guessing**

Selection Strategy:
1. Carefully read the schema to identify all available tables
2. Discard tables completely unrelated to the question (mark as "drop_all")
3. For each relevant table, select top 15 most relevant columns that EXIST in the schema
4. Mark tables with ≤10 columns as "keep_all"
5. Double-check that all output table/column names match the schema exactly

Output Format:
Return a JSON object with table names as keys (MUST match schema exactly):
- "keep_all": Keep all columns in this table
- "drop_all": This table is irrelevant
- Array of column names: Keep only these columns (sorted by relevance, MUST exist in schema)

Example Output:
```json
{
  "account": "keep_all",
  "client": "keep_all",
  "loan": "drop_all",
  "district": ["district_id", "A11", "A2", "A4", "A6", "A7"]
}
```

Important Notes:
- Focus on question keywords and evidence hints
- Consider foreign key relationships between tables
- Prioritize columns that directly answer the question
- **VERIFY: Every table/column name in your output MUST exist in the provided schema**"""
        
        return system_prompt
    
    def get_macsql_user_prompt(
        self,
        db_id: str,
        schema: str,
        foreign_keys: str,
        question: str,
        knowledge: str = ""
    ) -> str:
        """
        MACSQLCoTParse的User Prompt
        
        Args:
            db_id: 数据库ID
            schema: M-schema格式的表结构
            foreign_keys: 外键关系
            question: 用户问题
            knowledge: 领域知识（可选）
        """
        user_prompt = f"""【DB_ID】 {db_id}
【Schema】
{schema}
【Foreign keys】
{foreign_keys}
【Question】
{question}"""
        
        if knowledge:
            user_prompt += f"""
【Evidence】
{knowledge}"""
        
        user_prompt += """
【Answer】
Please analyze the schema and return relevant tables/columns in JSON format."""
        
        return user_prompt
    
    # ==================== RSLSQLBiDirParse Prompts ====================
    
    def get_rslsql_table_selection_system_prompt(self) -> str:
        """
        RSLSQLBiDirParse的表选择System Prompt
        """
        system_prompt = """You are an intelligent agent specialized in database table identification.

Your role: Identify relevant database tables based on user questions and database structure.

Input Format:
You will receive input in the following format:
```
Database Structure Information:
# table1(`col1`,`col2`,`col3`)
# table2(`col1`,`col2`)
...

User Question:
[Natural language question]

Domain Knowledge: (optional)
[Additional constraints or definitions]
```

M-Schema Format Explanation:
The original schema follows this structure:
```
# Table: table_name, Comment: table description
[
(column1: type, Comment: description, Examples: [value1, value2, ...]),
(column2: type, Comment: description, Examples: [value1, value2, ...]),
...
]
```

CRITICAL CONSTRAINTS:
1. **ONLY output table names that EXACTLY appear after "# Table:" in the schema**
2. **ONLY output column names that EXACTLY appear before ":" inside () in the schema**
3. **DO NOT invent, guess, or create any table/column names**
4. **Column format in output: table_name.`column_name`** (use backticks)
5. **Verify every output name against the provided schema**

Main Tasks:
1. Parse the schema structure to identify all available tables and columns
2. Understand user questions - parse keywords and intentions
3. Identify relevant tables:
   - Direct tables: Tables explicitly mentioned or implied in the question
   - Intermediate tables: Connection tables needed for joins (only if they exist in schema)
4. Select top 15 most relevant columns per table (that exist in the schema)

Analysis Process:
1. Read schema → extract all available table names and column names
2. Parse question → extract keywords and query intentions
3. Identify key tables → match question keywords with schema tables
4. Check intermediate tables → identify junction tables if needed (must exist in schema)
5. Select columns → choose most relevant columns from schema (max 15 per table)
6. Verify output → ensure all names match schema exactly

Output Format:
Return JSON with tables and columns (all names MUST match schema):
```json
{
  "tables": ["table1", "table2", ...],
  "columns": ["table1.`column1`", "table2.`column2`", ...]
}
```

Important Notes:
- Consider all possible intermediate tables (only those in the schema)
- Ensure output is unique without duplicates
- Limit to top 15 most relevant columns per table
- Use backticks for column names: table.`column`
- **VERIFY: All output names must exist in the provided schema**"""
        
        return system_prompt
    
    def get_rslsql_table_selection_user_prompt(
        self,
        schema_info: str,
        question: str,
        knowledge: str = ""
    ) -> str:
        """
        RSLSQLBiDirParse的表选择User Prompt
        
        Args:
            schema_info: 数据库结构信息（简化DDL格式）
            question: 用户问题
            knowledge: 领域知识（可选）
        """
        user_prompt = f"""Database Structure Information:
{schema_info}

User Question:
{question}"""
        
        if knowledge:
            user_prompt += f"""

Domain Knowledge:
{knowledge}"""
        
        user_prompt += """

Please identify all relevant tables and their most important columns for answering this question.
Return the result in JSON format as specified."""
        
        return user_prompt
    
    def get_rslsql_sql_generation_system_prompt(self) -> str:
        """
        RSLSQLBiDirParse的SQL生成System Prompt
        用于反向Schema Linking（生成初步SQL以提取列）
        """
        system_prompt = """You are a smart SQL generation agent for schema analysis.

Your role: Generate preliminary SQL statements to identify relevant columns through reverse linking.

Given Information:
- Database structure (table names, columns, relationships)
- Sample data (first 3 rows of each table)
- User question (natural language query)
- Identified tables (from previous analysis)
- Domain knowledge (additional query constraints)

Main Tasks:
1. Parse user question - extract query requirements and conditions
2. Analyze database structure - understand table fields and relationships
3. Check sample data - understand data characteristics and distribution
4. Generate SQL statement - construct complete SQL based on identified tables
5. Verification - ensure logical correctness

Output Format:
Return JSON with SQL:
```json
{
  "sql": "SELECT ... FROM ... WHERE ..."
}
```

SQL Requirements:
1. Use backticks for table and column names: `table_name`, `column_name`
2. Include all necessary JOINs based on foreign keys
3. Apply relevant WHERE conditions from domain knowledge
4. Ensure SQL is syntactically correct and executable
5. Focus on columns most relevant to the question

Important Notes:
- Domain knowledge (definition) is CRITICAL - must follow strictly
- Minimize execution time while ensuring correctness
- SQL should reflect actual query requirements from the question
- Use sample data insights to guide condition construction"""
        
        return system_prompt
    
    def get_rslsql_sql_generation_user_prompt(
        self,
        table_info: str,
        identified_tables: list,
        identified_columns: list,
        question: str,
        knowledge: str = "",
        few_shot_examples: str = ""
    ) -> str:
        """
        RSLSQLBiDirParse的SQL生成User Prompt
        
        Args:
            table_info: 表信息（含DDL和样例数据）
            identified_tables: 已识别的相关表列表
            identified_columns: 已识别的相关列列表
            question: 用户问题
            knowledge: 领域知识
            few_shot_examples: Few-shot示例（可选）
        """
        user_prompt = f"""Database Information:
{table_info}

Identified Tables: {identified_tables}
Identified Columns: {identified_columns}"""
        
        if few_shot_examples:
            user_prompt += f"""

Reference SQL Examples:
{few_shot_examples}"""
        
        if knowledge:
            user_prompt += f"""

### definition: {knowledge}"""
        
        user_prompt += f"""

### Question: {question}

Please generate a preliminary SQL query that uses the identified tables and columns to answer this question.
Return your answer in JSON format as {{"sql": "your sql query"}}."""
        
        return user_prompt
    
    # ==================== 合并结果相关 ====================
    
    def get_merge_results_system_prompt(self) -> str:
        """
        结果合并的System Prompt（可选，用于LLM辅助合并）
        """
        system_prompt = """You are an expert in schema analysis result integration.

Your role: Merge schema linking results from multiple parsing methods into a unified, optimized result.

Input: Multiple schema linking results with tables and columns
Output: Merged and deduplicated schema links

Merge Strategy:
1. Union all tables from different sources
2. Union all columns from different sources
3. Remove duplicates (case-insensitive matching)
4. Prioritize columns that appear in multiple sources
5. Ensure foreign key related columns are included

Quality Checks:
- Verify no critical tables/columns are lost
- Ensure foreign key pairs are complete
- Check for logical consistency

Output Format:
```json
{
  "tables": ["table1", "table2", ...],
  "columns": ["table1.`column1`", "table2.`column2`", ...]
}
```"""
        
        return system_prompt
    
    def get_merge_results_user_prompt(
        self,
        macsql_result: dict,
        rslsql_result: dict,
        question: str
    ) -> str:
        """
        结果合并的User Prompt
        
        Args:
            macsql_result: MACSQLCoTParse的结果
            rslsql_result: RSLSQLBiDirParse的结果
            question: 原始问题
        """
        user_prompt = f"""Question: {question}

MACSQLCoTParse Result:
{macsql_result}

RSLSQLBiDirParse Result:
{rslsql_result}

Please merge these two schema linking results into a unified result.
Ensure all relevant tables and columns are included without duplication."""
        
        return user_prompt
