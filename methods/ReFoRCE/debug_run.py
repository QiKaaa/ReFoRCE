"""
调试脚本 - 检查程序运行状态
"""
import os
from dotenv import load_dotenv
from data_loader import DatasetLoader
from schema_parser import SchemaParser

# 加载环境变量
load_dotenv()

print("=" * 60)
print("🔍 ReFoRCE 调试检查")
print("=" * 60)

# 1. 检查环境变量
print("\n1️⃣ 环境变量检查:")
ds_key = os.getenv('DS_API_KEY')
openai_key = os.getenv('OPENAI_API_KEY')
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '9030')

if ds_key:
    print(f"  ✓ DS_API_KEY: {ds_key[:10]}...")
elif openai_key:
    print(f"  ✓ OPENAI_API_KEY: {openai_key[:10]}...")
else:
    print("  ✗ 未找到 API Key")

print(f"  ✓ DB配置: {db_host}:{db_port}")

# 2. 检查数据集
print("\n2️⃣ 数据集检查:")
dataset_path = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
if os.path.exists(dataset_path):
    print(f"  ✓ 数据集路径: {dataset_path}")
    loader = DatasetLoader(dataset_path)
    examples = loader.get_example_dict()
    print(f"  ✓ 总问题数: {len(examples)}")
    
    # 显示第一个问题
    first_id = list(examples.keys())[0]
    first_example = examples[first_id]
    print(f"\n  第一个问题 ({first_id}):")
    print(f"    问题: {first_example['question'][:50]}...")
    print(f"    复杂度: {first_example['复杂度']}")
    print(f"    涉及表: {first_example['table_list']}")
else:
    print(f"  ✗ 数据集不存在: {dataset_path}")

# 3. 检查Schema
print("\n3️⃣ Schema检查:")
schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
if os.path.exists(schema_path):
    print(f"  ✓ Schema路径: {schema_path}")
    parser = SchemaParser(schema_path)
    print(f"  ✓ 数据库: {parser.db_id}")
    print(f"  ✓ 表数量: {len(parser.tables)}")
    
    # 检查第一个问题的表是否存在
    if 'first_example' in locals():
        missing_tables = []
        for table in first_example['table_list']:
            if table not in parser.tables:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"  ⚠️  缺失的表: {missing_tables}")
        else:
            print(f"  ✓ 所有表都存在于Schema中")
else:
    print(f"  ✗ Schema不存在: {schema_path}")

# 4. 检查数据库连接
print("\n4️⃣ 数据库连接检查:")
try:
    from sqlalchemy import create_engine, text
    
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'final_algorithm_competition')
    
    if db_password:
        conn_str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        conn_str = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"
    
    engine = create_engine(conn_str)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.fetchone()
    
    print(f"  ✓ 数据库连接成功: {db_name}")
    
    # 检查第一个问题的表是否存在于数据库
    if 'first_example' in locals():
        print(f"\n  检查表是否存在于数据库:")
        with engine.connect() as conn:
            for table in first_example['table_list']:
                try:
                    result = conn.execute(text(f"SHOW TABLES LIKE '{table}'"))
                    if result.fetchone():
                        print(f"    ✓ {table}")
                    else:
                        print(f"    ✗ {table} (不存在)")
                except Exception as e:
                    print(f"    ✗ {table} (错误: {e})")
    
except Exception as e:
    print(f"  ✗ 数据库连接失败: {e}")

# 5. 检查输出目录
print("\n5️⃣ 输出目录检查:")
output_path = "output/starrocks-log"
if os.path.exists(output_path):
    print(f"  ✓ 输出目录: {output_path}")
    
    # 检查 sql_1 目录
    sql_1_path = os.path.join(output_path, "sql_1")
    if os.path.exists(sql_1_path):
        files = os.listdir(sql_1_path)
        if files:
            print(f"  ✓ sql_1 目录包含文件:")
            for f in files:
                print(f"    - {f}")
        else:
            print(f"  ⚠️  sql_1 目录为空")
    else:
        print(f"  ℹ️  sql_1 目录不存在（程序尚未创建）")
else:
    print(f"  ✗ 输出目录不存在: {output_path}")

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
