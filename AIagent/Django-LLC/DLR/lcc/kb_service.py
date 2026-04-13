"""
知识库管理服务 - 集成Langchain-Chatchat
"""

import requests
import logging
import json
import os
from typing import List, Dict, Optional
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """知识库管理服务"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or getattr(settings, 'CHATCHAT_API_BASE_URL', 'http://127.0.0.1:7861')
        self.timeout = 60  # 增加默认超时到60秒
        self.upload_timeout = 1800  # 上传操作超时30分钟（适合大PDF）
        self.pdf_timeout = 3600  # PDF处理超时1小时
        
    def _make_request(self, method, endpoint, **kwargs):
        """统一的请求处理"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {method} {url} - {str(e)}")
            raise Exception(f"API请求失败: {str(e)}")
    
    def list_knowledge_bases(self) -> List[str]:
        """获取知识库列表"""
        try:
            data = self._make_request('GET', '/knowledge_base/list_knowledge_bases')
            kb_list = data.get('data', [])
            # 提取知识库名称
            if isinstance(kb_list, list) and len(kb_list) > 0:
                if isinstance(kb_list[0], dict) and 'kb_name' in kb_list[0]:
                    return [kb['kb_name'] for kb in kb_list]
                elif isinstance(kb_list[0], str):
                    return kb_list
            return []
        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return []
    
    def create_knowledge_base(self, kb_name: str, vector_store_type: str = "faiss",
                            embed_model: str = "bge-m3") -> Dict:
        """创建知识库"""
        data = {
            "knowledge_base_name": kb_name,
            "vector_store_type": vector_store_type,
            "embed_model": embed_model
        }
        
        try:
            result = self._make_request('POST', '/knowledge_base/create_knowledge_base', json=data)
            logger.info(f"创建知识库成功: {kb_name}")
            return result
        except Exception as e:
            logger.error(f"创建知识库失败: {kb_name} - {str(e)}")
            raise
    
    def delete_knowledge_base(self, kb_name: str) -> Dict:
        """删除知识库"""
        data = {"knowledge_base_name": kb_name}
        
        try:
            result = self._make_request('POST', '/knowledge_base/delete_knowledge_base', json=data)
            logger.info(f"删除知识库成功: {kb_name}")
            return result
        except Exception as e:
            logger.error(f"删除知识库失败: {kb_name} - {str(e)}")
            raise
    
    def list_files(self, kb_name: str) -> List[str]:
        """获取知识库文件列表"""
        try:
            data = self._make_request('GET', f'/knowledge_base/list_files?knowledge_base_name={kb_name}')
            files_data = data.get('data', [])

            # 提取文件名
            if isinstance(files_data, list) and len(files_data) > 0:
                if isinstance(files_data[0], dict) and 'file_name' in files_data[0]:
                    return [file_info['file_name'] for file_info in files_data]
                elif isinstance(files_data[0], str):
                    return files_data

            return []
        except Exception as e:
            logger.error(f"获取文件列表失败: {kb_name} - {str(e)}")
            return []
    
    def upload_file(self, kb_name: str, file_path: str, file_content: bytes,
                   override: bool = False) -> Dict:
        """上传文件到知识库"""
        files = {
            'files': (os.path.basename(file_path), file_content, 'application/octet-stream')
        }
        data = {
            'knowledge_base_name': kb_name,
            'override': str(override).lower()
        }

        try:
            url = f"{self.base_url}/knowledge_base/upload_docs"

            # 根据文件类型选择超时时间
            file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
            if file_ext == 'pdf':
                timeout = self.pdf_timeout  # PDF文件使用1小时超时
                logger.info(f"PDF文件检测到，使用扩展超时: {timeout}秒")
            else:
                timeout = self.upload_timeout  # 其他文件使用30分钟超时

            logger.info(f"开始上传文件: {file_path} -> {kb_name} (超时: {timeout}秒)")
            response = requests.post(url, files=files, data=data, timeout=timeout)
            response.raise_for_status()
            result = response.json()
            logger.info(f"上传文件成功: {file_path} -> {kb_name}")
            return result
        except requests.exceptions.Timeout as e:
            logger.error(f"上传文件超时: {file_path} -> {kb_name} - 处理时间超过{timeout}秒")
            if file_ext == 'pdf':
                raise Exception(f"PDF文档处理超时。大型PDF文档的OCR处理可能需要很长时间，请考虑：\n1. 分割PDF为较小的文件\n2. 使用文本版PDF而非扫描版\n3. 稍后重试")
            else:
                raise Exception(f"文档上传超时，请尝试上传较小的文件或稍后重试")
        except Exception as e:
            logger.error(f"上传文件失败: {file_path} -> {kb_name} - {str(e)}")
            raise
    
    def delete_file(self, kb_name: str, file_name: str) -> Dict:
        """删除知识库文件"""
        data = {
            "knowledge_base_name": kb_name,
            "file_names": [file_name]
        }
        
        try:
            result = self._make_request('POST', '/knowledge_base/delete_docs', json=data)
            logger.info(f"删除文件成功: {file_name} from {kb_name}")
            return result
        except Exception as e:
            logger.error(f"删除文件失败: {file_name} from {kb_name} - {str(e)}")
            raise
    
    def search_docs(self, kb_name: str, query: str, top_k: int = 3,
                   score_threshold: float = 0.5) -> List[Dict]:
        """搜索知识库文档

        Args:
            kb_name: 知识库名称
            query: 查询内容
            top_k: 返回文档数量
            score_threshold: 相似度阈值
        """
        data = {
            "knowledge_base_name": kb_name,
            "query": query,
            "top_k": top_k,
            "score_threshold": score_threshold
        }

        try:
            # 直接调用API，不使用_make_request因为返回格式不同
            url = f"{self.base_url}/knowledge_base/search_docs"
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()

            # 搜索API直接返回文档列表，不是包装在data字段中
            result = response.json()

            if isinstance(result, list):
                logger.info(f"搜索到 {len(result)} 个相关文档")
                return result
            elif isinstance(result, dict) and 'data' in result:
                logger.info(f"搜索到 {len(result['data'])} 个相关文档")
                return result['data']
            else:
                logger.warning(f"搜索返回格式异常: {type(result)}")
                return []

        except Exception as e:
            logger.error(f"搜索文档失败: {query} in {kb_name} - {str(e)}")
            return []
    
    def knowledge_base_chat(self, kb_name: str, query: str, history: List = None,
                          model: str = "deepseek-r1", stream: bool = True,
                          top_k: int = 3, score_threshold: float = 0.5,
                          max_context_length: int = 4000) -> Dict:
        """知识库对话 - 真正的RAG实现：检索+LLM生成"""
        logger.info(f"RAG对话请求: {kb_name}, 查询: {query[:50]}..., 模型: {model}")
        logger.info(f"RAG参数: top_k={top_k}, score_threshold={score_threshold}, max_context_length={max_context_length}")

        # 保存参数供降级使用
        self._current_max_content_length = max_context_length
        self._current_query = query  # 保存查询供文档质量评分使用

        try:
            # 1. 检索相关文档
            logger.info(f"开始检索文档: {query}")
            search_results = self.search_docs(kb_name, query, top_k, score_threshold)
            logger.info(f"Chatchat返回 {len(search_results) if search_results else 0} 个文档")

            # 客户端限制文档数量（修复Chatchat的top_k问题）
            if search_results and len(search_results) > top_k:
                search_results = search_results[:top_k]
                logger.info(f"客户端限制后保留 {len(search_results)} 个文档")

            # 详细记录检索结果
            if search_results:
                for i, doc in enumerate(search_results[:2]):  # 只记录前2个文档
                    content_preview = str(doc)[:100] + "..." if len(str(doc)) > 100 else str(doc)
                    logger.info(f"文档{i+1}预览: {content_preview}")
            else:
                logger.warning(f"search_docs返回空结果: {search_results}")

            if not search_results:
                logger.warning(f"在知识库 {kb_name} 中未找到相关文档")
                # 使用LLM生成回答，说明没有找到相关信息
                return self._generate_no_context_response(query, kb_name, model, stream)

            # 2. 构建上下文
            context = self._build_context(search_results, max_context_length)
            logger.info(f"构建的上下文长度: {len(context)}")

            # 3. 构建RAG提示词
            rag_prompt = self._build_rag_prompt(query, context, kb_name)
            logger.info(f"RAG提示词长度: {len(rag_prompt)}")

            # 4. 调用LLM生成回答
            return self._generate_rag_response(rag_prompt, model, stream, search_results)

        except Exception as e:
            logger.error(f"RAG对话失败: {query} in {kb_name} - {str(e)}")
            raise

    def _calculate_document_quality(self, doc: Dict, query: str) -> float:
        """计算文档质量评分"""
        content = doc.get('page_content', '').strip()
        if not content:
            return 0.0

        quality_score = 0.0
        query_lower = query.lower()
        content_lower = content.lower()

        # 1. 定义性内容检查 (最重要)
        definition_patterns = ["就是", "是一种", "定义为", "指的是"]
        if any(pattern in content for pattern in definition_patterns):
            quality_score += 3.0
            logger.debug("文档包含定义性内容 +3.0")

        # 2. 核心概念检查
        if "单片机" in query_lower:
            if "集成" in content and ("cpu" in content_lower or "处理器" in content):
                quality_score += 2.0
                logger.debug("文档包含核心概念 +2.0")
            if any(word in content for word in ["特点", "优点", "应用", "功能"]):
                quality_score += 1.0
                logger.debug("文档包含特点描述 +1.0")

        # 3. 内容长度检查
        if len(content) >= 200:
            quality_score += 0.5
        elif len(content) < 100:
            quality_score -= 1.0
            logger.debug("文档内容过短 -1.0")

        # 4. 负面内容检查 (严重扣分)
        negative_keywords = ["题目", "参考文献", "附录", "练习", "习题", "答案", "第1章", "第2章"]
        negative_count = sum(1 for keyword in negative_keywords if keyword in content)
        if negative_count > 0:
            penalty = negative_count * 2.0
            quality_score -= penalty
            logger.debug(f"文档包含无关内容 -{penalty}")

        # 5. 相似度权重
        original_score = doc.get('score', 0.0)
        quality_score += original_score * 0.3  # 相似度占30%权重

        return max(0.0, quality_score)

    def _build_context(self, search_results: List[Dict], max_length: int = 4000) -> str:
        """构建上下文，智能截取和组织文档内容"""
        if not search_results:
            return ""

        # 1. 计算文档质量并重新排序
        query = getattr(self, '_current_query', '')
        scored_docs = []
        for doc in search_results:
            quality_score = self._calculate_document_quality(doc, query)
            scored_docs.append((doc, quality_score))

        # 按质量评分降序排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"文档质量排序: {[f'Doc{i+1}({score:.1f})' for i, (_, score) in enumerate(scored_docs)]}")

        # 过滤低质量文档
        quality_threshold = 1.0  # 质量阈值
        filtered_docs = [(doc, score) for doc, score in scored_docs if score >= quality_threshold]

        if not filtered_docs:
            # 如果所有文档都被过滤，降低阈值
            quality_threshold = 0.0
            filtered_docs = [(doc, score) for doc, score in scored_docs if score >= quality_threshold]
            logger.warning("所有文档质量评分过低，降低过滤阈值")

        logger.info(f"质量过滤后保留 {len(filtered_docs)}/{len(scored_docs)} 个文档")

        # 2. 构建上下文
        context_parts = []
        current_length = 0

        for i, (doc, quality_score) in enumerate(filtered_docs):
            if isinstance(doc, dict):
                content = doc.get('page_content', '').strip()
                metadata = doc.get('metadata', {})

                # 获取文档来源信息
                source = self._extract_source_info(doc, metadata)

                if content:  # 已经通过质量过滤
                    # 为每个文档添加来源标识
                    doc_content = f"【文档{i+1}】{source}\n{content}"

                    # 检查长度限制
                    if current_length + len(doc_content) > max_length:
                        # 如果超出限制，截取剩余空间
                        remaining_space = max_length - current_length - 50  # 留50字符余量
                        if remaining_space > 100:  # 至少要有100字符才有意义
                            doc_content = f"【文档{i+1}】{source}\n{content[:remaining_space]}..."
                            context_parts.append(doc_content)
                        break

                    context_parts.append(doc_content)
                    current_length += len(doc_content)

        return "\n\n".join(context_parts)

    def _build_structured_docs(self, search_results: List[Dict]) -> List[Dict]:
        """构建结构化的文档信息，用于前端展示"""
        structured_docs = []

        for i, doc in enumerate(search_results):
            if isinstance(doc, dict):
                content = doc.get('page_content', '').strip()
                metadata = doc.get('metadata', {})
                score = doc.get('score', 0.0)

                if content:
                    # 提取文档信息
                    source = self._extract_source_info(doc, metadata)

                    # 智能截取内容预览
                    preview_length = 200
                    if len(content) > preview_length:
                        # 寻找合适的截取点
                        truncate_pos = preview_length
                        for pos in range(preview_length - 50, min(preview_length + 50, len(content))):
                            if content[pos] in '。！？\n；':
                                truncate_pos = pos + 1
                                break
                        content_preview = content[:truncate_pos]
                        if truncate_pos < len(content):
                            content_preview += "..."
                    else:
                        content_preview = content

                    # 构建结构化信息
                    doc_info = {
                        "id": i + 1,
                        "title": f"文档 {i + 1}",
                        "source": source,
                        "score": round(score, 2),
                        "content": content,  # 完整内容
                        "preview": content_preview,  # 预览内容
                        "length": len(content),
                        "metadata": metadata
                    }

                    structured_docs.append(doc_info)

        return structured_docs

    def _extract_source_info(self, doc: Dict, metadata: Dict) -> str:
        """提取文档来源信息"""
        # 尝试从多个字段获取文件名
        possible_fields = ['source', 'file_name', 'filename', 'document_name']

        # 首先从顶级字段查找
        for field in possible_fields:
            if field in doc and doc[field]:
                return doc[field]  # 不添加"来源: "前缀，在前端添加

        # 从metadata中查找
        if isinstance(metadata, dict):
            for field in possible_fields:
                if field in metadata and metadata[field]:
                    return metadata[field]  # 不添加"来源: "前缀

        return "知识库文档"

    def _build_rag_prompt(self, query: str, context: str, kb_name: str) -> str:
        """构建RAG提示词 - 优化版本，减少处理时间"""
        # 简化提示词，减少LLM处理时间
        prompt = f"""基于以下文档回答问题：

问题：{query}

文档：
{context}

要求：基于文档内容简洁回答，语言自然流畅。

回答："""

        return prompt

    def _generate_rag_response(self, prompt: str, model: str, stream: bool, search_results: List[Dict]):
        """使用LLM生成RAG回答"""
        try:
            # 直接调用LLM API，避免循环导入
            logger.info("尝试调用LLM API...")
            logger.info(f"提示词长度: {len(prompt)} 字符")
            logger.info(f"提示词预览: {prompt[:200]}...")

            llm_response = self._call_llm_api(prompt, model, stream)
            logger.info("LLM API调用成功")
            logger.info(f"LLM响应类型: {type(llm_response)}")

            if stream:
                return self._handle_rag_stream_response(llm_response, search_results)
            else:
                # 处理非流式响应
                if isinstance(llm_response, dict):
                    # 尝试从不同字段获取内容
                    content = ""
                    logger.info(f"LLM响应结构: {list(llm_response.keys())}")

                    if 'choices' in llm_response and llm_response['choices']:
                        choice = llm_response['choices'][0]
                        logger.info(f"Choice结构: {list(choice.keys())}")

                        if 'message' in choice and 'content' in choice['message']:
                            raw_content = choice['message']['content']
                            logger.info(f"从message.content获取原始内容，长度: {len(raw_content)}")

                            # 处理包含<think>标签的内容
                            content = self._extract_actual_answer(raw_content)
                            logger.info(f"提取实际回答后，长度: {len(content)}")

                        elif 'text' in choice:
                            raw_content = choice['text']
                            content = self._extract_actual_answer(raw_content)
                            logger.info(f"从choice.text获取并处理内容，长度: {len(content)}")
                    elif 'content' in llm_response:
                        raw_content = llm_response['content']
                        content = self._extract_actual_answer(raw_content)
                        logger.info(f"从顶级content获取并处理内容，长度: {len(content)}")
                    elif 'text' in llm_response:
                        raw_content = llm_response['text']
                        content = self._extract_actual_answer(raw_content)
                        logger.info(f"从顶级text获取并处理内容，长度: {len(content)}")

                    if content.strip():
                        logger.info("✅ 成功提取LLM生成的回答")

                        # 构建结构化的文档信息
                        structured_docs = self._build_structured_docs(search_results)

                        return {
                            "answer": content.strip(),
                            "docs": search_results,  # 保持原有格式兼容性
                            "structured_docs": structured_docs,  # 新增结构化文档信息
                            "type": "rag"
                        }
                    else:
                        logger.warning("LLM返回空内容，使用降级模式")
                        return self._fallback_to_simple_response(search_results, False, getattr(self, '_current_max_content_length', 800))
                else:
                    logger.warning(f"未知的LLM响应格式: {type(llm_response)}")
                    return self._fallback_to_simple_response(search_results, stream, getattr(self, '_current_max_content_length', 800))

        except Exception as e:
            logger.error(f"LLM生成失败: {str(e)}")
            # 降级到简单回答
            return self._fallback_to_simple_response(search_results, stream, getattr(self, '_current_max_content_length', 800))

    def _extract_actual_answer(self, raw_content: str) -> str:
        """从LLM响应中提取实际回答，去掉思考过程"""
        if not raw_content:
            return ""

        # 如果包含<think>标签，提取</think>之后的内容
        if '<think>' in raw_content and '</think>' in raw_content:
            # 找到</think>标签的位置
            think_end = raw_content.find('</think>')
            if think_end != -1:
                # 提取</think>之后的内容
                actual_answer = raw_content[think_end + 8:].strip()  # 8是</think>的长度
                logger.info("检测到思考过程，已提取实际回答部分")
                return actual_answer

        # 如果没有思考标签，直接返回原内容
        return raw_content.strip()

    def _check_llm_health(self) -> bool:
        """检查LLM服务健康状态"""
        try:
            # 先尝试docs端点（已知可用）
            url = "http://127.0.0.1:7861/docs"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info("LLM服务健康检查通过（docs端点）")
                return True

            # 如果docs失败，尝试models端点
            url = "http://127.0.0.1:7861/v1/models"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.info("LLM服务健康检查通过（models端点）")
                return True

            logger.warning(f"LLM健康检查失败，状态码: {response.status_code}")
            return False
        except Exception as e:
            logger.warning(f"LLM健康检查异常: {str(e)}")
            return False

    def _call_llm_api(self, prompt: str, model: str, stream: bool = True):
        """直接调用LLM API"""
        # 使用正确的LLM API端点 - 基于测试结果
        url = "http://127.0.0.1:7861/v1/chat/completions"
        logger.info(f"使用LLM端点: {url}")

        # 检查LLM服务健康状态
        logger.info("开始LLM服务健康检查...")
        health_check_result = self._check_llm_health()
        logger.info(f"LLM健康检查结果: {health_check_result}")

        if not health_check_result:
            logger.warning("LLM服务健康检查失败，可能服务未启动或配置错误")
            raise Exception("LLM服务不可用")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "temperature": 0.3,  # 降低温度，减少随机性，提高速度
            "max_tokens": 1000,  # 限制最大token数，避免过长回答
            "top_p": 0.8,       # 限制采样范围
        }

        try:
            # 基于实际测试结果调整超时时间
            # 简单查询约20秒，复杂RAG查询需要60-120秒
            timeout = 200 if not stream else 240  # 非流式200秒，流式240秒
            logger.info(f"调用LLM API: {url}, 超时: {timeout}秒")

            response = requests.post(url, json=payload, stream=stream, timeout=timeout)
            response.raise_for_status()

            if stream:
                return response  # 返回响应对象用于流式处理
            else:
                return response.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"LLM API超时: {str(e)}")
            raise Exception("LLM服务超时，请检查服务状态")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"LLM API连接失败: {str(e)}")
            raise Exception("无法连接到LLM服务")
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            raise

    def _handle_rag_stream_response(self, llm_response, search_results: List[Dict]):
        """处理RAG流式响应"""
        def rag_stream_generator():
            try:
                # 首先返回文档信息
                yield {"docs": search_results, "type": "docs"}

                # 然后流式返回LLM生成的内容
                for line in llm_response.iter_lines(decode_unicode=True):
                    if line and line.strip():
                        # 解析OpenAI格式的流式响应
                        if line.startswith('data: '):
                            try:
                                json_str = line[6:].strip()
                                if json_str and json_str != '[DONE]':
                                    data = json.loads(json_str)
                                    if 'choices' in data and data['choices']:
                                        choice = data['choices'][0]
                                        if 'delta' in choice and 'content' in choice['delta']:
                                            content = choice['delta']['content']
                                            if content:
                                                yield {"answer": content, "type": "content"}
                                        elif 'finish_reason' in choice and choice['finish_reason']:
                                            yield {"type": "done"}
                                            return
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.warning(f"解析流式响应失败: {e}")
                                continue

                # 确保发送完成信号
                yield {"type": "done"}

            except Exception as e:
                logger.error(f"RAG流式响应处理失败: {str(e)}")
                yield {"error": str(e), "type": "error"}

        return rag_stream_generator()

    def _generate_no_context_response(self, query: str, kb_name: str, model: str, stream: bool):
        """当没有找到相关文档时的响应"""
        no_context_prompt = f"""用户在知识库"{kb_name}"中询问：{query}

但是没有找到相关的文档内容。请礼貌地告知用户没有找到相关信息，并建议他们：
1. 尝试使用不同的关键词重新搜索
2. 检查问题的表述是否准确
3. 或者联系管理员确认知识库内容

请用友好、专业的语气回复。"""

        try:
            llm_response = self._call_llm_api(no_context_prompt, model, stream)

            if stream:
                def no_context_stream():
                    for line in llm_response.iter_lines(decode_unicode=True):
                        if line and line.strip():
                            if line.startswith('data: '):
                                try:
                                    json_str = line[6:].strip()
                                    if json_str and json_str != '[DONE]':
                                        data = json.loads(json_str)
                                        if 'choices' in data and data['choices']:
                                            choice = data['choices'][0]
                                            if 'delta' in choice and 'content' in choice['delta']:
                                                content = choice['delta']['content']
                                                if content:
                                                    yield {"answer": content, "type": "content"}
                                            elif 'finish_reason' in choice and choice['finish_reason']:
                                                yield {"type": "done"}
                                                return
                                except (json.JSONDecodeError, KeyError):
                                    continue
                    yield {"type": "done"}
                return no_context_stream()
            else:
                response_data = llm_response
                return {"answer": response_data.get("content", f"抱歉，在知识库 {kb_name} 中没有找到关于 '{query}' 的相关信息。"), "type": "no_context"}
        except Exception as e:
            logger.error(f"生成无上下文响应失败: {str(e)}")
            # 返回简单的静态回答
            simple_message = f"抱歉，在知识库 {kb_name} 中没有找到关于 '{query}' 的相关信息。请尝试使用不同的关键词重新搜索。"
            if stream:
                def simple_stream():
                    for char in simple_message:
                        yield {"answer": char, "type": "content"}
                    yield {"type": "done"}
                return simple_stream()
            else:
                return {"answer": simple_message, "type": "simple"}

    def _fallback_to_simple_response(self, search_results: List[Dict], stream: bool, max_content_length: int = 800):
        """降级到简单的文档拼接响应"""
        logger.info("使用降级模式：智能文档拼接")

        # 构建更智能的回答
        answer_parts = []
        # 使用所有检索到的文档（已经在上层按top_k限制了）
        actual_docs = search_results
        answer_parts.append(f"根据知识库检索，为您找到以下 {len(actual_docs)} 个相关信息：\n")

        for i, doc in enumerate(actual_docs, 1):
            content = ""
            source = "知识库文档"

            if isinstance(doc, dict):
                content = doc.get('page_content', '')
                # 获取文档来源
                metadata = doc.get('metadata', {})
                if isinstance(metadata, dict) and 'source' in metadata:
                    source = metadata['source']
            elif isinstance(doc, str):
                content = doc

            if content:
                # 智能截取：使用用户设置的内容长度限制
                # 如果max_content_length为0，表示不限制长度
                if max_content_length > 0 and len(content) > max_content_length:
                    # 找到合适位置的句号、换行符或其他标点
                    truncate_pos = max_content_length
                    # 在截取位置前后寻找合适的断点
                    search_start = max(0, max_content_length - 100)
                    search_end = min(len(content), max_content_length + 50)
                    for pos in range(search_start, search_end):
                        if content[pos] in '。！？\n；':
                            truncate_pos = pos + 1
                            break
                    summary = content[:truncate_pos]
                    if truncate_pos < len(content):
                        summary += "..."
                else:
                    summary = content

                # 格式化输出
                answer_parts.append(f"**文档 {i}** (来源: {source})")
                answer_parts.append(summary.strip())
                answer_parts.append("")  # 空行分隔

        # 添加总结
        answer_parts.append("💡 **说明**: 以上内容来自知识库文档检索结果。由于AI生成服务暂时不可用，为您提供了相关文档的直接内容。")

        final_answer = "\n".join(answer_parts)

        # 构建结构化的文档信息
        structured_docs = self._build_structured_docs(search_results)

        if stream:
            def fallback_stream():
                # 先发送文档信息
                yield {"docs": search_results, "structured_docs": structured_docs, "type": "docs"}
                # 然后逐字符发送内容
                for char in final_answer:
                    yield {"answer": char, "type": "content"}
                yield {"type": "done"}
            return fallback_stream()
        else:
            return {
                "answer": final_answer,
                "docs": search_results,  # 保持原有格式兼容性
                "structured_docs": structured_docs,  # 新增结构化文档信息
                "type": "fallback"
            }

    def delete_file(self, kb_name: str, file_name: str) -> bool:
        """删除知识库中的文件"""
        data = {
            "knowledge_base_name": kb_name,
            "file_names": [file_name]  # 注意：使用file_names数组
        }

        try:
            logger.info(f"删除文件: {file_name} from {kb_name}")

            # 调用Chatchat的删除文件API
            url = f"{self.base_url}/knowledge_base/delete_docs"
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            logger.info(f"删除文件响应: {result}")

            # 检查删除是否成功
            if isinstance(result, dict):
                # 如果返回的是字典格式
                if result.get('code') == 200 or result.get('success', False):
                    logger.info(f"文件 {file_name} 删除成功")

                    # 检查是否有失败的文件
                    failed_files = result.get('data', {}).get('failed_files', {})
                    if failed_files:
                        logger.warning(f"部分文件删除失败: {failed_files}")
                        return False

                    return True
                else:
                    logger.error(f"删除文件失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                # 如果返回其他格式，根据HTTP状态码判断
                logger.info(f"文件 {file_name} 删除成功")
                return True

        except Exception as e:
            logger.error(f"删除文件失败: {file_name} from {kb_name} - {str(e)}")
            return False
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        def stream_generator():
            try:
                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            yield data
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"流式响应处理异常: {str(e)}")
                yield {"error": str(e)}
        
        return stream_generator()
    
    def get_kb_summary(self, kb_name: str) -> Dict:
        """获取知识库摘要信息"""
        try:
            files = self.list_files(kb_name)
            return {
                "kb_name": kb_name,
                "name": kb_name,  # 保持向后兼容
                "file_count": len(files),
                "files": files[:10],  # 只返回前10个文件名
                "total_files": len(files)
            }
        except Exception as e:
            logger.error(f"获取知识库摘要失败: {kb_name} - {str(e)}")
            return {"kb_name": kb_name, "name": kb_name, "file_count": 0, "files": [], "total_files": 0, "error": str(e)}


# 全局实例
kb_service = KnowledgeBaseService()
