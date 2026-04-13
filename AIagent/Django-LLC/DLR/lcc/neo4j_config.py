"""
Neo4j数据库配置
"""

import os
from django.conf import settings

class Neo4jConfig:
    """Neo4j数据库配置"""
    
    # 连接配置
    URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    USER = os.getenv('NEO4J_USER', 'neo4j')
    PASSWORD = os.getenv('NEO4J_PASSWORD', 'kg123456')
    DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    # 连接池配置
    MAX_CONNECTION_LIFETIME = 30 * 60  # 30分钟
    MAX_CONNECTION_POOL_SIZE = 50
    CONNECTION_ACQUISITION_TIMEOUT = 60  # 60秒
    CONNECTION_TIMEOUT = 30  # 30秒
    
    # 知识图谱配置
    DEFAULT_KG_DATABASE = 'knowledge_graph'
    
    @classmethod
    def get_driver_config(cls):
        """获取驱动配置"""
        return {
            'max_connection_lifetime': cls.MAX_CONNECTION_LIFETIME,
            'max_connection_pool_size': cls.MAX_CONNECTION_POOL_SIZE,
            'connection_acquisition_timeout': cls.CONNECTION_ACQUISITION_TIMEOUT,
            'connection_timeout': cls.CONNECTION_TIMEOUT,
            'encrypted': False  # 本地开发环境
        }
