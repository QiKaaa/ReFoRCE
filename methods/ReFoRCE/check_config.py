#!/usr/bin/env python3
"""
配置检查脚本
验证 .env 文件中的配置是否正确
"""
import os
import sys
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

def check_api_keys():
    """检查 API Key 配置"""
    print("=" * 50)
    print("📋 API Key 配置检查")
    print("=" * 50)
    
    openai_key = os.getenv('OPENAI_API_KEY')
    azure_endpoint = os.getenv('AZURE_ENDPOINT')
    azure_key = os.getenv('AZURE_OPENAI_KEY')
    ds_key = os.getenv('DS_API_KEY')
    
    has_valid_config = False
    
    # 检查 OpenAI
    if openai_key:
        if openai_key == "sk-your-api-key-here":
            print("⚠️  OpenAI Key: 使用的是示例值，请替换为真实 API Key")
        else:
            print(f"✅ OpenAI Key: {openai_key[:10]}...")
            has_valid_config = True
    else:
        print("❌ OpenAI Key: 未设置")
    
    # 检查 Azure
    if azure_endpoint and azure_key:
        print(f"✅ Azure Endpoint: {azure_endpoint}")
        print(f"✅ Azure Key: {azure_key[:10]}...")
        has_valid_config = True
    elif azure_endpoint or azure_key:
        print("⚠️  Azure OpenAI: 配置不完整（需要同时设置 AZURE_ENDPOINT 和 AZURE_OPENAI_KEY）")
    
    # 检查 DeepSeek
    if ds_key:
        print(f"✅ DeepSeek Key: {ds_key[:10]}...")
        has_valid_config = True
    
    if not has_valid_config:
        print("\n❌ 错误: 未找到有效的 API Key 配置")
        print("请在 .env 文件中配置以下之一：")
        print("  - OPENAI_API_KEY")
        print("  - AZURE_ENDPOINT + AZURE_OPENAI_KEY")
        print("  - DS_API_KEY")
        return False
    
    return True

def check_db_config():
    """检查数据库配置"""
    print("\n" + "=" * 50)
    print("🗄️  数据库配置检查")
    print("=" * 50)
    
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '9030')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'final_algorithm_competition')
    
    print(f"✅ Host: {db_host}")
    print(f"✅ Port: {db_port}")
    print(f"✅ User: {db_user}")
    print(f"✅ Password: {'(已设置)' if db_password else '(空)'}")
    print(f"✅ Database: {db_name}")
    
    return True

def check_db_connection():
    """测试数据库连接"""
    print("\n" + "=" * 50)
    print("🔌 数据库连接测试")
    print("=" * 50)
    
    try:
        from sqlalchemy import create_engine, text
        
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '9030')
        db_user = os.getenv('DB_USER', 'root')
        db_password = os.getenv('DB_PASSWORD', '')
        db_name = os.getenv('DB_NAME', 'final_algorithm_competition')
        
        # 构建连接字符串
        if db_password:
            conn_str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            conn_str = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"
        
        print(f"连接字符串: mysql+pymysql://{db_user}:***@{db_host}:{db_port}/{db_name}")
        
        # 尝试连接
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print("✅ 数据库连接成功！")
        return True
        
    except ImportError:
        print("⚠️  跳过连接测试（未安装 sqlalchemy 或 pymysql）")
        print("   安装命令: uv pip install sqlalchemy pymysql")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n请检查：")
        print("  1. StarRocks 是否正在运行？")
        print("  2. 连接参数是否正确？")
        print("  3. 数据库是否存在？")
        return False

def check_env_file():
    """检查 .env 文件是否存在"""
    print("=" * 50)
    print("📄 .env 文件检查")
    print("=" * 50)
    
    env_path = os.path.join(os.getcwd(), '.env')
    
    if os.path.exists('.env'):
        print(f"✅ 找到 .env 文件: {env_path}")
        
        # 显示文件大小
        size = os.path.getsize('.env')
        print(f"   文件大小: {size} 字节")
        
        # 检查文件内容
        with open('.env', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            non_empty_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
            print(f"   配置项数: {len(non_empty_lines)}")
        
        return True
    else:
        print(f"⚠️  未找到 .env 文件: {env_path}")
        print("\n建议：")
        print("  1. 复制模板: cp .env.example .env")
        print("  2. 编辑配置: notepad .env")
        print("  3. 重新运行此脚本")
        return False

def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║" + " " * 12 + "ReFoRCE 配置检查工具" + " " * 14 + "║")
    print("╚" + "=" * 48 + "╝")
    print()
    
    results = []
    
    # 1. 检查 .env 文件
    results.append(("环境文件", check_env_file()))
    
    # 2. 检查 API Keys
    results.append(("API配置", check_api_keys()))
    
    # 3. 检查数据库配置
    results.append(("数据库配置", check_db_config()))
    
    # 4. 测试数据库连接
    results.append(("数据库连接", check_db_connection()))
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 检查结果汇总")
    print("=" * 50)
    
    for name, status in results:
        icon = "✅" if status else "❌"
        print(f"{icon} {name}: {'通过' if status else '失败'}")
    
    all_passed = all(status for _, status in results)
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有检查通过！可以开始使用了。")
        print("\n运行示例：")
        print("  python run_starrocks.py --max_questions 1 --generation_model gpt-4o")
    else:
        print("⚠️  存在配置问题，请根据上述提示修复。")
        print("\n需要帮助？查看文档：")
        print("  - START_HERE.md - 快速开始")
        print("  - ENV_CONFIG.md - 配置详解")
    print("=" * 50)
    print()
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
