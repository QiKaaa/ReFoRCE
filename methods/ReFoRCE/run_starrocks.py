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


def execute_single_question(
    sql_id, question, table_list, knowledge, 
    schema_parser, args, 
    csv_save_path, log_save_path, sql_save_path, 
    search_directory, format_csv
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
    
    # 获取相关表的Schema
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
        chat_session_ex = ChatClass(
            args.azure, 
            args.column_exploration_model, 
            temperature=args.temperature
        )
    
    if args.generation_model:
        chat_session = ChatClass(
            args.azure, 
            args.generation_model, 
            temperature=args.temperature
        )
    
    # 初始化SQL环境（StarRocks）
    sql_env = SqlEnvStarRocks(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name
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
        db_id=args.db_name,
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


def process_question(sql_id, example, schema_parser, args):
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
        chat_session_format = ChatClass(
            args.azure, 
            args.format_model, 
            temperature=args.temperature
        )
        format_csv = agent_format.format_answer(question, chat_session_format)
    
    # 投票模式
    if args.do_vote:
        num_votes = args.num_votes
        sql_paths = {}
        threads = []
        
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
                    search_directory, format_csv
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
                    table_info += f"\n\nDomain Knowledge:\n{knowledge}\n"
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
            search_directory, format_csv
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
    print(f"\n数据集统计:")
    print(f"  总问题数: {stats['total_examples']}")
    print(f"  复杂度分布: {stats['complexity_distribution']}")
    print(f"  涉及表数: {stats['total_unique_tables']}")
    
    # 加载Schema
    print(f"\nLoading schema from {args.schema_path}...")
    global schema_parser
    schema_parser = SchemaParser(args.schema_path)
    print(f"  数据库: {schema_parser.db_id}")
    print(f"  表数量: {len(schema_parser.tables)}")
    
    # 获取所有示例
    examples_dict = loader.get_example_dict()
    
    # 过滤（如果需要）
    if args.filter_complexity:
        examples_dict = {
            k: v for k, v in examples_dict.items() 
            if v.get('复杂度') == args.filter_complexity
        }
        print(f"\n过滤复杂度为 '{args.filter_complexity}' 的问题: {len(examples_dict)} 个")
    
    # 限制问题数量（用于测试）
    if args.max_questions:
        examples_dict = dict(list(examples_dict.items())[:args.max_questions])
        print(f"\n限制处理前 {args.max_questions} 个问题")
    
    # 并行处理
    print(f"\n开始处理（使用 {args.num_workers} 个worker）...\n")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        futures = [
            executor.submit(process_question, sql_id, example, schema_parser, args)
            for sql_id, example in examples_dict.items()
        ]
        list(concurrent.futures.as_completed(futures))
    
    print("\n✓ 所有问题处理完成！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ReFoRCE for StarRocks")
    
    # 数据源配置
    parser.add_argument('--dataset_path', type=str, 
                       default="E:/Project/track3_2/final_for_student/data/final_dataset_example.json",
                       help="数据集JSON文件路径")
    parser.add_argument('--schema_path', type=str,
                       default="E:/Project/track3_2/M-schema/final_algorithm_competition.txt",
                       help="Schema文件路径")
    
    # StarRocks数据库配置
    parser.add_argument('--db_host', type=str, default="localhost", help="StarRocks主机")
    parser.add_argument('--db_port', type=int, default=9030, help="StarRocks端口")
    parser.add_argument('--db_user', type=str, default="root", help="数据库用户名")
    parser.add_argument('--db_password', type=str, default="", help="数据库密码")
    parser.add_argument('--db_name', type=str, default="final_algorithm_competition", 
                       help="数据库名")
    
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
    
    args = parser.parse_args()
    
    # 初始化Prompt类
    prompt_all = PromptsStarRocks()
    
    # 设置Chat类
    ChatClass = GPTChat
    
    # 创建输出目录
    os.makedirs(args.output_path, exist_ok=True)
    
    # 运行
    main(args)
