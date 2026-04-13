"""
Neo4j数据库连接管理器
"""

from neo4j import GraphDatabase
from django.conf import settings
from .neo4j_config import Neo4jConfig
import logging

logger = logging.getLogger(__name__)

class Neo4jManager:
    """Neo4j数据库连接管理器"""
    
    _instance = None
    _driver = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._driver is None:
            self.connect()
    
    def connect(self):
        """建立Neo4j连接"""
        try:
            self._driver = GraphDatabase.driver(
                Neo4jConfig.URI,
                auth=(Neo4jConfig.USER, Neo4jConfig.PASSWORD),
                **Neo4jConfig.get_driver_config()
            )
            logger.info("Neo4j连接建立成功")
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            raise
    
    def get_session(self, database=None):
        """获取数据库会话"""
        if self._driver is None:
            self.connect()
        
        db_name = database or Neo4jConfig.DATABASE
        return self._driver.session(database=db_name)
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j连接已关闭")
    
    def test_connection(self):
        """测试连接"""
        try:
            with self.get_session() as session:
                result = session.run("RETURN 'Hello Neo4j!' as message")
                record = result.single()
                return {
                    'success': True,
                    'message': record['message'],
                    'version': self.get_version()
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_version(self):
        """获取Neo4j版本"""
        try:
            with self.get_session() as session:
                result = session.run("CALL dbms.components() YIELD name, versions")
                for record in result:
                    if record['name'] == 'Neo4j Kernel':
                        return record['versions'][0]
                return 'Unknown'
        except:
            return 'Unknown'
    
    def get_database_stats(self):
        """获取数据库统计信息"""
        try:
            with self.get_session() as session:
                # 节点数量
                node_result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = node_result.single()['count']
                
                # 关系数量
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = rel_result.single()['count']
                
                # 标签统计
                labels = {}
                try:
                    label_result = session.run("CALL db.labels() YIELD label RETURN label")
                    for record in label_result:
                        label = record['label']
                        count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                        count = count_result.single()['count']
                        labels[label] = count
                except:
                    # 如果查询失败，使用简单统计
                    labels = {'Total': node_count}
                
                return {
                    'node_count': node_count,
                    'relationship_count': rel_count,
                    'labels': labels
                }
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {
                'node_count': 0,
                'relationship_count': 0,
                'labels': {}
            }

# 创建全局实例
neo4j_manager = Neo4jManager()
