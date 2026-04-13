"""
关系抽取器
基于模式匹配和依存句法分析的关系抽取
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import jieba.posseg as pseg

from ..entity_recognition.chinese_ner import Entity

logger = logging.getLogger(__name__)


@dataclass
class Relation:
    """关系类"""
    source_entity: Entity
    target_entity: Entity
    relation_type: str
    confidence: float
    evidence_text: str
    start_pos: int
    end_pos: int
    properties: Dict = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self):
        # 关系抽取模式
        self.relation_patterns = self._load_relation_patterns()
        
        # 关系指示词
        self.relation_indicators = self._load_relation_indicators()
        
        # 依存关系映射
        self.dependency_mappings = self._load_dependency_mappings()
    
    def extract_relations(self, text: str, entities: List[Entity], 
                         relation_types: List[str] = None) -> List[Relation]:
        """
        抽取关系
        
        Args:
            text: 输入文本
            entities: 已识别的实体列表
            relation_types: 要抽取的关系类型列表
            
        Returns:
            List[Relation]: 抽取的关系列表
        """
        if not text or not entities or len(entities) < 2:
            return []
        
        if relation_types is None:
            relation_types = list(self.relation_patterns.keys())
        
        relations = []
        
        try:
            # 1. 基于模式的关系抽取
            pattern_relations = self._extract_by_patterns(text, entities, relation_types)
            relations.extend(pattern_relations)
            
            # 2. 基于距离的关系抽取
            distance_relations = self._extract_by_distance(text, entities, relation_types)
            relations.extend(distance_relations)
            
            # 3. 基于共现的关系抽取
            cooccurrence_relations = self._extract_by_cooccurrence(text, entities, relation_types)
            relations.extend(cooccurrence_relations)
            
            # 4. 去重和过滤
            relations = self._filter_relations(relations)
            
            # 5. 计算置信度
            relations = self._calculate_relation_confidence(relations, text)
            
            # 6. 按置信度排序
            relations.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.debug(f"抽取到 {len(relations)} 个关系")
            
            return relations
            
        except Exception as e:
            logger.error(f"关系抽取失败: {e}")
            return []
    
    def _extract_by_patterns(self, text: str, entities: List[Entity], 
                           relation_types: List[str]) -> List[Relation]:
        """基于模式的关系抽取"""
        relations = []
        
        for relation_type in relation_types:
            if relation_type not in self.relation_patterns:
                continue
            
            patterns = self.relation_patterns[relation_type]
            
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                confidence = pattern_info.get('confidence', 0.7)
                source_types = pattern_info.get('source_types', [])
                target_types = pattern_info.get('target_types', [])
                
                # 查找匹配的模式
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    match_start = match.start()
                    match_end = match.end()
                    evidence_text = match.group()
                    
                    # 查找模式附近的实体
                    nearby_entities = self._find_nearby_entities(
                        entities, match_start, match_end, window=100
                    )
                    
                    # 尝试匹配实体对
                    for i, entity1 in enumerate(nearby_entities):
                        for entity2 in nearby_entities[i+1:]:
                            # 检查实体类型是否匹配
                            if self._check_entity_types(entity1, entity2, source_types, target_types):
                                relation = Relation(
                                    source_entity=entity1,
                                    target_entity=entity2,
                                    relation_type=relation_type,
                                    confidence=confidence,
                                    evidence_text=evidence_text,
                                    start_pos=match_start,
                                    end_pos=match_end,
                                    properties={
                                        'extraction_method': 'pattern',
                                        'pattern': pattern
                                    }
                                )
                                relations.append(relation)
        
        return relations
    
    def _extract_by_distance(self, text: str, entities: List[Entity], 
                           relation_types: List[str]) -> List[Relation]:
        """基于距离的关系抽取"""
        relations = []
        max_distance = 50  # 最大距离阈值
        
        # 按位置排序实体
        sorted_entities = sorted(entities, key=lambda x: x.start_pos)
        
        for i, entity1 in enumerate(sorted_entities):
            for entity2 in sorted_entities[i+1:]:
                # 计算实体间距离
                distance = entity2.start_pos - entity1.end_pos
                
                if distance > max_distance:
                    break  # 距离太远，跳出内层循环
                
                # 获取实体间的文本
                between_text = text[entity1.end_pos:entity2.start_pos]
                
                # 检查是否包含关系指示词
                for relation_type in relation_types:
                    if relation_type in self.relation_indicators:
                        indicators = self.relation_indicators[relation_type]
                        
                        for indicator in indicators:
                            if indicator in between_text:
                                # 计算基于距离的置信度
                                distance_confidence = max(0.3, 1.0 - distance / max_distance)
                                
                                relation = Relation(
                                    source_entity=entity1,
                                    target_entity=entity2,
                                    relation_type=relation_type,
                                    confidence=distance_confidence * 0.6,  # 基础置信度较低
                                    evidence_text=between_text,
                                    start_pos=entity1.start_pos,
                                    end_pos=entity2.end_pos,
                                    properties={
                                        'extraction_method': 'distance',
                                        'distance': distance,
                                        'indicator': indicator
                                    }
                                )
                                relations.append(relation)
                                break
        
        return relations
    
    def _extract_by_cooccurrence(self, text: str, entities: List[Entity], 
                               relation_types: List[str]) -> List[Relation]:
        """基于共现的关系抽取"""
        relations = []
        
        # 分句处理
        sentences = self._split_sentences(text)
        
        for sentence in sentences:
            # 找到句子中的实体
            sentence_entities = []
            for entity in entities:
                if self._entity_in_sentence(entity, sentence, text):
                    sentence_entities.append(entity)
            
            # 如果句子中有多个实体，尝试建立关系
            if len(sentence_entities) >= 2:
                for i, entity1 in enumerate(sentence_entities):
                    for entity2 in sentence_entities[i+1:]:
                        # 根据实体类型推断可能的关系
                        possible_relations = self._infer_relations_by_types(
                            entity1.entity_type, entity2.entity_type, relation_types
                        )
                        
                        for relation_type in possible_relations:
                            relation = Relation(
                                source_entity=entity1,
                                target_entity=entity2,
                                relation_type=relation_type,
                                confidence=0.4,  # 共现关系置信度较低
                                evidence_text=sentence,
                                start_pos=min(entity1.start_pos, entity2.start_pos),
                                end_pos=max(entity1.end_pos, entity2.end_pos),
                                properties={
                                    'extraction_method': 'cooccurrence',
                                    'sentence': sentence
                                }
                            )
                            relations.append(relation)
        
        return relations
    
    def _find_nearby_entities(self, entities: List[Entity], start: int, end: int, 
                            window: int = 50) -> List[Entity]:
        """查找附近的实体"""
        nearby = []
        
        for entity in entities:
            # 检查实体是否在窗口范围内
            if (entity.end_pos >= start - window and 
                entity.start_pos <= end + window):
                nearby.append(entity)
        
        return nearby
    
    def _check_entity_types(self, entity1: Entity, entity2: Entity, 
                          source_types: List[str], target_types: List[str]) -> bool:
        """检查实体类型是否匹配关系要求"""
        if not source_types and not target_types:
            return True  # 没有类型限制
        
        # 检查正向匹配
        if (not source_types or entity1.entity_type in source_types) and \
           (not target_types or entity2.entity_type in target_types):
            return True
        
        # 检查反向匹配（对于对称关系）
        if (not source_types or entity2.entity_type in source_types) and \
           (not target_types or entity1.entity_type in target_types):
            return True
        
        return False
    
    def _split_sentences(self, text: str) -> List[str]:
        """分句"""
        # 简单的分句实现
        sentence_delimiters = r'[。！？；!?;]+'
        sentences = re.split(sentence_delimiters, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _entity_in_sentence(self, entity: Entity, sentence: str, full_text: str) -> bool:
        """检查实体是否在句子中"""
        # 简单实现：检查实体文本是否在句子中
        return entity.text in sentence
    
    def _infer_relations_by_types(self, type1: str, type2: str, 
                                relation_types: List[str]) -> List[str]:
        """根据实体类型推断可能的关系"""
        possible_relations = []
        
        # 定义类型组合到关系的映射
        type_relation_map = {
            ('PERSON', 'ORGANIZATION'): ['WORKS_FOR', 'STUDIES_AT', 'FOUNDED_BY'],
            ('PERSON', 'LOCATION'): ['BORN_IN', 'LIVES_IN', 'LOCATED_IN'],
            ('PERSON', 'PERSON'): ['KNOWS', 'COLLEAGUE_OF', 'MARRIED_TO'],
            ('PERSON', 'CONCEPT'): ['EXPERT_IN', 'RESEARCHES'],
            ('ORGANIZATION', 'LOCATION'): ['LOCATED_IN', 'HEADQUARTERED_IN'],
            ('ORGANIZATION', 'PRODUCT'): ['PRODUCES', 'DEVELOPS'],
            ('CONCEPT', 'CONCEPT'): ['IS_A', 'PART_OF', 'RELATED_TO'],
            ('PRODUCT', 'ORGANIZATION'): ['MANUFACTURED_BY', 'DEVELOPED_BY'],
        }
        
        # 检查正向和反向匹配
        for (t1, t2), relations in type_relation_map.items():
            if (type1 == t1 and type2 == t2) or (type1 == t2 and type2 == t1):
                for relation in relations:
                    if relation in relation_types:
                        possible_relations.append(relation)
        
        return possible_relations
    
    def _filter_relations(self, relations: List[Relation]) -> List[Relation]:
        """过滤和去重关系"""
        if not relations:
            return relations
        
        # 去重：相同实体对和关系类型的关系只保留置信度最高的
        unique_relations = {}
        
        for relation in relations:
            key = (
                relation.source_entity.text,
                relation.target_entity.text,
                relation.relation_type
            )
            
            if key not in unique_relations or relation.confidence > unique_relations[key].confidence:
                unique_relations[key] = relation
        
        return list(unique_relations.values())
    
    def _calculate_relation_confidence(self, relations: List[Relation], text: str) -> List[Relation]:
        """计算关系置信度"""
        for relation in relations:
            confidence = relation.confidence
            
            # 实体置信度影响
            entity_conf = (relation.source_entity.confidence + relation.target_entity.confidence) / 2
            confidence *= entity_conf
            
            # 证据文本长度影响
            evidence_length = len(relation.evidence_text)
            if evidence_length > 100:
                confidence *= 0.9  # 证据太长，降低置信度
            elif evidence_length < 10:
                confidence *= 0.8  # 证据太短，降低置信度
            
            # 实体距离影响
            entity_distance = relation.target_entity.start_pos - relation.source_entity.end_pos
            if entity_distance > 50:
                confidence *= 0.8
            
            relation.confidence = max(0.1, min(1.0, confidence))
        
        return relations
    
    def _load_relation_patterns(self) -> Dict[str, List[Dict]]:
        """加载关系抽取模式"""
        patterns = {
            'WORKS_FOR': [
                {
                    'pattern': r'(.+?)(?:在|任职于|工作于|就职于)(.+?)(?:工作|任职)',
                    'confidence': 0.8,
                    'source_types': ['PERSON'],
                    'target_types': ['ORGANIZATION']
                },
                {
                    'pattern': r'(.+?)(?:是|担任)(.+?)(?:的|员工|职员|成员)',
                    'confidence': 0.7,
                    'source_types': ['PERSON'],
                    'target_types': ['ORGANIZATION']
                }
            ],
            'LOCATED_IN': [
                {
                    'pattern': r'(.+?)(?:位于|坐落在|在)(.+?)(?:地区|境内)',
                    'confidence': 0.8,
                    'source_types': ['ORGANIZATION', 'LOCATION'],
                    'target_types': ['LOCATION']
                }
            ],
            'IS_A': [
                {
                    'pattern': r'(.+?)(?:是|属于)(.+?)(?:的一种|的一个|之一)',
                    'confidence': 0.8
                }
            ],
            'PART_OF': [
                {
                    'pattern': r'(.+?)(?:包含|包括|由)(.+?)(?:组成|构成)',
                    'confidence': 0.7
                }
            ],
            'CAUSES': [
                {
                    'pattern': r'(.+?)(?:导致|引起|造成|产生)(.+)',
                    'confidence': 0.7
                }
            ]
        }
        
        return patterns
    
    def _load_relation_indicators(self) -> Dict[str, List[str]]:
        """加载关系指示词"""
        indicators = {
            'WORKS_FOR': ['在', '任职于', '工作于', '就职于', '供职于'],
            'STUDIES_AT': ['在', '就读于', '学习于', '毕业于'],
            'LOCATED_IN': ['位于', '坐落在', '在', '处于'],
            'IS_A': ['是', '属于', '为'],
            'PART_OF': ['包含', '包括', '由', '组成'],
            'RELATED_TO': ['相关', '有关', '关于', '涉及'],
            'CAUSES': ['导致', '引起', '造成', '产生', '带来'],
            'USES': ['使用', '采用', '应用', '利用'],
            'PRODUCES': ['生产', '制造', '开发', '研发']
        }
        
        return indicators
    
    def _load_dependency_mappings(self) -> Dict[str, str]:
        """加载依存关系映射"""
        # 这里可以扩展为更复杂的依存句法分析
        mappings = {
            'nsubj': 'SUBJECT_OF',
            'dobj': 'OBJECT_OF',
            'nmod': 'MODIFIER_OF',
            'compound': 'COMPOUND_OF'
        }
        
        return mappings
    
    def add_custom_pattern(self, relation_type: str, pattern: str, 
                          confidence: float = 0.7, source_types: List[str] = None, 
                          target_types: List[str] = None):
        """添加自定义关系抽取模式"""
        if relation_type not in self.relation_patterns:
            self.relation_patterns[relation_type] = []
        
        pattern_info = {
            'pattern': pattern,
            'confidence': confidence
        }
        
        if source_types:
            pattern_info['source_types'] = source_types
        if target_types:
            pattern_info['target_types'] = target_types
        
        self.relation_patterns[relation_type].append(pattern_info)
        
        logger.info(f"添加自定义关系模式: {relation_type} - {pattern}")
    
    def get_relation_statistics(self, relations: List[Relation]) -> Dict:
        """获取关系统计信息"""
        if not relations:
            return {}
        
        stats = {
            'total_count': len(relations),
            'type_distribution': {},
            'confidence_distribution': {
                'high': 0,  # >= 0.7
                'medium': 0,  # 0.4 - 0.7
                'low': 0  # < 0.4
            },
            'avg_confidence': 0.0,
            'extraction_methods': {}
        }
        
        # 类型分布
        for relation in relations:
            rel_type = relation.relation_type
            stats['type_distribution'][rel_type] = stats['type_distribution'].get(rel_type, 0) + 1
        
        # 置信度分布
        confidences = [relation.confidence for relation in relations]
        for conf in confidences:
            if conf >= 0.7:
                stats['confidence_distribution']['high'] += 1
            elif conf >= 0.4:
                stats['confidence_distribution']['medium'] += 1
            else:
                stats['confidence_distribution']['low'] += 1
        
        # 平均置信度
        stats['avg_confidence'] = sum(confidences) / len(confidences)
        
        # 抽取方法分布
        for relation in relations:
            method = relation.properties.get('extraction_method', 'unknown')
            stats['extraction_methods'][method] = stats['extraction_methods'].get(method, 0) + 1
        
        return stats
