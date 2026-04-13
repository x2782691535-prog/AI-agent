"""
实体链接和消歧
处理实体的链接、合并和消歧
"""

import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from ..entity_recognition.chinese_ner import Entity
from ..neo4j_manager import neo4j_manager

logger = logging.getLogger(__name__)


@dataclass
class EntityCandidate:
    """实体候选"""
    neo4j_id: str
    name: str
    entity_type: str
    aliases: List[str]
    properties: Dict
    similarity_score: float
    confidence: float


class EntityLinker:
    """实体链接器"""
    
    def __init__(self):
        self.similarity_threshold = 0.8
        self.alias_threshold = 0.9
        self.context_window = 100
    
    def link_entities(self, entities: List[Entity], text: str, 
                     knowledge_graph_id: str = None) -> List[Entity]:
        """
        链接实体到知识图谱
        
        Args:
            entities: 待链接的实体列表
            text: 原始文本
            knowledge_graph_id: 知识图谱ID
            
        Returns:
            List[Entity]: 链接后的实体列表
        """
        if not entities:
            return entities
        
        linked_entities = []
        
        try:
            for entity in entities:
                # 查找候选实体
                candidates = self._find_candidates(entity, knowledge_graph_id)
                
                if candidates:
                    # 选择最佳候选
                    best_candidate = self._select_best_candidate(
                        entity, candidates, text
                    )
                    
                    if best_candidate:
                        # 更新实体信息
                        linked_entity = self._create_linked_entity(entity, best_candidate)
                        linked_entities.append(linked_entity)
                    else:
                        # 没有合适的候选，保持原实体
                        linked_entities.append(entity)
                else:
                    # 没有找到候选，保持原实体
                    linked_entities.append(entity)
            
            # 实体消歧和合并
            disambiguated_entities = self._disambiguate_entities(linked_entities, text)
            
            logger.debug(f"链接了 {len([e for e in disambiguated_entities if hasattr(e, 'neo4j_id')])} 个实体")
            
            return disambiguated_entities
            
        except Exception as e:
            logger.error(f"实体链接失败: {e}")
            return entities
    
    def _find_candidates(self, entity: Entity, knowledge_graph_id: str = None) -> List[EntityCandidate]:
        """查找候选实体"""
        candidates = []
        
        try:
            with neo4j_manager.get_session() as session:
                # 构建查询条件
                where_conditions = ["e.type = $entity_type"]
                params = {"entity_type": entity.entity_type}
                
                if knowledge_graph_id:
                    where_conditions.append("e.knowledge_graph_id = $kg_id")
                    params["kg_id"] = knowledge_graph_id
                
                # 精确匹配
                exact_query = f"""
                MATCH (e:Entity)
                WHERE {' AND '.join(where_conditions)} AND e.name = $name
                RETURN e.id as neo4j_id, e.name as name, e.type as entity_type,
                       e.aliases as aliases, e as properties
                LIMIT 10
                """
                
                result = session.run(exact_query, {**params, "name": entity.text})
                
                for record in result:
                    candidate = EntityCandidate(
                        neo4j_id=record["neo4j_id"],
                        name=record["name"],
                        entity_type=record["entity_type"],
                        aliases=record["aliases"] or [],
                        properties=dict(record["properties"]),
                        similarity_score=1.0,  # 精确匹配
                        confidence=0.9
                    )
                    candidates.append(candidate)
                
                # 如果没有精确匹配，尝试模糊匹配
                if not candidates:
                    fuzzy_query = f"""
                    MATCH (e:Entity)
                    WHERE {' AND '.join(where_conditions)}
                    AND (e.name CONTAINS $partial_name OR 
                         any(alias IN e.aliases WHERE alias CONTAINS $partial_name))
                    RETURN e.id as neo4j_id, e.name as name, e.type as entity_type,
                           e.aliases as aliases, e as properties
                    LIMIT 20
                    """
                    
                    result = session.run(fuzzy_query, {**params, "partial_name": entity.text})
                    
                    for record in result:
                        # 计算相似度
                        similarity = self._calculate_similarity(
                            entity.text, record["name"], record["aliases"] or []
                        )
                        
                        if similarity >= self.similarity_threshold:
                            candidate = EntityCandidate(
                                neo4j_id=record["neo4j_id"],
                                name=record["name"],
                                entity_type=record["entity_type"],
                                aliases=record["aliases"] or [],
                                properties=dict(record["properties"]),
                                similarity_score=similarity,
                                confidence=similarity * 0.8  # 模糊匹配置信度较低
                            )
                            candidates.append(candidate)
                
        except Exception as e:
            logger.error(f"查找候选实体失败: {e}")
        
        return candidates
    
    def _calculate_similarity(self, text: str, name: str, aliases: List[str]) -> float:
        """计算相似度"""
        # 与主名称的相似度
        name_similarity = SequenceMatcher(None, text, name).ratio()
        
        # 与别名的相似度
        alias_similarities = []
        for alias in aliases:
            alias_similarity = SequenceMatcher(None, text, alias).ratio()
            alias_similarities.append(alias_similarity)
        
        # 取最高相似度
        max_alias_similarity = max(alias_similarities) if alias_similarities else 0
        
        return max(name_similarity, max_alias_similarity)
    
    def _select_best_candidate(self, entity: Entity, candidates: List[EntityCandidate], 
                             text: str) -> Optional[EntityCandidate]:
        """选择最佳候选实体"""
        if not candidates:
            return None
        
        # 计算上下文相似度
        for candidate in candidates:
            context_score = self._calculate_context_similarity(entity, candidate, text)
            candidate.confidence *= (1 + context_score * 0.3)  # 上下文加权
        
        # 按置信度排序
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        best_candidate = candidates[0]
        
        # 检查是否满足阈值
        if best_candidate.confidence >= 0.7:
            return best_candidate
        
        return None
    
    def _calculate_context_similarity(self, entity: Entity, candidate: EntityCandidate, 
                                    text: str) -> float:
        """计算上下文相似度"""
        # 获取实体周围的上下文
        start = max(0, entity.start_pos - self.context_window)
        end = min(len(text), entity.end_pos + self.context_window)
        context = text[start:end]
        
        # 简单的上下文匹配（可以扩展为更复杂的语义匹配）
        context_keywords = self._extract_context_keywords(context)
        candidate_keywords = self._extract_candidate_keywords(candidate)
        
        # 计算关键词重叠度
        if not context_keywords or not candidate_keywords:
            return 0.0
        
        intersection = len(context_keywords & candidate_keywords)
        union = len(context_keywords | candidate_keywords)
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_context_keywords(self, context: str) -> Set[str]:
        """提取上下文关键词"""
        # 简单的关键词提取
        words = re.findall(r'[\u4e00-\u9fff]+', context)
        return set(word for word in words if len(word) > 1)
    
    def _extract_candidate_keywords(self, candidate: EntityCandidate) -> Set[str]:
        """提取候选实体关键词"""
        keywords = set()
        
        # 从名称提取
        name_words = re.findall(r'[\u4e00-\u9fff]+', candidate.name)
        keywords.update(word for word in name_words if len(word) > 1)
        
        # 从别名提取
        for alias in candidate.aliases:
            alias_words = re.findall(r'[\u4e00-\u9fff]+', alias)
            keywords.update(word for word in alias_words if len(word) > 1)
        
        # 从属性提取
        description = candidate.properties.get('description', '')
        if description:
            desc_words = re.findall(r'[\u4e00-\u9fff]+', description)
            keywords.update(word for word in desc_words if len(word) > 1)
        
        return keywords
    
    def _create_linked_entity(self, original_entity: Entity, 
                            candidate: EntityCandidate) -> Entity:
        """创建链接后的实体"""
        # 复制原实体
        linked_entity = Entity(
            text=original_entity.text,
            entity_type=original_entity.entity_type,
            start_pos=original_entity.start_pos,
            end_pos=original_entity.end_pos,
            confidence=original_entity.confidence,
            context=original_entity.context,
            properties=original_entity.properties.copy()
        )
        
        # 添加链接信息
        linked_entity.properties.update({
            'neo4j_id': candidate.neo4j_id,
            'canonical_name': candidate.name,
            'aliases': candidate.aliases,
            'linking_confidence': candidate.confidence,
            'similarity_score': candidate.similarity_score,
            'is_linked': True
        })
        
        return linked_entity
    
    def _disambiguate_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """实体消歧和合并"""
        if len(entities) <= 1:
            return entities
        
        # 按类型分组
        type_groups = {}
        for entity in entities:
            entity_type = entity.entity_type
            if entity_type not in type_groups:
                type_groups[entity_type] = []
            type_groups[entity_type].append(entity)
        
        disambiguated = []
        
        # 对每个类型的实体进行消歧
        for entity_type, type_entities in type_groups.items():
            disambiguated_type_entities = self._disambiguate_same_type_entities(
                type_entities, text
            )
            disambiguated.extend(disambiguated_type_entities)
        
        return disambiguated
    
    def _disambiguate_same_type_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """消歧同类型实体"""
        if len(entities) <= 1:
            return entities
        
        # 查找可能重复的实体
        groups = []
        used = set()
        
        for i, entity1 in enumerate(entities):
            if i in used:
                continue
            
            group = [entity1]
            used.add(i)
            
            for j, entity2 in enumerate(entities[i+1:], i+1):
                if j in used:
                    continue
                
                if self._are_same_entity(entity1, entity2):
                    group.append(entity2)
                    used.add(j)
            
            groups.append(group)
        
        # 合并每个组中的实体
        merged_entities = []
        for group in groups:
            if len(group) == 1:
                merged_entities.append(group[0])
            else:
                merged_entity = self._merge_entities(group, text)
                merged_entities.append(merged_entity)
        
        return merged_entities
    
    def _are_same_entity(self, entity1: Entity, entity2: Entity) -> bool:
        """判断两个实体是否为同一实体"""
        # 如果都有neo4j_id，比较ID
        id1 = entity1.properties.get('neo4j_id')
        id2 = entity2.properties.get('neo4j_id')
        
        if id1 and id2:
            return id1 == id2
        
        # 比较文本相似度
        similarity = SequenceMatcher(None, entity1.text, entity2.text).ratio()
        
        if similarity >= 0.9:
            return True
        
        # 检查别名
        aliases1 = entity1.properties.get('aliases', [])
        aliases2 = entity2.properties.get('aliases', [])
        
        if entity1.text in aliases2 or entity2.text in aliases1:
            return True
        
        return False
    
    def _merge_entities(self, entities: List[Entity], text: str) -> Entity:
        """合并多个实体"""
        # 选择置信度最高的作为主实体
        main_entity = max(entities, key=lambda x: x.confidence)
        
        # 合并属性
        merged_properties = main_entity.properties.copy()
        
        # 收集所有别名
        all_aliases = set()
        for entity in entities:
            all_aliases.add(entity.text)
            aliases = entity.properties.get('aliases', [])
            all_aliases.update(aliases)
        
        merged_properties['aliases'] = list(all_aliases)
        merged_properties['merged_from'] = [e.text for e in entities]
        merged_properties['merge_confidence'] = sum(e.confidence for e in entities) / len(entities)
        
        # 创建合并后的实体
        merged_entity = Entity(
            text=main_entity.text,
            entity_type=main_entity.entity_type,
            start_pos=min(e.start_pos for e in entities),
            end_pos=max(e.end_pos for e in entities),
            confidence=max(e.confidence for e in entities),
            context=main_entity.context,
            properties=merged_properties
        )
        
        return merged_entity
    
    def create_new_entity_in_kg(self, entity: Entity, knowledge_graph_id: str) -> str:
        """在知识图谱中创建新实体"""
        try:
            with neo4j_manager.get_session() as session:
                # 生成唯一ID
                import uuid
                entity_id = str(uuid.uuid4())
                
                # 创建实体节点
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
                    knowledge_graph_id: $kg_id
                })
                RETURN e.id as neo4j_id
                """
                
                params = {
                    'entity_id': entity_id,
                    'name': entity.text,
                    'entity_type': entity.entity_type,
                    'domain': 'general',  # 可以从配置获取
                    'description': entity.properties.get('description', ''),
                    'confidence': entity.confidence,
                    'source': 'extraction',
                    'kg_id': knowledge_graph_id
                }
                
                result = session.run(create_query, params)
                record = result.single()
                
                if record:
                    logger.info(f"创建新实体: {entity.text} -> {entity_id}")
                    return entity_id
                
        except Exception as e:
            logger.error(f"创建新实体失败: {e}")
        
        return None
    
    def get_linking_statistics(self, entities: List[Entity]) -> Dict:
        """获取链接统计信息"""
        if not entities:
            return {}
        
        linked_count = sum(1 for e in entities if e.properties.get('is_linked', False))
        
        stats = {
            'total_entities': len(entities),
            'linked_entities': linked_count,
            'unlinked_entities': len(entities) - linked_count,
            'linking_rate': linked_count / len(entities) if entities else 0,
            'avg_linking_confidence': 0.0,
            'type_linking_rates': {}
        }
        
        # 计算平均链接置信度
        linking_confidences = [
            e.properties.get('linking_confidence', 0) 
            for e in entities if e.properties.get('is_linked', False)
        ]
        
        if linking_confidences:
            stats['avg_linking_confidence'] = sum(linking_confidences) / len(linking_confidences)
        
        # 按类型统计链接率
        type_stats = {}
        for entity in entities:
            entity_type = entity.entity_type
            if entity_type not in type_stats:
                type_stats[entity_type] = {'total': 0, 'linked': 0}
            
            type_stats[entity_type]['total'] += 1
            if entity.properties.get('is_linked', False):
                type_stats[entity_type]['linked'] += 1
        
        for entity_type, counts in type_stats.items():
            stats['type_linking_rates'][entity_type] = (
                counts['linked'] / counts['total'] if counts['total'] > 0 else 0
            )
        
        return stats
