"""
数据加载器 - 加载final_dataset_example.json
"""
import json
from typing import List, Dict


class DatasetLoader:
    """加载和管理final_dataset数据集"""
    
    def __init__(self, json_path: str):
        """
        初始化数据加载器
        
        Args:
            json_path: JSON数据集路径
        """
        self.json_path = json_path
        self.data = []
        self._load_data()
    
    def _load_data(self):
        """加载JSON数据"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        print(f"✓ 加载了 {len(self.data)} 个问题")
    
    def get_all_examples(self) -> List[Dict]:
        """获取所有示例"""
        return self.data
    
    def get_example_by_id(self, sql_id: str) -> Dict:
        """根据sql_id获取示例"""
        for example in self.data:
            if example.get('sql_id') == sql_id:
                return example
        return None
    
    def get_example_dict(self) -> Dict[str, Dict]:
        """
        获取示例字典 {sql_id: example}
        
        Returns:
            dict: 以sql_id为key的字典
        """
        return {ex['sql_id']: ex for ex in self.data}
    
    def get_questions_dict(self) -> Dict[str, str]:
        """
        获取问题字典 {sql_id: question}
        兼容原有的task_dict格式
        
        Returns:
            dict: 以sql_id为key，question为value的字典
        """
        return {ex['sql_id']: ex['question'] for ex in self.data}
    
    def filter_by_complexity(self, complexity: str) -> List[Dict]:
        """
        根据复杂度过滤
        
        Args:
            complexity: 复杂度（简单/中等/复杂）
            
        Returns:
            list: 过滤后的示例列表
        """
        return [ex for ex in self.data if ex.get('复杂度') == complexity]
    
    def get_statistics(self) -> Dict:
        """获取数据集统计信息"""
        complexities = {}
        total_tables = set()
        
        for ex in self.data:
            # 统计复杂度分布
            complexity = ex.get('复杂度', '未知')
            complexities[complexity] = complexities.get(complexity, 0) + 1
            
            # 统计涉及的表
            for table in ex.get('table_list', []):
                total_tables.add(table)
        
        return {
            'total_examples': len(self.data),
            'complexity_distribution': complexities,
            'total_unique_tables': len(total_tables),
            'tables': list(total_tables)
        }


if __name__ == "__main__":
    # 测试代码
    loader = DatasetLoader("E:/Project/track3_2/final_for_student/data/final_dataset_example.json")
    
    print("\n数据集统计:")
    stats = loader.get_statistics()
    for key, value in stats.items():
        if key != 'tables':
            print(f"  {key}: {value}")
    
    print("\n第一个示例:")
    first_ex = loader.get_all_examples()[0]
    print(f"  SQL ID: {first_ex['sql_id']}")
    print(f"  Question: {first_ex['question'][:100]}...")
    print(f"  Tables: {first_ex['table_list']}")
    print(f"  Complexity: {first_ex['复杂度']}")
