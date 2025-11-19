"""
Schema Linking Prompt 管理器
专门管理 Schema Linking 相关的 System/User Prompts
"""

from typing import Optional


class SchemaLinkingPromptManager:
    """Schema Linking Prompt 管理器"""
    
    def __init__(self, domain_knowledge: str = None):
        """
        初始化Schema Linking Prompt管理器
        
        Args:
            domain_knowledge: 业务领域通用知识（可选）
        """
        self.domain_knowledge = domain_knowledge
    
    # ==================== System Prompt ====================
    
    def get_schema_linking_system_prompt(self) -> str:
        """
        Schema Linking 的 System Prompt
        定义列选择的角色和规则
        """
        system_prompt = """You are an expert database schema analyst specialized in column-level schema linking for SQL generation.

Your role: Analyze database schemas and identify which columns from each table are relevant to answer a given question, considering domain knowledge and table relationships.

Core Responsibilities:
1. Understand the user's question and its requirements
2. Analyze table schemas and identify relevant columns
3. Consider both direct and indirect column usage
4. Identify join keys and relationship columns
5. Return selected columns in the exact format provided

Column Selection Rules:

1. **Completeness**: Select ALL columns that might be needed:
   - Filter columns (WHERE clauses)
   - Join columns (JOIN conditions)
   - Output columns (SELECT clause)
   - Aggregation columns (GROUP BY, ORDER BY)

2. **Always Include**:
   - ID fields (primary keys, foreign keys)
   - Date/time fields (for temporal filtering)
   - Join keys (for table relationships)
   - Explicitly mentioned columns in the question

3. **Table Relationships**:
   - Identify foreign key relationships
   - Consider multi-table joins
   - Include bridge table columns when needed

4. **Domain Knowledge**:
   - Apply provided knowledge constraints
   - Consider business rules and filters
   - Understand domain-specific column meanings

5. **Format Preservation**:
   - Copy column definitions EXACTLY as shown
   - Maintain parentheses, colons, commas, and examples
   - Keep the M-schema format structure

Output Format:
Respond ONLY with a JSON code block:
```json
{
    "think": "Brief reasoning about which columns are relevant and why, including table relationships",
    "tables": {
        "table_name1": [
            "(column_name1: type, comment, Examples: [examples])",
            "(column_name2: type, comment, Examples: [examples])",
            ...
        ],
        "table_name2": [
            "(column_name1: type, comment, Examples: [examples])",
            ...
        ]
    }
}
```

Important Notes:
- Copy column definitions EXACTLY (no modifications)
- Include thinking process in "think" field
- List all relevant tables, even if only one column is selected
- Better to include extra columns than miss critical ones
- Consider the full query execution path

Remember: Your goal is to create a focused, relevant schema subset that enables accurate SQL generation."""
        
        # ✨ 添加业务领域知识
        if self.domain_knowledge:
            system_prompt += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**CRITICAL: BUSINESS DOMAIN KNOWLEDGE**
You MUST consider these business rules when selecting columns:

{self.domain_knowledge}

Schema Linking Requirements:
1. Include columns mentioned in business rules (e.g., sgamecode, saccounttype)
2. Select columns needed for business constraint filters
3. Prioritize columns that align with domain knowledge
4. Consider business logic patterns in column selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return system_prompt
    
    # ==================== User Prompt ====================
    
    def get_schema_linking_user_prompt(
        self, 
        question: str, 
        knowledge: str, 
        all_table_schemas: str
    ) -> str:
        """
        Schema Linking 的 User Prompt
        提供具体的问题、知识和表结构
        """
        user_prompt = f"""Question:
{question}

Domain Knowledge:
{knowledge if knowledge else "None"}

All Table Schemas:
{all_table_schemas}

Please analyze the question and schemas, then return the selected columns for each table in the JSON format specified."""
        
        return user_prompt
    
    # ==================== 兼容旧接口 ====================
    
    def get_schema_linking_prompt(
        self, 
        question: str, 
        knowledge: str, 
        all_table_schemas: str
    ) -> str:
        """
        兼容旧接口：组合 system + user prompt
        """
        system = self.get_schema_linking_system_prompt()
        user = self.get_schema_linking_user_prompt(question, knowledge, all_table_schemas)
        
        # 返回组合后的 prompt（旧格式）
        prompt = f"""{system}

---

{user}"""
        
        return prompt
    
    def get_legacy_prompt_template(self) -> str:
        """
        返回原始的 prompt 模板（完全兼容旧版本）
        """
        return """You are performing column-level schema linking for SQL generation.

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

Please analyze and return the selected columns for each table in the JSON format above."""


# ==================== 全局常量（保持兼容性） ====================

SCHEMA_LINKING_PROMPT = SchemaLinkingPromptManager().get_legacy_prompt_template()
