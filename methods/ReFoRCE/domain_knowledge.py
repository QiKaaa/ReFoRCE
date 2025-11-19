"""
业务领域通用知识库
管理数据集所处场景下的通用业务规则
"""

class DomainKnowledge:
    """业务领域知识管理器"""
    
    # ==================== 通用业务规则 ====================
    
    GENERAL_BUSINESS_RULES = """
## 游戏场景下数据分析业务通用规则

### 游戏业务场景建模

理解游戏数据库中的核心实体及其关系是正确识别外键的基础。

### 实体层级结构
```
自然人 (swxid + swxid_type)
    ↓ 1对N (一人多号)
游戏账号 (*userid / *playerid)  
    ↓ 1对N (一号多角色)
游戏角色 (*roleid)
    ↓ 1对N (一角色多行为)
游戏行为 (登录/充值/任务等)
```

### 实体识别规则

#### 1. 自然人 → 账号映射
- **swxid字段**: 
  - 同一swxid在不同表中标识同一自然人
  - 需结合swxid_type确认平台（微信/QQ）
  - 一个自然人可能拥有多个游戏账号
  
- **关联场景**:
  - 用户注册表 ↔ 账号表（通过swxid）
  - 实名信息表 ↔ 账号表（通过swxid）

#### 2. 账号 → 角色映射
- **userid/playerid字段**:
  - 同一账号可创建多个游戏角色
  - 注意字段命名的前缀变化（game_userid, main_userid等）
  
- **roleid字段**:
  - 标识具体的游戏角色
  - 可能有主角色(main_roleid)和普通角色的区分
  
- **关联场景**:
  - 账号表 ↔ 角色表（userid → roleid）
  - 角色表 ↔ 角色行为表（roleid关联）

### 3. 统计注意事项 
* **对用户统计去重** - 满足以下任一条件时必须使用`DISTINCT`:
    - 问题要求统计**用户数**（如"有多少用户"、"用户数量"、"几个用户"）
    - 问题要求统计**用户ID**（如"用户ID数"、"不同用户ID"）
    - 问题或schema_link中涉及到**用户数/用户ID**的计算或比较
    - **用户相关字段**: `suerid`, `iuserid`, `swxid`
    - **正确示例**: 
    * "有多少用户购买了商品" → `COUNT(DISTINCT suerid)`
    * "统计用户数" → `COUNT(DISTINCT iuserid)`

* **对玩家统计去重** - 满足以下任一条件时必须使用`DISTINCT`:
    - 问题要求统计**玩家数**（如"有多少玩家"、"玩家数量"、"几个玩家"）
    - 问题要求统计**玩家ID**（如"玩家ID数"、"不同玩家ID"）
    - 问题或schema_link中涉及到**玩家数/玩家ID**的计算或比较
    - **玩家相关字段**: `gplayerid`, `vplayerid`
    - **正确示例**: 
    * "有多少玩家参与了活动" → `COUNT(DISTINCT gplayerid)`
    * "统计玩家数" → `COUNT(DISTINCT vplayerid)`
"""
    
    # ==================== 特定场景规则 ====================
    
    ONLINE_DURATION_RULES = """
## 在线时长统计规则

### 计算公式
- 总在线时长: `SUM(iloginminutes)`
- 平均在线时长: `AVG(iloginminutes)`
- 在线用户数: `COUNT(DISTINCT userid)`

### 过滤条件
- `iloginminutes > 0` (排除无效数据)
- `factivedays > 0` (活跃天数大于0)

### 示例查询
```sql
SELECT 
    sgamecode,
    SUM(iloginminutes) AS total_minutes,
    COUNT(DISTINCT userid) AS user_count,
    ROUND(AVG(iloginminutes), 2) AS avg_minutes
FROM table_name
WHERE dtstatdate BETWEEN 20250530 AND 20250724
  AND iloginminutes > 0
  AND sgamecode IN ('initiatived','jordass',...)
GROUP BY sgamecode
```
"""
    
    ACTIVE_USER_RULES = """
## 活跃用户统计规则

### 活跃用户定义
- 登录天数 > 0: `ilogindays > 0`
- 或活跃天数 > 0: `factivedays > 0`

### 统计方法
- 去重统计: `COUNT(DISTINCT userid)`
- 分组统计: 按日期/游戏/标签分组

### 注意事项
- 避免重复统计同一用户
- 时间范围必须明确
- 考虑用户类型筛选 (QQ/微信)
"""
    
    # ==================== 公开方法 ====================
    
    @classmethod
    def get_general_rules(cls) -> str:
        """获取通用业务规则"""
        return cls.GENERAL_BUSINESS_RULES
    
    @classmethod
    def get_online_duration_rules(cls) -> str:
        """获取在线时长统计规则"""
        return cls.ONLINE_DURATION_RULES
    
    @classmethod
    def get_active_user_rules(cls) -> str:
        """获取活跃用户统计规则"""
        return cls.ACTIVE_USER_RULES
    
    @classmethod
    def get_all_rules(cls) -> str:
        """获取所有业务规则"""
        return f"""{cls.GENERAL_BUSINESS_RULES}

{cls.ONLINE_DURATION_RULES}

{cls.ACTIVE_USER_RULES}"""
    
    @classmethod
    def get_rules_for_prompt(cls, include_specific: bool = True) -> str:
        """
        获取适合加入Prompt的业务规则
        
        Args:
            include_specific: 是否包含特定场景规则
        
        Returns:
            格式化的业务规则文本
        """
        rules = cls.GENERAL_BUSINESS_RULES
        
        if include_specific:
            rules += f"\n\n{cls.ONLINE_DURATION_RULES}"
            rules += f"\n\n{cls.ACTIVE_USER_RULES}"
        
        return rules
