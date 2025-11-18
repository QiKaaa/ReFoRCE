"""简单测试脚本"""
import os
from dotenv import load_dotenv

load_dotenv()

print("开始测试...")

# 1. 测试数据加载
from data_loader import DatasetLoader
dataset_path = "E:/Project/track3_2/final_for_student/data/final_dataset_example.json"
loader = DatasetLoader(dataset_path)
examples = loader.get_all_examples()
print(f"1. 加载 {len(examples)} 个问题")

# 2. 测试Schema加载
from schema_parser import SchemaParser
schema_path = "E:/Project/track3_2/M-schema/final_algorithm_competition.txt"
parser = SchemaParser(schema_path)
print(f"2. 加载 {len(parser.tables)} 个表定义")

# 3. 测试Chat API
print("3. 测试Chat API...")
from chat import GPTChat

api_key = os.getenv('DS_API_KEY')
print(f"   API Key: {api_key[:10]}...")

try:
    chat = GPTChat(False, "deepseek-reasoner", temperature=0)
    response = chat.generate_one(messages=[{"role": "user", "content": "Say hello"}])
    print(f"   API响应: {response[:50]}...")
except Exception as e:
    print(f"   错误: {e}")
    import traceback
    traceback.print_exc()

print("测试完成!")
