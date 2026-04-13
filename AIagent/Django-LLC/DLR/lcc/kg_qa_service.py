"""
知识图谱智能问答服务
结合知识图谱的结构化数据和大模型的理解能力
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from .neo4j_manager import Neo4jManager
from .models import KnowledgeGraph, EntityRecord, RelationRecord

logger = logging.getLogger(__name__)

class KnowledgeGraphQAService:
    """知识图谱智能问答服务"""
    
    def __init__(self):
        self.neo4j_manager = Neo4jManager()
        # 使用正确的LLM API端点
        self.llm_api_base = 'http://127.0.0.1:7861/v1/chat/completions'
        self.default_model = getattr(settings, 'LCC_DEFAULT_MODEL', 'deepseek-r1')
    
    def answer_question(self, kg_id: int, question: str, model: str = None, 
                       max_entities: int = 10, max_relations: int = 20) -> Dict:
        """
        基于知识图谱回答问题
        
        Args:
            kg_id: 知识图谱ID
            question: 用户问题
            model: 使用的大模型
            max_entities: 最大检索实体数
            max_relations: 最大检索关系数
            
        Returns:
            包含答案和相关信息的字典
        """
        try:
            # 1. 验证知识图谱
            kg = self._validate_knowledge_graph(kg_id)
            if not kg:
                return {
                    'success': False,
                    'error': '知识图谱不存在或无数据'
                }
            
            # 2. 从问题中提取关键实体和关系
            entities, relations = self._extract_entities_and_relations(kg_id, question)
            
            # 3. 检索相关的图谱数据
            graph_context = self._retrieve_graph_context(
                kg_id, entities, relations, max_entities, max_relations
            )
            
            # 4. 构建增强的提示词
            enhanced_prompt = self._build_enhanced_prompt(
                question, graph_context, kg
            )
            
            # 5. 调用大模型生成答案
            llm_response = self._call_llm(enhanced_prompt, model or self.default_model)
            
            # 6. 构建完整响应
            return {
                'success': True,
                'answer': llm_response.get('content', ''),
                'knowledge_graph': {
                    'id': kg.id,
                    'name': kg.name,
                    'domain': kg.domain
                },
                'context': {
                    'entities_found': len(entities),
                    'relations_found': len(relations),
                    'graph_context_size': len(graph_context.get('entities', [])) + len(graph_context.get('relations', []))
                },
                'sources': graph_context
            }
            
        except Exception as e:
            logger.error(f"知识图谱问答失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_knowledge_graph(self, kg_id: int) -> Optional[KnowledgeGraph]:
        """验证知识图谱是否存在且有数据"""
        try:
            kg = KnowledgeGraph.objects.get(id=kg_id)
            if kg.entity_count == 0:
                return None
            return kg
        except KnowledgeGraph.DoesNotExist:
            return None
    
    def _extract_entities_and_relations(self, kg_id: int, question: str) -> Tuple[List[Dict], List[Dict]]:
        """从问题中提取可能相关的实体和关系"""
        entities = []
        relations = []
        
        try:
            with self.neo4j_manager.get_session() as session:
                # 使用模糊匹配查找相关实体
                entity_query = """
                MATCH (e:Entity {knowledge_graph_id: $kg_id})
                WHERE toLower(e.name) CONTAINS toLower($keyword)
                   OR toLower(e.entity_type) CONTAINS toLower($keyword)
                RETURN e.name as name, e.entity_type as type, id(e) as id
                LIMIT 10
                """
                
                # 分词并搜索实体
                keywords = self._extract_keywords(question)
                for keyword in keywords:
                    result = session.run(entity_query, kg_id=kg_id, keyword=keyword)
                    for record in result:
                        entity_info = {
                            'id': record['id'],
                            'name': record['name'],
                            'type': record['type'],
                            'keyword': keyword
                        }
                        if entity_info not in entities:
                            entities.append(entity_info)
                
                # 查找相关关系类型
                relation_query = """
                MATCH ()-[r {knowledge_graph_id: $kg_id}]->()
                WHERE toLower(type(r)) CONTAINS toLower($keyword)
                RETURN DISTINCT type(r) as relation_type
                LIMIT 5
                """
                
                for keyword in keywords:
                    result = session.run(relation_query, kg_id=kg_id, keyword=keyword)
                    for record in result:
                        relation_info = {
                            'type': record['relation_type'],
                            'keyword': keyword
                        }
                        if relation_info not in relations:
                            relations.append(relation_info)
        
        except Exception as e:
            logger.error(f"提取实体和关系失败: {e}")
        
        return entities, relations
    
    def _extract_keywords(self, question: str) -> List[str]:
        """从问题中提取关键词"""
        import re

        keywords = []

        # 1. 提取中文词汇（2-4个字符）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
        keywords.extend(chinese_words)

        # 2. 提取英文单词
        english_words = re.findall(r'[a-zA-Z]{2,}', question)
        keywords.extend([word.lower() for word in english_words])

        # 3. 提取数字+字母组合（如AT24, DS18B20等）
        alphanumeric = re.findall(r'[A-Z]+\d+[A-Z]*\d*', question, re.IGNORECASE)
        keywords.extend([word.upper() for word in alphanumeric])

        # 过滤停用词
        stop_words = {
            '的', '是', '在', '有', '和', '与', '或', '但', '如果', '那么',
            '什么', '怎么', '为什么', '哪里', '谁', '何时', '这个', '那个',
            '包含', '哪些', '总结', '主要', '内容', '功能', '特点',
            'what', 'how', 'why', 'where', 'when', 'who', 'which', 'that', 'this'
        }

        # 去重并过滤停用词
        filtered_keywords = []
        for keyword in keywords:
            if keyword not in stop_words and len(keyword) > 1 and keyword not in filtered_keywords:
                filtered_keywords.append(keyword)

        return filtered_keywords[:15]  # 增加关键词数量限制
    
    def _retrieve_graph_context(self, kg_id: int, entities: List[Dict], 
                               relations: List[Dict], max_entities: int, max_relations: int) -> Dict:
        """检索相关的图谱上下文"""
        context = {
            'entities': [],
            'relations': [],
            'paths': []
        }
        
        try:
            with self.neo4j_manager.get_session() as session:
                # 获取实体详细信息
                if entities:
                    entity_ids = [e['id'] for e in entities[:max_entities]]
                    entity_detail_query = """
                    MATCH (e:Entity {knowledge_graph_id: $kg_id})
                    WHERE id(e) IN $entity_ids
                    RETURN e.name as name, e.entity_type as type, id(e) as id,
                           e.description as description, e.properties as properties
                    """
                    
                    result = session.run(entity_detail_query, kg_id=kg_id, entity_ids=entity_ids)
                    for record in result:
                        context['entities'].append({
                            'id': record['id'],
                            'name': record['name'],
                            'type': record['type'],
                            'description': record.get('description', ''),
                            'properties': record.get('properties', {})
                        })
                
                # 获取相关关系
                if entities:
                    entity_ids = [e['id'] for e in entities[:max_entities]]
                    relation_query = """
                    MATCH (s:Entity {knowledge_graph_id: $kg_id})-[r]->(t:Entity {knowledge_graph_id: $kg_id})
                    WHERE id(s) IN $entity_ids OR id(t) IN $entity_ids
                    RETURN s.name as source_name, s.entity_type as source_type,
                           type(r) as relation_type, r.properties as relation_properties,
                           t.name as target_name, t.entity_type as target_type
                    LIMIT $max_relations
                    """
                    
                    result = session.run(relation_query, 
                                       kg_id=kg_id, 
                                       entity_ids=entity_ids, 
                                       max_relations=max_relations)
                    
                    for record in result:
                        context['relations'].append({
                            'source': {
                                'name': record['source_name'],
                                'type': record['source_type']
                            },
                            'relation': {
                                'type': record['relation_type'],
                                'properties': record.get('relation_properties', {})
                            },
                            'target': {
                                'name': record['target_name'],
                                'type': record['target_type']
                            }
                        })
                
                # 查找实体间的路径（如果有多个相关实体）
                if len(entities) >= 2:
                    entity_ids = [e['id'] for e in entities[:5]]  # 限制路径查询的实体数量
                    path_query = """
                    MATCH path = (s:Entity {knowledge_graph_id: $kg_id})-[*1..3]-(t:Entity {knowledge_graph_id: $kg_id})
                    WHERE id(s) IN $entity_ids AND id(t) IN $entity_ids AND id(s) <> id(t)
                    RETURN [node in nodes(path) | {name: node.name, type: node.entity_type}] as nodes,
                           [rel in relationships(path) | type(rel)] as relations
                    LIMIT 5
                    """
                    
                    result = session.run(path_query, kg_id=kg_id, entity_ids=entity_ids)
                    for record in result:
                        context['paths'].append({
                            'nodes': record['nodes'],
                            'relations': record['relations']
                        })
        
        except Exception as e:
            logger.error(f"检索图谱上下文失败: {e}")
        
        return context
    
    def _build_enhanced_prompt(self, question: str, graph_context: Dict, kg: KnowledgeGraph) -> str:
        """构建增强的提示词"""
        prompt_parts = [
            f"你是一个基于知识图谱的智能问答助手。请根据以下知识图谱信息回答用户问题。",
            f"",
            f"知识图谱信息：",
            f"- 名称：{kg.name}",
            f"- 领域：{kg.get_domain_display()}",
            f"- 描述：{kg.description or '无描述'}",
            f"",
            f"用户问题：{question}",
            f""
        ]
        
        # 添加相关实体信息
        if graph_context.get('entities'):
            prompt_parts.append("相关实体：")
            for entity in graph_context['entities']:
                entity_info = f"- {entity['name']} ({entity['type']})"
                if entity.get('description'):
                    entity_info += f": {entity['description']}"
                prompt_parts.append(entity_info)
            prompt_parts.append("")
        
        # 添加相关关系信息
        if graph_context.get('relations'):
            prompt_parts.append("相关关系：")
            for relation in graph_context['relations']:
                rel_info = f"- {relation['source']['name']} --{relation['relation']['type']}--> {relation['target']['name']}"
                prompt_parts.append(rel_info)
            prompt_parts.append("")
        
        # 添加路径信息
        if graph_context.get('paths'):
            prompt_parts.append("实体间路径：")
            for i, path in enumerate(graph_context['paths'], 1):
                path_str = " -> ".join([f"{node['name']}({node['type']})" for node in path['nodes']])
                prompt_parts.append(f"- 路径{i}: {path_str}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "请基于以上知识图谱信息回答用户问题。要求：",
            "1. 优先使用知识图谱中的准确信息",
            "2. 如果知识图谱信息不足，可以结合常识进行推理",
            "3. 明确指出答案的来源（知识图谱 vs 推理）",
            "4. 如果无法回答，请诚实说明原因",
            "5. 回答要简洁明了，重点突出"
        ])
        
        return "\n".join(prompt_parts)
    
    def _call_llm(self, prompt: str, model: str) -> Dict:
        """调用大模型API - 与知识库服务保持一致"""
        try:
            # 使用与知识库服务完全相同的API格式和参数
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.3,  # 降低温度，减少随机性
                "max_tokens": 1000,  # 限制最大token数
                "top_p": 0.8
            }

            logger.info(f"调用LLM API: {self.llm_api_base}")
            logger.info(f"提示词长度: {len(prompt)} 字符")
            logger.info(f"提示词预览: {prompt[:200]}...")

            # 使用与知识库服务相同的超时时间
            timeout = 200  # 200秒超时，与知识库服务保持一致

            response = requests.post(
                self.llm_api_base,
                json=payload,
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()
                logger.info("LLM API调用成功")
                logger.info(f"LLM响应结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")

                # 解析OpenAI格式的响应
                if 'choices' in data and len(data['choices']) > 0:
                    choice = data['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        content = choice['message']['content']
                        logger.info(f"成功获取LLM回答，长度: {len(content)} 字符")
                        return {'content': content}
                    elif 'text' in choice:
                        content = choice['text']
                        logger.info(f"成功获取LLM回答（text字段），长度: {len(content)} 字符")
                        return {'content': content}

                # 如果格式不符合预期，返回原始响应
                logger.warning("LLM响应格式异常，使用原始响应")
                return {'content': str(data)}
            else:
                logger.error(f"LLM API调用失败: {response.status_code}, {response.text}")
                # 返回基于知识图谱的基础回答
                return self._generate_fallback_answer(prompt)

        except requests.exceptions.Timeout as e:
            logger.error(f"LLM API超时: {str(e)}")
            # 返回基于知识图谱的基础回答
            return self._generate_fallback_answer(prompt)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"LLM API连接失败: {str(e)}")
            # 返回基于知识图谱的基础回答
            return self._generate_fallback_answer(prompt)
        except Exception as e:
            logger.error(f"调用LLM失败: {e}")
            # 返回基于知识图谱的基础回答
            return self._generate_fallback_answer(prompt)

    def _generate_fallback_answer(self, prompt: str) -> Dict:
        """当LLM不可用时，生成基于知识图谱的基础回答"""
        try:
            # 从提示词中提取知识图谱信息
            lines = prompt.split('\n')
            kg_name = ""
            kg_domain = ""
            entities = []
            relations = []

            for line in lines:
                if "名称：" in line:
                    kg_name = line.split("名称：")[1].strip()
                elif "领域：" in line:
                    kg_domain = line.split("领域：")[1].strip()
                elif line.startswith("- ") and "(" in line and ")" in line:
                    # 解析实体信息
                    entity_info = line[2:].strip()
                    if " (" in entity_info and entity_info.endswith(")"):
                        name = entity_info.split(" (")[0]
                        type_info = entity_info.split(" (")[1][:-1]
                        entities.append(f"{name}({type_info})")
                elif line.startswith("- ") and "--" in line and "-->" in line:
                    # 解析关系信息
                    relations.append(line[2:].strip())

            # 生成基础回答
            answer_parts = []

            if kg_name:
                answer_parts.append(f"基于知识图谱「{kg_name}」的信息：")

            if entities:
                answer_parts.append(f"\n📊 相关实体（{len(entities)}个）：")
                for entity in entities[:5]:  # 只显示前5个
                    answer_parts.append(f"• {entity}")
                if len(entities) > 5:
                    answer_parts.append(f"• 还有{len(entities)-5}个相关实体...")

            if relations:
                answer_parts.append(f"\n🔗 相关关系（{len(relations)}个）：")
                for relation in relations[:3]:  # 只显示前3个
                    answer_parts.append(f"• {relation}")
                if len(relations) > 3:
                    answer_parts.append(f"• 还有{len(relations)-3}个相关关系...")

            if not entities and not relations:
                answer_parts.append("抱歉，在当前知识图谱中没有找到与您问题直接相关的信息。")
                answer_parts.append("建议您：")
                answer_parts.append("1. 尝试使用更具体的关键词")
                answer_parts.append("2. 检查知识图谱是否包含相关领域的数据")
                answer_parts.append("3. 联系管理员确认AI服务状态")
            else:
                answer_parts.append(f"\n💡 注意：由于AI服务暂时不可用，以上是基于知识图谱结构化数据的基础回答。")

            return {
                'content': '\n'.join(answer_parts)
            }

        except Exception as e:
            logger.error(f"生成基础回答失败: {e}")
            return {
                'content': '抱歉，AI服务暂时不可用，且无法生成基础回答。请稍后重试或联系管理员。'
            }

# 创建全局实例
kg_qa_service = KnowledgeGraphQAService()
