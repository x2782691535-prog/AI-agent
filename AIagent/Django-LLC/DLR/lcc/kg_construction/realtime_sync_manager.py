"""
实时同步管理器 - 确保Django和Neo4j数据的实时一致性
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, Tuple
from django.utils import timezone

logger = logging.getLogger(__name__)

class RealtimeSyncManager:
    """实时同步管理器"""
    
    def __init__(self):
        self.neo4j_manager = None
        self._init_neo4j()
    
    def _init_neo4j(self):
        """初始化Neo4j连接"""
        try:
            from ..neo4j_manager import neo4j_manager
            self.neo4j_manager = neo4j_manager
        except Exception as e:
            logger.error(f"初始化Neo4j连接失败: {e}")
            self.neo4j_manager = None
    
    def create_entity_with_sync(self, kg, entity_data: Dict[str, Any], entity_type, doc_source=None) -> Tuple[Any, bool]:
        """
        创建实体并同步到Neo4j
        
        Args:
            kg: 知识图谱对象
            entity_data: 实体数据
            entity_type: 实体类型对象
            doc_source: 文档源对象
            
        Returns:
            (entity_record, neo4j_success): 实体记录和Neo4j同步是否成功
        """
        from ..models import EntityRecord
        
        entity_name = entity_data.get('name', '')
        neo4j_id = str(uuid.uuid4())
        neo4j_success = False
        
        # 1. 先尝试保存到Neo4j
        if self.neo4j_manager:
            try:
                neo4j_success = self._save_entity_to_neo4j(
                    kg_id=str(kg.id),
                    entity_id=neo4j_id,
                    name=entity_name,
                    entity_type=entity_type.name,
                    confidence=entity_data.get('confidence', 1.0),
                    properties=entity_data.get('properties', {}),
                    created_at=timezone.now()
                )
            except Exception as e:
                logger.error(f"保存实体到Neo4j失败 {entity_name}: {e}")
        
        # 2. 保存到Django（无论Neo4j是否成功）
        try:
            entity_record = EntityRecord.objects.create(
                knowledge_graph=kg,
                entity_type=entity_type,
                name=entity_name,
                confidence=entity_data.get('confidence', 1.0),
                neo4j_id=neo4j_id,
                source_document=doc_source,
                extraction_method=entity_data.get('extraction_method', 'structured_import'),
                properties=entity_data.get('properties', {})
            )
            
            if not neo4j_success:
                logger.warning(f"实体 {entity_name} 已保存到Django，但Neo4j同步失败")
            else:
                logger.debug(f"实体 {entity_name} 已成功同步到Django和Neo4j")
            
            return entity_record, neo4j_success
            
        except Exception as e:
            logger.error(f"保存实体到Django失败 {entity_name}: {e}")
            # 如果Django保存失败，尝试清理Neo4j中的数据
            if neo4j_success:
                self._cleanup_entity_from_neo4j(str(kg.id), neo4j_id)
            raise
    
    def create_relation_with_sync(self, kg, relation_data: Dict[str, Any], relation_type, 
                                 source_entity, target_entity, doc_source=None) -> Tuple[Any, bool]:
        """
        创建关系并同步到Neo4j
        
        Args:
            kg: 知识图谱对象
            relation_data: 关系数据
            relation_type: 关系类型对象
            source_entity: 源实体对象
            target_entity: 目标实体对象
            doc_source: 文档源对象
            
        Returns:
            (relation_record, neo4j_success): 关系记录和Neo4j同步是否成功
        """
        from ..models import RelationRecord
        
        neo4j_id = str(uuid.uuid4())
        neo4j_success = False
        
        # 1. 先尝试保存到Neo4j
        if self.neo4j_manager:
            try:
                # 使用实体的neo4j_id而不是Django的id
                neo4j_success = self._save_relation_to_neo4j(
                    kg_id=str(kg.id),
                    relation_id=neo4j_id,
                    source_entity_neo4j_id=source_entity.neo4j_id,
                    target_entity_neo4j_id=target_entity.neo4j_id,
                    relation_type=relation_type.name,
                    confidence=relation_data.get('confidence', 1.0),
                    properties=relation_data.get('properties', {}),
                    created_at=timezone.now()
                )
            except Exception as e:
                logger.error(f"保存关系到Neo4j失败 {source_entity.name} -> {target_entity.name}: {e}")
        
        # 2. 保存到Django（无论Neo4j是否成功）
        try:
            relation_record = RelationRecord.objects.create(
                knowledge_graph=kg,
                relation_type=relation_type,
                source_entity=source_entity,
                target_entity=target_entity,
                confidence=relation_data.get('confidence', 1.0),
                neo4j_id=neo4j_id,
                source_document=doc_source,
                source_text=relation_data.get('text', ''),
                extraction_method=relation_data.get('extraction_method', 'structured_import'),
                properties=relation_data.get('properties', {})
            )
            
            if not neo4j_success:
                logger.warning(f"关系 {source_entity.name} -> {target_entity.name} 已保存到Django，但Neo4j同步失败")
            else:
                logger.debug(f"关系 {source_entity.name} -> {target_entity.name} 已成功同步到Django和Neo4j")
            
            return relation_record, neo4j_success
            
        except Exception as e:
            logger.error(f"保存关系到Django失败 {source_entity.name} -> {target_entity.name}: {e}")
            # 如果Django保存失败，尝试清理Neo4j中的数据
            if neo4j_success:
                self._cleanup_relation_from_neo4j(str(kg.id), neo4j_id)
            raise
    
    def _save_entity_to_neo4j(self, kg_id: str, entity_id: str, name: str, entity_type: str, 
                             confidence: float, properties: Dict, created_at) -> bool:
        """保存实体到Neo4j"""
        try:
            with self.neo4j_manager.get_session() as session:
                query = """
                CREATE (n:Entity {
                    knowledge_graph_id: $kg_id,
                    entity_id: $entity_id,
                    name: $name,
                    type: $entity_type,
                    confidence: $confidence,
                    properties_json: $properties_json,
                    created_at: datetime($created_at)
                })
                """
                
                properties_json = json.dumps(properties, ensure_ascii=False)
                
                session.run(query,
                           kg_id=kg_id,
                           entity_id=entity_id,
                           name=name,
                           entity_type=entity_type,
                           confidence=confidence,
                           properties_json=properties_json,
                           created_at=created_at.isoformat())
                
                return True
                
        except Exception as e:
            logger.error(f"Neo4j实体保存失败: {e}")
            return False
    
    def _save_relation_to_neo4j(self, kg_id: str, relation_id: str, source_entity_neo4j_id: str,
                               target_entity_neo4j_id: str, relation_type: str, confidence: float,
                               properties: Dict, created_at) -> bool:
        """保存关系到Neo4j"""
        try:
            with self.neo4j_manager.get_session() as session:
                # 首先查找源实体和目标实体
                source_query = "MATCH (n:Entity {knowledge_graph_id: $kg_id, entity_id: $entity_id}) RETURN n"
                source_result = session.run(source_query, kg_id=kg_id, entity_id=source_entity_neo4j_id)
                source_exists = source_result.single() is not None

                target_query = "MATCH (n:Entity {knowledge_graph_id: $kg_id, entity_id: $entity_id}) RETURN n"
                target_result = session.run(target_query, kg_id=kg_id, entity_id=target_entity_neo4j_id)
                target_exists = target_result.single() is not None

                if not source_exists:
                    logger.error(f"源实体不存在于Neo4j: {source_entity_neo4j_id}")
                    return False

                if not target_exists:
                    logger.error(f"目标实体不存在于Neo4j: {target_entity_neo4j_id}")
                    return False

                query = """
                MATCH (source:Entity {knowledge_graph_id: $kg_id, entity_id: $source_id})
                MATCH (target:Entity {knowledge_graph_id: $kg_id, entity_id: $target_id})
                CREATE (source)-[r:RELATES {
                    knowledge_graph_id: $kg_id,
                    relation_id: $relation_id,
                    type: $relation_type,
                    confidence: $confidence,
                    properties_json: $properties_json,
                    created_at: datetime($created_at)
                }]->(target)
                """

                properties_json = json.dumps(properties, ensure_ascii=False)

                session.run(query,
                           kg_id=kg_id,
                           source_id=source_entity_neo4j_id,
                           target_id=target_entity_neo4j_id,
                           relation_id=relation_id,
                           relation_type=relation_type,
                           confidence=confidence,
                           properties_json=properties_json,
                           created_at=created_at.isoformat())
                
                return True
                
        except Exception as e:
            logger.error(f"Neo4j关系保存失败: {e}")
            return False
    
    def _cleanup_entity_from_neo4j(self, kg_id: str, entity_id: str):
        """从Neo4j清理实体"""
        try:
            with self.neo4j_manager.get_session() as session:
                query = "MATCH (n:Entity {knowledge_graph_id: $kg_id, entity_id: $entity_id}) DELETE n"
                session.run(query, kg_id=kg_id, entity_id=entity_id)
        except Exception as e:
            logger.error(f"清理Neo4j实体失败: {e}")
    
    def _cleanup_relation_from_neo4j(self, kg_id: str, relation_id: str):
        """从Neo4j清理关系"""
        try:
            with self.neo4j_manager.get_session() as session:
                query = "MATCH ()-[r:RELATES {knowledge_graph_id: $kg_id, relation_id: $relation_id}]->() DELETE r"
                session.run(query, kg_id=kg_id, relation_id=relation_id)
        except Exception as e:
            logger.error(f"清理Neo4j关系失败: {e}")

# 全局实例
realtime_sync_manager = RealtimeSyncManager()
