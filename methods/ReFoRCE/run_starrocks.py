"""
StarRocks版本的ReFoRCE运行脚本
处理final_dataset_example.json中的问题
"""
import os
import argparse
import glob
from utils import initialize_logger
from agent import REFORCE
from chat import GPTChat
# from prompt_starrocks import PromptsStarRocks  # 已废弃
from prompts.starrocks_prompts import StarRocksPromptManager
import threading
import concurrent.futures
import time

# 导入StarRocks特定模块
from sql_starrocks import SqlEnvStarRocks
from schema_parser import SchemaParser
from data_loader import DatasetLoader
from dotenv import load_dotenv

# 导入 Schema Linking
from schema_linking_optimized import OptimizedSchemaLinker
from parallel_schema_linker import ParallelSchemaLinker

# ✨ 导入业务领域知识管理器
from domain_knowledge import DomainKnowledge

# ✨ 导入分解模块（Scaler已合并到agent.py）
from decomposer_starrocks import StarRocksDecomposer

# 加载.env文件中的环境变量
load_dotenv()

# 从.env文件中获取数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '9030')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'final_algorithm_competition')
}
def execute_single_question(
    sql_id, question, table_list, knowledge, 
    schema_parser, args, 
    csv_save_path, log_save_path, sql_save_path, 
    search_directory, format_csv,
    schema_linker=None, use_schema_linking=False,
    complexity='unknown',
    cached_exploration_result=None,  # ✨ 新增:缓存的列探索结果
    cached_linked_schema=None,  # ✨ 新增:缓存的schema linking结果(M-schema文本)
    cached_schema_links=None,  # ✨ 新增:缓存的schema links结果({"tables": [...], "columns": [...]})
    prompt_manager=None,  # ✨ 新增:Prompt管理器
    thread_prefix=""  # ✨ 新增:线程前缀（用于区分linked/original）
):
    """
    执行单个问题
    
    Args:
        sql_id: SQL问题ID
        question: 问题文本
        table_list: 相关表列表
        knowledge: 领域知识
        schema_parser: Schema解析器
        args: 命令行参数
        csv_save_path: CSV保存路径
        log_save_path: 日志保存路径
        sql_save_path: SQL保存路径
        search_directory: 搜索目录
        format_csv: 格式化CSV
        schema_linker: Schema Linking器（可选）
        use_schema_linking: 是否使用Schema Linking
        complexity: 问题复杂度（简单/中等/复杂）
        cached_exploration_result: 缓存的列探索结果(pre_info, response_pre_txt) ✨
        cached_linked_schema: 缓存的schema linking结果(M-schema文本) ✨
        cached_schema_links: 缓存的schema links结果({"tables": [...], "columns": [...]}) ✨
        thread_prefix: 线程前缀，用于区分文件来源（如 "linked_0", "original_1"）✨
    """
    
    # 如果结果已存在且不允许覆盖，则跳过
    if args.rerun:
        if os.path.exists(os.path.join(search_directory, sql_save_path)):
            return
        else:
            print(f"Rerun: {search_directory}")
    elif os.path.exists(os.path.join(search_directory, log_save_path)):
        return
    
    # 删除旧文件
    self_files = glob.glob(os.path.join(search_directory, f'*{log_save_path}*'))
    for self_file in self_files:
        os.remove(self_file)
    
    # 初始化日志
    log_file_path = os.path.join(search_directory, log_save_path)
    logger = initialize_logger(log_file_path)
    
    # 根据use_schema_linking决定使用哪种schema
    if use_schema_linking and schema_linker:
        # ===== 使用缓存的Schema Linking结果（如果有）=====
        if cached_linked_schema is not None:
            table_info = cached_linked_schema
            logger.info("[Schema Linking] Using cached schema")
        else:
            # 使用Schema Linking获取精简的Schema
            logger.info("[Schema Linking] Generating optimized schema...")
            
            # 创建 chat session
            chat_session_sl = GPTChat(
                args.azure if hasattr(args, 'azure') else False,
                args.schema_linking_model if hasattr(args, 'schema_linking_model') else args.generation_model,
                temperature=0
            )
            
            linked_schema = schema_linker.link_schema(
                question=question,
                table_list=table_list,
                knowledge=knowledge,
                chat_session=chat_session_sl
            )
            table_info = linked_schema  # 已经是 M-schema 格式的文本
            logger.info(f"[Schema Linking] Optimized schema generated")
    else:
        # 使用完整Schema（原方式）
        table_info = schema_parser.get_tables_chunks(table_list)
    
    # 添加领域知识
    if knowledge:
        table_info += f"\n\nDomain Knowledge:\n{knowledge}\n"
    
    logger.info(f"[Table Info]\n{table_info}\n[Table Info]")
    
    if format_csv:
        logger.info(f"[Answer Format]\n{format_csv}\n[Answer Format]")
    
    table_struct = f"Available tables: {', '.join(table_list)}"
    
    # 初始化Chat会话
    chat_session_ex = None
    chat_session = None
    
    # 判断是否需要列探索
    # 逻辑：do_column_exploration为False时不开启
    #      do_column_exploration为True时，根据复杂度判断：
    #        - 简单：不开启列探索
    #        - 中等/复杂：开启列探索
    should_do_column_exploration = False
    if args.do_column_exploration:
        if complexity in ['中等', '复杂']:
            should_do_column_exploration = True
            logger.info(f"[Column Exploration] Enabled for complexity: {complexity}")
        else:
            logger.info(f"[Column Exploration] Skipped for complexity: {complexity} (only enabled for 中等/复杂)")
    
    if should_do_column_exploration:
        chat_session_ex = GPTChat(
            args.azure, 
            args.column_exploration_model, 
            temperature=args.temperature
        )
    
    if args.generation_model:
        chat_session = GPTChat(
            args.azure, 
            args.generation_model, 
            temperature=args.temperature
        )
    
    # 初始化SQL环境（StarRocks）- 从.env文件中获取配置
    sql_env = SqlEnvStarRocks(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database']
    )
    
    # 初始化Agent
    agent = REFORCE(
        db_path=None,  # StarRocks不需要db_path
        sql_data=sql_id,
        search_directory=search_directory,
        prompt_class=prompt_manager,
        sql_env=sql_env,
        chat_session_pre=chat_session_ex,
        chat_session=chat_session,
        log_save_path=sql_id + '/' + log_save_path,
        db_id=DB_CONFIG['database'],
        task="starrocks"
    )
    
    # ===== 列探索（使用缓存机制）=====
    pre_info, response_pre_txt = None, None
    if should_do_column_exploration:
        # 如果有缓存结果，直接使用
        if cached_exploration_result is not None:
            pre_info, response_pre_txt = cached_exploration_result
            logger.info("[Column Exploration] Using cached exploration result")
            print(f"{sql_id}: Using cached column exploration")
        else:
            # 没有缓存，执行列探索
            pre_info, response_pre_txt, max_try = agent.exploration(
                question, table_struct, table_info, logger
            )
            if max_try <= 0:
                print(f"{sql_id}: Inadequate preparation, skip")
                return
            print(f"{sql_id}: chat_session_ex len: {chat_session_ex.get_message_len()}")
    
    csv_save_path_full = os.path.join(search_directory, csv_save_path)
    sql_save_path_full = os.path.join(search_directory, sql_save_path)
    
    # ===== ✨ 分解-合并流程（中等/困难题目）=====
    use_decompose_scale = False
    if args.use_decompose and complexity in ['中等', '复杂']:
        logger.info(f"[Decompose-Scale] Enabled for complexity: {complexity}")
        use_decompose_scale = True
        
        # 1. 初始化Decomposer
        decomposer = StarRocksDecomposer(
            chat_session=GPTChat(args.azure, args.decompose_model if hasattr(args, 'decompose_model') else args.generation_model),
            azure=args.azure,
            model=args.decompose_model if hasattr(args, 'decompose_model') else args.generation_model
        )
        
        # 2. 执行问题分解
        logger.info("[Decompose] Starting question decomposition...")
        qa_pairs = decomposer.decompose(
            question=question,
            schema=table_info,
            evidence=knowledge if knowledge else "",
            schema_links="",  # 可以传递Schema Linking结果
            few_shot_examples=pre_info if pre_info else "",
            logger=logger
        )
        
        if not qa_pairs:
            logger.warning("[Decompose] No sub-questions generated, falling back to normal flow")
            use_decompose_scale = False
        else:
            logger.info(f"[Decompose] Generated {len(qa_pairs)} sub-questions")
            
            # 保存分解结果
            decompose_dir = os.path.join(search_directory, "decomposition")
            decomposer.save_decomposition(qa_pairs, decompose_dir, sql_id)
            
            # 3. 处理每个子问题SQL
            refined_qa_pairs = []
            for sub_id, (sub_q, sub_sql) in enumerate(qa_pairs, 1):
                logger.info(f"[Sub-Question {sub_id}] Processing: {sub_q}")
                
                # 应用self-refinement到子问题SQL
                refined_sql, csv_path = agent.process_sub_question_sql(
                    sub_sql=sub_sql,
                    sub_question=sub_q,
                    sub_id=sub_id,
                    args=args,
                    logger=logger,
                    table_info=table_info,
                    search_directory=decompose_dir,
                    task=question
                )
                
                refined_qa_pairs.append((sub_q, refined_sql))
                logger.info(f"[Sub-Question {sub_id}] ✓ Refined")
            
            # 4. 创建专用于SQL合并的chat session
            chat_session_scale = GPTChat(
                args.azure, 
                args.scale_model if hasattr(args, 'scale_model') else args.generation_model
            )
            
            logger.info("[Scale] Starting SQL synthesis...")
            
            # 🔧 修改：每个线程只生成一个SQL候选（不是多个）
            # 策略选择：根据thread_prefix中的编号决定是否使用fallback
            if args.do_vote and args.use_decompose:
                # 提取线程编号，决定使用哪种策略
                thread_index = 0
                if thread_prefix:
                    parts = thread_prefix.split('_')
                    if len(parts) > 1 and parts[1].isdigit():
                        thread_index = int(parts[1])
                
                # 每3个线程中有1个使用fallback（第2, 5, 8...个线程）
                use_fallback = (thread_index % 3 == 2)
                
                logger.info(f"[Scale] Thread {thread_prefix}: Using {'fallback' if use_fallback else 'normal'} strategy")
                
                # 🔧 准备schema_links参数（使用缓存的schema linking结果）
                schema_links_for_scale = ""
                if use_schema_linking and cached_linked_schema:
                    schema_links_for_scale = cached_linked_schema
                    logger.info("[Scale] Using cached schema linking result")
                
                # 生成单个SQL候选
                final_sql = agent.scale_sql(
                    question=question,
                    schema=table_info,
                    qa_pairs=refined_qa_pairs,
                    evidence=knowledge if knowledge else "",
                    schema_links=schema_links_for_scale,  # ✨ 使用缓存的结果
                    few_shot_examples=pre_info if pre_info else "",
                    use_fallback=use_fallback,
                    chat_session=chat_session_scale,
                    logger=logger
                )
                
                if not final_sql:
                    logger.error("[Scale] Failed to generate SQL")
                    return
                
                # ✨ 确定文件前缀（用于区分来源）
                if thread_prefix:
                    # 直接使用thread_prefix作为文件前缀（如 "linked_0", "original_0"）
                    file_prefix = thread_prefix
                else:
                    file_prefix = "vote"
                
                logger.info(f"[Scale] Using file prefix: {file_prefix}")
                
                # 保存SQL候选文件
                vote_csv_path = os.path.join(search_directory, f"{file_prefix}_result.csv")
                vote_sql_path = os.path.join(search_directory, f"{file_prefix}_result.sql")
                
                # ✨ 对生成的SQL进行self-refinement
                logger.info(f"[Scale] Refining generated SQL...")
                # 🔧 优先使用final_sql_max_iter，如果未设置则使用max_iter
                refine_max_iter = args.final_sql_max_iter if args.final_sql_max_iter else args.max_iter
                final_sql = agent.refine_final_sql(
                    initial_sql=final_sql,
                    question=question,
                    schema=table_info,
                    evidence=knowledge if knowledge else "",
                    schema_links=schema_links_for_scale,  # ✨ 使用相同的缓存结果
                    max_iter=refine_max_iter,
                    sql_id=f"{sql_id}_{thread_prefix if thread_prefix else 'default'}",
                    csv_save_path=vote_csv_path,
                    sql_save_path=vote_sql_path,
                    table_struct=table_struct,
                    chat_session=chat_session_scale,
                    logger=logger
                )
                
                if final_sql:
                    logger.info(f"[Scale] SQL candidate generated and refined successfully")
                else:
                    logger.warning(f"[Scale] Failed to refine SQL")
                
                # ✨ 不在线程内部投票，等待所有线程完成后统一投票
                logger.info(f"[Decompose-Vote] Generated 1 candidate with prefix '{file_prefix}'")
            else:
                # 单次合并模式
                # 🔧 准备schema_links参数（使用缓存的schema linking结果）
                schema_links_for_scale = ""
                if use_schema_linking and cached_linked_schema:
                    schema_links_for_scale = cached_linked_schema
                    logger.info("[Scale] Using cached schema linking result")
                
                final_sql = agent.scale_sql(
                    question=question,
                    schema=table_info,
                    qa_pairs=refined_qa_pairs,
                    evidence=knowledge if knowledge else "",
                    schema_links=schema_links_for_scale,  # ✨ 使用缓存的结果
                    few_shot_examples=pre_info if pre_info else "",
                    use_fallback=False,
                    chat_session=chat_session_scale,
                    logger=logger
                )
                
                logger.info(f"[Scale] Initial final SQL generated:\n{final_sql}")
                
                # ✨ 如果启用最终SQL refinement，进行优化
                if args.do_final_sql_refinement:
                    logger.info("[Scale-Refine] Starting final SQL refinement...")
                    # 🔧 优先使用final_sql_max_iter，如果未设置则使用max_iter
                    refine_max_iter = args.final_sql_max_iter if args.final_sql_max_iter else args.max_iter
                    final_sql = agent.refine_final_sql(
                        initial_sql=final_sql,
                        question=question,
                        schema=table_info,
                        evidence=knowledge if knowledge else "",
                        schema_links=schema_links_for_scale,  # ✨ 使用缓存的结果
                        max_iter=refine_max_iter,
                        sql_id=sql_id,
                        csv_save_path=csv_save_path_full,
                        sql_save_path=sql_save_path_full,
                        table_struct=table_struct,
                        chat_session=chat_session_scale,
                        logger=logger
                    )
                    logger.info("[Scale-Refine] ✓ Final SQL refinement complete")
                else:
                    # 不进行refinement，直接执行
                    result = agent.sql_env.execute_sql_api(
                        final_sql, 
                        sql_id,
                        csv_save_path_full,
                        api=agent.api,
                        sqlite_path=agent.sqlite_path
                    )
                    
                    if result == '0':
                        with open(sql_save_path_full, 'w', encoding='utf-8') as f:
                            f.write(final_sql)
                        logger.info("[Scale] ✓ Final SQL executed successfully")
                    else:
                        logger.error(f"[Scale] Final SQL execution failed: {result}")
                        use_decompose_scale = False  # 失败则回退到常规流程
    
    # ===== 常规SQL生成流程 =====
    if not use_decompose_scale:
        # 生成SQL
        if args.do_self_refinement:
            agent.self_refine(
                args, logger, question, format_csv, 
                table_struct, table_info, response_pre_txt, pre_info,
                csv_save_path_full, sql_save_path_full, task=question
            )
        elif args.generation_model:
            agent.gen(
                args, logger, question, format_csv,
                table_struct, table_info, response_pre_txt, pre_info,
                csv_save_path_full, sql_save_path_full, task=question
            )
    
    # 关闭数据库连接
    if args.generation_model:
        agent.sql_env.close_db()


def process_question(sql_id, example, schema_parser, schema_linker, args, prompt_manager):
    """处理单个问题（用于并行执行）"""
    start_time = time.time()
    
    print(f"Processing: {sql_id}")
    
    question = example['question']
    table_list = example.get('table_list', [])
    knowledge = example.get('knowledge', '')
    complexity = example.get('复杂度', 'unknown')
    golden_sql = example.get('sql', None)  # 获取金标准SQL
    is_golden = example.get('golden_sql', False)  # 是否为金标准题目
    
    # 创建输出目录
    search_directory = os.path.join(args.output_path, sql_id)
    if not os.path.exists(search_directory):
        os.makedirs(search_directory)
    
    # 创建Agent格式化对象
    agent_format = REFORCE(
        db_path=None,
        sql_data=sql_id,
        search_directory=search_directory,
        prompt_class=prompt_manager
    )
    
    # 跳过已完成的
    if os.path.exists(agent_format.complete_sql_save_path) and not args.revote:
        print(f"  ✓ {sql_id} already completed, skipping")
        return
    
    if args.overwrite_unfinished:
        if not os.path.exists(agent_format.complete_sql_save_path):
            for filename in os.listdir(search_directory):
                filepath = os.path.join(search_directory, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        else:
            return
    
    if not os.path.exists(search_directory):
        os.makedirs(search_directory)
    
    # ===== ✨ 预先执行一次列探索（如果需要）=====
    # 修改目的：避免投票模式下重复执行列探索，提高效率
    cached_exploration_result = None
    should_do_column_exploration = False
    
    if args.do_column_exploration and complexity in ['中等', '复杂']:
        should_do_column_exploration = True
        print(f"[{sql_id}] Pre-executing column exploration (complexity: {complexity})...")
        
        # 创建临时的chat session用于列探索
        chat_session_ex_temp = GPTChat(
            args.azure, 
            args.column_exploration_model, 
            temperature=args.temperature
        )
        
        # 获取table_info（用于列探索）
        table_info_for_exploration = schema_parser.get_tables_chunks(table_list)
        if knowledge:
            table_info_for_exploration += f"Domain Knowledge:{knowledge}"
        
        table_struct = f"Available tables: {', '.join(table_list)}"
        
        # 创建临时Agent执行列探索
        sql_env_temp = SqlEnvStarRocks(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        
        agent_temp = REFORCE(
            db_path=None,
            sql_data=sql_id,
            search_directory=search_directory,
            prompt_class=prompt_manager,
            sql_env=sql_env_temp,
            chat_session_pre=chat_session_ex_temp,
            chat_session=None,
            log_save_path=sql_id + '/temp_exploration.log',
            db_id=DB_CONFIG['database'],
            task="starrocks"
        )
        
        # 执行列探索（只执行一次）
        logger_temp = initialize_logger(os.path.join(search_directory, 'temp_exploration.log'))
        pre_info, response_pre_txt, max_try = agent_temp.exploration(
            question, table_struct, table_info_for_exploration, logger_temp
        )
        
        if max_try <= 0:
            print(f"{sql_id}: Column exploration failed, skip")
            sql_env_temp.close_db()
            return
        
        # 缓存结果
        cached_exploration_result = (pre_info, response_pre_txt)
        sql_env_temp.close_db()
        print(f"[{sql_id}] ✓ Column exploration cached")
    
    # ===== ✨ 预先执行一次Schema Linking（如果需要）=====
    # 修改目的：避免投票模式下重复执行Schema Linking，提高效率
    cached_linked_schema = None
    cached_schema_links = None
    
    if (args.do_schema_linking_vote or args.use_schema_linking) and schema_linker:
        print(f"[{sql_id}] Pre-executing schema linking...")
        
        # 创建临时chat session
        chat_session_sl_temp = GPTChat(
            args.azure if hasattr(args, 'azure') else False,
            args.schema_linking_model if hasattr(args, 'schema_linking_model') else args.generation_model,
            temperature=0
        )
        
        # 执行Schema Linking（只执行一次）
        schema_links, linked_schema = schema_linker.link_schema(
            question=question,
            table_list=table_list,
            knowledge=knowledge,
            chat_session=chat_session_sl_temp
        )
        
        # 缓存两个结果
        cached_linked_schema = linked_schema  # M-schema文本
        cached_schema_links = schema_links    # {"tables": [...], "columns": [...]}
        
        print(f"[{sql_id}] ✓ Schema linking cached:")
        print(f"  - Tables: {len(schema_links.get('tables', []))}")
        print(f"  - Columns: {len(schema_links.get('columns', []))}")
    
    # ===== 格式限制（可选）=====
    format_csv = None
    if args.do_format_restriction:
        chat_session_format = GPTChat(
            args.azure, 
            args.format_model, 
            temperature=args.temperature
        )
        format_csv = agent_format.format_answer(question, chat_session_format)
    
    # 投票模式
    if args.do_vote:
        sql_paths = {}
        threads = []
        
        # 如果启用Schema Linking投票，则生成两组SQL：原始Schema和Linked Schema
        if args.do_schema_linking_vote:
            num_votes = args.num_votes
            
            # 第一组：使用原始Schema生成（num_votes次）
            # for i in range(num_votes):
            #     csv_save_pathi = f"original_{i}_{agent_format.csv_save_name}"
            #     log_pathi = f"original_{i}_{agent_format.log_save_name}"
            #     sql_save_pathi = f"original_{i}_{agent_format.sql_save_name}"
            #     sql_paths[sql_save_pathi] = csv_save_pathi
                
            #     thread = threading.Thread(
            #         target=execute_single_question,
            #         args=(
            #             sql_id, question, table_list, knowledge,
            #             schema_parser, args,
            #             csv_save_pathi, log_pathi, sql_save_pathi,
            #             search_directory, format_csv,
            #             None, False,  # 不使用schema linking
            #             complexity,  # 传递复杂度参数
            #             cached_exploration_result,  # ✨ 传递缓存的列探索结果
            #             None,  # 不使用cached_linked_schema（原始schema模式）
            #             None,  # 不使用cached_schema_links（原始schema模式）
            #             prompt_manager,  # ✨ 传递prompt_manager
            #             f"original_{i}"  # ✨ 传递线程前缀
            #         )
            #     )
            #     threads.append(thread)
            #     thread.start()
            
            # 第二组：使用Schema Linking生成（num_votes次）
            for i in range(num_votes):
                csv_save_pathi = f"linked_{i}_{agent_format.csv_save_name}"
                log_pathi = f"linked_{i}_{agent_format.log_save_name}"
                sql_save_pathi = f"linked_{i}_{agent_format.sql_save_name}"
                sql_paths[sql_save_pathi] = csv_save_pathi
                
                thread = threading.Thread(
                    target=execute_single_question,
                    args=(
                        sql_id, question, table_list, knowledge,
                        schema_parser, args,
                        csv_save_pathi, log_pathi, sql_save_pathi,
                        search_directory, format_csv,
                        schema_linker, True,  # 使用schema linking
                        complexity,  # 传递复杂度参数
                        cached_exploration_result,  # ✨ 传递缓存的列探索结果
                        cached_linked_schema,  # ✨ 传递缓存的M-schema文本
                        cached_schema_links,  # ✨ 传递缓存的schema links
                        prompt_manager,  # ✨ 传递prompt_manager
                        f"linked_{i}"  # ✨ 传递线程前缀
                    )
                )
                threads.append(thread)
                thread.start()
        else:
            # 原始投票模式：只使用原始Schema
            num_votes = args.num_votes
            for i in range(num_votes):
                csv_save_pathi = str(i) + agent_format.csv_save_name
                log_pathi = str(i) + agent_format.log_save_name
                sql_save_pathi = str(i) + agent_format.sql_save_name
                sql_paths[sql_save_pathi] = csv_save_pathi
                
                thread = threading.Thread(
                    target=execute_single_question,
                    args=(
                        sql_id, question, table_list, knowledge,
                        schema_parser, args,
                        csv_save_pathi, log_pathi, sql_save_pathi,
                        search_directory, format_csv,
                        None, False,
                        complexity,  # 传递复杂度参数
                        cached_exploration_result,  # ✨ 传递缓存的列探索结果
                        None,  # 不使用cached_linked_schema
                        None,  # 不使用cached_schema_links
                        prompt_manager,  # ✨ 传递prompt_manager
                        f"vote_{i}"  # ✨ 传递线程前缀
                    )
                )
                threads.append(thread)
                thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 投票
        if args.revote:
            print(search_directory)
            if "result.sql" in os.listdir(search_directory):
                print("Revote, remove", os.path.join(search_directory, "result.sql"))
                os.remove(os.path.join(search_directory, "result.sql"))
            if "result.csv" in os.listdir(search_directory):
                print("Revote, remove", os.path.join(search_directory, "result.csv"))
                os.remove(os.path.join(search_directory, "result.csv"))
        
        if "result.sql" not in os.listdir(search_directory):
            if any(file.endswith('.sql') for file in os.listdir(search_directory) 
                   if os.path.isfile(os.path.join(search_directory, file))):
                # 🔧 重新收集实际生成的SQL文件（支持decompose场景）
                candidate_sql_files = {}
                for filename in os.listdir(search_directory):
                    if filename.endswith('_result.sql') and filename != 'result.sql':
                        # 找到对应的CSV文件
                        csv_filename = filename.replace('.sql', '.csv')
                        csv_path = os.path.join(search_directory, csv_filename)
                        if os.path.exists(csv_path):
                            candidate_sql_files[filename] = csv_filename
                
                if candidate_sql_files:
                    # 执行投票 - 传递knowledge参数
                    table_info = schema_parser.get_tables_chunks(table_list)
                    if knowledge:
                        table_info += f"Domain Knowledge:\n{knowledge}"
                    agent_format.vote_result(search_directory, args, candidate_sql_files, table_info, question, knowledge=knowledge)
                else:
                    print(f"{sql_id}: No valid candidates for voting")
            else:
                print(f"{sql_id}: Empty")
    else:
        # 直接执行（非投票模式）
        execute_single_question(
            sql_id, question, table_list, knowledge,
            schema_parser, args,
            agent_format.csv_save_name, agent_format.log_save_name, 
            agent_format.sql_save_name,
            search_directory, format_csv,
            schema_linker if args.use_schema_linking else None,
            args.use_schema_linking if hasattr(args, 'use_schema_linking') else False,
            complexity,  # 传递复杂度参数
            cached_exploration_result,  # ✨ 传递缓存的列探索结果
            cached_linked_schema,  # ✨ 传递缓存的M-schema文本
            cached_schema_links,  # ✨ 传递缓存的schema links
            prompt_manager,  # ✨ 传递prompt_manager
            ""  # ✨ 非投票模式不需要线程前缀
        )
    
    elapsed = int((time.time() - start_time) // 60)
    print(f"✓ {sql_id} completed in {elapsed} min")
    
    # 如果有金标准SQL，进行对比评估
    if args.enable_golden_evaluation and is_golden and golden_sql:
        try:
            evaluate_with_golden_sql(
                sql_id, 
                search_directory, 
                golden_sql, 
                args
            )
        except Exception as e:
            print(f"⚠️ {sql_id}: Golden SQL evaluation failed - {e}")


def evaluate_with_golden_sql(sql_id, search_directory, golden_sql, args):
    """
    使用金标准SQL评估生成的结果
    
    Args:
        sql_id: SQL问题ID
        search_directory: 输出目录
        golden_sql: 金标准SQL
        args: 命令行参数
    """
    import pandas as pd
    from io import StringIO
    
    print(f"{'='*60}")
    print(f"📊 Golden SQL Evaluation for {sql_id}")
    print(f"{'='*60}")
    
    # 1. 执行金标准SQL
    golden_result_path = os.path.join(search_directory, "golden_result.csv")
    golden_sql_path = os.path.join(search_directory, "golden.sql")
    
    # 保存金标准SQL
    with open(golden_sql_path, 'w', encoding='utf-8') as f:
        f.write(golden_sql)
    
    print(f"📝 Executing Golden SQL...")
    sql_env = SqlEnvStarRocks(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database']
    )
    
    result = sql_env.execute_sql_api(
        golden_sql, 
        sql_id, 
        golden_result_path,
        api="starrocks"
    )
    
    if result != "0":
        print(f"❌ Golden SQL execution failed: {result}")
        sql_env.close_db()
        return
    
    print(f"✅ Golden SQL executed successfully")
    
    # 读取金标准结果
    with open(golden_result_path, 'r', encoding='utf-8') as f:
        golden_df = pd.read_csv(StringIO(f.read())).fillna("")
    
    print(f"   Rows: {len(golden_df)}, Columns: {len(golden_df.columns)}")
    
    # 2. 读取生成的结果
    generated_result_path = os.path.join(search_directory, "result.csv")
    
    if not os.path.exists(generated_result_path):
        print(f"⚠️ Generated result not found: {generated_result_path}")
        sql_env.close_db()
        return
    
    print(f"📝 Comparing with generated result...")
    with open(generated_result_path, 'r', encoding='utf-8') as f:
        generated_df = pd.read_csv(StringIO(f.read())).fillna("")
    
    print(f"   Rows: {len(generated_df)}, Columns: {len(generated_df.columns)}")
    
    # 3. 对比结果
    from utils import compare_pandas_table
    
    is_match = compare_pandas_table(golden_df, generated_df, ignore_order=True)
    shape_match = golden_df.shape == generated_df.shape
    
    # 4. 生成评估报告
    evaluation_report = os.path.join(search_directory, "evaluation_report.txt")
    
    with open(evaluation_report, 'w', encoding='utf-8') as f:
        f.write(f"Golden SQL Evaluation Report")
        f.write(f"="*60 + "")
        f.write(f"SQL ID: {sql_id}")
        f.write(f"Evaluation Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        f.write(f"Golden Result:")
        f.write(f"  Rows: {len(golden_df)}")
        f.write(f"  Columns: {len(golden_df.columns)}")
        f.write(f"  Column Names: {list(golden_df.columns)}")
        
        f.write(f"Generated Result:")
        f.write(f"  Rows: {len(generated_df)}")
        f.write(f"  Columns: {len(generated_df.columns)}")
        f.write(f"  Column Names: {list(generated_df.columns)}")
        
        f.write(f"Comparison:")
        f.write(f"  Shape Match: {'✅ Yes' if shape_match else '❌ No'}")
        f.write(f"  Content Match (ignore order): {'✅ Yes' if is_match else '❌ No'}")
        
        if is_match and shape_match:
            f.write(f"🎉 Result: PASS - Results are identical!")
            print(f"🎉 PASS - Results are identical!")
        elif shape_match:
            f.write(f"⚠️ Result: PARTIAL - Shape matches but content differs")
            print(f"⚠️ PARTIAL - Shape matches but content differs")
        else:
            f.write(f"❌ Result: FAIL - Results differ significantly")
            print(f"❌ FAIL - Results differ")
            
            # 显示详细差异
            f.write(f"Detailed Differences:")
            if len(golden_df) != len(generated_df):
                f.write(f"  Row count: Golden={len(golden_df)}, Generated={len(generated_df)}")
            if len(golden_df.columns) != len(generated_df.columns):
                f.write(f"  Column count: Golden={len(golden_df.columns)}, Generated={len(generated_df.columns)}")
            if list(golden_df.columns) != list(generated_df.columns):
                f.write(f"  Column names differ")
                f.write(f"    Golden: {list(golden_df.columns)}")
                f.write(f"    Generated: {list(generated_df.columns)}")
        
        # 显示前几行数据
        f.write(f"{'='*60}")
        f.write(f"Golden Result Preview (first 5 rows):")
        f.write(golden_df.head().to_string() + "")
        
        f.write(f"Generated Result Preview (first 5 rows):")
        f.write(generated_df.head().to_string() + "")
    
    print(f"📄 Evaluation report saved to: {evaluation_report}")
    print(f"{'='*60}")
    
    sql_env.close_db()


def main(args, prompt_manager):
    """主函数"""
    
    # 加载数据集
    print(f"Loading dataset from {args.dataset_path}...")
    loader = DatasetLoader(args.dataset_path)
    
    # 显示统计信息
    stats = loader.get_statistics()
    print(f"  数据集统计:")
    print(f"  总问题数: {stats['total_examples']}")
    print(f"  复杂度分布: {stats['complexity_distribution']}")
    print(f"  涉及表数: {stats['total_unique_tables']}")
    
    # 加载Schema
    print(f"Loading schema from {args.schema_path}...")
    global schema_parser
    schema_parser = SchemaParser(args.schema_path)
    print(f"  数据库: {schema_parser.db_id}")
    print(f"  表数量: {len(schema_parser.tables)}")
    
    # 初始化Schema Linker（如果需要）
    global schema_linker
    schema_linker = None
    if args.do_schema_linking_vote or args.use_schema_linking:
        print(f"Initializing Schema Linker...")
        schema_linker = ParallelSchemaLinker(schema_file=args.schema_path)
        print(f"  ✓ Schema Linker ready with {len(schema_linker.all_tables)} tables")
    
    # 获取所有示例
    examples_dict = loader.get_example_dict()
    
    # 过滤（如果需要）
    if args.filter_complexity:
        examples_dict = {
            k: v for k, v in examples_dict.items() 
            if v.get('复杂度') == args.filter_complexity
        }
        print(f"过滤复杂度为 '{args.filter_complexity}' 的问题: {len(examples_dict)} 个")
    
    # 限制问题数量（用于测试）
    if args.max_questions:
        examples_dict = dict(list(examples_dict.items())[:args.max_questions])
        print(f"限制处理前 {args.max_questions} 个问题")
    
    # 并行处理
    print(f"\n开始处理（使用 {args.num_workers} 个worker）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(process_question, sql_id, example, schema_parser, schema_linker, args, prompt_manager)
            for sql_id, example in examples_dict.items()
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # 获取结果，如果有异常会在这里抛出
            except Exception as e:
                print(f"[ERROR] 处理失败: {e}")
                import traceback
                traceback.print_exc()
    
    print("✓ 所有问题处理完成！")
    
    # 生成 final_dataset.json
    generate_final_dataset(args.output_path, examples_dict, args.final_dataset_path)
    
    # 如果启用了金标准评估，生成总结报告
    if args.enable_golden_evaluation:
        generate_evaluation_summary(args.output_path, examples_dict)


def generate_final_dataset(output_path, examples_dict, final_dataset_path=None):
    """
    生成 final_dataset.json 文件
    
    Args:
        output_path: 输出目录路径
        examples_dict: 问题字典
        final_dataset_path: final_dataset.json 的输出路径（默认: E:/Project/track3_2/final_dataset.json）
    """
    import json
    
    # 使用默认路径（如果未指定）
    if final_dataset_path is None:
        final_dataset_path = "E:/Project/track3_2/final_dataset.json"
    
    print(f"{'='*60}")
    print(f"📝 生成 final_dataset.json")
    print(f"{'='*60}")
    
    final_results = []
    
    for sql_id, example in examples_dict.items():
        result_sql_path = os.path.join(output_path, sql_id, "result.sql")
        
        # 检查是否有生成的SQL
        if os.path.exists(result_sql_path):
            try:
                with open(result_sql_path, 'r', encoding='utf-8') as f:
                    generated_sql = f.read().strip()
                
                # 添加到结果列表
                final_results.append({
                    "sql_id": sql_id,
                    "sql": generated_sql
                })
                
                print(f"  ✓ {sql_id}: SQL已收集")
            except Exception as e:
                print(f"  ✗ {sql_id}: 读取SQL失败 - {e}")
        else:
            print(f"  ⚠ {sql_id}: 未找到生成的SQL")
    
    # 确保输出目录存在
    final_dataset_dir = os.path.dirname(final_dataset_path)
    if final_dataset_dir and not os.path.exists(final_dataset_dir):
        os.makedirs(final_dataset_dir, exist_ok=True)
    
    try:
        with open(final_dataset_path, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 成功写入 {len(final_results)} 条结果到: {final_dataset_path}")
        print(f"  总问题数: {len(examples_dict)}")
        print(f"  成功生成: {len(final_results)}")
        print(f"  失败数量: {len(examples_dict) - len(final_results)}")
    except Exception as e:
        print(f"\n✗ 写入 final_dataset.json 失败: {e}")
        import traceback
        traceback.print_exc()
    
        print(f"{'='*60}")
        print(f"  成功生成: {len(final_results)}")
        print(f"  失败数量: {len(examples_dict) - len(final_results)}")
    except Exception as e:
        print(f"✗ 写入 final_dataset.json 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"{'='*60}")


def generate_evaluation_summary(output_path, examples_dict):
    """生成金标准评估总结报告"""
    print(f"{'='*60}")
    print(f"📊 Generating Golden SQL Evaluation Summary")
    print(f"{'='*60}")
    
    results = {
        'pass': [],
        'partial': [],
        'fail': [],
        'not_evaluated': []
    }
    
    # 遍历所有题目，读取评估报告
    for sql_id, example in examples_dict.items():
        is_golden = example.get('golden_sql', False)
        
        if not is_golden:
            continue
        
        eval_report_path = os.path.join(output_path, sql_id, "evaluation_report.txt")
        
        if not os.path.exists(eval_report_path):
            results['not_evaluated'].append(sql_id)
            continue
        
        # 读取评估结果
        with open(eval_report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "Result: PASS" in content:
            results['pass'].append(sql_id)
        elif "Result: PARTIAL" in content:
            results['partial'].append(sql_id)
        elif "Result: FAIL" in content:
            results['fail'].append(sql_id)
        else:
            results['not_evaluated'].append(sql_id)
    
    # 统计
    total_golden = len([e for e in examples_dict.values() if e.get('golden_sql', False)])
    total_evaluated = len(results['pass']) + len(results['partial']) + len(results['fail'])
    
    if total_evaluated == 0:
        print("⚠️ 没有找到任何评估结果")
        return
    
    # 生成总结报告
    summary_path = os.path.join(output_path, "golden_evaluation_summary.txt")
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Golden SQL Evaluation Summary")
        f.write(f"{'='*60}")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        f.write(f"Total Golden SQL Questions: {total_golden}")
        f.write(f"Evaluated: {total_evaluated}")
        f.write(f"Not Evaluated: {len(results['not_evaluated'])}")
        
        f.write(f"Results Breakdown:")
        f.write(f"  ✅ PASS (Identical):   {len(results['pass'])} ({len(results['pass'])/total_evaluated*100:.1f}% of evaluated)")
        f.write(f"  ⚠️  PARTIAL (Shape OK): {len(results['partial'])} ({len(results['partial'])/total_evaluated*100:.1f}% of evaluated)")
        f.write(f"  ❌ FAIL (Different):   {len(results['fail'])} ({len(results['fail'])/total_evaluated*100:.1f}% of evaluated)")
        
        accuracy = len(results['pass']) / total_evaluated * 100
        f.write(f"Accuracy (PASS only): {accuracy:.2f}%")
        
        f.write(f"PASSED Questions ({len(results['pass'])}):")
        for sql_id in results['pass']:
            f.write(f"  ✅ {sql_id}")
        
        f.write(f"PARTIAL Questions ({len(results['partial'])}):")
        for sql_id in results['partial']:
            f.write(f"  ⚠️  {sql_id}")
        
        f.write(f"FAILED Questions ({len(results['fail'])}):")
        for sql_id in results['fail']:
            f.write(f"  ❌ {sql_id}")
        
        if results['not_evaluated']:
            f.write(f"Not Evaluated ({len(results['not_evaluated'])}):")
            for sql_id in results['not_evaluated']:
                f.write(f"  ⏭️  {sql_id}")
    
    # 打印到控制台
    print(f"📈 Evaluation Summary:")
    print(f"   Total Golden Questions: {total_golden}")
    print(f"   Evaluated: {total_evaluated}")
    print(f"   ✅ PASS: {len(results['pass'])} ({len(results['pass'])/total_evaluated*100:.1f}%)")
    print(f"   ⚠️  PARTIAL: {len(results['partial'])} ({len(results['partial'])/total_evaluated*100:.1f}%)")
    print(f"   ❌ FAIL: {len(results['fail'])} ({len(results['fail'])/total_evaluated*100:.1f}%)")
    accuracy = len(results['pass']) / total_evaluated * 100
    print(f"   📊 Accuracy: {accuracy:.2f}%")
    
    print(f"📄 Summary report saved to: {summary_path}")
    print(f"{'='*60}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ReFoRCE for StarRocks")
    
    # 数据源配置
    parser.add_argument('--dataset_path', type=str, 
                       default="E:/Project/track3_2/final_for_student/data/final_dataset_example.json",
                       help="数据集JSON文件路径")
    parser.add_argument('--schema_path', type=str,
                       default="E:/Project/track3_2/M-schema/final_algorithm_competition.txt",
                       help="Schema文件路径")
    
    # 注意: 数据库配置现在从.env文件中读取
    # DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
    
    # 输出配置
    parser.add_argument('--output_path', type=str, default="output/starrocks-log",
                       help="输出目录")
    parser.add_argument('--final_dataset_path', type=str, 
                       default="E:/Project/track3_2/final_dataset.json",
                       help="final_dataset.json 输出路径")
    
    # 模型配置
    parser.add_argument('--azure', action="store_true", help="使用Azure OpenAI")
    parser.add_argument('--generation_model', type=str, default="deepseek-chat",
                       help="生成模型")
    parser.add_argument('--column_exploration_model', type=str, default="deepseek-chat",
                       help="列探索模型")
    parser.add_argument('--format_model', type=str, default="deepseek-chat",
                       help="格式化模型")
    parser.add_argument('--schema_linking_model', type=str, default="deepseek-chat",
                       help="Schema Linking模型")
    parser.add_argument('--model_vote', type=str, default=None,
                       help="投票模型")
    
    # 功能开关
    parser.add_argument('--do_format_restriction', action="store_true",
                       help="启用格式限制")
    parser.add_argument('--do_column_exploration', action="store_true",
                       help="启用列探索（根据复杂度自动判断：简单题不开启，中等/复杂题开启）")
    parser.add_argument('--do_self_refinement', action="store_true",
                       help="启用自我精化")
    parser.add_argument('--do_self_consistency', action="store_true",
                       help="启用自我一致性")
    parser.add_argument('--do_vote', action="store_true",
                       help="启用投票机制")
    
    # Schema Linking 相关
    parser.add_argument('--do_schema_linking_vote', action="store_true",
                       help="启用Schema Linking投票：同时使用原始Schema和Linked Schema生成SQL并投票")
    parser.add_argument('--use_schema_linking', action="store_true",
                       help="直接使用Schema Linking（不投票模式）")
    
    # ✨ 分解-合并模块（中等/困难题目）
    parser.add_argument('--use_decompose', action="store_true",
                       help="启用分解-合并流程（自动对中等/复杂题目进行子问题分解和SQL合并）")
    parser.add_argument('--decompose_model', type=str, default="deepseek-reasoner",
                       help="问题分解模型（默认与generation_model相同）")
    parser.add_argument('--scale_model', type=str, default="deepseek-chat",
                       help="SQL合并模型（默认与generation_model相同）")
    parser.add_argument('--sub_question_max_iter', type=int, default=3,
                       help="子问题的最大迭代次数（默认3，通常比主问题的max_iter更小）")
    parser.add_argument('--final_sql_max_iter', type=int, default=None,
                       help="最终合并SQL的最大refinement迭代次数（默认None，使用max_iter的值）")
    parser.add_argument('--do_final_sql_refinement', action="store_true",
                       help="对最终合并SQL进行refinement优化")
    parser.add_argument('--do_final_sql_consistency', action="store_true",
                       help="对最终合并SQL使用self-consistency投票")
    
    # 运行参数
    parser.add_argument('--max_iter', type=int, default=5, help="主问题的最大迭代次数")
    parser.add_argument('--temperature', type=float, default=1.0, help="采样温度")
    parser.add_argument('--num_votes', type=int, default=3, help="投票次数")
    parser.add_argument('--num_workers', type=int, default=10, help="并行worker数量")
    parser.add_argument('--early_stop', action="store_true", help="早停")
    
    # 其他选项
    parser.add_argument('--rerun', action="store_true", help="重新运行")
    parser.add_argument('--revote', action="store_true", help="重新投票")
    parser.add_argument('--overwrite_unfinished', action="store_true",
                       help="覆盖未完成的")
    parser.add_argument('--random_vote_for_tie', action="store_true",
                       help="平局时随机投票")
    parser.add_argument('--final_choose', action="store_true",
                       help="最终选择")
    parser.add_argument('--save_all_results', action="store_true",
                       help="保存所有结果")
    
    # 过滤选项
    parser.add_argument('--filter_complexity', type=str, default=None,
                       choices=['简单', '中等', '复杂'],
                       help="按复杂度过滤")
    parser.add_argument('--max_questions', type=int, default=None,
                       help="限制处理的问题数量（用于测试）")
    
    # 额外配置
    parser.add_argument('--omnisql_format_pth', type=str, default=None,
                       help="OmniSQL格式路径（可选）")
    parser.add_argument('--gold_result_path', type=str, default=None,
                       help="金标准结果路径（可选）")
    parser.add_argument('--enable_golden_evaluation', action='store_true',
                       help="启用金标准SQL评估（自动对比有golden_sql=true的题目）")
    
    args = parser.parse_args()
    
    # ✨ 获取业务领域通用知识
    domain_knowledge_general = DomainKnowledge.get_rules_for_prompt(include_specific=True)
    
    # ✨ 初始化Prompt管理器（注入业务知识）
    prompt_all = StarRocksPromptManager(domain_knowledge=domain_knowledge_general)
    
    # 创建输出目录
    os.makedirs(args.output_path, exist_ok=True)
    
    # 运行
    main(args, prompt_all)
