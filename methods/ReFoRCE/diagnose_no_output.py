"""
诊断"没有输出"问题
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("诊断报告：为什么没有输出")
print("=" * 60)

# 1. 检查配置
print("\n1️⃣  检查配置文件")
if os.path.exists('.env'):
    print("   ✅ .env 文件存在")
else:
    print("   ❌ .env 文件不存在！请从 .env.example 创建")

api_key = os.getenv('DS_API_KEY') or os.getenv('OPENAI_API_KEY')
if api_key:
    key_name = 'DS_API_KEY' if os.getenv('DS_API_KEY') else 'OPENAI_API_KEY'
    print(f"   ✅ {key_name}: {api_key[:10]}...{api_key[-5:]}")
else:
    print("   ❌ API_KEY 未设置！（需要 DS_API_KEY 或 OPENAI_API_KEY）")

# 2. 检查数据集
print("\n2️⃣  检查数据集")
dataset_path = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
if os.path.exists(dataset_path):
    print(f"   ✅ 数据集存在: {dataset_path}")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"   ✅ 问题数量: {len(data)}")
    if data:
        print(f"   ✅ 第一个问题: {data[0].get('question', 'N/A')[:50]}...")
else:
    print(f"   ❌ 数据集不存在: {dataset_path}")

# 3. 检查Schema
print("\n3️⃣  检查Schema文件")
schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
if os.path.exists(schema_path):
    print(f"   ✅ Schema存在: {schema_path}")
    with open(schema_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"   ✅ Schema大小: {len(content)} 字符")
else:
    print(f"   ❌ Schema不存在: {schema_path}")

# 4. 检查输出目录
print("\n4️⃣  检查输出目录")
output_dir = "output/starrocks-log"
if os.path.exists(output_dir):
    files = []
    for root, dirs, filenames in os.walk(output_dir):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            size = os.path.getsize(filepath)
            files.append((filepath, size))
    
    if files:
        print(f"   ⚠️  输出目录已存在 {len(files)} 个文件:")
        for filepath, size in files[:5]:  # 只显示前5个
            print(f"      - {filepath} ({size} bytes)")
        if len(files) > 5:
            print(f"      ... 还有 {len(files) - 5} 个文件")
        print("\n   💡 建议: 运行 python clean_output.py 清理后重试")
    else:
        print(f"   ✅ 输出目录为空")
else:
    print(f"   ℹ️  输出目录不存在（首次运行会自动创建）")

# 5. 检查数据库连接
print("\n5️⃣  检查数据库配置")
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '9030')
db_user = os.getenv('DB_USER', 'root')
db_name = os.getenv('DB_NAME', 'final_algorithm_competition')
print(f"   Host: {db_host}:{db_port}")
print(f"   User: {db_user}")
print(f"   Database: {db_name}")

try:
    from sqlalchemy import create_engine, text
    engine = create_engine(
        f"mysql+pymysql://{db_user}:{os.getenv('DB_PASSWORD', '')}@{db_host}:{db_port}/{db_name}"
    )
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("   ✅ 数据库连接成功！")
except Exception as e:
    print(f"   ❌ 数据库连接失败: {e}")

# 6. 推荐命令
print("\n" + "=" * 60)
print("📝 推荐的运行命令:")
print("=" * 60)
print("\n方案1: 清理后运行（推荐）")
print("   python clean_output.py")
print("   python run_starrocks.py --generation_model deepseek-reasoner --max_questions 1 --num_workers 1 --do_self_refinement")

print("\n方案2: 强制覆盖")
print("   python run_starrocks.py --generation_model deepseek-reasoner --max_questions 1 --num_workers 1 --do_self_refinement --overwrite_unfinished")

print("\n方案3: 使用debug模式")
print("   python debug_run.py")

print("\n" + "=" * 60)
