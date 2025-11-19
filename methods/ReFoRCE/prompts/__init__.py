"""
Prompt 管理包
统一管理所有 System/User Prompt
"""

from .base_prompts import BasePromptManager
from .starrocks_prompts import StarRocksPromptManager
from .schema_linking_prompts import SchemaLinkingPromptManager

__all__ = [
    'BasePromptManager',
    'StarRocksPromptManager',
    'SchemaLinkingPromptManager'
]
