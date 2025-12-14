"""
并行Schema Linking实现
同时调用MACSQLCoTParse和RSLSQLBiDirParse，合并结果

参考Squrve\core\actor\nest\tree.py中的ParseActorGroup合并逻辑
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from chat import GPTChat
from prompts.parallel_schema_linking_prompts import ParallelSchemaLinkingPromptManager


class ParallelSchemaLinker:
    """
    并行Schema Linking器
    
    功能：
    1. 并行执行MACSQLCoTParse和RSLSQLBiDirParse
    2. 合并两种解析器的结果
    3. 生成简化的M-schema表示
    """
    
    def __init__(
        self,
        schema_file: str,
        prompt_manager: Optional[ParallelSchemaLinkingPromptManager] = None,
        max_workers: int = 2
    ):
        """
        初始化并行Schema Linker
        
        Args:
            schema_file: M-schema文件路径
            prompt_manager: Prompt管理器（可选）
            max_workers: 最大并行数（默认2，对应2个解析器）
        """
        self.schema_file = schema_file
        self.prompt_manager = prompt_manager or ParallelSchemaLinkingPromptManager()
        self.max_workers = max_workers
        
        # 加载完整Schema
        with open(schema_file, 'r', encoding='utf-8') as f:
            self.full_schema = f.read()
        
        # 解析Schema结构
        self.all_tables = self._parse_all_tables()
        self.table_schemas = self._parse_table_schemas()
        self.foreign_keys = self._extract_foreign_keys()
        
        logger.info(f"ParallelSchemaLinker initialized with {len(self.all_tables)} tables")
    
    def _parse_all_tables(self) -> List[str]:
        """解析所有表名"""
        tables = []
        for line in self.full_schema.split('\n'):
            if line.startswith('# Table:'):
                parts = line.split(',', 1)
                table_name = parts[0].replace('# Table:', '').strip()
                tables.append(table_name)
        return tables
    
    def _parse_table_schemas(self) -> Dict[str, str]:
        """解析每个表的Schema片段"""
        table_schemas = {}
        current_table = None
        current_schema = []
        
        for line in self.full_schema.split('\n'):
            if line.startswith('# Table:'):
                # 保存上一个表（如果有内容）
                if current_table and current_schema:
                    table_schemas[current_table] = '\n'.join(current_schema)
                
                # 开始新表
                parts = line.split(',', 1)
                current_table = parts[0].replace('# Table:', '').strip()
                current_schema = [line]
            elif current_table:
                current_schema.append(line)
                # 检查是否到达表结束（遇到下一个表或空行）
                if line.strip() == ']':
                    table_schemas[current_table] = '\n'.join(current_schema)
                    current_schema = []
        
        # 保存最后一个表
        if current_table and current_schema:
            table_schemas[current_table] = '\n'.join(current_schema)
        
        logger.info(f"[Parse Schema] Parsed {len(table_schemas)} tables from M-schema")
        for table_name in list(table_schemas.keys())[:3]:  # 显示前3个表名
            logger.debug(f"[Parse Schema] Table '{table_name}' length: {len(table_schemas[table_name])} chars")
        
        return table_schemas
    
    def _extract_foreign_keys(self) -> str:
        """提取外键关系"""
        fk_lines = []
        in_fk_section = False
        
        for line in self.full_schema.split('\n'):
            line_stripped = line.strip()
            
            # 检测外键部分（通常在文件末尾，包含 "=" 符号）
            if '=' in line_stripped and '.' in line_stripped and '`' in line_stripped:
                in_fk_section = True
                fk_lines.append(line_stripped)
            elif in_fk_section and not line_stripped:
                # 空行标志外键部分结束
                break
        
        return '\n'.join(fk_lines) if fk_lines else "No foreign key constraints defined."
    
    def _get_filtered_schema(self, table_list: List[str]) -> str:
        """根据table_list过滤Schema"""
        filtered_parts = []
        
        logger.debug(f"[Filter Schema] Input table_list: {table_list}")
        logger.debug(f"[Filter Schema] Available tables in schema: {list(self.table_schemas.keys())}")
        
        for table in table_list:
            if table in self.table_schemas:
                filtered_parts.append(self.table_schemas[table])
                logger.debug(f"[Filter Schema] ✓ Found table '{table}' in schema")
            else:
                logger.warning(f"[Filter Schema] ⚠️ Table '{table}' not found in schema")
        
        result = '\n'.join(filtered_parts)
        
        if not result:
            logger.error(f"[Filter Schema] ❌ Result is EMPTY! No tables matched from table_list: {table_list}")
        else:
            logger.info(f"[Filter Schema] ✓ Filtered schema length: {len(result)} chars, {len(filtered_parts)} tables")
        
        # 添加外键信息（如果相关）
        if self.foreign_keys and self.foreign_keys != "No foreign key constraints defined.":
            # 只包含涉及table_list中表的外键
            relevant_fks = []
            for fk_line in self.foreign_keys.split('\n'):
                if any(table in fk_line for table in table_list):
                    relevant_fks.append(fk_line)
            
            if relevant_fks:
                result += '\n\n### Foreign Keys:\n' + '\n'.join(relevant_fks)
        
        return result
    
    def _call_macsql_parser(
        self,
        question: str,
        schema: str,
        knowledge: str,
        chat_session: GPTChat
    ) -> Dict[str, any]:
        """
        调用MACSQLCoTParse解析器
        
        Returns:
            {"tables": [...], "columns": {...}}
            其中columns是字典格式: {"table1": ["col1", "col2"], ...}
        """
        try:
            logger.info("[MACSQLCoTParse] Starting...")
            
            # ✨ 检查schema是否为空
            if not schema or not schema.strip():
                logger.error("[MACSQLCoTParse] ❌ Received EMPTY schema!")
                return {"tables": [], "columns": {}}
            
            logger.info(f"[MACSQLCoTParse] Received schema length: {len(schema)} chars")
            logger.debug(f"[MACSQLCoTParse] Schema preview: {schema[:200]}...")
            
            # 构造Prompt
            system_prompt = self.prompt_manager.get_macsql_system_prompt()
            user_prompt = self.prompt_manager.get_macsql_user_prompt(
                db_id="final_algorithm_competition",
                schema=schema,
                foreign_keys=self.foreign_keys,
                question=question,
                knowledge=knowledge
            )
            
            logger.debug(f"[MACSQLCoTParse] User prompt length: {len(user_prompt)} chars")
            
            # 调用LLM - 设置system prompt后发送user prompt
            chat_session.clear_messages()  # 清空历史消息
            chat_session.set_system_prompt(system_prompt)  # 设置system prompt
            response = chat_session.get_model_response_txt(user_prompt)  # 发送user prompt
            
            logger.info(f"[MACSQLCoTParse] Raw response: {response[:200]}...")
            
            # 解析JSON响应
            result = self._parse_macsql_response(response)
            
            logger.info(f"[MACSQLCoTParse] Parsed result: {len(result.get('tables', []))} tables")
            return result
            
        except Exception as e:
            logger.error(f"[MACSQLCoTParse] Error: {e}")
            return {"tables": [], "columns": {}}
    
    def _parse_macsql_response(self, response: str) -> Dict[str, any]:
        """
        解析MACSQLCoTParse的响应
        
        Expected format:
        {
          "table1": "keep_all",
          "table2": ["col1", "col2", ...],
          "table3": "drop_all"
        }
        """
        # 提取JSON
        json_str = self._extract_json_from_text(response)
        if not json_str:
            logger.warning("[MACSQLCoTParse] Failed to extract JSON from response")
            return {"tables": [], "columns": {}}
        
        try:
            raw_result = json.loads(json_str)
            logger.info(f"[MACSQLCoTParse] Raw parsed JSON: {raw_result}")
            
            tables = []
            columns = {}
            invalid_tables = []
            
            for table, value in raw_result.items():
                if value == "drop_all":
                    continue
                
                # ✨ 验证表名是否在schema中
                if table not in self.table_schemas:
                    invalid_tables.append(table)
                    logger.warning(f"[MACSQLCoTParse] ⚠️ Invalid table '{table}' not in schema, skipping")
                    continue
                
                tables.append(table)
                
                if value == "keep_all":
                    # 保留所有列
                    if table in self.table_schemas:
                        all_cols = self._extract_table_columns(table)
                        columns[table] = all_cols
                        logger.debug(f"[MACSQLCoTParse] Table '{table}': keep_all ({len(all_cols)} columns)")
                elif isinstance(value, list):
                    # ✨ 验证列名是否在schema中
                    valid_cols = []
                    invalid_cols = []
                    available_cols = self._extract_table_columns(table)
                    
                    for col in value:
                        if col in available_cols:
                            valid_cols.append(col)
                        else:
                            invalid_cols.append(col)
                            logger.warning(f"[MACSQLCoTParse] ⚠️ Invalid column '{table}.{col}' not in schema, skipping")
                    
                    if valid_cols:
                        columns[table] = valid_cols
                        logger.debug(f"[MACSQLCoTParse] Table '{table}': {len(valid_cols)} valid columns")
                    if invalid_cols:
                        logger.warning(f"[MACSQLCoTParse] Table '{table}': {len(invalid_cols)} invalid columns filtered")
            
            if invalid_tables:
                logger.warning(f"[MACSQLCoTParse] ⚠️ Filtered {len(invalid_tables)} invalid tables: {invalid_tables}")
            
            return {"tables": tables, "columns": columns}
            
        except json.JSONDecodeError as e:
            logger.error(f"[MACSQLCoTParse] JSON parsing error: {e}")
            return {"tables": [], "columns": {}}
    
    def _call_rslsql_parser(
        self,
        question: str,
        schema: str,
        knowledge: str,
        chat_session: GPTChat
    ) -> Dict[str, any]:
        """
        调用RSLSQLBiDirParse解析器
        
        Returns:
            {"tables": [...], "columns": ["table1.`col1`", "table2.`col2`", ...]}
        """
        try:
            logger.info("[RSLSQLBiDirParse] Starting...")
            
            # ✨ 检查schema是否为空
            if not schema or not schema.strip():
                logger.error("[RSLSQLBiDirParse] ❌ Received EMPTY schema!")
                return {"tables": [], "columns": []}
            
            logger.info(f"[RSLSQLBiDirParse] Received schema length: {len(schema)} chars")
            logger.debug(f"[RSLSQLBiDirParse] Schema preview: {schema[:200]}...")
            
            # Step 1: 表选择
            simple_ddl = self._build_simple_ddl(schema)
            
            system_prompt = self.prompt_manager.get_rslsql_table_selection_system_prompt()
            user_prompt = self.prompt_manager.get_rslsql_table_selection_user_prompt(
                schema_info=simple_ddl,
                question=question,
                knowledge=knowledge
            )
            
            chat_session.clear_messages()
            chat_session.set_system_prompt(system_prompt)  # 设置system prompt
            response1 = chat_session.get_model_response_txt(user_prompt)  # 发送user prompt
            
            logger.info(f"[RSLSQLBiDirParse] Table selection response: {response1[:200]}...")
            
            # 解析表选择结果
            table_column = self._parse_rslsql_table_response(response1)
            identified_tables = table_column.get('tables', [])
            identified_columns = table_column.get('columns', [])
            
            logger.info(f"[RSLSQLBiDirParse] Identified {len(identified_tables)} tables")
            
            # Step 2: 反向Schema Linking（生成初步SQL）
            if identified_tables:
                ddl_with_data = self._build_ddl_with_sample_data(schema, identified_tables)
                
                system_prompt2 = self.prompt_manager.get_rslsql_sql_generation_system_prompt()
                user_prompt2 = self.prompt_manager.get_rslsql_sql_generation_user_prompt(
                    table_info=ddl_with_data,
                    identified_tables=identified_tables,
                    identified_columns=identified_columns,
                    question=question,
                    knowledge=knowledge
                )
                
                # 重新设置system prompt (第二步)
                chat_session.clear_messages()
                chat_session.set_system_prompt(system_prompt2)
                response2 = chat_session.get_model_response_txt(user_prompt2)
                
                logger.info(f"[RSLSQLBiDirParse] SQL generation response: {response2[:200]}...")
                
                # 解析SQL
                preliminary_sql = self._parse_rslsql_sql_response(response2)
                
                # Step 3: 从SQL中提取列（双向链接）
                final_columns = self._extract_columns_from_sql(preliminary_sql, schema)
                
                # 合并列
                all_columns = list(set(identified_columns + final_columns))
                
                return {"tables": identified_tables, "columns": all_columns}
            else:
                return {"tables": [], "columns": []}
            
        except Exception as e:
            logger.error(f"[RSLSQLBiDirParse] Error: {e}")
            return {"tables": [], "columns": []}
    
    def _build_simple_ddl(self, schema: str) -> str:
        """构建简化DDL（不含样例数据）"""
        ddl_lines = []
        
        for line in schema.split('\n'):
            if line.startswith('# Table:'):
                table_name = line.split(',')[0].replace('# Table:', '').strip()
                cols = self._extract_table_columns_from_text(schema, table_name)
                
                if cols:
                    ddl_lines.append(f"# {table_name}(" + ",".join([f"`{c}`" for c in cols]) + ")")
        
        return '\n'.join(ddl_lines)
    
    def _build_ddl_with_sample_data(self, schema: str, tables: List[str]) -> str:
        """构建含样例数据的DDL"""
        ddl_lines = []
        
        for table in tables:
            if table in self.table_schemas:
                table_schema = self.table_schemas[table]
                
                # 提取列和样例数据
                cols_with_samples = []
                current_col = None
                
                for line in table_schema.split('\n'):
                    if line.strip().startswith('(') and ':' in line:
                        # 列定义
                        col_def = line.strip().strip('(),')
                        col_name = col_def.split(':')[0].strip()
                        
                        # 提取样例值
                        samples = []
                        if 'Examples:' in col_def:
                            try:
                                example_part = col_def.split('Examples:')[1]
                                start_idx = example_part.find('[')
                                end_idx = example_part.find(']')
                                if start_idx != -1 and end_idx != -1:
                                    import ast
                                    values_str = example_part[start_idx:end_idx+1]
                                    samples = ast.literal_eval(values_str)[:3]
                            except:
                                samples = []
                        
                        # 格式化样例
                        if samples:
                            sample_str = ','.join([str(s) for s in samples])
                            cols_with_samples.append(f"`{col_name}`[{sample_str}]")
                        else:
                            cols_with_samples.append(f"`{col_name}`[]")
                
                if cols_with_samples:
                    ddl_lines.append(f"# {table}(" + ",".join(cols_with_samples) + ")")
        
        return '\n'.join(ddl_lines)
    
    def _parse_rslsql_table_response(self, response: str) -> Dict[str, any]:
        """解析RSLSQLBiDirParse的表选择响应"""
        json_str = self._extract_json_from_text(response)
        if not json_str:
            logger.warning("[RSLSQLBiDirParse] Failed to extract JSON from response")
            return {"tables": [], "columns": []}
        
        try:
            result = json.loads(json_str)
            logger.info(f"[RSLSQLBiDirParse] Raw parsed JSON: {result}")
            
            raw_tables = result.get("tables", [])
            raw_columns = result.get("columns", [])
            
            # ✨ 验证表名
            valid_tables = []
            invalid_tables = []
            for table in raw_tables:
                if table in self.table_schemas:
                    valid_tables.append(table)
                else:
                    invalid_tables.append(table)
                    logger.warning(f"[RSLSQLBiDirParse] ⚠️ Invalid table '{table}' not in schema, skipping")
            
            # ✨ 验证列名
            valid_columns = []
            invalid_columns = []
            for col in raw_columns:
                if '.' in col:
                    table = col.split('.')[0]
                    column = col.split('.', 1)[1].strip('`')
                    
                    # 检查表是否存在
                    if table not in self.table_schemas:
                        invalid_columns.append(col)
                        logger.warning(f"[RSLSQLBiDirParse] ⚠️ Invalid column '{col}': table not in schema")
                        continue
                    
                    # 检查列是否存在
                    available_cols = self._extract_table_columns(table)
                    if column in available_cols:
                        valid_columns.append(col)
                    else:
                        invalid_columns.append(col)
                        logger.warning(f"[RSLSQLBiDirParse] ⚠️ Invalid column '{col}': column not in schema")
                else:
                    invalid_columns.append(col)
                    logger.warning(f"[RSLSQLBiDirParse] ⚠️ Invalid column format '{col}': missing table prefix")
            
            if invalid_tables:
                logger.warning(f"[RSLSQLBiDirParse] ⚠️ Filtered {len(invalid_tables)} invalid tables: {invalid_tables}")
            if invalid_columns:
                logger.warning(f"[RSLSQLBiDirParse] ⚠️ Filtered {len(invalid_columns)} invalid columns")
            
            logger.info(f"[RSLSQLBiDirParse] Valid: {len(valid_tables)} tables, {len(valid_columns)} columns")
            
            return {
                "tables": valid_tables,
                "columns": valid_columns
            }
        except json.JSONDecodeError:
            logger.error("[RSLSQLBiDirParse] JSON parsing error")
            return {"tables": [], "columns": []}
    
    def _parse_rslsql_sql_response(self, response: str) -> str:
        """解析RSLSQLBiDirParse的SQL生成响应"""
        json_str = self._extract_json_from_text(response)
        if not json_str:
            return ""
        
        try:
            result = json.loads(json_str)
            return result.get("sql", "")
        except json.JSONDecodeError:
            return ""
    
    def _extract_columns_from_sql(self, sql: str, schema: str) -> List[str]:
        """从SQL中提取列名"""
        if not sql:
            return []
        
        columns = []
        sql_lower = sql.lower()
        
        # 从schema中获取所有可能的列
        all_schema_columns = self._get_all_schema_columns(schema)
        
        # 检查哪些列出现在SQL中
        for col in all_schema_columns:
            # 提取table.column 中的column
            col_clean = col.replace('`', '').lower().rsplit('.', 1)[1]
            
            if col_clean in sql_lower:
                columns.append(col)
        
        return columns
    
    def _get_all_schema_columns(self, schema: str) -> List[str]:
        """获取schema中所有的table.column组合"""
        columns = []
        current_table = None
        in_columns = False
        
        for line in schema.split('\n'):
            if line.startswith('# Table:'):
                current_table = line.split(',')[0].replace('# Table:', '').strip()
                in_columns = False
            elif line.strip() == '[':
                in_columns = True
            elif line.strip() == ']':
                in_columns = False
            elif current_table and in_columns and line.strip().startswith('('):
                col_def = line.strip().strip('(),')
                if ':' in col_def:
                    col_name = col_def.split(':')[0].strip()
                    columns.append(f"{current_table}.`{col_name}`")
        
        return columns
    
    def _extract_table_columns(self, table_name: str) -> List[str]:
        """提取指定表的所有列名"""
        if table_name not in self.table_schemas:
            return []
        
        return self._extract_table_columns_from_text(self.table_schemas[table_name], table_name)
    
    def _extract_table_columns_from_text(self, schema_text: str, table_name: str) -> List[str]:
        """从schema文本中提取表的列名"""
        columns = []
        in_columns = False
        
        for line in schema_text.split('\n'):
            if line.strip() == '[':
                in_columns = True
            elif line.strip() == ']':
                in_columns = False
            elif in_columns and line.strip().startswith('('):
                col_def = line.strip().strip('(),')
                if ':' in col_def:
                    col_name = col_def.split(':')[0].strip()
                    columns.append(col_name)
        
        return columns
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """从文本中提取JSON字符串"""
        import re
        
        # 尝试从```json ... ```中提取
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # 尝试从```...```中提取
        json_match = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # 尝试直接提取JSON对象
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return None
    
    def merge_results(
        self,
        macsql_result: Dict[str, any],
        rslsql_result: Dict[str, any],
        table_list: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        合并两个解析器的结果
        
        参考Squrve\core\actor\nest\tree.py中的ParseActorGroup.merge_results
        
        Args:
            macsql_result: {"tables": [...], "columns": {"table1": ["col1", ...], ...}}
            rslsql_result: {"tables": [...], "columns": ["table1.`col1`", ...]}
            table_list: 允许的表列表（用于过滤，防止解析器返回不在范围内的表）
        
        Returns:
            {"tables": [...], "columns": ["table1.`col1`", ...]}
        """
        logger.info("[Merge] Starting result merge...")
        
        # 合并表列表
        all_tables = list(set(
            macsql_result.get('tables', []) + 
            rslsql_result.get('tables', [])
        ))
        
        # ✨ 过滤：只保留在table_list中的表
        if table_list:
            original_count = len(all_tables)
            all_tables = [t for t in all_tables if t in table_list]
            filtered_count = original_count - len(all_tables)
            if filtered_count > 0:
                logger.warning(f"[Merge] Filtered out {filtered_count} tables not in table_list")
            
            # ✨ 任务2：检查table_list中未被选中的表，将其全部加入
            unselected_tables = [t for t in table_list if t not in all_tables]
            if unselected_tables:
                logger.info(f"[Merge] Adding {len(unselected_tables)} unselected tables from table_list: {unselected_tables}")
                all_tables.extend(unselected_tables)
        
        # 合并列列表
        all_columns = []
        
        # 从MACSQLCoTParse结果提取列
        macsql_columns = macsql_result.get('columns', {})
        if isinstance(macsql_columns, dict):
            for table, cols in macsql_columns.items():
                # ✨ 只处理在table_list中的表
                if table_list and table not in table_list:
                    logger.warning(f"[Merge] Skipping columns from table '{table}' (not in table_list)")
                    continue
                
                if isinstance(cols, list):
                    for col in cols:
                        # 确保格式为 table.`column`
                        if '.' not in col:
                            all_columns.append(f"{table}.`{col}`")
                        else:
                            all_columns.append(col)
        
        # 从RSLSQLBiDirParse结果提取列（参考tree.py:269-274）
        rslsql_columns = rslsql_result.get('columns', [])
        if isinstance(rslsql_columns, list):
            for col in rslsql_columns:
                # ✨ 只保留属于table_list中表的列
                if table_list and '.' in col:
                    table = col.split('.')[0]
                    if table not in table_list:
                        logger.warning(f"[Merge] Skipping column '{col}' (table not in table_list)")
                        continue
                all_columns.append(col)
        
        # ✨ 任务2：为未被选中的表添加所有列
        if table_list:
            unselected_tables = [t for t in table_list if t not in macsql_result.get('tables', []) 
                                and t not in rslsql_result.get('tables', [])]
            if unselected_tables:
                logger.info(f"[Merge] Adding all columns for {len(unselected_tables)} unselected tables")
                for table in unselected_tables:
                    if table in self.table_schemas:
                        # 提取该表的所有列
                        table_cols = self._extract_table_columns(table)
                        for col in table_cols:
                            all_columns.append(f"{table}.`{col}`")
                        logger.info(f"[Merge] Added {len(table_cols)} columns for unselected table '{table}'")
        
        # 去重（参考tree.py:276）
        all_columns = list(set(all_columns))
        
        logger.info(f"[Merge] Result: {len(all_tables)} tables, {len(all_columns)} columns")
        
        return {
            "tables": all_tables,
            "columns": all_columns
        }
    
    def generate_linked_schema(
        self,
        merged_result: Dict[str, List[str]],
        original_schema: str
    ) -> str:
        """
        根据合并结果生成简化的M-schema
        
        Args:
            merged_result: {"tables": [...], "columns": ["table.`col`", ...]}
            original_schema: 原始完整schema
        
        Returns:
            简化的M-schema文本
        """
        logger.info("[Generate Schema] Creating linked schema...")
        
        tables = merged_result.get('tables', [])
        columns = merged_result.get('columns', [])
        
        # 按表组织列
        table_columns = {}
        for col in columns:
            if '.' in col:
                table = col.split('.')[0]
                column = col.split('.', 1)[1].strip('`')
                
                if table not in table_columns:
                    table_columns[table] = []
                table_columns[table].append(column)
        
        # 生成简化schema
        schema_parts = []
        
        for table in tables:
            if table in self.table_schemas:
                table_schema_lines = []
                relevant_cols = set(table_columns.get(table, []))
                
                # 如果没有指定列，保留所有列
                if not relevant_cols:
                    schema_parts.append(self.table_schemas[table])
                    continue
                
                # 只保留相关列
                in_columns = False
                for line in self.table_schemas[table].split('\n'):
                    if line.startswith('# Table:'):
                        table_schema_lines.append(line)
                    elif line.strip() == '[':
                        table_schema_lines.append(line)
                        in_columns = True
                    elif line.strip() == ']':
                        table_schema_lines.append(line)
                        in_columns = False
                    elif in_columns and line.strip().startswith('('):
                        col_def = line.strip().strip('(),')
                        if ':' in col_def:
                            col_name = col_def.split(':')[0].strip()
                            if col_name in relevant_cols:
                                table_schema_lines.append(line)
                    else:
                        table_schema_lines.append(line)
                
                if table_schema_lines:
                    schema_parts.append('\n'.join(table_schema_lines))
        
        linked_schema = '\n'.join(schema_parts)
        
        # 添加外键信息
        if self.foreign_keys and self.foreign_keys != "No foreign key constraints defined.":
            relevant_fks = []
            for fk_line in self.foreign_keys.split('\n'):
                if any(table in fk_line for table in tables):
                    relevant_fks.append(fk_line)
            
            if relevant_fks:
                linked_schema += '\n\n### Foreign Keys:\n' + '\n'.join(relevant_fks)
        
        logger.info(f"[Generate Schema] Generated schema with {len(tables)} tables")
        
        return linked_schema
    
    def link_schema(
        self,
        question: str,
        table_list: List[str],
        knowledge: str = "",
        chat_session: Optional[GPTChat] = None
    ) -> str:
        """
        执行并行Schema Linking
        
        Args:
            question: 用户问题
            table_list: 相关表列表（用于预过滤）
            knowledge: 领域知识
            chat_session: Chat会话（可选，如果不提供则内部创建）
        
        Returns:
            schema-linking结果
            简化的M-schema文本
        """
        logger.info(f"[Parallel Schema Linking] Starting for question: {question[:50]}...")
        
        # 预过滤Schema（使用table_list）
        filtered_schema = self._get_filtered_schema(table_list)
        
        # ✨ 关键修复：为每个解析器创建独立的chat session，避免线程竞态
        if chat_session:
            # 提取配置参数
            azure = chat_session.azure if hasattr(chat_session, 'azure') else False
            model = chat_session.model if hasattr(chat_session, 'model') else "deepseek-chat"
            
            # 为两个解析器分别创建独立的session
            chat_macsql = GPTChat(azure, model)
            chat_rslsql = GPTChat(azure, model)
        else:
            # 默认配置
            chat_macsql = GPTChat(False, "deepseek-chat")
            chat_rslsql = GPTChat(False, "deepseek-chat")
        
        logger.info("[Parallel] Created independent chat sessions for each parser")
        
        # 并行执行两个解析器
        macsql_result = None
        rslsql_result = None
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_macsql = executor.submit(
                self._call_macsql_parser,
                question, filtered_schema, knowledge, chat_macsql
            )
            future_rslsql = executor.submit(
                self._call_rslsql_parser,
                question, filtered_schema, knowledge, chat_rslsql
            )
            
            # 收集结果
            for future in as_completed([future_macsql, future_rslsql]):
                try:
                    result = future.result()
                    
                    if future == future_macsql:
                        macsql_result = result
                        logger.info("[Parallel] MACSQLCoTParse completed")
                    else:
                        rslsql_result = result
                        logger.info("[Parallel] RSLSQLBiDirParse completed")
                        
                except Exception as e:
                    logger.error(f"[Parallel] Parser execution error: {e}")
        
        # 如果任一解析器失败，使用默认结果
        if macsql_result is None:
            macsql_result = {"tables": [], "columns": {}}
        if rslsql_result is None:
            rslsql_result = {"tables": [], "columns": []}
        
        # ✨ 输出两个parser的结果到日志
        logger.info("="*60)
        logger.info("[Parser Results] MACSQLCoTParse:")
        logger.info(f"  Tables ({len(macsql_result.get('tables', []))}): {macsql_result.get('tables', [])}")
        macsql_cols = macsql_result.get('columns', {})
        if isinstance(macsql_cols, dict):
            total_cols = sum(len(cols) for cols in macsql_cols.values() if isinstance(cols, list))
            logger.info(f"  Columns: {total_cols} total across {len(macsql_cols)} tables")
            for table, cols in macsql_cols.items():
                if isinstance(cols, list):
                    logger.info(f"    {table}: {len(cols)} columns - {cols[:5]}{'...' if len(cols) > 5 else ''}")
        
        logger.info("[Parser Results] RSLSQLBiDirParse:")
        logger.info(f"  Tables ({len(rslsql_result.get('tables', []))}): {rslsql_result.get('tables', [])}")
        rslsql_cols = rslsql_result.get('columns', [])
        if isinstance(rslsql_cols, list):
            logger.info(f"  Columns: {len(rslsql_cols)} total")
            # 按表分组显示
            cols_by_table = {}
            for col in rslsql_cols:
                if '.' in col:
                    table = col.split('.')[0]
                    if table not in cols_by_table:
                        cols_by_table[table] = []
                    cols_by_table[table].append(col)
            for table, cols in cols_by_table.items():
                logger.info(f"    {table}: {len(cols)} columns - {[c.split('.', 1)[1] for c in cols[:5]]}{'...' if len(cols) > 5 else ''}")
        logger.info("="*60)
        
        # 合并结果（传递table_list进行过滤）
        merged_result = self.merge_results(macsql_result, rslsql_result, table_list)
        
        # ✨ 输出合并结果到日志
        logger.info("[Merged Result]:")
        logger.info(f"  Tables ({len(merged_result.get('tables', []))}): {merged_result.get('tables', [])}")
        merged_cols = merged_result.get('columns', [])
        logger.info(f"  Columns: {len(merged_cols)} total")
        # 按表分组显示合并后的列
        merged_cols_by_table = {}
        for col in merged_cols:
            if '.' in col:
                table = col.split('.')[0]
                if table not in merged_cols_by_table:
                    merged_cols_by_table[table] = []
                merged_cols_by_table[table].append(col)
        for table in merged_result.get('tables', []):
            cols = merged_cols_by_table.get(table, [])
            logger.info(f"    {table}: {len(cols)} columns - {[c.split('.', 1)[1] for c in cols[:5]]}{'...' if len(cols) > 5 else ''}")
        logger.info("="*60)
        
        # 生成简化Schema
        linked_schema = self.generate_linked_schema(merged_result, filtered_schema)
        
        logger.info("[Parallel Schema Linking] ✓ Completed")
        
        return merged_result, linked_schema
