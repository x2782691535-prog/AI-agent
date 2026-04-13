#!/usr/bin/env python
"""
基于结构化数据的知识图谱构建器
"""

import logging
import os
import uuid
from typing import List, Dict, Optional
from django.utils import timezone
from django.db import transaction

from lcc.models import (
    KnowledgeGraph, EntityRecord, RelationRecord,
    EntityType, RelationType, DocumentSource
)
from django.contrib.auth import get_user_model
User = get_user_model()
from lcc.neo4j_manager import neo4j_manager
from lcc.file_processors.structured_data_processor import StructuredDataProcessor
from .realtime_sync_manager import realtime_sync_manager

logger = logging.getLogger(__name__)


class StructuredKGBuilder:
    """基于结构化数据的知识图谱构建器"""
    
    def __init__(self):
        self.processor = StructuredDataProcessor()
    
    def build_knowledge_graph_from_files(
        self, 
        kg_name: str,
        kg_description: str,
        entity_file_path: str,
        relation_file_path: str,
        user=None
    ) -> Dict:
        """
        从Excel和CSV文件构建知识图谱
        
        Args:
            kg_name: 知识图谱名称
            kg_description: 知识图谱描述
            entity_file_path: 实体Excel文件路径
            relation_file_path: 关系CSV文件路径
            user: 用户对象
            
        Returns:
            构建结果字典
        """
        try:
            logger.info(f"开始从结构化文件构建知识图谱: {kg_name}")
            
            # 验证文件
            entity_validation = self.processor.validate_entity_file(entity_file_path)
            relation_validation = self.processor.validate_relation_file(relation_file_path)
            
            if not entity_validation['valid']:
                raise ValueError(f"实体文件验证失败: {entity_validation['message']}")
            
            if not relation_validation['valid']:
                raise ValueError(f"关系文件验证失败: {relation_validation['message']}")
            
            # 解析文件
            entities_data = self.processor.process_entity_file(entity_file_path)
            relations_data = self.processor.process_relation_file(relation_file_path)
            
            logger.info(f"解析完成: {len(entities_data)} 实体, {len(relations_data)} 关系")
            
            # 构建知识图谱
            with transaction.atomic():
                # 创建知识图谱
                kg_data = {
                    'name': kg_name,
                    'description': kg_description,
                    'entity_count': 0,
                    'relation_count': 0,
                    'document_count': 1,
                    'status': 'processing'
                }

                # 确保有用户
                if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
                    user, created = User.objects.get_or_create(
                        username='system_user',
                        defaults={'email': 'system@example.com'}
                    )

                kg_data['created_by'] = user
                kg = KnowledgeGraph.objects.create(**kg_data)

                # 创建文档源记录

                import uuid
                unique_id = str(uuid.uuid4())[:8]

                doc_source = DocumentSource.objects.create(
                    knowledge_graph=kg,
                    title=f"{kg_name}_结构化数据",
                    file_name=f"{kg_name}_structured_data",
                    file_path=f"structured_data_{unique_id}",
                    file_type="txt",  # 使用txt作为结构化数据的类型
                    file_size=0,
                    file_hash=f"structured_data_hash_{unique_id}",
                    uploaded_by=user,
                    processing_status='completed'
                )
                
                # 保存实体
                entity_records = self._save_entities(entities_data, kg, doc_source)
                
                # 自动创建缺失的实体
                missing_entities = self._create_missing_entities(relations_data, kg, entity_records)
                entity_records.update(missing_entities)

                # 保存关系
                relation_records = self._save_relations(relations_data, kg, doc_source, entity_records)
                
                # 更新统计信息
                kg.status = 'completed'
                kg.save()

                # 使用模型方法更新统计信息，确保准确性
                updated_stats = kg.update_statistics()
                logger.info(f"统计信息已更新: {updated_stats}")
                
                logger.info(f"知识图谱构建完成: {kg.entity_count} 实体, {kg.relation_count} 关系")

                return {
                    'success': True,
                    'knowledge_graph_id': kg.id,
                    'entity_count': kg.entity_count,
                    'relation_count': kg.relation_count,
                    'message': f'成功构建知识图谱: {kg.entity_count} 个实体, {kg.relation_count} 个关系'
                }
        
        except Exception as e:
            logger.error(f"构建知识图谱失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'构建失败: {str(e)}'
            }
    
    def _save_entities(self, entities_data: List[Dict], kg: KnowledgeGraph, doc_source: DocumentSource) -> Dict[str, EntityRecord]:
        """保存实体到数据库和Neo4j"""
        entity_records = {}
        
        logger.info(f"开始保存 {len(entities_data)} 个实体")
        
        for entity_data in entities_data:
            try:
                # 实体名称已经在processor中标准化过了
                entity_name = entity_data['name']
                entity_type_name = entity_data['type']

                # 获取或创建实体类型
                entity_type, created = EntityType.objects.get_or_create(
                    name=entity_type_name,
                    defaults={
                        'label': entity_type_name,
                        'description': f'从结构化数据导入的实体类型: {entity_type_name}'
                    }
                )

                if created:
                    logger.info(f"创建新实体类型: {entity_type_name}")

                # 检查实体是否已存在（使用标准化的名称）
                existing_entity = EntityRecord.objects.filter(
                    knowledge_graph=kg,
                    name=entity_name  # 这里的entity_name已经是标准化的
                ).first()
                
                if existing_entity:
                    logger.warning(f"实体已存在，跳过: {entity_name}")
                    entity_records[entity_name] = existing_entity
                    continue
                
                # 使用实时同步管理器创建实体
                entity_data_with_props = {
                    'name': entity_name,
                    'confidence': entity_data.get('confidence', 1.0),
                    'extraction_method': 'structured_import',
                    'properties': {
                        'data_source': entity_data.get('data_source', 'manual_annotation'),
                        'imported_at': timezone.now().isoformat()
                    }
                }

                entity_record, neo4j_success = realtime_sync_manager.create_entity_with_sync(
                    kg=kg,
                    entity_data=entity_data_with_props,
                    entity_type=entity_type,
                    doc_source=doc_source
                )
                
                entity_records[entity_name] = entity_record
                logger.debug(f"成功保存实体: {entity_name}")
                
            except Exception as e:
                logger.error(f"保存实体失败: {entity_data.get('name', 'Unknown')} - {e}")
                continue
        
        logger.info(f"实体保存完成: {len(entity_records)} 个")
        return entity_records

    def _create_missing_entities(self, relations_data: List[Dict], kg: KnowledgeGraph, existing_entities: Dict[str, EntityRecord]) -> Dict[str, EntityRecord]:
        """
        自动创建关系中缺失的实体

        Args:
            relations_data: 关系数据列表
            kg: 知识图谱对象
            existing_entities: 已存在的实体字典

        Returns:
            新创建的实体字典
        """
        missing_entities = {}

        try:
            # 收集关系中所有涉及的实体名称
            relation_entities = set()
            for relation_data in relations_data:
                relation_entities.add(relation_data['source'])
                relation_entities.add(relation_data['target'])

            # 找出缺失的实体
            missing_entity_names = relation_entities - set(existing_entities.keys())

            if missing_entity_names:
                logger.info(f"发现 {len(missing_entity_names)} 个缺失实体，将自动创建")

                # 创建缺失的实体
                for entity_name in missing_entity_names:
                    try:
                        # 根据实体名称推断类型
                        entity_type = self._infer_entity_type(entity_name)

                        # 检查实体是否已存在（避免重复创建）
                        existing_entity = EntityRecord.objects.filter(
                            knowledge_graph=kg,
                            name=entity_name
                        ).first()

                        if not existing_entity:
                            # 使用实时同步管理器创建自动生成的实体
                            auto_entity_data = {
                                'name': entity_name,
                                'confidence': 0.7,  # 自动生成的实体置信度较低
                                'extraction_method': 'auto_generated',
                                'properties': {'auto_generated': True, 'source': 'relation_data'}
                            }

                            entity_record, neo4j_success = realtime_sync_manager.create_entity_with_sync(
                                kg=kg,
                                entity_data=auto_entity_data,
                                entity_type=entity_type,
                                doc_source=None
                            )

                            missing_entities[entity_name] = entity_record
                            logger.info(f"自动创建实体: {entity_name} (类型: {entity_type.name})")
                        else:
                            missing_entities[entity_name] = existing_entity
                            logger.info(f"实体已存在: {entity_name}")

                    except Exception as e:
                        logger.error(f"创建缺失实体 {entity_name} 失败: {e}")
                        continue

                logger.info(f"成功自动创建 {len(missing_entities)} 个缺失实体")

            return missing_entities

        except Exception as e:
            logger.error(f"自动创建缺失实体失败: {e}")
            return {}

    def _infer_entity_type(self, entity_name: str) -> EntityType:
        """
        根据实体名称推断实体类型

        Args:
            entity_name: 实体名称

        Returns:
            推断的实体类型
        """
        # 定义实体类型推断规则
        type_rules = [
            ('程序结构', ['语句', '函数', '命令', 'if', 'while', 'for', 'switch', 'break', 'continue', 'goto', 'main', 'function']),
            ('存储器', ['存储', 'RAM', 'ROM', '区', 'data', 'pdata', 'SMALL', 'COMPACT', 'LARGE']),
            ('显示器件', ['LED', '数码管', '点阵', '显示', 'LCD']),
            ('接口', ['I/O', '口', '端口', 'P0', 'P1', 'P2', 'P3']),
            ('数据类型', ['指针', '变量', '数组', '字符']),
            ('芯片', ['74', 'HD', '译码器', 'LS']),
            ('硬件组件', ['晶体', '振荡', '电路', '二极管']),
        ]

        # 根据关键词匹配推断类型
        for type_name, keywords in type_rules:
            if any(keyword in entity_name for keyword in keywords):
                entity_type, created = EntityType.objects.get_or_create(
                    name=type_name,
                    defaults={
                        'label': type_name,
                        'description': f'自动推断的{type_name}类型'
                    }
                )
                if created:
                    logger.info(f"创建新实体类型: {type_name}")
                return entity_type

        # 默认类型
        default_type, created = EntityType.objects.get_or_create(
            name='概念',
            defaults={
                'label': '概念',
                'description': '通用概念类型'
            }
        )
        if created:
            logger.info(f"创建默认实体类型: 概念")

        return default_type

    def _save_relations(self, relations_data: List[Dict], kg: KnowledgeGraph,
                       doc_source: DocumentSource, entity_records: Dict[str, EntityRecord]) -> List[RelationRecord]:
        """保存关系到数据库和Neo4j"""
        relation_records = []
        
        logger.info(f"开始保存 {len(relations_data)} 个关系")
        
        for relation_data in relations_data:
            try:
                source_name = relation_data['source']
                target_name = relation_data['target']
                relation_type_name = relation_data['relation']
                evidence_text = relation_data.get('text', f"{source_name} {relation_type_name} {target_name}")
                
                # 检查实体是否存在
                if source_name not in entity_records:
                    logger.warning(f"跳过关系，找不到实体: {source_name} -> {target_name}")
                    continue

                if target_name not in entity_records:
                    logger.warning(f"跳过关系，找不到实体: {source_name} -> {target_name}")
                    continue
                
                source_entity = entity_records[source_name]
                target_entity = entity_records[target_name]
                
                # 获取或创建关系类型
                relation_type, created = RelationType.objects.get_or_create(
                    name=relation_type_name,
                    defaults={
                        'label': relation_type_name,
                        'description': f'从结构化数据导入的关系类型: {relation_type_name}'
                    }
                )
                
                if created:
                    logger.info(f"创建新关系类型: {relation_type_name}")
                
                # 检查关系是否已存在
                existing_relation = RelationRecord.objects.filter(
                    knowledge_graph=kg,
                    source_entity=source_entity,
                    target_entity=target_entity,
                    relation_type=relation_type
                ).first()
                
                if existing_relation:
                    logger.warning(f"关系已存在，跳过: {source_name} -> {target_name}")
                    continue
                
                # 使用实时同步管理器创建关系
                relation_data_with_props = {
                    'confidence': relation_data.get('confidence', 1.0),
                    'text': evidence_text,
                    'extraction_method': 'structured_import',
                    'properties': {
                        'data_source': relation_data.get('data_source', 'manual_annotation'),
                        'imported_at': timezone.now().isoformat()
                    }
                }

                relation_record, neo4j_success = realtime_sync_manager.create_relation_with_sync(
                    kg=kg,
                    relation_data=relation_data_with_props,
                    relation_type=relation_type,
                    source_entity=source_entity,
                    target_entity=target_entity,
                    doc_source=doc_source
                )
                
                relation_records.append(relation_record)
                logger.debug(f"成功保存关系: {source_name} -> {relation_type_name} -> {target_name}")
                
            except Exception as e:
                logger.error(f"保存关系失败: {relation_data} - {e}")
                continue
        
        logger.info(f"关系保存完成: {len(relation_records)} 个")
        return relation_records
    
    def _save_entity_to_neo4j(self, entity_name: str, entity_type: str, 
                             neo4j_id: str, kg_id: int) -> bool:
        """保存实体到Neo4j"""
        try:
            with neo4j_manager.get_session() as session:
                create_query = """
                CREATE (e:Entity {
                    id: $entity_id,
                    name: $name,
                    type: $entity_type,
                    confidence: $confidence,
                    created_at: datetime(),
                    updated_at: datetime(),
                    knowledge_graph_id: $kg_id,
                    source: $source
                })
                RETURN e.id as neo4j_id
                """
                
                params = {
                    'entity_id': neo4j_id,
                    'name': entity_name,
                    'entity_type': entity_type,
                    'confidence': 1.0,
                    'kg_id': kg_id,  # 保持为整数
                    'source': 'structured_import'
                }
                
                result = session.run(create_query, params)
                record = result.single()
                
                return record is not None
                
        except Exception as e:
            logger.error(f"Neo4j实体保存失败: {entity_name} - {e}")
            return False
    
    def _save_relation_to_neo4j(self, source_id: str, target_id: str, 
                               relation_type: str, neo4j_id: str, 
                               kg_id: int, evidence: str) -> bool:
        """保存关系到Neo4j"""
        try:
            with neo4j_manager.get_session() as session:
                # 清理关系类型名称
                import re
                clean_relation_type = re.sub(r'[^A-Za-z0-9_]', '_', relation_type)
                
                create_query = f"""
                MATCH (source:Entity {{id: $source_id}})
                MATCH (target:Entity {{id: $target_id}})
                CREATE (source)-[r:{clean_relation_type} {{
                    id: $relation_id,
                    type: $relation_type,
                    confidence: $confidence,
                    evidence: $evidence,
                    created_at: datetime(),
                    updated_at: datetime(),
                    knowledge_graph_id: $kg_id,
                    source: $source
                }}]->(target)
                RETURN r.id as neo4j_id
                """
                
                params = {
                    'source_id': source_id,
                    'target_id': target_id,
                    'relation_id': neo4j_id,
                    'relation_type': relation_type,
                    'confidence': 1.0,
                    'evidence': evidence,
                    'kg_id': kg_id,  # 保持为整数
                    'source': 'structured_import'
                }
                
                result = session.run(create_query, params)
                record = result.single()
                
                return record is not None
                
        except Exception as e:
            logger.error(f"Neo4j关系保存失败: {relation_type} - {e}")
            return False

    def update_knowledge_graph_from_files(
        self,
        knowledge_graph_id: int,
        entity_file_path: str,
        relation_file_path: str,
        user=None
    ) -> Dict:
        """
        从文件更新现有知识图谱

        Args:
            knowledge_graph_id: 知识图谱ID
            entity_file_path: 实体文件路径
            relation_file_path: 关系文件路径
            user: 用户对象

        Returns:
            更新结果字典
        """
        try:
            logger.info(f"开始更新知识图谱: {knowledge_graph_id}")

            # 获取现有知识图谱
            try:
                kg = KnowledgeGraph.objects.get(id=knowledge_graph_id)
            except KnowledgeGraph.DoesNotExist:
                return {
                    'success': False,
                    'error': f'知识图谱ID {knowledge_graph_id} 不存在'
                }

            # 处理实体文件
            logger.info("处理实体文件...")
            entities = self.processor.process_entity_file(entity_file_path)

            # 处理关系文件
            logger.info("处理关系文件...")
            relations = self.processor.process_relation_file(relation_file_path)

            # 验证数据
            entity_validation = self.processor.validate_data_quality(entities, 'entity')
            relation_validation = self.processor.validate_data_quality(relations, 'relation')

            if not entity_validation['valid']:
                return {
                    'success': False,
                    'error': f'实体数据验证失败: {entity_validation["message"]}'
                }

            if not relation_validation['valid']:
                return {
                    'success': False,
                    'error': f'关系数据验证失败: {relation_validation["message"]}'
                }

            # 开始数据库事务
            with transaction.atomic():
                # 保存实体到数据库
                logger.info("保存实体到数据库...")
                entity_count = 0
                for entity in entities:
                    entity_name = entity.get('name', '').strip()
                    entity_type_name = entity.get('type', 'UNKNOWN').strip()

                    if not entity_name:
                        continue

                    # 获取或创建实体类型
                    entity_type, created = EntityType.objects.get_or_create(
                        name=entity_type_name,
                        defaults={
                            'label': entity_type_name,
                            'description': f'从结构化数据导入的实体类型: {entity_type_name}'
                        }
                    )

                    # 检查实体是否已存在
                    existing_entity = EntityRecord.objects.filter(
                        knowledge_graph=kg,
                        name=entity_name
                    ).first()

                    if existing_entity:
                        # 更新现有实体
                        existing_entity.entity_type = entity_type
                        existing_entity.save()
                    else:
                        # 创建文档源（如果不存在）
                        doc_source, created = DocumentSource.objects.get_or_create(
                            knowledge_graph=kg,
                            file_name=os.path.basename(entity_file_path),
                            defaults={
                                'file_path': entity_file_path,
                                'file_type': 'csv',
                                'file_size': os.path.getsize(entity_file_path) if os.path.exists(entity_file_path) else 0,
                                'file_hash': f"entity_update_{kg.id}",
                                'uploaded_by': kg.created_by,
                                'processing_status': 'completed'
                            }
                        )

                        # 生成Neo4j ID
                        neo4j_id = str(uuid.uuid4())

                        # 保存到Neo4j
                        neo4j_success = self._save_entity_to_neo4j(
                            entity_name, entity_type_name, neo4j_id, kg.id
                        )

                        if not neo4j_success:
                            logger.warning(f"Neo4j实体保存失败，但继续保存到Django: {entity_name}")

                        # 创建新实体
                        EntityRecord.objects.create(
                            knowledge_graph=kg,
                            entity_type=entity_type,
                            name=entity_name,
                            confidence=1.0,
                            neo4j_id=neo4j_id,
                            source_document=doc_source,
                            extraction_method='structured_import',
                            properties=entity.get('properties', {})
                        )

                    entity_count += 1

                # 保存关系到数据库
                logger.info("保存关系到数据库...")
                relation_count = 0
                for relation in relations:
                    source_name = relation.get('source', '').strip()
                    target_name = relation.get('target', '').strip()
                    relation_type_name = relation.get('relation', 'RELATED_TO').strip()

                    if not all([source_name, target_name, relation_type_name]):
                        continue

                    # 查找源实体和目标实体
                    source_entity = EntityRecord.objects.filter(
                        knowledge_graph=kg,
                        name=source_name
                    ).first()

                    target_entity = EntityRecord.objects.filter(
                        knowledge_graph=kg,
                        name=target_name
                    ).first()

                    if not source_entity or not target_entity:
                        logger.warning(f"跳过关系，找不到实体: {source_name} -> {target_name}")
                        continue

                    # 获取或创建关系类型
                    relation_type, created = RelationType.objects.get_or_create(
                        name=relation_type_name,
                        defaults={
                            'label': relation_type_name,
                            'description': f'从结构化数据导入的关系类型: {relation_type_name}'
                        }
                    )

                    # 检查关系是否已存在
                    existing_relation = RelationRecord.objects.filter(
                        knowledge_graph=kg,
                        source_entity=source_entity,
                        target_entity=target_entity,
                        relation_type=relation_type
                    ).first()

                    if not existing_relation:
                        # 创建文档源（如果不存在）
                        doc_source, created = DocumentSource.objects.get_or_create(
                            knowledge_graph=kg,
                            file_name=os.path.basename(relation_file_path),
                            defaults={
                                'file_path': relation_file_path,
                                'file_type': 'csv',
                                'file_size': os.path.getsize(relation_file_path) if os.path.exists(relation_file_path) else 0,
                                'file_hash': f"relation_update_{kg.id}",
                                'uploaded_by': kg.created_by,
                                'processing_status': 'completed'
                            }
                        )

                        # 生成Neo4j ID
                        neo4j_id = str(uuid.uuid4())
                        evidence_text = relation.get('text', '')

                        # 保存到Neo4j
                        neo4j_success = self._save_relation_to_neo4j(
                            source_entity.neo4j_id, target_entity.neo4j_id,
                            relation_type_name, neo4j_id, kg.id, evidence_text
                        )

                        if not neo4j_success:
                            logger.warning(f"Neo4j关系保存失败，但继续保存到Django: {source_name} -> {target_name}")

                        # 创建新关系
                        RelationRecord.objects.create(
                            knowledge_graph=kg,
                            relation_type=relation_type,
                            neo4j_id=neo4j_id,
                            source_entity=source_entity,
                            target_entity=target_entity,
                            confidence=1.0,
                            source_document=doc_source,
                            source_text=evidence_text,
                            extraction_method='structured_import',
                            is_verified=True,
                            is_active=True
                        )
                        relation_count += 1

                # 更新知识图谱统计信息
                kg.updated_at = timezone.now()
                kg.save()

                # 使用模型方法更新统计信息，确保准确性
                updated_stats = kg.update_statistics()
                logger.info(f"统计信息已更新: {updated_stats}")

                # 同步Neo4j统计信息
                neo4j_stats = self._get_neo4j_statistics(kg.id)
                if neo4j_stats:
                    logger.info(f"Neo4j统计: {neo4j_stats['entity_count']} 个实体, {neo4j_stats['relation_count']} 个关系")
                    # 如果Neo4j中的数据更多，更新Django统计
                    if neo4j_stats['entity_count'] > kg.entity_count or neo4j_stats['relation_count'] > kg.relation_count:
                        kg.entity_count = max(kg.entity_count, neo4j_stats['entity_count'])
                        kg.relation_count = max(kg.relation_count, neo4j_stats['relation_count'])
                        kg.save()
                        logger.info(f"已更新知识图谱统计信息: {kg.entity_count} 个实体, {kg.relation_count} 个关系")

                logger.info(f"知识图谱更新完成: 新增 {entity_count} 个实体, {relation_count} 个关系")

                return {
                    'success': True,
                    'knowledge_graph_id': kg.id,
                    'entity_count': entity_count,
                    'relation_count': relation_count,
                    'total_entities': kg.entity_count,
                    'total_relations': kg.relation_count,
                    'message': f'知识图谱更新成功，新增 {entity_count} 个实体和 {relation_count} 个关系'
                }

        except Exception as e:
            logger.error(f"知识图谱更新失败: {e}")
            return {
                'success': False,
                'error': f'更新失败: {str(e)}'
            }

    def _get_neo4j_statistics(self, knowledge_graph_id: int) -> Dict:
        """
        从Neo4j获取知识图谱统计信息

        Args:
            knowledge_graph_id: 知识图谱ID

        Returns:
            统计信息字典
        """
        try:
            from ..neo4j_manager import neo4j_manager

            with neo4j_manager.get_session() as session:
                # 查询实体数量（同时尝试整数和字符串类型）
                entity_query = """
                MATCH (n)
                WHERE n.knowledge_graph_id = $kg_id_int OR n.knowledge_graph_id = $kg_id_str
                RETURN count(n) as entity_count
                """

                entity_result = session.run(entity_query,
                                           kg_id_int=knowledge_graph_id,
                                           kg_id_str=str(knowledge_graph_id))
                entity_count = entity_result.single()['entity_count']

                # 查询关系数量（同时尝试整数和字符串类型）
                relation_query = """
                MATCH ()-[r]->()
                WHERE r.knowledge_graph_id = $kg_id_int OR r.knowledge_graph_id = $kg_id_str
                RETURN count(r) as relation_count
                """

                relation_result = session.run(relation_query,
                                            kg_id_int=knowledge_graph_id,
                                            kg_id_str=str(knowledge_graph_id))
                relation_count = relation_result.single()['relation_count']

                return {
                    'entity_count': entity_count,
                    'relation_count': relation_count
                }

        except Exception as e:
            logger.error(f"获取Neo4j统计信息失败: {e}")
            return None

    def sync_statistics_with_neo4j(self, knowledge_graph_id: int) -> Dict:
        """
        同步Django和Neo4j的统计信息

        Args:
            knowledge_graph_id: 知识图谱ID

        Returns:
            同步结果
        """
        try:
            # 获取知识图谱
            kg = KnowledgeGraph.objects.get(id=knowledge_graph_id)

            # 获取Django统计
            django_entity_count = EntityRecord.objects.filter(knowledge_graph=kg).count()
            django_relation_count = RelationRecord.objects.filter(knowledge_graph=kg).count()

            # 获取Neo4j统计
            neo4j_stats = self._get_neo4j_statistics(knowledge_graph_id)

            if neo4j_stats:
                neo4j_entity_count = neo4j_stats['entity_count']
                neo4j_relation_count = neo4j_stats['relation_count']

                # 使用较大的数值作为最终统计
                final_entity_count = max(django_entity_count, neo4j_entity_count)
                final_relation_count = max(django_relation_count, neo4j_relation_count)

                # 更新知识图谱统计信息
                # 使用模型方法更新统计信息，确保准确性
                updated_stats = kg.update_statistics()
                logger.info(f"同步后统计信息已更新: {updated_stats}")

                return {
                    'success': True,
                    'django_stats': {
                        'entity_count': django_entity_count,
                        'relation_count': django_relation_count
                    },
                    'neo4j_stats': {
                        'entity_count': neo4j_entity_count,
                        'relation_count': neo4j_relation_count
                    },
                    'final_stats': {
                        'entity_count': final_entity_count,
                        'relation_count': final_relation_count
                    },
                    'message': f'统计信息已同步: {final_entity_count} 个实体, {final_relation_count} 个关系'
                }
            else:
                return {
                    'success': False,
                    'error': '无法获取Neo4j统计信息'
                }

        except Exception as e:
            logger.error(f"统计信息同步失败: {e}")
            return {
                'success': False,
                'error': f'同步失败: {str(e)}'
            }
