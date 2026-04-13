"""
知识图谱构建器
整合文本处理、实体识别、关系抽取等模块，构建完整的知识图谱
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import uuid
from django.utils import timezone

from ..text_processing.document_parser import DocumentParser
from ..text_processing.text_preprocessor import TextPreprocessor
from ..entity_recognition.chinese_ner import ChineseNER, Entity
from ..relation_extraction.relation_extractor import RelationExtractor, Relation
from ..entity_linking.entity_linker import EntityLinker
from ..neo4j_manager import neo4j_manager
from ..models import (
    KnowledgeGraph, DocumentSource, EntityRecord, RelationRecord,
    ProcessingTask, EntityType, RelationType
)

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self):
        # 初始化各个组件
        self.document_parser = DocumentParser()
        self.text_preprocessor = TextPreprocessor()
        self.entity_recognizer = ChineseNER()
        self.relation_extractor = RelationExtractor()
        self.entity_linker = EntityLinker()
    
    def build_from_document(self, document_path: str, knowledge_graph_id: int, 
                          user_id: int, options: Dict = None) -> Dict:
        """
        从文档构建知识图谱
        
        Args:
            document_path: 文档路径
            knowledge_graph_id: 知识图谱ID
            user_id: 用户ID
            options: 构建选项
            
        Returns:
            Dict: 构建结果
        """
        options = options or {}
        
        try:
            # 1. 创建处理任务
            task = self._create_processing_task(
                knowledge_graph_id, user_id, 'document_processing', 
                f'处理文档: {document_path}'
            )
            
            # 2. 解析文档
            self._update_task_progress(task, 10, '解析文档...')
            doc_result = self.document_parser.parse_document(document_path)
            
            if not doc_result['success']:
                self._update_task_status(task, 'failed', f"文档解析失败: {doc_result['error']}")
                return {'success': False, 'error': doc_result['error']}
            
            # 3. 创建文档记录
            self._update_task_progress(task, 20, '创建文档记录...')
            doc_source = self._create_document_source(doc_result, knowledge_graph_id, user_id)
            
            # 4. 文本预处理
            self._update_task_progress(task, 30, '文本预处理...')
            text_result = self.text_preprocessor.preprocess_text(
                doc_result['content'], options.get('preprocess_options', {})
            )
            
            # 5. 实体识别
            self._update_task_progress(task, 50, '实体识别...')
            entities = self.entity_recognizer.extract_entities(
                text_result['cleaned_text'], 
                options.get('entity_types')
            )
            
            # 6. 关系抽取
            self._update_task_progress(task, 70, '关系抽取...')
            relations = self.relation_extractor.extract_relations(
                text_result['cleaned_text'], entities,
                options.get('relation_types')
            )
            
            # 7. 实体链接
            self._update_task_progress(task, 80, '实体链接...')
            linked_entities = self.entity_linker.link_entities(
                entities, text_result['cleaned_text'], str(knowledge_graph_id)
            )
            
            # 8. 保存到知识图谱
            self._update_task_progress(task, 90, '保存到知识图谱...')
            kg_result = self._save_to_knowledge_graph(
                linked_entities, relations, doc_source, knowledge_graph_id
            )
            
            # 9. 更新统计信息
            self._update_task_progress(task, 95, '更新统计信息...')
            self._update_knowledge_graph_stats(knowledge_graph_id)
            
            # 10. 完成任务
            self._update_task_status(
                task, 'completed', 
                f"成功处理文档，提取 {len(linked_entities)} 个实体，{len(relations)} 个关系"
            )
            
            result = {
                'success': True,
                'task_id': task.id,
                'document_id': doc_source.id,
                'entities_count': len(linked_entities),
                'relations_count': len(relations),
                'statistics': {
                    'text_stats': text_result['statistics'],
                    'entity_stats': self.entity_recognizer.get_entity_statistics(linked_entities),
                    'relation_stats': self.relation_extractor.get_relation_statistics(relations),
                    'linking_stats': self.entity_linker.get_linking_statistics(linked_entities)
                }
            }
            
            logger.info(f"成功构建知识图谱: {result}")
            return result
            
        except Exception as e:
            logger.error(f"知识图谱构建失败: {e}")
            if 'task' in locals():
                self._update_task_status(task, 'failed', str(e))
            return {'success': False, 'error': str(e)}
    
    def build_from_text(self, text: str, knowledge_graph_id: int, 
                       user_id: int, title: str = "文本输入", 
                       options: Dict = None) -> Dict:
        """
        从文本构建知识图谱
        
        Args:
            text: 输入文本
            knowledge_graph_id: 知识图谱ID
            user_id: 用户ID
            title: 文本标题
            options: 构建选项
            
        Returns:
            Dict: 构建结果
        """
        options = options or {}
        
        try:
            # 1. 创建处理任务
            task = self._create_processing_task(
                knowledge_graph_id, user_id, 'text_processing', 
                f'处理文本: {title}'
            )
            
            # 2. 创建虚拟文档记录
            self._update_task_progress(task, 10, '创建文档记录...')
            doc_source = self._create_text_document_source(
                text, title, knowledge_graph_id, user_id
            )
            
            # 3. 文本预处理
            self._update_task_progress(task, 30, '文本预处理...')
            text_result = self.text_preprocessor.preprocess_text(
                text, options.get('preprocess_options', {})
            )
            
            # 4. 实体识别
            self._update_task_progress(task, 50, '实体识别...')
            entities = self.entity_recognizer.extract_entities(
                text_result['cleaned_text'], 
                options.get('entity_types')
            )
            
            # 5. 关系抽取
            self._update_task_progress(task, 70, '关系抽取...')
            relations = self.relation_extractor.extract_relations(
                text_result['cleaned_text'], entities,
                options.get('relation_types')
            )
            
            # 6. 实体链接
            self._update_task_progress(task, 80, '实体链接...')
            linked_entities = self.entity_linker.link_entities(
                entities, text_result['cleaned_text'], str(knowledge_graph_id)
            )
            
            # 7. 保存到知识图谱
            self._update_task_progress(task, 90, '保存到知识图谱...')
            kg_result = self._save_to_knowledge_graph(
                linked_entities, relations, doc_source, knowledge_graph_id
            )
            
            # 8. 更新统计信息
            self._update_task_progress(task, 95, '更新统计信息...')
            self._update_knowledge_graph_stats(knowledge_graph_id)
            
            # 9. 完成任务
            self._update_task_status(
                task, 'completed', 
                f"成功处理文本，提取 {len(linked_entities)} 个实体，{len(relations)} 个关系"
            )
            
            result = {
                'success': True,
                'task_id': task.id,
                'document_id': doc_source.id,
                'entities_count': len(linked_entities),
                'relations_count': len(relations),
                'statistics': {
                    'text_stats': text_result['statistics'],
                    'entity_stats': self.entity_recognizer.get_entity_statistics(linked_entities),
                    'relation_stats': self.relation_extractor.get_relation_statistics(relations),
                    'linking_stats': self.entity_linker.get_linking_statistics(linked_entities)
                }
            }
            
            logger.info(f"成功从文本构建知识图谱: {result}")
            return result
            
        except Exception as e:
            logger.error(f"从文本构建知识图谱失败: {e}")
            if 'task' in locals():
                self._update_task_status(task, 'failed', str(e))
            return {'success': False, 'error': str(e)}
    
    def _create_processing_task(self, kg_id: int, user_id: int, 
                              task_type: str, description: str) -> ProcessingTask:
        """创建处理任务"""
        from lcc.models import User
        
        kg = KnowledgeGraph.objects.get(id=kg_id)
        user = User.objects.get(id=user_id)
        
        task = ProcessingTask.objects.create(
            knowledge_graph=kg,
            task_type=task_type,
            task_name=f"{task_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            description=description,
            status='running',
            created_by=user,
            started_at=timezone.now()
        )
        
        return task
    
    def _update_task_progress(self, task: ProcessingTask, progress: int, message: str):
        """更新任务进度"""
        task.progress = progress
        task.result_summary = message
        task.save()
        logger.debug(f"任务进度: {progress}% - {message}")
    
    def _update_task_status(self, task: ProcessingTask, status: str, message: str):
        """更新任务状态"""
        task.status = status
        task.result_summary = message
        if status in ['completed', 'failed']:
            task.completed_at = timezone.now()
            if task.started_at:
                task.execution_time = (task.completed_at - task.started_at).total_seconds()
        task.save()
        logger.info(f"任务状态更新: {status} - {message}")
    
    def _create_document_source(self, doc_result: Dict, kg_id: int, user_id: int) -> DocumentSource:
        """创建文档来源记录"""
        from lcc.models import User
        import hashlib
        
        kg = KnowledgeGraph.objects.get(id=kg_id)
        user = User.objects.get(id=user_id)
        
        # 计算文件哈希
        content_hash = hashlib.md5(doc_result['content'].encode()).hexdigest()
        
        doc_source = DocumentSource.objects.create(
            knowledge_graph=kg,
            title=doc_result.get('title', doc_result['file_name']),
            file_name=doc_result['file_name'],
            file_path=doc_result['file_path'],
            file_type=doc_result['file_type'].replace('.', ''),
            file_size=doc_result['file_size'],
            file_hash=content_hash,
            content=doc_result['content'],
            metadata=doc_result.get('metadata', {}),
            processing_status='processing',
            uploaded_by=user
        )
        
        return doc_source
    
    def _create_text_document_source(self, text: str, title: str, 
                                   kg_id: int, user_id: int) -> DocumentSource:
        """创建文本文档来源记录"""
        from lcc.models import User
        import hashlib
        
        kg = KnowledgeGraph.objects.get(id=kg_id)
        user = User.objects.get(id=user_id)
        
        # 计算文本哈希
        content_hash = hashlib.md5(text.encode()).hexdigest()
        
        doc_source = DocumentSource.objects.create(
            knowledge_graph=kg,
            title=title,
            file_name=f"{title}.txt",
            file_path=f"text_input_{timezone.now().strftime('%Y%m%d_%H%M%S')}.txt",
            file_type='txt',
            file_size=len(text.encode()),
            file_hash=content_hash,
            content=text,
            processing_status='processing',
            uploaded_by=user
        )
        
        return doc_source

    def _save_to_knowledge_graph(self, entities: List[Entity], relations: List[Relation],
                               doc_source: DocumentSource, kg_id: int) -> Dict:
        """保存实体和关系到知识图谱"""
        saved_entities = 0
        saved_relations = 0

        try:
            with neo4j_manager.get_session() as session:
                # 保存实体
                for entity in entities:
                    neo4j_id = self._save_entity_to_neo4j(entity, doc_source, session)
                    if neo4j_id:
                        self._save_entity_record(entity, neo4j_id, doc_source)
                        saved_entities += 1

                # 保存关系
                for relation in relations:
                    neo4j_id = self._save_relation_to_neo4j(relation, doc_source, session)
                    if neo4j_id:
                        self._save_relation_record(relation, neo4j_id, doc_source)
                        saved_relations += 1

            # 更新文档处理状态
            doc_source.processing_status = 'completed'
            doc_source.processed_at = timezone.now()
            doc_source.entity_extracted = saved_entities
            doc_source.relation_extracted = saved_relations
            doc_source.save()

            return {
                'saved_entities': saved_entities,
                'saved_relations': saved_relations
            }

        except Exception as e:
            logger.error(f"保存到知识图谱失败: {e}")
            doc_source.processing_status = 'failed'
            doc_source.error_message = str(e)
            doc_source.save()
            raise e

    def _save_entity_to_neo4j(self, entity: Entity, doc_source: DocumentSource, session) -> str:
        """保存实体到Neo4j"""
        try:
            # 检查是否已链接到现有实体
            neo4j_id = entity.properties.get('neo4j_id')

            if neo4j_id:
                # 更新现有实体
                update_query = """
                MATCH (e:Entity {id: $neo4j_id})
                SET e.updated_at = datetime(),
                    e.confidence = CASE WHEN $confidence > e.confidence THEN $confidence ELSE e.confidence END
                RETURN e.id as neo4j_id
                """

                result = session.run(update_query, {
                    'neo4j_id': neo4j_id,
                    'confidence': entity.confidence
                })

                record = result.single()
                return record['neo4j_id'] if record else None

            else:
                # 创建新实体
                entity_id = str(uuid.uuid4())

                create_query = """
                CREATE (e:Entity {
                    id: $entity_id,
                    name: $name,
                    type: $entity_type,
                    domain: $domain,
                    description: $description,
                    confidence: $confidence,
                    source: $source,
                    created_at: datetime(),
                    updated_at: datetime(),
                    knowledge_graph_id: $kg_id,
                    document_id: $doc_id
                })
                RETURN e.id as neo4j_id
                """

                params = {
                    'entity_id': entity_id,
                    'name': entity.text,
                    'entity_type': entity.entity_type,
                    'domain': doc_source.knowledge_graph.domain,
                    'description': entity.properties.get('description', ''),
                    'confidence': entity.confidence,
                    'source': 'extraction',
                    'kg_id': str(doc_source.knowledge_graph.id),
                    'doc_id': str(doc_source.id)
                }

                result = session.run(create_query, params)
                record = result.single()
                return record['neo4j_id'] if record else None

        except Exception as e:
            logger.error(f"保存实体到Neo4j失败: {e}")
            return None

    def _save_relation_to_neo4j(self, relation: Relation, doc_source: DocumentSource, session) -> str:
        """保存关系到Neo4j"""
        try:
            # 获取源实体和目标实体的Neo4j ID
            source_neo4j_id = relation.source_entity.properties.get('neo4j_id')
            target_neo4j_id = relation.target_entity.properties.get('neo4j_id')

            if not source_neo4j_id or not target_neo4j_id:
                logger.warning(f"关系的源实体或目标实体缺少Neo4j ID: {relation.source_entity.text} -> {relation.target_entity.text}")
                # 尝试通过实体名称查找Neo4j ID
                source_query = session.run("""
                    MATCH (e:Entity)
                    WHERE e.name = $name AND e.knowledge_graph_id = $kg_id
                    RETURN e.id as neo4j_id
                """, name=relation.source_entity.text, kg_id=str(doc_source.knowledge_graph.id))

                source_result = source_query.single()
                if source_result:
                    source_neo4j_id = source_result['neo4j_id']

                target_query = session.run("""
                    MATCH (e:Entity)
                    WHERE e.name = $name AND e.knowledge_graph_id = $kg_id
                    RETURN e.id as neo4j_id
                """, name=relation.target_entity.text, kg_id=str(doc_source.knowledge_graph.id))

                target_result = target_query.single()
                if target_result:
                    target_neo4j_id = target_result['neo4j_id']

                if not source_neo4j_id or not target_neo4j_id:
                    logger.warning(f"仍然无法找到实体的Neo4j ID: {relation.source_entity.text} -> {relation.target_entity.text}")
                    return None

            relation_id = str(uuid.uuid4())

            # 清理关系类型名称，确保符合Neo4j标识符规范
            clean_relation_type = re.sub(r'[^A-Za-z0-9_]', '_', relation.relation_type)

            create_query = f"""
            MATCH (source:Entity {{id: $source_id}})
            MATCH (target:Entity {{id: $target_id}})
            CREATE (source)-[r:{clean_relation_type} {{
                id: $relation_id,
                type: $relation_type,
                confidence: $confidence,
                evidence: $evidence,
                source: $source,
                created_at: datetime(),
                updated_at: datetime(),
                knowledge_graph_id: $kg_id,
                document_id: $doc_id
            }}]->(target)
            RETURN r.id as neo4j_id
            """

            params = {
                'source_id': source_neo4j_id,
                'target_id': target_neo4j_id,
                'relation_id': relation_id,
                'relation_type': relation.relation_type,
                'confidence': relation.confidence,
                'evidence': relation.evidence_text or '',
                'source': 'extraction',
                'kg_id': str(doc_source.knowledge_graph.id),
                'doc_id': str(doc_source.id)
            }

            result = session.run(create_query, params)
            record = result.single()

            if record:
                logger.info(f"成功保存关系到Neo4j: {relation.source_entity.text} -> {relation.relation_type} -> {relation.target_entity.text}")
                return record['neo4j_id']
            else:
                logger.warning(f"Neo4j关系创建失败: {relation.source_entity.text} -> {relation.target_entity.text}")
                return None

        except Exception as e:
            logger.error(f"保存关系到Neo4j失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return None

    def _save_entity_record(self, entity: Entity, neo4j_id: str, doc_source: DocumentSource):
        """保存实体记录到Django"""
        try:
            entity_type = EntityType.objects.filter(name=entity.entity_type).first()
            if not entity_type:
                logger.warning(f"未找到实体类型: {entity.entity_type}")
                return

            EntityRecord.objects.create(
                knowledge_graph=doc_source.knowledge_graph,
                entity_type=entity_type,
                neo4j_id=neo4j_id,
                name=entity.text,
                description=entity.properties.get('description', ''),
                confidence=entity.confidence,
                source_document=doc_source,
                source_text=entity.context,
                extraction_method=entity.properties.get('extraction_method', 'unknown'),
                properties=entity.properties
            )

        except Exception as e:
            logger.error(f"保存实体记录失败: {e}")

    def _save_relation_record(self, relation: Relation, neo4j_id: str, doc_source: DocumentSource):
        """保存关系记录到Django"""
        try:
            relation_type = RelationType.objects.filter(name=relation.relation_type).first()
            if not relation_type:
                logger.warning(f"未找到关系类型: {relation.relation_type}")
                # 创建新的关系类型
                relation_type = RelationType.objects.create(
                    name=relation.relation_type,
                    label=relation.relation_type,
                    description=f"自动创建的关系类型: {relation.relation_type}"
                )
                logger.info(f"创建新关系类型: {relation.relation_type}")

            # 查找对应的实体记录 - 使用实体名称查找
            source_entity_record = EntityRecord.objects.filter(
                knowledge_graph=doc_source.knowledge_graph,
                name=relation.source_entity.text
            ).first()

            target_entity_record = EntityRecord.objects.filter(
                knowledge_graph=doc_source.knowledge_graph,
                name=relation.target_entity.text
            ).first()

            if not source_entity_record:
                logger.warning(f"未找到源实体记录: {relation.source_entity.text}")
                return

            if not target_entity_record:
                logger.warning(f"未找到目标实体记录: {relation.target_entity.text}")
                return

            # 检查是否已存在相同关系
            existing_relation = RelationRecord.objects.filter(
                knowledge_graph=doc_source.knowledge_graph,
                source_entity=source_entity_record,
                target_entity=target_entity_record,
                relation_type=relation_type
            ).first()

            if existing_relation:
                logger.info(f"关系已存在: {relation.source_entity.text} -> {relation.target_entity.text}")
                return

            RelationRecord.objects.create(
                knowledge_graph=doc_source.knowledge_graph,
                relation_type=relation_type,
                neo4j_id=neo4j_id,
                source_entity=source_entity_record,
                target_entity=target_entity_record,
                confidence=relation.confidence,
                source_document=doc_source,
                source_text=relation.evidence_text,
                extraction_method=relation.properties.get('extraction_method', 'pattern'),
                properties=relation.properties
            )

            logger.info(f"成功保存关系: {relation.source_entity.text} -> {relation.relation_type} -> {relation.target_entity.text}")

        except Exception as e:
            logger.error(f"保存关系记录失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")

    def _update_knowledge_graph_stats(self, kg_id: int):
        """更新知识图谱统计信息"""
        try:
            kg = KnowledgeGraph.objects.get(id=kg_id)

            # 统计实体数量
            entity_count = EntityRecord.objects.filter(knowledge_graph=kg).count()

            # 统计关系数量
            relation_count = RelationRecord.objects.filter(knowledge_graph=kg).count()

            # 统计文档数量
            document_count = DocumentSource.objects.filter(knowledge_graph=kg).count()

            # 更新统计信息
            kg.entity_count = entity_count
            kg.relation_count = relation_count
            kg.document_count = document_count
            kg.last_processed_at = timezone.now()
            kg.save()

            logger.info(f"更新知识图谱统计: 实体={entity_count}, 关系={relation_count}, 文档={document_count}")

        except Exception as e:
            logger.error(f"更新知识图谱统计失败: {e}")

    def get_supported_formats(self) -> List[str]:
        """获取支持的文档格式"""
        return self.document_parser.get_supported_formats()

    def validate_document(self, file_path: str) -> Dict:
        """验证文档是否可以处理"""
        try:
            if not self.document_parser.is_supported_format(file_path):
                return {
                    'valid': False,
                    'error': f'不支持的文件格式: {file_path}'
                }

            # 可以添加更多验证逻辑，如文件大小、权限等

            return {'valid': True}

        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    def clear_neo4j_data(self, kg_id, clear_entities=True, clear_relations=True):
        """清空Neo4j中指定知识图谱的数据"""
        try:
            from neo4j import GraphDatabase
            from ..neo4j_config import Neo4jConfig

            # 使用统一的Neo4j连接配置
            driver = GraphDatabase.driver(
                Neo4jConfig.URI,
                auth=(Neo4jConfig.USER, Neo4jConfig.PASSWORD),
                **Neo4jConfig.get_driver_config()
            )

            with driver.session() as session:
                cleared_counts = {'nodes': 0, 'relationships': 0}

                # 清空关系（同时支持整数和字符串类型的knowledge_graph_id）
                if clear_relations:
                    result = session.run(
                        "MATCH ()-[r]->() WHERE r.knowledge_graph_id = $kg_id_int OR r.knowledge_graph_id = $kg_id_str DELETE r RETURN count(r) as count",
                        kg_id_int=kg_id,
                        kg_id_str=str(kg_id)
                    )
                    record = result.single()
                    cleared_counts['relationships'] = record['count'] if record else 0

                # 清空节点（同时支持整数和字符串类型的knowledge_graph_id）
                if clear_entities:
                    result = session.run(
                        "MATCH (n) WHERE n.knowledge_graph_id = $kg_id_int OR n.knowledge_graph_id = $kg_id_str DELETE n RETURN count(n) as count",
                        kg_id_int=kg_id,
                        kg_id_str=str(kg_id)
                    )
                    record = result.single()
                    cleared_counts['nodes'] = record['count'] if record else 0

            driver.close()

            logger.info(f"Neo4j清空完成 - 知识图谱ID: {kg_id}, 节点: {cleared_counts['nodes']}, 关系: {cleared_counts['relationships']}")

            return {
                'success': True,
                'cleared_counts': cleared_counts
            }

        except Exception as e:
            logger.error(f"Neo4j清空失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def clear_all_neo4j_data(self):
        """清空Neo4j中的所有数据"""
        try:
            from neo4j import GraphDatabase
            from ..neo4j_config import Neo4jConfig

            # 使用统一的Neo4j连接配置
            driver = GraphDatabase.driver(
                Neo4jConfig.URI,
                auth=(Neo4jConfig.USER, Neo4jConfig.PASSWORD),
                **Neo4jConfig.get_driver_config()
            )

            with driver.session() as session:
                # 清空所有关系
                result = session.run("MATCH ()-[r]->() DELETE r RETURN count(r) as count")
                record = result.single()
                relationships_count = record['count'] if record else 0

                # 清空所有节点
                result = session.run("MATCH (n) DELETE n RETURN count(n) as count")
                record = result.single()
                nodes_count = record['count'] if record else 0

            driver.close()

            logger.info(f"Neo4j全部清空完成 - 节点: {nodes_count}, 关系: {relationships_count}")

            return {
                'success': True,
                'cleared_counts': {
                    'nodes': nodes_count,
                    'relationships': relationships_count
                }
            }

        except Exception as e:
            logger.error(f"Neo4j全部清空失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
