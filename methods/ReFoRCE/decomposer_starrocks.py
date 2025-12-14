"""
StarRocks版问题分解器
用于将中等/困难复杂度的问题分解为子问题和对应的SQL
基于MAC-SQL方法,适配StarRocks语法
"""

import re
import os
import json
from typing import List, Tuple, Optional, Dict
from chat import GPTChat


class StarRocksDecomposer:
    """
    StarRocks问题分解器
    将复杂问题分解为多个子问题,并为每个子问题生成SQL
    """
    
    # StarRocks版分解模板
    DECOMPOSE_TEMPLATE_STARROCKS = '''Given a 【Database schema】 description, a knowledge 【Evidence】, 【Few-shot Examples】 from column exploration, and the 【Question】, you need to use valid StarRocks SQL and understand the database and knowledge, and then decompose the question into subquestions for text-to-SQL generation.

When generating SQL, we should always consider constraints:
【Constraints】
- In `SELECT <column>`, just select needed columns in the 【Question】 without any unnecessary column or value
- In `FROM <table>` or `JOIN <table>`, do not include unnecessary table
- If use max or min func, `JOIN <table>` FIRST, THEN use `SELECT MAX(<column>)` or `SELECT MIN(<column>)`
- If [Value examples] of <column> has 'None' or NULL, use `JOIN <table>` or `WHERE <column> is NOT NULL` is better
- If use `ORDER BY <column> ASC|DESC`, consider using `GROUP BY <column>` before to select distinct values
- **StarRocks Date Format**: dtstatdate uses YYYYMMDD format (INTEGER), use `dtstatdate BETWEEN 20250101 AND 20250131` for date filtering
- **StarRocks Aggregations**: Always handle NULL values with COALESCE() when using SUM/AVG
- **User Deduplication**: When counting users (suerid, iuserid, swxid), always use COUNT(DISTINCT ...)
- **Player Deduplication**: When counting players (gplayerid, vplayerid), always use COUNT(DISTINCT ...)

==========

【Database schema】
# Table: tb_user_active_stat
[
  (dtstatdate, Date in YYYYMMDD format. INTEGER type. Value examples: [20250724, 20250530]. For date range: dtstatdate BETWEEN 20250530 AND 20250724),
  (sgamecode, Game code. Value examples: ['initiatived', 'jordass', 'esports']. For competitive games: sgamecode IN ('initiatived','jordass','esports','allianceforce','strategy','playzone','su')),
  (saccounttype, Account type. Value examples: ['-100']. Always use '-100' for aggregated data),
  (suseridtype, User ID type. Value examples: ['qq', 'wxid']. For all users: suseridtype IN ('qq','wxid')),
  (stags, User tags. Value examples: ['新增用户', '其他']),
  (iloginminutes, Login duration in minutes. INTEGER. Value examples: [120, 3600]),
  (factivedays, Active days. INTEGER. Value examples: [1, 7, 30])
]

【Foreign keys】
None (Single table scenario)

【Question】
统计2025.07.24的手游全量用户且标签为其他,在竞品业务下2025.05.30-2025.07.24的在线时长。

【Evidence】
竞品业务：sgamecode IN ('initiatived','jordass','esports','allianceforce','strategy','playzone','su')
saccounttype = '-100' -- 账号体系,取-100表示汇总
suseridtype IN ('qq','wxid') -- 用户类型
在线时长：SUM(iloginminutes)

【Few-shot Examples】
Query: SELECT DISTINCT sgamecode FROM tb_user_active_stat LIMIT 10;
Answer: 
sgamecode
initiatived
jordass
esports
...

Query: SELECT DISTINCT stags FROM tb_user_active_stat WHERE dtstatdate = 20250724 LIMIT 10;
Answer:
stags
新增用户
其他
流失用户
...

Decompose the question into sub questions, considering 【Constraints】, and generate the SQL after thinking step by step:

Sub question 1: Get all users with tag '其他' on 2025-07-24.
SQL
```sql
SELECT DISTINCT suserid
FROM tb_user_active_stat
WHERE dtstatdate = 20250724
  AND stags = '其他'
  AND saccounttype = '-100'
  AND suseridtype IN ('qq', 'wxid')
```

Sub question 2: Calculate total online duration for these users in competitive games from 2025-05-30 to 2025-07-24.
SQL
```sql
SELECT COALESCE(SUM(iloginminutes), 0) AS total_minutes
FROM tb_user_active_stat
WHERE dtstatdate BETWEEN 20250530 AND 20250724
  AND sgamecode IN ('initiatived','jordass','esports','allianceforce','strategy','playzone','su')
  AND saccounttype = '-100'
  AND suseridtype IN ('qq', 'wxid')
  AND suserid IN (
    SELECT DISTINCT suserid
    FROM tb_user_active_stat
    WHERE dtstatdate = 20250724
      AND stags = '其他'
      AND saccounttype = '-100'
      AND suseridtype IN ('qq', 'wxid')
  )
```

Question Solved.

==========

【Database schema】
{schema}

【Schema Links】
{schema_links}

【Question】
{question}

【Evidence】
{evidence}

【Few-shot Examples】
{few_shot_examples}

Decompose the question into sub questions, considering 【Constraints】, and generate the SQL after thinking step by step:

**IMPORTANT OUTPUT FORMAT REQUIREMENT**:
You MUST follow this exact format for each sub-question:

Sub question 1: <Your sub-question description here>
SQL
```sql
<Your SQL query here>
```

Sub question 2: <Your sub-question description here>
SQL
```sql
<Your SQL query here>
```

... (continue for all sub-questions)

Question Solved.

DO NOT just output SQL directly without the "Sub question X:" prefix!
'''

    def __init__(self, chat_session: GPTChat = None, azure: bool = False, model: str = "gpt-4o"):
        """
        初始化分解器
        
        Args:
            chat_session: GPT聊天会话(可选)
            azure: 是否使用Azure
            model: 模型名称
        """
        self.chat_session = chat_session or GPTChat(azure, model)
    
    def parse_qa_pairs(self, response: str) -> List[Tuple[str, str]]:
        """
        解析LLM响应,提取子问题和对应的SQL
        支持多种格式:
        1. 标准格式: Sub question 1: ... SQL ```sql ... ```
        2. Fallback: 直接返回的SQL代码块
        
        Returns:
            List[(sub_question, sub_sql), ...]
        """
        qa_pairs = []
        
        # 尝试标准格式解析
        sub_parts = re.split(r'Sub question \d+:', response)
        
        # 如果找到了标准格式的子问题
        if len(sub_parts) > 1:
            for part in sub_parts[1:]:
                if 'SQL' in part or '```sql' in part:
                    # 提取子问题文本
                    sub_q = part.split('SQL')[0].strip()
                    if '```sql' in sub_q:
                        sub_q = sub_q.split('```sql')[0].strip()
                    
                    # 提取SQL
                    sql_match = re.search(r'```sql(.*?)```', part, re.DOTALL)
                    if sql_match:
                        sub_sql = sql_match.group(1).strip()
                        qa_pairs.append((sub_q, sub_sql))
        
        # Fallback: 如果没有找到标准格式，尝试直接提取SQL代码块
        if len(qa_pairs) == 0:
            # 查找所有SQL代码块
            sql_blocks = re.findall(r'```sql(.*?)```', response, re.DOTALL)
            
            if sql_blocks:
                for i, sql in enumerate(sql_blocks, 1):
                    sql = sql.strip()
                    if sql:
                        # 尝试从SQL上方提取描述作为子问题
                        # 例如: "Get users with tag '其他'\n```sql..."
                        sql_block_pattern = r'(.*?)```sql' + re.escape(sql) + r'```'
                        context_match = re.search(sql_block_pattern, response, re.DOTALL)
                        
                        if context_match:
                            context = context_match.group(1).strip()
                            # 取最后一行作为子问题描述
                            lines = [l.strip() for l in context.split('\n') if l.strip()]
                            sub_q = lines[-1] if lines else f"Sub-step {i}"
                        else:
                            sub_q = f"Sub-step {i}"
                        
                        qa_pairs.append((sub_q, sql))
            else:
                # 如果连SQL代码块都没有，尝试直接提取SELECT语句
                select_pattern = r'(SELECT\s+.*?;)'
                select_matches = re.findall(select_pattern, response, re.DOTALL | re.IGNORECASE)
                
                if select_matches:
                    for i, sql in enumerate(select_matches, 1):
                        sql = sql.strip()
                        qa_pairs.append((f"SQL Query {i}", sql))
        
        return qa_pairs
    
    def decompose(
        self,
        question: str,
        schema: str,
        evidence: str = "",
        schema_links: str = "",
        few_shot_examples: str = "",
        logger=None
    ) -> List[Tuple[str, str]]:
        """
        执行问题分解
        
        Args:
            question: 原始问题
            schema: 数据库Schema
            evidence: 领域知识
            schema_links: Schema Linking结果
            few_shot_examples: 列探索的Few-shot示例
            logger: 日志记录器
        
        Returns:
            List[(sub_question, sub_sql), ...]
        """
        if logger:
            logger.info(f"[Decomposer] Starting decomposition for question: {question}")
        
        # 构建Prompt
        prompt = self.DECOMPOSE_TEMPLATE_STARROCKS.format(
            schema=schema,
            schema_links=schema_links if schema_links else "Not provided",
            question=question,
            evidence=evidence if evidence else "No specific evidence provided",
            few_shot_examples=few_shot_examples if few_shot_examples else "No examples available"
        )
        
        # 调用LLM - 使用 get_model_response_txt 获取完整文本
        # 注意：不能使用 get_model_response(prompt, "sql")，因为它只会提取SQL代码块
        # 而丢弃 "Sub question 1:" 等文本标记，导致无法解析分解结果
        response_text = self.chat_session.get_model_response_txt(prompt)
        
        if logger:
            logger.info(f"[Decomposer] LLM Response:\n{response_text}")
        
        # 解析结果
        qa_pairs = self.parse_qa_pairs(response_text)
        
        if logger:
            logger.info(f"[Decomposer] Extracted {len(qa_pairs)} sub-questions")
            if len(qa_pairs) == 0:
                logger.warning(f"[Decomposer] Failed to extract sub-questions! Response format may be incorrect.")
                logger.warning(f"[Decomposer] Expected format: 'Sub question 1: ... SQL ```sql ... ```'")
                logger.warning(f"[Decomposer] Actual response preview: {response_text[:500]}...")
            else:
                for i, (q, sql) in enumerate(qa_pairs, 1):
                    logger.info(f"  Sub-Q{i}: {q}")
                    logger.info(f"  Sub-SQL{i}:\n{sql}")
        
        return qa_pairs
    
    def save_decomposition(
        self,
        qa_pairs: List[Tuple[str, str]],
        output_dir: str,
        sql_id: str
    ):
        """
        保存分解结果
        
        Args:
            qa_pairs: [(sub_question, sub_sql), ...]
            output_dir: 输出目录
            sql_id: SQL ID
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存为JSON格式
        decomposition_data = {
            "sql_id": sql_id,
            "sub_questions_count": len(qa_pairs),
            "decomposition": [
                {
                    "sub_question_id": i,
                    "sub_question": q,
                    "sub_sql": sql
                }
                for i, (q, sql) in enumerate(qa_pairs, 1)
            ]
        }
        
        json_path = os.path.join(output_dir, "decomposition.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(decomposition_data, f, ensure_ascii=False, indent=2)
        
        # 同时保存为单独的SQL文件
        for i, (q, sql) in enumerate(qa_pairs, 1):
            sql_path = os.path.join(output_dir, f"sub_{i}.sql")
            with open(sql_path, 'w', encoding='utf-8') as f:
                f.write(f"-- Sub Question {i}: {q}\n")
                f.write(f"{sql}\n")
