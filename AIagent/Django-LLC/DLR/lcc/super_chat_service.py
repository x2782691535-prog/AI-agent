"""
超级智能对话服务
整合知识库、知识图谱和大模型的综合对话系统
"""

import logging
import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from django.conf import settings
from .neo4j_manager import Neo4jManager
from .kb_service import KnowledgeBaseService
from .kg_qa_service import KnowledgeGraphQAService

logger = logging.getLogger(__name__)

class SuperChatService:
    """超级智能对话服务"""
    
    def __init__(self):
        self.neo4j_manager = Neo4jManager()
        self.kb_service = KnowledgeBaseService()
        self.kg_qa_service = KnowledgeGraphQAService()
        self.llm_api_base = 'http://127.0.0.1:7861/v1/chat/completions'
        
    def super_chat(self, 
                   question: str,
                   model: str = 'deepseek-r1',
                   kb_name: Optional[str] = None,
                   kg_id: Optional[int] = None,
                   top_k: int = 3,
                   score_threshold: float = 0.5,
                   max_entities: int = 8,
                   max_relations: int = 12) -> Dict[str, Any]:
        """
        超级智能对话主函数
        
        Args:
            question: 用户问题
            model: 使用的大模型
            kb_name: 知识库名称（可选）
            kg_id: 知识图谱ID（可选）
            top_k: 知识库检索数量
            score_threshold: 知识库相似度阈值
            max_entities: 知识图谱最大实体数
            max_relations: 知识图谱最大关系数
            
        Returns:
            包含回答和来源信息的字典
        """
        try:
            logger.info(f"开始超级智能对话: {question}")
            logger.info(f"参数: model={model}, kb_name={kb_name}, kg_id={kg_id}")
            
            # 1. 问题理解和意图分析
            question_analysis = self._analyze_question(question, model)
            logger.info(f"问题分析完成: {question_analysis}")
            
            # 2. 并行检索知识库和知识图谱
            kb_results = None
            kg_results = None
            
            # 知识库检索
            if kb_name:
                kb_results = self._search_knowledge_base(
                    question, kb_name, model, top_k, score_threshold
                )
                logger.info(f"知识库检索完成: 找到{len(kb_results.get('docs', []))}个相关文档")
            
            # 知识图谱查询
            if kg_id:
                kg_results = self._query_knowledge_graph(
                    question, kg_id, max_entities, max_relations
                )
                logger.info(f"知识图谱查询完成: 找到{len(kg_results.get('entities', []))}个实体")
            
            # 3. 整合所有信息并生成综合回答
            final_answer = self._generate_comprehensive_answer(
                question, question_analysis, kb_results, kg_results, model
            )
            
            return {
                'success': True,
                'answer': final_answer['content'],
                'question_analysis': question_analysis,
                'knowledge_base_results': kb_results,
                'knowledge_graph_results': kg_results,
                'sources': {
                    'kb_docs': kb_results.get('docs', []) if kb_results else [],
                    'kg_entities': kg_results.get('entities', []) if kg_results else [],
                    'kg_relations': kg_results.get('relations', []) if kg_results else []
                },
                'metadata': {
                    'model': model,
                    'kb_name': kb_name,
                    'kg_id': kg_id,
                    'total_sources': (
                        len(kb_results.get('docs', [])) if kb_results else 0
                    ) + (
                        len(kg_results.get('entities', [])) if kg_results else 0
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"超级智能对话失败: {str(e)}")
            return {
                'success': False,
                'error': f"对话处理失败: {str(e)}",
                'answer': '抱歉，处理您的问题时遇到了错误，请稍后重试。'
            }
    
    def _analyze_question(self, question: str, model: str) -> Dict[str, Any]:
        """分析问题意图和关键信息"""
        try:
            analysis_prompt = f"""
请分析以下用户问题，提取关键信息：

用户问题：{question}

请从以下几个方面分析：
1. 问题类型（事实查询、解释说明、比较分析、操作指导等）
2. 关键词和实体（提取重要的名词、概念、技术术语）
3. 问题意图（用户想要了解什么）
4. 可能的知识领域（技术、科学、历史等）

请以JSON格式返回分析结果：
{{
    "question_type": "问题类型",
    "keywords": ["关键词1", "关键词2"],
    "entities": ["实体1", "实体2"],
    "intent": "问题意图描述",
    "domain": "知识领域",
    "complexity": "简单/中等/复杂"
}}
"""
            
            response = self._call_llm(analysis_prompt, model)
            
            # 尝试解析JSON响应
            try:
                content = response.get('content', '{}')
                # 提取JSON部分
                if '{' in content and '}' in content:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    json_str = content[json_start:json_end]
                    analysis = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            except (json.JSONDecodeError, ValueError):
                # 如果JSON解析失败，返回基础分析
                analysis = {
                    "question_type": "一般查询",
                    "keywords": self._extract_simple_keywords(question),
                    "entities": [],
                    "intent": "获取相关信息",
                    "domain": "通用",
                    "complexity": "中等"
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"问题分析失败: {str(e)}")
            return {
                "question_type": "一般查询",
                "keywords": self._extract_simple_keywords(question),
                "entities": [],
                "intent": "获取相关信息",
                "domain": "通用",
                "complexity": "中等"
            }
    
    def _extract_simple_keywords(self, question: str) -> List[str]:
        """简单的关键词提取"""
        import re
        
        # 提取中文词汇（2-4个字符）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
        
        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]{2,}', question)
        
        # 提取数字+字母组合
        alphanumeric = re.findall(r'[A-Z]+\d+[A-Z]*\d*', question, re.IGNORECASE)
        
        keywords = chinese_words + [w.lower() for w in english_words] + [w.upper() for w in alphanumeric]
        
        # 过滤停用词
        stop_words = {
            '什么', '怎么', '为什么', '哪里', '谁', '何时', '如何', '是否',
            'what', 'how', 'why', 'where', 'when', 'who', 'which'
        }
        
        return [kw for kw in keywords if kw not in stop_words and len(kw) > 1][:10]
    
    def _search_knowledge_base(self, question: str, kb_name: str, model: str,
                              top_k: int, score_threshold: float) -> Optional[Dict[str, Any]]:
        """搜索知识库"""
        try:
            # 使用现有的知识库服务
            docs = self.kb_service.search_docs(
                kb_name=kb_name,
                query=question,
                top_k=top_k,
                score_threshold=score_threshold
            )

            # search_docs直接返回文档列表
            if docs:
                # 格式化文档数据
                formatted_docs = []
                for doc in docs:
                    if isinstance(doc, dict):
                        formatted_doc = {
                            'title': doc.get('metadata', {}).get('source', '未知文档'),
                            'content': doc.get('page_content', ''),
                            'score': doc.get('score', 0.0)
                        }
                        formatted_docs.append(formatted_doc)
                    else:
                        # 如果是其他格式，尝试转换
                        formatted_docs.append({
                            'title': '文档',
                            'content': str(doc),
                            'score': 0.0
                        })

                return {
                    'docs': formatted_docs,
                    'total_found': len(formatted_docs)
                }
            else:
                logger.info(f"知识库搜索未找到相关文档: {question}")
                return {
                    'docs': [],
                    'total_found': 0
                }

        except Exception as e:
            logger.error(f"知识库搜索异常: {str(e)}")
            return None
    
    def _query_knowledge_graph(self, question: str, kg_id: int, 
                              max_entities: int, max_relations: int) -> Optional[Dict[str, Any]]:
        """查询知识图谱"""
        try:
            # 使用现有的知识图谱问答服务的实体提取功能
            entities, relations = self.kg_qa_service._extract_entities_and_relations(
                kg_id, question
            )
            
            if entities:
                # 获取详细的图谱上下文
                context = self.kg_qa_service._retrieve_graph_context(
                    kg_id, entities, relations, max_entities, max_relations
                )
                
                return {
                    'entities': context.get('entities', []),
                    'relations': context.get('relations', []),
                    'paths': context.get('paths', []),
                    'total_entities': len(context.get('entities', [])),
                    'total_relations': len(context.get('relations', []))
                }
            else:
                return {
                    'entities': [],
                    'relations': [],
                    'paths': [],
                    'total_entities': 0,
                    'total_relations': 0
                }
                
        except Exception as e:
            logger.error(f"知识图谱查询异常: {str(e)}")
            return None

    def _generate_comprehensive_answer(self, question: str, question_analysis: Dict[str, Any],
                                     kb_results: Optional[Dict[str, Any]],
                                     kg_results: Optional[Dict[str, Any]],
                                     model: str) -> Dict[str, str]:
        """生成综合回答"""
        try:
            # 构建综合提示词
            prompt = self._build_comprehensive_prompt(
                question, question_analysis, kb_results, kg_results
            )

            logger.info(f"综合提示词长度: {len(prompt)} 字符")

            # 调用大模型生成回答
            response = self._call_llm(prompt, model)

            return response

        except Exception as e:
            logger.error(f"生成综合回答失败: {str(e)}")
            return {
                'content': f"抱歉，生成回答时遇到错误: {str(e)}"
            }

    def _build_comprehensive_prompt(self, question: str, question_analysis: Dict[str, Any],
                                   kb_results: Optional[Dict[str, Any]],
                                   kg_results: Optional[Dict[str, Any]]) -> str:
        """构建综合提示词"""

        prompt_parts = []

        # 系统角色定义
        prompt_parts.append("""你是一个超级智能助手，能够整合多种知识源来回答用户问题。
你可以访问知识库文档和知识图谱数据，请基于这些信息提供准确、全面的回答。

回答要求：
1. 基于提供的知识源信息回答，确保准确性
2. 如果多个知识源有相关信息，请综合分析
3. 明确标注信息来源（知识库文档或知识图谱）
4. 如果信息不足，请诚实说明
5. 回答要结构清晰，逻辑性强""")

        # 问题分析信息
        prompt_parts.append(f"\n## 问题分析")
        prompt_parts.append(f"用户问题：{question}")
        prompt_parts.append(f"问题类型：{question_analysis.get('question_type', '未知')}")
        prompt_parts.append(f"关键词：{', '.join(question_analysis.get('keywords', []))}")
        prompt_parts.append(f"问题意图：{question_analysis.get('intent', '未知')}")
        prompt_parts.append(f"知识领域：{question_analysis.get('domain', '未知')}")

        # 知识库信息
        if kb_results and kb_results.get('docs'):
            prompt_parts.append(f"\n## 知识库信息")
            prompt_parts.append(f"找到 {len(kb_results['docs'])} 个相关文档：")

            for i, doc in enumerate(kb_results['docs'][:5], 1):  # 最多显示5个文档
                prompt_parts.append(f"\n### 文档 {i}")
                prompt_parts.append(f"标题：{doc.get('title', '未知')}")
                prompt_parts.append(f"内容：{doc.get('content', '')[:500]}...")  # 限制长度
                if doc.get('score'):
                    prompt_parts.append(f"相似度：{doc['score']:.3f}")

        # 知识图谱信息
        if kg_results and (kg_results.get('entities') or kg_results.get('relations')):
            prompt_parts.append(f"\n## 知识图谱信息")

            entities = kg_results.get('entities', [])
            if entities:
                prompt_parts.append(f"\n### 相关实体 ({len(entities)} 个)：")
                for entity in entities[:8]:  # 最多显示8个实体
                    prompt_parts.append(f"- {entity['name']} ({entity['type']})")
                    if entity.get('description'):
                        prompt_parts.append(f"  描述：{entity['description'][:100]}...")

            relations = kg_results.get('relations', [])
            if relations:
                prompt_parts.append(f"\n### 相关关系 ({len(relations)} 个)：")
                for relation in relations[:6]:  # 最多显示6个关系
                    source = relation['source']['name']
                    rel_type = relation['relation']['type']
                    target = relation['target']['name']
                    prompt_parts.append(f"- {source} --{rel_type}--> {target}")

            paths = kg_results.get('paths', [])
            if paths:
                prompt_parts.append(f"\n### 实体路径 ({len(paths)} 条)：")
                for i, path in enumerate(paths[:3], 1):  # 最多显示3条路径
                    nodes = [f"{node['name']}({node['type']})" for node in path['nodes']]
                    prompt_parts.append(f"路径{i}: {' -> '.join(nodes)}")

        # 如果没有找到相关信息
        if not kb_results and not kg_results:
            prompt_parts.append(f"\n## 注意")
            prompt_parts.append("没有找到相关的知识库文档或知识图谱信息。请基于你的通用知识回答，并说明信息来源限制。")
        elif not kb_results:
            prompt_parts.append(f"\n## 注意")
            prompt_parts.append("没有找到相关的知识库文档，回答主要基于知识图谱信息。")
        elif not kg_results:
            prompt_parts.append(f"\n## 注意")
            prompt_parts.append("没有找到相关的知识图谱信息，回答主要基于知识库文档。")

        # 回答指导
        prompt_parts.append(f"\n## 请回答")
        prompt_parts.append("请基于以上信息回答用户问题。回答要：")
        prompt_parts.append("1. 准确引用相关信息")
        prompt_parts.append("2. 结构清晰，分点说明")
        prompt_parts.append("3. 标注信息来源")
        prompt_parts.append("4. 如有不确定的地方，请说明")

        return '\n'.join(prompt_parts)

    def _call_llm(self, prompt: str, model: str) -> Dict[str, str]:
        """调用大模型API"""
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.3,  # 降低温度，提高准确性
                "max_tokens": 2000,  # 增加最大token数
                "top_p": 0.8
            }

            logger.info(f"调用LLM API: {self.llm_api_base}")

            response = requests.post(
                self.llm_api_base,
                json=payload,
                timeout=300  # 增加到300秒超时
            )

            if response.status_code == 200:
                data = response.json()
                logger.info("LLM API调用成功")

                # 解析OpenAI格式的响应
                if 'choices' in data and len(data['choices']) > 0:
                    choice = data['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        content = choice['message']['content']
                        return {'content': content}
                    elif 'text' in choice:
                        return {'content': choice['text']}

                # 如果格式不符合预期，返回原始响应
                return {'content': str(data)}
            else:
                logger.error(f"LLM API调用失败: {response.status_code}, {response.text}")
                return {'content': f"AI服务调用失败: {response.status_code}"}

        except requests.exceptions.Timeout:
            logger.error("LLM API超时")
            return {'content': "AI服务响应超时，请稍后重试"}
        except Exception as e:
            logger.error(f"调用LLM失败: {e}")
            return {'content': f"AI服务调用异常: {str(e)}"}


# 创建全局服务实例
super_chat_service = SuperChatService()
