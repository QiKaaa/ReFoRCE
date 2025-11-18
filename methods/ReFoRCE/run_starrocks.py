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
from prompt_starrocks import PromptsStarRocks
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
    schema_linker=None, use_schema_linking=False
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
        # 使用Schema Linking获取精简的Schema
        logger.info("[Schema Linking] Generating optimized schema...")
        
        # 创建 chat session
        chat_session_sl = GPTChat(
            args.azure if hasattr(args, 'azure') else False,
            args.generation_model,
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
    
    if args.do_column_exploration:
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
        prompt_class=prompt_all,
        sql_env=sql_env,
        chat_session_pre=chat_session_ex,
        chat_session=chat_session,
        log_save_path=sql_id + '/' + log_save_path,
        db_id=DB_CONFIG['database'],
        task="starrocks"
    )
    
    # 列探索
    pre_info, response_pre_txt = None, None
    if args.do_column_exploration:
        pre_info, response_pre_txt, max_try = agent.exploration(
            question, table_struct, table_info, logger
        )
        if max_try <= 0:
            print(f"{sql_id}: Inadequate preparation, skip")
            return
        print(f"{sql_id}: chat_session_ex len: {chat_session_ex.get_message_len()}")
    
    csv_save_path_full = os.path.join(search_directory, csv_save_path)
    sql_save_path_full = os.path.join(search_directory, sql_save_path)
    
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


def process_question(sql_id, example, schema_parser, schema_linker, args):
    """处理单个问题（用于并行执行）"""
    start_time = time.time()
    
    print(f"Processing: {sql_id}")
    
    question = example['question']
    table_list = example.get('table_list', [])
    knowledge = example.get('knowledge', '')
    complexity = example.get('复杂度', 'unknown')
    
    # 创建输出目录
    search_directory = os.path.join(args.output_path, sql_id)
    if not os.path.exists(search_directory):
        os.makedirs(search_directory)
    
    # 创建Agent格式化对象
    agent_format = REFORCE(
        db_path=None,
        sql_data=sql_id,
        search_directory=search_directory,
        prompt_class=prompt_all
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
    
    # 格式限制（可选）
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
            for i in range(num_votes):
                csv_save_pathi = f"original_{i}_{agent_format.csv_save_name}"
                log_pathi = f"original_{i}_{agent_format.log_save_name}"
                sql_save_pathi = f"original_{i}_{agent_format.sql_save_name}"
                sql_paths[sql_save_pathi] = csv_save_pathi
                
                thread = threading.Thread(
                    target=execute_single_question,
                    args=(
                        sql_id, question, table_list, knowledge,
                        schema_parser, args,
                        csv_save_pathi, log_pathi, sql_save_pathi,
                        search_directory, format_csv,
                        None, False  # 不使用schema linking
                    )
                )
                threads.append(thread)
                thread.start()
            
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
                        schema_linker, True  # 使用schema linking
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
                        None, False
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
                # 执行投票
                table_info = schema_parser.get_tables_chunks(table_list)
                if knowledge:
                    table_info += f"Domain Knowledge:\n{knowledge}"
                agent_format.vote_result(search_directory, args, sql_paths, table_info, question)
            else:
                print(f"{sql_id}: Empty")
    else:
        # 直接执行
        execute_single_question(
            sql_id, question, table_list, knowledge,
            schema_parser, args,
            agent_format.csv_save_name, agent_format.log_save_name, 
            agent_format.sql_save_name,
            search_directory, format_csv,
            schema_linker if args.use_schema_linking else None,
            args.use_schema_linking if hasattr(args, 'use_schema_linking') else False
        )
    
    elapsed = int((time.time() - start_time) // 60)
    print(f"✓ {sql_id} completed in {elapsed} min")


def main(args):
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
        schema_linker = OptimizedSchemaLinker(schema_file=args.schema_path)
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
            executor.submit(process_question, sql_id, example, schema_parser, schema_linker, args)
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
    
    # 模型配置
    parser.add_argument('--azure', action="store_true", help="使用Azure OpenAI")
    parser.add_argument('--generation_model', type=str, default="gpt-4o",
                       help="生成模型")
    parser.add_argument('--column_exploration_model', type=str, default="gpt-4o",
                       help="列探索模型")
    parser.add_argument('--format_model', type=str, default="gpt-4o",
                       help="格式化模型")
    parser.add_argument('--model_vote', type=str, default=None,
                       help="投票模型")
    
    # 功能开关
    parser.add_argument('--do_format_restriction', action="store_true",
                       help="启用格式限制")
    parser.add_argument('--do_column_exploration', action="store_true",
                       help="启用列探索")
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
    
    # 运行参数
    parser.add_argument('--max_iter', type=int, default=5, help="最大迭代次数")
    parser.add_argument('--temperature', type=float, default=1.0, help="采样温度")
    parser.add_argument('--num_votes', type=int, default=3, help="投票次数")
    parser.add_argument('--num_workers', type=int, default=4, help="并行worker数量")
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
    
    args = parser.parse_args()
    
    # 初始化Prompt类
    prompt_all = PromptsStarRocks()
    
    # 创建输出目录
    os.makedirs(args.output_path, exist_ok=True)
    
    # 运行
    main(args)
