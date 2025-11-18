"""
测试单个问题的处理流程
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 加载数据和Schema
from data_loader import DatasetLoader
from schema_parser import SchemaParser

print("=" * 60)
print("测试单个问题处理")
print("=" * 60)

# 1. 加载数据
dataset_path = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
loader = DatasetLoader(dataset_path)
all_examples = loader.get_all_examples()

print(f"1. 数据集加载成功: {len(all_examples)} 个问题")

# 获取第一个问题
example = all_examples[0]
sql_id = example['sql_id']
question = example['question']
table_list = example.get('table_list', [])

print(f"   SQL ID: {sql_id}")
print(f"   问题: {question[:100]}...")
print(f"   涉及表: {len(table_list)} 个")
print(f"   表列表: {', '.join(table_list[:5])}{'...' if len(table_list) > 5 else ''}")

# 2. 加载Schema
schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
schema_parser = SchemaParser(schema_path)

print(f"2. Schema加载成功: {len(schema_parser.tables)} 个表定义")

# 获取相关表的Schema
table_info = schema_parser.get_tables_chunks(table_list)
print(f"   相关Schema大小: {len(table_info)} 字符")

# 3. 检查输出目录
output_dir = "output/starrocks-log"
search_directory = os.path.join(output_dir, sql_id)

print(f"3. 输出目录: {search_directory}")
if os.path.exists(search_directory):
    files = os.listdir(search_directory)
    if files:
        print(f"   ⚠️  目录已存在，包含 {len(files)} 个文件:")
        for f in files[:3]:
            print(f"      - {f}")
    else:
        print(f"   ℹ️  目录为空")
else:
    print(f"   ℹ️  目录不存在（将自动创建）")

# 4. 测试Chat API调用
print(f"4. 测试Chat API连接")
api_key = os.getenv('DS_API_KEY') or os.getenv('OPENAI_API_KEY')
if not api_key:
    print("   ❌ 错误：API Key未设置!")
    sys.exit(1)

print(f"   ✅ API Key已设置: {api_key[:10]}...{api_key[-5:]}")

try:
    from chat import ChatClass
    chat = ChatClass(False, "deepseek-reasoner", temperature=0)
    print(f"   ✅ Chat类初始化成功")
    
    # 简单测试
    test_prompt = "请用一句话回答：什么是SQL?"
    response = chat.generate_one(messages=[{"role": "user", "content": test_prompt}])
    print(f"   ✅ API调用成功")
    print(f"   响应: {response[:100]}...")
except Exception as e:
    print(f"   ❌ Chat API测试失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试数据库连接
print(f"5. 测试StarRocks数据库连接")
try:
    from sql_starrocks import SqlEnvStarRocks
    
    sql_env = SqlEnvStarRocks(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '9030')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'final_algorithm_competition')
    )
    
    print(f"   ✅ 数据库连接成功")
    
    # 测试查询
    test_sql = "SELECT 1"
    result = sql_env.execute_sql(test_sql)
    print(f"   ✅ 测试查询成功: {result}")
    
    sql_env.close_db()
except Exception as e:
    print(f"   ❌ 数据库连接失败: {e}")
    import traceback
    traceback.print_exc()

print("" + "=" * 60)
print("所有基础检查完成！")
print("=" * 60)

# 6. 尝试生成一个简单的SQL
print(f"\n6. 尝试使用Agent生成SQL")

try:
    from prompt_starrocks import PromptsStarRocks
    from agent import REFORCE
    from utils import initialize_logger
    from chat import ChatClass as ChatClassImport
    
    # 创建输出目录
    if not os.path.exists(search_directory):
        os.makedirs(search_directory)
    
    # 初始化日志
    log_path = os.path.join(search_directory, "test.log")
    logger = initialize_logger(log_path)
    
    # 初始化Prompt
    prompt_all = PromptsStarRocks()
    
    # 初始化Chat
    chat_session = ChatClassImport(False, "deepseek-reasoner", temperature=0)
    
    # 初始化SQL环境
    sql_env = SqlEnvStarRocks(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '9030')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'final_algorithm_competition')
    )
    
    # 初始化Agent
    agent = REFORCE(
        db_path=None,
        sql_data=sql_id,
        search_directory=search_directory,
        prompt_class=prompt_all,
        sql_env=sql_env,
        chat_session_pre=None,
        chat_session=chat_session,
        log_save_path=sql_id + '/log.log',
        db_id='final_algorithm_competition',
        task="starrocks"
    )
    
    print(f"   ✅ Agent初始化成功")
    print(f"   现在开始生成SQL（这可能需要几分钟）...")
    
    # 简单的生成测试（不使用self-refinement）
    class Args:
        max_total_time = 3000
        max_retry_times = 3
        max_chat_round = 10
        exploration_round = 3
        max_chat_token_length = 20000
    
    args = Args()
    
    table_struct = f"Available tables: {', '.join(table_list[:3])}"  # 只用前3个表
    
    csv_save_path = os.path.join(search_directory, "result.csv")
    sql_save_path = os.path.join(search_directory, "result.sql")
    
    # 调用生成方法
    agent.gen(
        args, logger, question, None,
        table_struct, table_info[:5000], None, None,  # 限制Schema大小
        csv_save_path, sql_save_path, task=question
    )
    
    print(f"   ✅ SQL生成完成!")
    
    # 检查输出
    if os.path.exists(sql_save_path):
        with open(sql_save_path, 'r', encoding='utf-8') as f:
            generated_sql = f.read()
        print(f"   生成的SQL:")
        print(f"   {generated_sql[:200]}...")
    else:
        print(f"   ⚠️  未找到生成的SQL文件")
    
    sql_env.close_db()
    
except Exception as e:
    print(f"   ❌ Agent测试失败: {e}")
    import traceback
    traceback.print_exc()

print("" + "=" * 60)
print("测试完成！")
print("=" * 60)
