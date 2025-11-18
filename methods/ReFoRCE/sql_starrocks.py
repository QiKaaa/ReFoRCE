"""
StarRocks SQL执行引擎 - 替代原有的sql.py
支持通过SQLAlchemy连接StarRocks数据库
"""
import io
import csv
import pandas as pd
from sqlalchemy import create_engine, text
from func_timeout import func_timeout, FunctionTimedOut
from utils import hard_cut


class SqlEnvStarRocks:
    """StarRocks SQL执行环境"""
    
    def __init__(self, host="localhost", port=9030, user="root", password="", database="final_algorithm_competition"):
        """
        初始化StarRocks连接
        
        Args:
            host: StarRocks主机地址
            port: StarRocks端口
            user: 用户名
            password: 密码
            database: 数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.engine = None
        self.conn = None
        
    def connect(self):
        """建立数据库连接"""
        if self.engine is None:
            # 构建连接字符串
            connection_string = f"starrocks://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self.engine = create_engine(connection_string)
            print(f"✓ 已连接到 StarRocks: {self.host}:{self.port}/{self.database}")
    
    def get_rows(self, result, max_len):
        """获取查询结果行，限制总长度"""
        rows = []
        current_len = 0
        for row in result:
            row_tuple = tuple(row)
            row_str = str(row_tuple)
            if current_len + len(row_str) > max_len:
                break
            rows.append(row_tuple)
            current_len += len(row_str)
        return rows
    
    def get_csv(self, columns, rows):
        """将结果转换为CSV格式"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        csv_content = output.getvalue()
        output.close()
        return csv_content
    
    def exec_sql_starrocks(self, sql_query, save_path=None, max_len=30000):
        """
        执行StarRocks SQL查询
        
        Args:
            sql_query: SQL查询语句
            save_path: 保存结果的路径（可选）
            max_len: 最大返回长度
            
        Returns:
            str: 成功返回"0"（已保存）或CSV内容，失败返回错误信息
        """
        try:
            self.connect()
            
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                
                # 获取列名
                columns = list(result.keys())
                
                # 获取数据行
                rows = self.get_rows(result, max_len)
                
                if not rows:
                    return "No data found for the specified query.\n"
                
                # 生成CSV
                csv_content = self.get_csv(columns, rows)
                
                # 保存或返回
                if save_path:
                    with open(save_path, 'w', newline='', encoding='utf-8') as f:
                        f.write(csv_content)
                    return "0"  # 成功标志
                else:
                    return hard_cut(csv_content, max_len)
                    
        except Exception as e:
            return f"##ERROR##{str(e)}"
    
    def execute_sql_api(self, sql_query, ex_id, save_path=None, api="starrocks", 
                       max_len=30000, sqlite_path=None, timeout=300):
        """
        统一的SQL执行接口（兼容原有接口）
        
        Args:
            sql_query: SQL查询
            ex_id: 示例ID
            save_path: 保存路径
            api: API类型（默认starrocks）
            max_len: 最大长度
            sqlite_path: SQLite路径（本实现中不使用）
            timeout: 超时时间（秒）
            
        Returns:
            str: "0"表示成功，其他为结果或错误
        """
        try:
            result = func_timeout(
                timeout, 
                self.exec_sql_starrocks, 
                args=(sql_query, save_path, max_len)
            )
            
            if "##ERROR##" in str(result):
                return {"status": "error", "error_msg": str(result)}
            else:
                return str(result)
                
        except FunctionTimedOut:
            error_msg = f"##ERROR## Query timed out after {timeout}s: {sql_query[:100]}..."
            print(error_msg)
            return {"status": "error", "error_msg": error_msg}
            
        except Exception as e:
            error_msg = f"##ERROR## Exception: {str(e)}"
            print(error_msg)
            return {"status": "error", "error_msg": error_msg}
    
    def close_db(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            print("✓ StarRocks连接已关闭")


# 向后兼容的别名
SqlEnv = SqlEnvStarRocks
