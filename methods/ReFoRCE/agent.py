from utils import hard_cut, get_values_from_table, get_api_name, filter_bijection_like_dict, compare_pandas_table, is_valid_result, get_sqlite_path, split_sql
# 条件导入：支持 StarRocks 和原始 SQL 环境
try:
    from sql import SqlEnv
except ImportError:
    # 如果原始 sql.py 导入失败（缺少 BigQuery 等依赖），使用 StarRocks
    from sql_starrocks import SqlEnvStarRocks as SqlEnv
import pandas as pd
from io import StringIO
import os
import shutil
import csv
# from prompt import Prompts  # 已废弃
from prompts.base_prompts import BasePromptManager
from typing import Type, Union
from chat import GPTChat
import sys

# 设置 CSV 字段大小限制（Windows 兼容）
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    # Windows 上使用较小的值
    max_int = int(2**31 - 1)
    csv.field_size_limit(max_int)

class REFORCE:
    def __init__(self, db_path, sql_data, search_directory, prompt_class: Union[Type[BasePromptManager], BasePromptManager], sql_env: Type[SqlEnv]=None, chat_session_pre=None, chat_session=None, log_save_path=None, db_id=None, task=None):
        self.csv_save_name = "result.csv"
        self.sql_save_name = "result.sql"
        self.log_save_name = "log.log"
        self.log_vote_name = "vote.log"
        self.empty_result = "No data found for the specified query.\n"

        self.api = get_api_name(sql_data)
        self.sqlite_path = get_sqlite_path(db_path, sql_data, db_id, task)

        self.sql_id = log_save_path

        self.complete_csv_save_path = os.path.join(search_directory, self.csv_save_name)
        self.complete_sql_save_path = os.path.join(search_directory, self.sql_save_name)
        self.complete_log_save_path = os.path.join(search_directory, self.log_save_name)
        self.complete_vote_log_path = os.path.join(search_directory, self.log_vote_name)

        self.prompt_class = prompt_class
        self.max_try = 3
        self.csv_max_len = 500

        self.sql_env = sql_env
        self.chat_session_pre = chat_session_pre
        self.chat_session = chat_session


    def execute_sqls(self, sqls, logger):
        result_dic_list = []
        error_rec = []
        while sqls:
            if len(result_dic_list) > 10 or len(self.chat_session_pre.messages) > 20:
                break
            result_dic = {}
            sql = sqls[0]
            sqls = sqls[1:]
            logger.info("[Try to execute]\n" + sql + "\n[Try to execute]")
            results = self.sql_env.execute_sql_api(sql, self.sql_id, api=self.api, max_len=self.csv_max_len, sqlite_path=self.sqlite_path)

            if isinstance(results, str) and results != self.empty_result:
                result_dic['sql'] = sql
                result_dic['res'] = results
                self.chat_session_pre.messages[-1]["content"] += f"\nSuccessfully executed. \nResults:\n{results}"
                logger.info("[Successfully executed]\n" +  f"Successfully executed. SQL:\n{sql}\nResults:\n{results}" + "\n[Successfully executed]")
                result_dic_list.append(result_dic)
            else:
                logger.info("[Error occurred]\n" + str(results) + "\n[Error occurred]")
                max_try = self.max_try
                simplify = False
                corrected_sql = None
                while not isinstance(results, str) or results == self.empty_result:
                    error_rec.append(0)
                    if max_try == 0:
                        break
                    if results == self.empty_result:
                        simplify = True
                    corrected_sql = self.self_correct(sql, results, logger, simplify=simplify)
                    if not isinstance(corrected_sql, list) or len(corrected_sql) < 1:
                        print(f"{self.sql_id}: Not a valid SQL: {corrected_sql}")
                        continue
                    corrected_sql = max(corrected_sql, key=len)
                    results = self.sql_env.execute_sql_api(corrected_sql, self.sql_id, api=self.api, max_len=self.csv_max_len, sqlite_path=self.sqlite_path)
                    logger.info("[Results for corrected sql]\n"+str(results)+"\n[Results for corrected sql]")
                    max_try -= 1
                    simplify = False

                if isinstance(results, str) and results != self.empty_result:
                    error_rec.append(1)
                    if sqls != []:
                        response = self.chat_session_pre.get_model_response(self.prompt_class.get_exploration_refine_prompt(sql, corrected_sql, sqls, results), "sql")

                        if isinstance(response, list) and response != []:
                            response_sqls = []
                            for s in response:
                                try:
                                    queries = split_sql(s)
                                    response_sqls += queries
                                except:
                                    pass
                            if len(response_sqls) >= len(sqls) // 2:
                                sqls = response_sqls
                                logger.info("[Corrected other sqls]\n"+self.chat_session_pre.messages[-1]['content']+"\n[Corrected other sqls]")
                else:
                    error_rec.append(0)
                    # Many times error, return
                    if len(error_rec) > 3 and sum(error_rec[-3:]) == 0:
                        return result_dic_list
                    continue
                if not corrected_sql:
                    continue
                result_dic['sql'] = corrected_sql
                result_dic['res'] = results
                self.chat_session_pre.messages[-1]["content"] += f"\nSuccessfully executed. \nResults:\n{results}"
                logger.info("[Successfully corrected]\n" +  f"Successfully executed. SQL:\n{sql}\nResults:\n{results}" + "\n[Successfully corrected]")
        return result_dic_list

    def self_correct(self, sql, error, logger, simplify=False):
        prompt = self.prompt_class.get_exploration_self_correct_prompt(sql, error)
        if simplify:
            prompt += "Since the output is empty, please simplify some conditions of the past sql.\n"
        response = self.chat_session_pre.get_model_response(prompt, "sql")

        max_try = self.max_try
        while max_try > 0 and (not isinstance(response, str) or len(response) > 1):
            response = self.chat_session_pre.get_model_response("Please generate only one SQL with thinking process.", "sql")
            max_try -= 1
        logger.info("[Corrected SQL]\n" + self.chat_session_pre.messages[-1]['content'] + "\n[Corrected SQL]")
        return response

    def format_answer(self, task, chat_session):
        format_prompt = self.prompt_class.get_format_prompt()
        response_csv = chat_session.get_model_response("Task: " + task + format_prompt, "csv")
        response_csv = "```csv\n"+response_csv[0].split("\n")[0]+"\n```"
        return response_csv

    def exploration(self, task, table_struct, table_info, logger):
        pre_info = ''
        
        # ✨ 使用 System/User 分离模式
        # System Prompt (只设置一次)
        system_prompt = self.prompt_class.get_exploration_system_prompt(api=self.api)
        self.chat_session_pre.set_system_prompt(system_prompt)
        
        # User Prompt
        user_prompt = self.prompt_class.get_exploration_user_prompt(
            table_info=table_info,
            question=task,
            table_struct=table_struct
        )
        
        max_try = self.max_try
        while max_try > 0:
            response_pre = self.chat_session_pre.get_model_response(user_prompt, "sql")
            response_pre_txt = self.chat_session_pre.messages[-1]['content']
            logger.info("[Exploration]\n" + response_pre_txt + "\n[Exploration]")
            if not isinstance(response_pre, list):
                max_try -= 1
                continue
            
            if len(response_pre) == 1:
                response_pre = split_sql(response_pre[0])
            if len(response_pre) < 3:
                max_try -= 1
                print(f"{self.sql_id}: Few sqls, retry preparation.")
                continue
            results_pre_dic_list = self.execute_sqls(response_pre, logger)
            sql_count = 0
            for dic in results_pre_dic_list:
                pre_info += "Query:\n" + dic['sql'] + "\nAnswer:\n" + str(dic['res'])
                if isinstance(dic['res'], str):
                    sql_count += 1

            if sql_count == 0:
                print(f"{self.sql_id}: sql_count: {sql_count}, len(response_pre): {len(response_pre)}. Inadequate preparation, break.")
                max_try = 0
                break

            if len(pre_info) < 1e5:
                break
            print(f"{self.sql_id}: Too long, retry preparation.")
            pre_info = ''
            max_try -= 1

        return pre_info, response_pre_txt, max_try

    def self_refine(self, args, logger, question, format_csv, table_struct, table_info, response_pre_txt, pre_info, csv_save_path, sql_save_path, task=None):
        itercount = 0
        # ===== 已注释:不再需要稳定性验证所需的变量 =====
        # results_values = []
        # results_tables = []
        # ===== 注释结束 =====

        # ✨ 使用 System/User 分离模式
        # System Prompt (只设置一次，可复用)
        system_prompt = self.prompt_class.get_self_refine_system_prompt(
            api=self.api, 
            table_struct=table_struct
        )
        self.chat_session.set_system_prompt(system_prompt)
        logger.info("[Self_refine System Prompt]\n" + system_prompt + "\n[Self_refine System Prompt]")
        
        # User Prompt (每次迭代可能不同)
        user_prompt = self.prompt_class.get_self_refine_user_prompt(
            table_info=table_info,
            question=question,
            pre_info=pre_info,
            format_csv=format_csv,
            table_struct=table_struct
        )

        error_rec = []
        while itercount < args.max_iter:
            logger.info(f"itercount: {itercount}")
            logger.info("[Self_refine User Prompt]\n" + user_prompt + "\n[Self_refine User Prompt]")
            
            max_try = self.max_try
            while max_try > 0:
                response = self.chat_session.get_model_response(user_prompt, "sql")
                if not isinstance(response, list) or len(response) != 1:
                    user_prompt = "Please output one SQL only."
                else:
                    break
                max_try -= 1
            if not isinstance(response, list) or response == []:
                if os.path.exists(csv_save_path):
                    os.remove(csv_save_path)
                print(f"{self.sql_id}: Error when generating final SQL.")
                break
            logger.info("[Try to run SQL in self-refine]\n" +self.chat_session.messages[-1]['content'] + "\n[Try to run SQL in self-refine]")
            response = response[0]
            executed_result = self.sql_env.execute_sql_api(response, self.sql_id, csv_save_path, api=self.api, sqlite_path=self.sqlite_path)
            error_rec.append(str(executed_result))
            if args.early_stop and len(error_rec) > 3:
                # Eraly stop for repeatitive empty results
                if len(set(error_rec[-4:])) == 1 and error_rec[-1] == self.empty_result:
                    logger.info("No data found for the specified query, remove file.")                    
                    if os.path.exists(csv_save_path):
                        os.remove(csv_save_path)
                    break
            
            if executed_result == '0' or isinstance(executed_result, dict) is not True:
                if not args.do_self_consistency:
                    with open(sql_save_path, "w") as f:
                        f.write(response)
                        break                    
                self_consistency_prompt = self.prompt_class.get_self_consistency_prompt(question, format_csv)
                with open(csv_save_path) as f:
                    csv_data = f.readlines()
                    csv_data_str = ''.join(csv_data)
                logger.info(f"[Executed results in self-refine]\n{hard_cut(csv_data_str, self.csv_max_len)}\n[Executed results in self-refine]")
                self_consistency_prompt += "Current snswer: \n" + hard_cut(csv_data_str, self.csv_max_len)
                self_consistency_prompt += f"Current sql:\n{response}"
                if '"""' in csv_data_str:
                    self_consistency_prompt += 'Please remove """ in results. Use CAST: CAST(column_name AS STRING).\n'

                # Filter results with null columns
                csv_buffer = StringIO(csv_data_str)
                df_csv = pd.read_csv(csv_buffer).fillna("")

                # ===== 原有代码(已注释):使用 results_values 进行稳定性验证 =====
                # nested_val = [(item) for i, row in enumerate(df_csv.values.tolist()) for j, item in enumerate(row) if isinstance(item, str) and '\n' in item in item]
                # df_csv_copy = df_csv.copy()
                # for col in df_csv.select_dtypes(include=['float']):
                #     df_csv_copy[col] = df_csv[col].round(2)
                # sort_col = df_csv_copy.columns[0]
                # df_csv_copy_sorted = df_csv_copy[sort_col].astype(str)
                # csv_data_str_round2 = df_csv_copy_sorted.to_string()
                # df_csv_str = df_csv.astype(str)
                # if get_values_from_table(csv_data_str_round2) not in results_values:
                #     if nested_val:
                #         self_consistency_prompt += f"Values {nested_val} are nested. Please correct them. e.g. Transfer '[\nA,\n B\n]' to 'A, B'.\n"
                #     elif not ((df_csv_str == "0") | (df_csv_str == "")).all().any():
                #             results_values.append(get_values_from_table(csv_data_str_round2))
                #             results_tables.append(csv_data_str)
                #     else:
                #         empty_columns = df_csv_str.columns[((df_csv_str == "0") | (df_csv_str == "")).all()].to_list()
                #         self_consistency_prompt += f"Empty results in Column {empty_columns}. Please correct them.\n"
                # else:
                #     # self-consistency
                #     logger.info(f"[Consistent results]\n{hard_cut(csv_data_str, 500)}\n[Consistent results]")
                #     with open(sql_save_path, "w") as f:
                #         f.write(response)
                #     break
                # ===== 原有代码结束 =====

                # ===== 新逻辑:仅过滤错误结果,不验证稳定性 =====
                # 修改目的:去除 results_values 稳定性检查,只要结果无明显错误就保存SQL并终止迭代
                
                # 1. 检查嵌套值错误(字符串中包含换行符)
                nested_val = [(item) for i, row in enumerate(df_csv.values.tolist()) 
                              for j, item in enumerate(row) 
                              if isinstance(item, str) and '\n' in item]
                
                # 2. 检查空列错误
                df_csv_str = df_csv.astype(str)
                has_empty_columns = ((df_csv_str == "0") | (df_csv_str == "")).all().any()
                
                # 3. 判断是否有错误需要修正
                has_errors = False
                
                if nested_val:
                    # 存在嵌套值,需要修正
                    self_consistency_prompt += f"Values {nested_val} are nested. Please correct them. e.g. Transfer '[\\nA,\\n B\\n]' to 'A, B'.\\n"
                    has_errors = True
                
                if has_empty_columns:
                    # 存在空列,需要修正
                    empty_columns = df_csv_str.columns[((df_csv_str == "0") | (df_csv_str == "")).all()].to_list()
                    self_consistency_prompt += f"Empty results in Column {empty_columns}. Please correct them.\\n"
                    has_errors = True
                
                # 4. 如果没有错误,直接保存SQL并终止迭代
                if not has_errors:
                    logger.info(f"[Valid results - no errors detected]\\n{hard_cut(csv_data_str, 500)}\\n[Valid results]")
                    with open(sql_save_path, "w") as f:
                        f.write(response)
                    break
                # 5. 如果有错误,继续迭代让LLM修正
                # (self_consistency_prompt 已在上面添加错误提示)
                # ===== 新逻辑结束 =====
                
                if any(keyword in response for keyword in self.prompt_class.get_condition_onmit_tables()):
                    self_consistency_prompt += self.prompt_class.get_prompt_dialect_list_all_tables(table_struct, self.api)
                if args.save_all_results:
                    save_path = save_path[:-4] + str(itercount) + save_path[-4:]
                self_refine_prompt = self_consistency_prompt
            
            else:
                self_refine_prompt = f"The error information is:\n" + str(executed_result) + "\nPlease correct it and output only 1 complete SQL query."

            itercount += 1

        logger.info(f"Total iteration counts: {itercount}")
        if itercount == args.max_iter and not args.save_all_results:
            if os.path.exists(csv_save_path):
                os.remove(csv_save_path)
            logger.info("Max Iter, remove file")
        print(f"{self.sql_id}: chat_session len: {self.chat_session.get_message_len()}")

    def gen(self, args, logger, question, format_csv, table_struct, table_info, response_pre_txt, pre_info, csv_save_path, sql_save_path, task=None):
        gen_prompt = self.prompt_class.get_self_refine_prompt(table_info, task, pre_info, question, self.api, format_csv, table_struct, args.omnisql_format_pth)
        logger.info("[Gen]\n" + gen_prompt + "\n[Gen]")
        max_try = self.max_try
        while max_try > 0:
            response = self.chat_session.get_model_response(gen_prompt, "sql")
            if not isinstance(response, list) or len(response) != 1:
                gen_prompt = "Please output one SQL only."
            else:
                break
            max_try -= 1
        if not isinstance(response, list) or response == []:
            if os.path.exists(csv_save_path):
                os.remove(csv_save_path)
            print(f"{self.sql_id}: Error when generating final SQL.")
        logger.info("[Gen SQL]\n" +self.chat_session.messages[-1]['content'] + "\n[Gen SQL]")
        response = response[0]
        executed_result = self.sql_env.execute_sql_api(response, self.sql_id, csv_save_path, api=self.api, sqlite_path=self.sqlite_path)
        if executed_result == '0':
            with open(sql_save_path, "w") as f:
                f.write(response)

    def model_vote(self, result, sql_paths, search_directory, args, table_info, task, knowledge=None):
        # 检查 result 是否为空
        if not result or not result.values():
            print(f"[WARNING] {search_directory}: No valid results for voting, skipping model_vote")
            return
        
        chat_session = GPTChat(args.azure, args.model_vote)
        max_value = max(result.values())
        max_dict = {k: v for k, v in result.items() if v == max_value}
        # print(max_dict)

        prompt = f"You are given DB info, task and candidate SQLs and their results. You should choose the most correct one based on database info:\n{table_info}. \n\nThe task is: {task}. \n"
        
        # 添加领域知识到prompt
        if knowledge:
            prompt += f"\n**Important Domain Knowledge:**\n{knowledge}\n\n"
            prompt += "Please strictly follow the domain knowledge rules when evaluating the SQL queries.\n\n"
        
        prompt += "Here are some candidate sqls and answers: \n"
        for sql, counts in max_dict.items():
            sql_path = os.path.join(search_directory, sql)
            csv_path = os.path.join(search_directory, sql_paths[sql])

            if os.path.exists(sql_path) and os.path.exists(csv_path):
                prompt += "SQL file name: " + sql + "\n"
                with open(sql_path) as f:
                    prompt += f.read()
                prompt += "CSV file name: " + sql_paths[sql] + "\n"
                with open(csv_path) as f:
                    prompt += hard_cut(f.read(), 5000)

        max_try = 3
        prompt += "Compare the SQL and results of each answer, think step by step and choose one SQL as the correct answer. Output thinking process and the name of sql in ```plaintext\nxxx.sql``` format. You should not ingnore 'plaintext'.\n"
        prompt += "For results with null or zero values, they tend to be wrong answer.\n"
        prompt += "You reasoning step should be: 1. Exclude unreasonable results. 2. Check results if aligning with task description. 3. Analyze SQL if aligning with task description.\n"
        response = chat_session.get_model_response(prompt, "plaintext")
        while max_try > 0:
            if not response or not isinstance(response, list) or ".sql" not in response[0]:
                print(f"{search_directory}, remained max_try for voting: {max_try}, {response}")
                response = chat_session.get_model_response("Please output the name of sql in ```plaintext\nxxx.sql``` format. You should not ingnore 'plaintext'.", "plaintext")
            else:
                break
            max_try -= 1
        if max_try == 0:
            print(f"{search_directory} Empty")
            return
        
        # 🔧 处理模型返回的文件名（可能不完整）
        selected_filename = response[0].strip()
        selected_sql_path = os.path.join(search_directory, selected_filename)
        
        # 如果文件不存在，尝试查找匹配的文件
        if not os.path.exists(selected_sql_path):
            # 尝试添加 _result 后缀
            if not selected_filename.endswith('_result.sql'):
                alternative_filename = selected_filename.replace('.sql', '_result.sql')
                alternative_path = os.path.join(search_directory, alternative_filename)
                if os.path.exists(alternative_path):
                    selected_sql_path = alternative_path
                    print(f"[Vote] Adjusted filename: {selected_filename} -> {alternative_filename}")
                else:
                    print(f"[Vote ERROR] Cannot find SQL file: {selected_filename} or {alternative_filename}")
                    return
            else:
                print(f"[Vote ERROR] Cannot find SQL file: {selected_filename}")
                return
        
        with open(selected_sql_path) as f:
            selected_sql = f.read()
        sql_env = SqlEnv()
        if sql_env.execute_sql_api(selected_sql, self.sql_id, self.complete_csv_save_path, api=self.api, sqlite_path=self.sqlite_path) == '0':
            with open(self.complete_sql_save_path, "w") as f:
                f.write(selected_sql)
            with open(self.complete_vote_log_path, "w") as f:
                f.write("[Vote]\n"+prompt+"\n[Vote]")
                f.write(chat_session.messages[-1]['content'])
        sql_env.close_db()

    def vote_result(self, search_directory, args, sql_paths, table_info, task, knowledge=None):
        # filter answer
        result = {}
        result_name = {}
        result_all = {}
        all_values = []
        for v in sql_paths.values():
            if os.path.exists(os.path.join(search_directory, v)):
                all_values.append(os.path.join(search_directory, v))

        if len(all_values) > 1:
            for key, value in sql_paths.items():
                complete_value = os.path.join(search_directory, value)
                if os.path.exists(complete_value):
                    same_ans = 0
                    for v in all_values:
                        v_df = pd.read_csv(v)
                        c_df = pd.read_csv(complete_value)
                        if v != complete_value and is_valid_result(v_df, args.do_column_exploration) and compare_pandas_table(v_df, c_df, ignore_order=True) and v_df.shape == c_df.shape:
                            same_ans += 1
                            result_name[v] = result_name.get(v, []) + [complete_value]
                        # print(result)
                    result_all[key] = same_ans
            result_name = filter_bijection_like_dict(result_name)
            for key, value in result_name.items():
                # 使用 os.path.basename 替代 split("/")，兼容 Windows 路径
                result[os.path.basename(key).replace(".csv", ".sql")] = len(value)
        if not result:
            if not result_all and not all_values:
                print(f"{search_directory} empty results")
                return
            elif args.model_vote:
                # 检查 result_all 是否有有效数据
                if not result_all:
                    print(f"[WARNING] {search_directory}: result_all is empty, cannot perform model_vote")
                    # 如果有all_values但result_all为空,尝试使用final_choose逻辑
                    if all_values and args.final_choose:
                        csv_pth = all_values[0]
                        print(f"[INFO] Using final_choose with single candidate: {csv_pth}")
                        os.makedirs(os.path.dirname(self.complete_sql_save_path), exist_ok=True)
                        shutil.copy2(csv_pth.replace(".csv", ".sql"), self.complete_sql_save_path)
                        shutil.copy2(csv_pth, self.complete_csv_save_path)
                        
                        # 🔧 正确生成log文件路径
                        log_pth = csv_pth.replace("_result.csv", "_log.log").replace("result.csv", "log.log")
                        if os.path.exists(log_pth):
                            shutil.copy2(log_pth, self.complete_log_save_path)
                        else:
                            print(f"[WARNING] Log file not found: {log_pth}")
                        print(f"[SUCCESS] Generated result files from single candidate")
                    else:
                        print(f"[ERROR] Cannot use final_choose: all_values={len(all_values) if all_values else 0}, final_choose={args.final_choose}")
                    return
                
                assert all(v == 0 for k, v in result_all.items()), result
                result_all = {k: v + 1 for k, v in result_all.items()}
                # print(result_all)
                self.model_vote(result_all, sql_paths, search_directory, args, table_info, task, knowledge=knowledge)
            elif args.final_choose:
                csv_pth = all_values[0]
                # 确保目标目录存在
                os.makedirs(os.path.dirname(self.complete_sql_save_path), exist_ok=True)
                shutil.copy2(csv_pth.replace(".csv", ".sql"), self.complete_sql_save_path)
                shutil.copy2(csv_pth, self.complete_csv_save_path)
                
                # 🔧 正确生成log文件路径
                log_pth = csv_pth.replace("_result.csv", "_log.log").replace("result.csv", "log.log")
                if os.path.exists(log_pth):
                    shutil.copy2(log_pth, self.complete_log_save_path)
                else:
                    print(f"[WARNING] Log file not found: {log_pth}")               
            else:
                print(f"{search_directory} Empty, return")
            return

        sorted_dict = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
        
        # 再次检查以防万一
        if not sorted_dict:
            print(f"[WARNING] {search_directory}: sorted_dict is empty after filtering")
            return
        
        first_key = next(iter(sorted_dict))

        vote_counts = list(sorted_dict.values())
        if not vote_counts:
            print(f"[WARNING] {search_directory}: vote_counts is empty")
            return
        
        max_vote = max(vote_counts)
        num_with_max_vote = vote_counts.count(max_vote)
        has_tie = num_with_max_vote > (max_vote + 1)
        if has_tie:
            assert num_with_max_vote % (max_vote + 1) == 0, result_name
            if args.model_vote:
                self.model_vote(result, sql_paths, search_directory, args, table_info, task, knowledge=knowledge)
                return
            if not args.random_vote_for_tie:
                print(f"{search_directory} has_tie {sorted_dict}, return")
                return

        # 确保目标目录存在
        target_dir = os.path.dirname(self.complete_sql_save_path)
        if target_dir:  # 只有当目录路径非空时才创建
            os.makedirs(target_dir, exist_ok=True)
        
        # 构建源文件路径并规范化
        src_sql = os.path.normpath(os.path.join(search_directory, first_key))
        src_csv = os.path.normpath(os.path.join(search_directory, sql_paths[first_key]))
        
        # ✨ 智能构造LOG路径：处理不同文件名模式
        # 例如: "decompose_0_result.sql" → "decompose_0_result.log"
        #      "result.sql" → "log.log"
        if first_key == self.sql_save_name:
            # 标准模式: result.sql → log.log
            log_filename = self.log_save_name
        else:
            # 自定义模式: xxx_result.sql → xxx_result.log
            log_filename = first_key.replace('.sql', '.log')
        
        src_log = os.path.normpath(os.path.join(search_directory, log_filename))
        
        # 规范化目标路径
        dst_sql = os.path.normpath(self.complete_sql_save_path)
        dst_csv = os.path.normpath(self.complete_csv_save_path)
        dst_log = os.path.normpath(self.complete_log_save_path)
        
        # 调试信息
        print(f"[投票] 复制获胜文件:")
        print(f"  获胜: {first_key}")
        print(f"  源SQL: {src_sql}")
        print(f"    存在: {os.path.exists(src_sql)}")
        print(f"  目标SQL: {dst_sql}")
        print(f"    目标目录: {os.path.dirname(dst_sql)}")
        print(f"    目标目录存在: {os.path.exists(os.path.dirname(dst_sql))}")
        
        # 检查源文件是否存在（LOG文件可选）
        if not os.path.exists(src_sql):
            raise FileNotFoundError(f"源SQL文件不存在: {src_sql}")
        if not os.path.exists(src_csv):
            raise FileNotFoundError(f"源CSV文件不存在: {src_csv}")
        
        # ✨ LOG文件检查：如果不存在则警告但不中断
        if not os.path.exists(src_log):
            print(f"  ⚠️  警告: 源LOG文件不存在: {src_log}，将跳过LOG文件复制")
            src_log = None
        
        # 执行复制
        shutil.copy2(src_sql, dst_sql)
        shutil.copy2(src_csv, dst_csv)
        
        # ✨ 只有当LOG文件存在时才复制
        if src_log:
            shutil.copy2(src_log, dst_log)
        
        print(f"  ✓ 投票完成，结果已保存")
    def process_sub_question_sql(self, sub_sql: str, sub_question: str, sub_id: int, 
                                 args, logger, table_info: str, search_directory: str,
                                 task: str = None) -> tuple:
        """
        处理单个子问题的SQL (应用self-refinement和self-consistency)
        
        Args:
            sub_sql: 子问题的初始SQL
            sub_question: 子问题文本
            sub_id: 子问题ID
            args: 命令行参数
            logger: 日志记录器
            table_info: Schema信息
            search_directory: 输出目录
            task: 任务名称
        
        Returns:
            (refined_sql, csv_path): 优化后的SQL和结果CSV路径
        """
        logger.info(f"[Sub-SQL {sub_id}] Processing sub-question: {sub_question}")
        
        # 创建子问题专用目录
        sub_dir = os.path.join(search_directory, f"sub_{sub_id}")
        os.makedirs(sub_dir, exist_ok=True)
        
        csv_save_path = os.path.join(sub_dir, "result.csv")
        sql_save_path = os.path.join(sub_dir, "result.sql")
        
        # 如果启用self-refinement
        if args.do_self_refinement:
            logger.info(f"[Sub-SQL {sub_id}] Applying self-refinement")
            
            # ✨ 创建args副本，使用独立的迭代次数
            # 目的：子问题通常比主问题简单，使用更少的迭代次数以提高效率
            import copy
            sub_args = copy.copy(args)
            
            # 如果指定了sub_question_max_iter，使用它；否则使用主问题的max_iter
            if hasattr(args, 'sub_question_max_iter') and args.sub_question_max_iter is not None:
                sub_args.max_iter = args.sub_question_max_iter
                logger.info(f"[Sub-SQL {sub_id}] Using sub_question_max_iter={args.sub_question_max_iter}")
            else:
                logger.info(f"[Sub-SQL {sub_id}] Using default max_iter={args.max_iter}")
            
            # 使用self_refine方法处理
            self.self_refine(
                args=sub_args,  # 使用修改后的args
                logger=logger,
                question=sub_question,
                format_csv=None,
                table_struct="",
                table_info=table_info,
                response_pre_txt="",  # 子问题不需要exploration
                pre_info="",
                csv_save_path=csv_save_path,
                sql_save_path=sql_save_path,
                task=task
            )
            
            # 读取refined SQL
            if os.path.exists(sql_save_path):
                with open(sql_save_path, 'r', encoding='utf-8') as f:
                    refined_sql = f.read()
            else:
                refined_sql = sub_sql
        else:
            # 直接执行SQL
            logger.info(f"[Sub-SQL {sub_id}] Executing SQL directly")
            results = self.sql_env.execute_sql_api(
                sub_sql, 
                f"sub_{sub_id}", 
                csv_save_path,
                api=self.api, 
                max_len=self.csv_max_len,
                sqlite_path=self.sqlite_path
            )
            
            # 保存结果
            if results == '0':
                with open(sql_save_path, 'w', encoding='utf-8') as f:
                    f.write(sub_sql)
                refined_sql = sub_sql
            else:
                logger.error(f"[Sub-SQL {sub_id}] Execution failed: {results}")
                refined_sql = sub_sql
        
        logger.info(f"[Sub-SQL {sub_id}] Processing complete")
        logger.info(f"[Sub-SQL {sub_id}] Refined SQL:\n{refined_sql}")
        
        return refined_sql, csv_save_path
    
    # ===== ✨ SQL合并（Scaler）功能 =====
    # 修改目的：将scaler_starrocks.py的功能合并到agent.py统一管理
    
    # StarRocks版SQL合并模板
    SCALE_TEMPLATE_STARROCKS = '''You are an expert StarRocks SQL developer. Your task is to synthesize multiple sub-question SQLs into a single comprehensive SQL query that answers the original question.

【Database Schema】
{schema}

【Schema Links (Critical Tables & Columns)】
{schema_links}

【Original Question】
{question}

【Evidence/Knowledge】
{evidence}

【Few-shot Examples from Column Exploration】
{few_shot_examples}

【Sub-questions and their SQLs】
{sub_questions_sqls}

【Instructions】
1. **Analyze Dependencies**: Understand how sub-questions build upon each other
2. **Identify Patterns**: Look for common filters, joins, and aggregations
3. **Synthesize Query**: Combine sub-question logic into ONE final SQL
4. **Optimize**: Remove redundant subqueries when possible
5. **Validate**: Ensure the final SQL answers the original question completely

【StarRocks Specific Rules】
- NULL Handling: Always use COALESCE() for SUM/AVG to avoid NULL results
- Distinct Counts: Use COUNT(DISTINCT column) for user/player counting


【Output Format】
Please think step by step and generate ONE complete SQL query that answers the original question.
Output the SQL in ```sql
``` format without any additional explanation outside the code block.

Final SQL:
'''

    FALLBACK_TEMPLATE = '''You are an expert StarRocks SQL developer.

Question: {question}

Database Schema:
{schema}

Evidence: {evidence}

Please generate a valid StarRocks SQL query that answers this question.
Output only the SQL statement in ```sql
``` format:
'''
    
    def format_sub_questions(self, qa_pairs: list) -> str:
        """
        格式化子问题和SQL为Prompt输入
        
        Args:
            qa_pairs: [(sub_question, sub_sql), ...]
        
        Returns:
            格式化的字符串
        """
        formatted = []
        for i, (q, sql) in enumerate(qa_pairs, 1):
            formatted.append(f"Sub-question {i}: {q}")
            formatted.append(f"SQL for sub-question {i}:")
            formatted.append(f"```sql\n{sql}\n```")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def scale_sql(
        self,
        question: str,
        schema: str,
        qa_pairs: list,
        evidence: str = "",
        schema_links: str = "",
        few_shot_examples: str = "",
        use_fallback: bool = False,
        chat_session: GPTChat = None,
        logger=None
    ) -> str:
        """
        执行SQL合并（将子问题SQL合并为最终SQL）
        
        Args:
            question: 原始问题
            schema: 数据库Schema
            qa_pairs: 子问题和SQL对 [(sub_q, sub_sql), ...]
            evidence: 领域知识
            schema_links: Schema Linking结果
            few_shot_examples: 列探索的Few-shot示例
            use_fallback: 是否使用简化模板
            chat_session: GPT会话（如果不提供则使用self.chat_session）
            logger: 日志记录器
        
        Returns:
            合并后的最终SQL
        """
        if logger:
            logger.info(f"[Scaler] Starting SQL scaling with {len(qa_pairs)} sub-questions")
        
        # 如果没有子问题,使用fallback模式
        if not qa_pairs:
            use_fallback = True
        
        # 使用提供的chat_session或默认的
        session = chat_session if chat_session else self.chat_session
        
        if use_fallback:
            prompt = self.FALLBACK_TEMPLATE.format(
                question=question,
                schema=schema,
                evidence=evidence if evidence else "No specific evidence"
            )
        else:
            # 格式化子问题
            sub_questions_sqls = self.format_sub_questions(qa_pairs)
            
            # 构建完整Prompt
            prompt = self.SCALE_TEMPLATE_STARROCKS.format(
                schema=schema,
                schema_links=schema_links if schema_links else "Not provided",
                question=question,
                evidence=evidence if evidence else "No specific evidence provided",
                few_shot_examples=few_shot_examples if few_shot_examples else "No examples available",
                sub_questions_sqls=sub_questions_sqls
            )
        
        # 调用LLM
        response = session.get_model_response(prompt, "sql")
        
        # 解析SQL
        final_sql = self._extract_sql_from_response(response)
        
        if logger:
            logger.info(f"[Scaler] Generated final SQL:\n{final_sql}")
        
        return final_sql
    
    def _extract_sql_from_response(self, response) -> str:
        """
        从LLM响应中提取SQL
        
        Args:
            response: LLM响应(可能是str或list)
        
        Returns:
            提取的SQL语句
        """
        import re
        
        # 处理不同响应格式
        if isinstance(response, list):
            if len(response) == 0:
                return ""
            response_text = response[0] if isinstance(response[0], str) else str(response)
        elif isinstance(response, str):
            response_text = response
        else:
            response_text = str(response)
        
        # 提取SQL代码块
        sql_match = re.search(r'```sql(.*?)```', response_text, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # 如果没有代码块标记,尝试查找SELECT语句
            lines = response_text.split('\n')
            select_found = False
            sql_lines = []
            
            for line in lines:
                if line.strip().upper().startswith('SELECT'):
                    select_found = True
                
                if select_found:
                    sql_lines.append(line)
                    # 如果遇到分号,停止
                    if ';' in line:
                        break
            
            if sql_lines:
                sql = '\n'.join(sql_lines).strip()
            else:
                sql = response_text.strip()
        
        # 清理SQL
        sql = sql.strip()
        
        # 移除可能的Markdown标记
        if sql.startswith('```'):
            sql = sql[3:].strip()
        if sql.endswith('```'):
            sql = sql[:-3].strip()
        
        # 确保有分号结尾
        if sql and not sql.endswith(';'):
            sql += ';'
        
        return sql
    
    def generate_multiple_sql_candidates(
        self,
        question: str,
        schema: str,
        qa_pairs: list,
        evidence: str = "",
        schema_links: str = "",
        few_shot_examples: str = "",
        num_candidates: int = 3,
        chat_session: GPTChat = None,
        logger=None
    ) -> list:
        """
        生成多个SQL候选(用于投票机制)
        
        Args:
            question: 原始问题
            schema: 数据库Schema
            qa_pairs: 子问题和SQL对
            evidence: 领域知识
            schema_links: Schema Linking结果
            few_shot_examples: Few-shot示例
            num_candidates: 候选数量
            chat_session: GPT会话（如果不提供则使用self.chat_session）
            logger: 日志记录器
        
        Returns:
            SQL候选列表
        """
        candidates = []
        
        for i in range(num_candidates):
            # 使用不同策略生成
            use_fallback = (i % 3 == 2)  # 每3个中有1个使用fallback
            
            sql = self.scale_sql(
                question=question,
                schema=schema,
                qa_pairs=qa_pairs,
                evidence=evidence,
                schema_links=schema_links,
                few_shot_examples=few_shot_examples,
                use_fallback=use_fallback,
                chat_session=chat_session,
                logger=logger
            )
            
            if sql:
                candidates.append(sql)
        
        # 去重
        candidates = list(dict.fromkeys(candidates))
        
        if logger:
            logger.info(f"[Scaler] Generated {len(candidates)} unique SQL candidates")
        
        return candidates
    
    def refine_final_sql(
        self,
        initial_sql: str,
        question: str,
        schema: str,
        evidence: str = "",
        schema_links: str = "",
        max_iter: int = 3,
        sql_id: str = "final",
        csv_save_path: str = None,
        sql_save_path: str = None,
        table_struct: str = "",
        chat_session: GPTChat = None,
        logger=None
    ) -> str:
        """
        对最终合并SQL进行self-refinement迭代优化（仿照self_refine的逻辑）
        
        Args:
            initial_sql: 初始合并SQL
            question: 原始问题
            schema: 数据库Schema
            evidence: 领域知识
            schema_links: Schema Linking结果
            max_iter: 最大迭代次数
            sql_id: SQL标识符
            csv_save_path: CSV保存路径
            sql_save_path: SQL保存路径
            table_struct: 表结构信息
            chat_session: GPT会话（如果不提供则使用self.chat_session）
            logger: 日志记录器
        
        Returns:
            优化后的SQL
        """
        if logger:
            logger.info(f"[Scaler-Refine] Starting refinement with max_iter={max_iter}")
        
        # 使用提供的chat_session或默认的
        session = chat_session if chat_session else self.chat_session
        
        itercount = 0
        error_rec = []
        
        # ✨ 使用BasePromptManager获取System Prompt
        system_prompt = self.prompt_class.get_self_refine_system_prompt(
            api=self.api, 
            table_struct=table_struct
        )
        
        # 设置系统提示
        session.set_system_prompt(system_prompt)
        if logger:
            logger.info("[Scaler-Refine System Prompt]\n" + system_prompt + "\n[Scaler-Refine System Prompt]")
        
        # ✨ 使用BasePromptManager获取User Prompt
        # 构建包含Schema Links和Evidence的table_info
        table_info_with_context = schema
        if schema_links:
            table_info_with_context += f"\n\n【Schema Links】\n{schema_links}"
        if evidence:
            table_info_with_context += f"\n\n【Evidence/Knowledge】\n{evidence}"
        
        # 初始User Prompt: 使用 pre_info 字段传递初始SQL
        pre_info = f"""Initial merged SQL:
```sql
{initial_sql}
```

Please refine this SQL if needed based on execution feedback."""
        
        user_prompt = self.prompt_class.get_self_refine_user_prompt(
            table_info=table_info_with_context,
            question=question,
            pre_info=pre_info,
            format_csv=None,  # Scaler阶段不需要format_csv
            table_struct=table_struct
        )
        
        current_sql = initial_sql
        
        # ✨ 迭代refinement循环
        while itercount < max_iter:
            if logger:
                logger.info(f"[Scaler-Refine] Iteration {itercount + 1}/{max_iter}")
                logger.info("[Scaler-Refine User Prompt]\n" + user_prompt + "\n[Scaler-Refine User Prompt]")
            
            # 如果不是第一次迭代，需要从LLM获取refined SQL
            if itercount > 0:
                max_try = 3
                while max_try > 0:
                    response = session.get_model_response(user_prompt, "sql")
                    if not isinstance(response, list) or len(response) != 1:
                        user_prompt = "Please output one SQL only."
                    else:
                        break
                    max_try -= 1
                
                if not isinstance(response, list) or response == []:
                    if logger:
                        logger.error(f"[Scaler-Refine] Error when generating refined SQL")
                    if csv_save_path and os.path.exists(csv_save_path):
                        os.remove(csv_save_path)
                    break
                
                current_sql = response[0]
                if logger:
                    logger.info("[Scaler-Refine Try SQL]\n" + session.messages[-1]['content'] + "\n[Scaler-Refine Try SQL]")
            
            # ✨ 执行当前SQL
            executed_result = self.sql_env.execute_sql_api(
                current_sql, 
                f"{sql_id}_refine_{itercount}",
                csv_save_path,
                api=self.api,
                sqlite_path=self.sqlite_path
            )
            
            error_rec.append(str(executed_result))
            
            # ✨ Early stop检查（重复空结果）
            if len(error_rec) > 3:
                if len(set(error_rec[-4:])) == 1 and error_rec[-1] == self.empty_result:
                    if logger:
                        logger.info("[Scaler-Refine] No data found for the specified query, early stop")
                    if csv_save_path and os.path.exists(csv_save_path):
                        os.remove(csv_save_path)
                    break
            
            # ✨ 执行成功的处理逻辑
            if executed_result== '0' or isinstance(executed_result, dict) is not True:
                if logger:
                    logger.info(f"[Scaler-Refine] ✓ SQL executed successfully at iteration {itercount + 1}")
                
                # 读取CSV结果
                if not csv_save_path or not os.path.exists(csv_save_path):
                    # 🔧 CSV文件不存在是异常情况,应该报错而不是直接返回
                    error_msg = "SQL executed successfully but CSV file not generated"
                    if logger:
                        logger.error(f"[Scaler-Refine] ✗ {error_msg}: {csv_save_path}")
                    
                    # 构建错误提示,让LLM重新生成
                    user_prompt = self.prompt_class.get_self_refine_prompt_on_error(
                        f"Internal error: {error_msg}. Please check the SQL and try again.",
                        current_sql,
                        question
                    )
                    itercount += 1
                    continue
                
                with open(csv_save_path, 'r', encoding='utf-8') as f:
                    csv_data = f.readlines()
                    csv_data_str = ''.join(csv_data)
                
                if logger:
                    logger.info(f"[Scaler-Refine Executed results]\n{hard_cut(csv_data_str, self.csv_max_len)}\n[Scaler-Refine Executed results]")
                
                # ✨ 构建self-consistency检查prompt
                self_consistency_prompt = f"""Current answer: 
{hard_cut(csv_data_str, self.csv_max_len)}

Current SQL:
```sql
{current_sql}
```

Please check if the result is correct and complete. """
                
                if '"""' in csv_data_str:
                    self_consistency_prompt += 'Please remove """ in results. Use CAST: CAST(column_name AS STRING).\n'
                
                # ✨ 过滤null列和嵌套值
                csv_buffer = StringIO(csv_data_str)
                df_csv = pd.read_csv(csv_buffer).fillna("")
                
                # 检查嵌套值错误
                nested_val = [(item) for i, row in enumerate(df_csv.values.tolist()) 
                              for j, item in enumerate(row) 
                              if isinstance(item, str) and '\n' in item]
                
                # 检查空列错误
                df_csv_str = df_csv.astype(str)
                has_empty_columns = ((df_csv_str == "0") | (df_csv_str == "")).all().any()
                
                # 判断是否有错误需要修正
                has_errors = False
                
                if nested_val:
                    # 存在嵌套值,需要修正
                    self_consistency_prompt += f"Values {nested_val} are nested. Please correct them. e.g. Transfer '[\\nA,\\n B\\n]' to 'A, B'.\\n"
                    has_errors = True
                
                if has_empty_columns:
                    # 存在空列,需要修正
                    empty_columns = df_csv_str.columns[((df_csv_str == "0") | (df_csv_str == "")).all()].to_list()
                    self_consistency_prompt += f"Empty results in Column {empty_columns}. Please correct them.\\n"
                    has_errors = True
                
                # ✨ 如果没有错误,直接保存SQL并终止迭代
                if not has_errors:
                    if logger:
                        logger.info(f"[Scaler-Refine Valid results - no errors detected]\\n{hard_cut(csv_data_str, 500)}\\n[Scaler-Refine Valid results]")
                    with open(sql_save_path, "w", encoding='utf-8') as f:
                        f.write(current_sql)
                    break
                
                # 有错误,继续迭代
                self_refine_prompt = self_consistency_prompt
            else:
                # ✨ 执行失败的处理
                if logger:
                    logger.warning(f"[Scaler-Refine] SQL execution failed: {executed_result}")
                
                self_refine_prompt = f"The error information is:\n" + str(executed_result) + "\nPlease correct it and output only 1 complete SQL query."
            
            # 更新下一次迭代的prompt
            user_prompt = self_refine_prompt
            itercount += 1
        
        # ✨ 迭代完成后的处理
        if logger:
            logger.info(f"[Scaler-Refine] Total iteration counts: {itercount}")
        
        if itercount == max_iter:
            if logger:
                logger.info("[Scaler-Refine] Max iteration reached")
            # 🔧 如果达到最大迭代且没有成功(SQL和CSV不配对),清理文件
            sql_exists = sql_save_path and os.path.exists(sql_save_path)
            csv_exists = csv_save_path and os.path.exists(csv_save_path)
            
            if sql_exists and not csv_exists:
                # SQL存在但CSV不存在 → 删除SQL
                os.remove(sql_save_path)
                if logger:
                    logger.warning("[Scaler-Refine] Max Iter reached, removed SQL without valid CSV")
            elif csv_exists and not sql_exists:
                # CSV存在但SQL不存在 → 删除CSV
                os.remove(csv_save_path)
                if logger:
                    logger.warning("[Scaler-Refine] Max Iter reached, removed CSV without valid SQL")
        
        # 🔧 只有当CSV存在时才保存SQL（表示SQL执行成功）
        if sql_save_path and not os.path.exists(sql_save_path):
            if csv_save_path and os.path.exists(csv_save_path):
                with open(sql_save_path, 'w', encoding='utf-8') as f:
                    f.write(current_sql)
                if logger:
                    logger.info(f"[Scaler-Refine] ✓ SQL saved: {sql_save_path}")
            else:
                if logger:
                    logger.warning(f"[Scaler-Refine] ✗ SQL not saved (no valid CSV): {sql_save_path}")
                return None  # 返回None表示失败
        
        return current_sql
