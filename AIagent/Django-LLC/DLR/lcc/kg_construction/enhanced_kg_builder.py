#!/usr/bin/env python
"""
增强的知识图谱构建器 - 支持自定义实体和关系类型配置
"""

import logging
from typing import Dict, List, Optional, Tuple
from .kg_builder import KnowledgeGraphBuilder
from ..entity_recognition.chinese_ner import ChineseNER
from ..relation_extraction.relation_extractor import RelationExtractor

logger = logging.getLogger(__name__)


class EnhancedKGBuilder(KnowledgeGraphBuilder):
    """增强的知识图谱构建器"""
    
    def __init__(self):
        super().__init__()
        self.custom_entity_types = []
        self.custom_relation_types = []
        self.type_mapping = {}
    
    def set_custom_entity_types(self, entity_types: List[str]):
        """
        设置自定义实体类型
        
        Args:
            entity_types: 实体类型列表，如 ['PERSON', 'ORGANIZATION', 'CONCEPT']
        """
        self.custom_entity_types = entity_types
        logger.info(f"设置自定义实体类型: {entity_types}")
    
    def set_custom_relation_types(self, relation_types: List[str]):
        """
        设置自定义关系类型
        
        Args:
            relation_types: 关系类型列表，如 ['WORKS_FOR', 'LOCATED_IN', 'IS_A']
        """
        self.custom_relation_types = relation_types
        logger.info(f"设置自定义关系类型: {relation_types}")
    
    def set_type_mapping(self, mapping: Dict[str, str]):
        """
        设置类型映射规则
        
        Args:
            mapping: 类型映射字典，如 {'人': 'PERSON', '公司': 'ORGANIZATION'}
        """
        self.type_mapping = mapping
        logger.info(f"设置类型映射: {mapping}")
    
    def build_from_document_with_types(self, document_path: str, knowledge_graph_id: int, 
                                     user_id: int, entity_types: List[str] = None,
                                     relation_types: List[str] = None, 
                                     type_mapping: Dict[str, str] = None,
                                     options: Dict = None) -> Dict:
        """
        从文档构建知识图谱，支持自定义类型配置
        
        Args:
            document_path: 文档路径
            knowledge_graph_id: 知识图谱ID
            user_id: 用户ID
            entity_types: 自定义实体类型
            relation_types: 自定义关系类型
            type_mapping: 类型映射规则
            options: 其他构建选项
            
        Returns:
            构建结果
        """
        try:
            # 设置自定义类型
            if entity_types:
                self.set_custom_entity_types(entity_types)
            if relation_types:
                self.set_custom_relation_types(relation_types)
            if type_mapping:
                self.set_type_mapping(type_mapping)
            
            # 更新选项
            options = options or {}
            if self.custom_entity_types:
                options['entity_types'] = self.custom_entity_types
            if self.custom_relation_types:
                options['relation_types'] = self.custom_relation_types
            
            # 调用父类方法
            result = super().build_from_document(
                document_path, knowledge_graph_id, user_id, options
            )
            
            # 后处理：应用类型映射
            if result.get('success') and self.type_mapping:
                self._apply_type_mapping(knowledge_graph_id)
            
            return result
            
        except Exception as e:
            logger.error(f"增强知识图谱构建失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def build_from_text_with_types(self, text: str, knowledge_graph_id: int, 
                                 user_id: int, title: str = "文本输入",
                                 entity_types: List[str] = None,
                                 relation_types: List[str] = None,
                                 type_mapping: Dict[str, str] = None,
                                 options: Dict = None) -> Dict:
        """
        从文本构建知识图谱，支持自定义类型配置
        """
        try:
            # 设置自定义类型
            if entity_types:
                self.set_custom_entity_types(entity_types)
            if relation_types:
                self.set_custom_relation_types(relation_types)
            if type_mapping:
                self.set_type_mapping(type_mapping)
            
            # 更新选项
            options = options or {}
            if self.custom_entity_types:
                options['entity_types'] = self.custom_entity_types
            if self.custom_relation_types:
                options['relation_types'] = self.custom_relation_types
            
            # 调用父类方法
            result = super().build_from_text(
                text, knowledge_graph_id, user_id, title, options
            )
            
            # 后处理：应用类型映射
            if result.get('success') and self.type_mapping:
                self._apply_type_mapping(knowledge_graph_id)
            
            return result
            
        except Exception as e:
            logger.error(f"增强文本知识图谱构建失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _apply_type_mapping(self, knowledge_graph_id: int):
        """应用类型映射到已构建的知识图谱"""
        try:
            from ..models import EntityRecord, RelationRecord
            
            # 映射实体类型
            for old_type, new_type in self.type_mapping.items():
                EntityRecord.objects.filter(
                    knowledge_graph_id=knowledge_graph_id,
                    entity_type=old_type
                ).update(entity_type=new_type)
                
                RelationRecord.objects.filter(
                    knowledge_graph_id=knowledge_graph_id,
                    relation_type=old_type
                ).update(relation_type=new_type)
            
            logger.info(f"类型映射应用完成: {self.type_mapping}")
            
        except Exception as e:
            logger.error(f"应用类型映射失败: {e}")
    
    def extract_entities_with_custom_types(self, text: str, entity_types: List[str] = None) -> List[Dict]:
        """
        使用自定义类型提取实体
        """
        try:
            # 使用自定义类型或默认类型
            types_to_use = entity_types or self.custom_entity_types
            
            # 调用实体识别器
            entities = self.entity_recognizer.extract_entities(text, types_to_use)
            
            # 应用类型映射
            if self.type_mapping:
                for entity in entities:
                    if entity.get('type') in self.type_mapping:
                        entity['type'] = self.type_mapping[entity['type']]
            
            return entities
            
        except Exception as e:
            logger.error(f"自定义实体提取失败: {e}")
            return []
    
    def extract_relations_with_custom_types(self, text: str, entities: List[Dict], 
                                          relation_types: List[str] = None) -> List[Dict]:
        """
        使用自定义类型提取关系
        """
        try:
            # 使用自定义类型或默认类型
            types_to_use = relation_types or self.custom_relation_types
            
            # 调用关系抽取器
            relations = self.relation_extractor.extract_relations(text, entities, types_to_use)
            
            # 应用类型映射
            if self.type_mapping:
                for relation in relations:
                    if relation.get('relation') in self.type_mapping:
                        relation['relation'] = self.type_mapping[relation['relation']]
            
            return relations
            
        except Exception as e:
            logger.error(f"自定义关系提取失败: {e}")
            return []
    
    def get_type_suggestions(self, text: str, suggestion_count: int = 10) -> Dict:
        """
        基于文本内容建议实体和关系类型
        
        Args:
            text: 输入文本
            suggestion_count: 建议数量
            
        Returns:
            类型建议
        """
        try:
            # 先进行基础的实体和关系提取
            entities = self.entity_recognizer.extract_entities(text)
            relations = self.relation_extractor.extract_relations(text, entities)
            
            # 统计类型频率
            entity_types = {}
            relation_types = {}
            
            for entity in entities:
                entity_type = entity.get('type', 'UNKNOWN')
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            for relation in relations:
                relation_type = relation.get('relation', 'UNKNOWN')
                relation_types[relation_type] = relation_types.get(relation_type, 0) + 1
            
            # 排序并取前N个
            suggested_entity_types = sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:suggestion_count]
            suggested_relation_types = sorted(relation_types.items(), key=lambda x: x[1], reverse=True)[:suggestion_count]
            
            return {
                'entity_types': [{'type': t[0], 'count': t[1]} for t in suggested_entity_types],
                'relation_types': [{'type': t[0], 'count': t[1]} for t in suggested_relation_types],
                'total_entities': len(entities),
                'total_relations': len(relations)
            }
            
        except Exception as e:
            logger.error(f"类型建议生成失败: {e}")
            return {
                'entity_types': [],
                'relation_types': [],
                'total_entities': 0,
                'total_relations': 0
            }
    
    def validate_custom_types(self, entity_types: List[str] = None, 
                            relation_types: List[str] = None) -> Dict:
        """
        验证自定义类型的有效性
        """
        try:
            issues = []
            warnings = []
            
            # 验证实体类型
            if entity_types:
                for entity_type in entity_types:
                    if not entity_type or not entity_type.strip():
                        issues.append("实体类型不能为空")
                    elif len(entity_type) > 50:
                        warnings.append(f"实体类型过长: {entity_type}")
                    elif not entity_type.replace('_', '').isalnum():
                        warnings.append(f"实体类型包含特殊字符: {entity_type}")
            
            # 验证关系类型
            if relation_types:
                for relation_type in relation_types:
                    if not relation_type or not relation_type.strip():
                        issues.append("关系类型不能为空")
                    elif len(relation_type) > 50:
                        warnings.append(f"关系类型过长: {relation_type}")
                    elif not relation_type.replace('_', '').isalnum():
                        warnings.append(f"关系类型包含特殊字符: {relation_type}")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'warnings': warnings,
                'message': '类型验证完成' if len(issues) == 0 else f'发现{len(issues)}个问题'
            }
            
        except Exception as e:
            logger.error(f"类型验证失败: {e}")
            return {
                'valid': False,
                'issues': [str(e)],
                'warnings': [],
                'message': '验证过程出错'
            }
