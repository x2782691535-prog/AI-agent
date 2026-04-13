import logging
import requests
import json
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class LCCService:
    def __init__(self, base_url=None, model=None):
        self.base_url = base_url or settings.LCC_API_BASE_URL
        self.model = model or settings.LCC_DEFAULT_MODEL
        logger.info(f"初始化LCCService，使用模型: {self.model}")

    def _handle_response(self, response, stream):
        """处理API响应"""
        if response.status_code != 200:
            error_msg = f"API错误: {response.status_code}"
            try:
                error_json = response.json()
                if 'error' in error_json:
                    error_msg += f" - {error_json['error']}"
            except:
                if response.text:
                    error_msg += f" - {response.text[:200]}"
            
            logger.error(f"API请求失败: {response.status_code}, {response.text[:500]}")
            raise Exception(error_msg)

        if stream:
            # 流式响应处理
            try:
                logger.info("开始处理流式响应")
                chunk_count = 0
                for chunk in response.iter_lines(decode_unicode=True):
                    if chunk:  # 过滤空块
                        chunk_count += 1
                        logger.info(f"LCCService收到第{chunk_count}个chunk: {chunk[:200]}...")
                        yield chunk
                logger.info(f"LCCService流式响应完成，共{chunk_count}个chunks")
            except Exception as e:
                logger.error(f"流式响应中断: {str(e)}")
                raise
        else:
            # 非流式响应处理
            return response.json()

    def llm_conversation(self, question, temperature=0.7, stream=True):
        """纯LLM对话"""
        logger.info(f"LLM对话请求: {question[:50]}... 使用模型: {self.model}")
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": question}],
            "stream": stream,
            "temperature": temperature,
        }
        try:
            response = requests.post(url, json=payload, stream=stream)
            return self._handle_response(response, stream)
        except Exception as e:
            logger.exception(f"LLM对话请求异常: {str(e)}")
            raise

    def kb_conversation_auto(self, question, stream=True):
        """知识库对话（自动选择数据库）- 使用RAG"""
        logger.info(f"RAG对话(自动)请求: {question[:50]}... 使用模型: {self.model}")

        # 使用集成的知识库服务
        from .kb_service import kb_service

        try:
            # 获取可用的知识库列表
            kb_list = kb_service.list_knowledge_bases()
            if not kb_list:
                logger.warning("没有可用的知识库，降级到LLM对话")
                return self.llm_conversation(question, stream=stream)

            # 使用第一个知识库进行RAG对话
            kb_name = kb_list[0]
            logger.info(f"使用知识库进行RAG对话: {kb_name}")

            # 调用真正的RAG功能
            rag_response = kb_service.knowledge_base_chat(
                kb_name=kb_name,
                query=question,
                model=self.model,
                stream=stream,
                top_k=3,
                score_threshold=0.5
            )

            # 转换RAG响应格式为前端期望的格式
            return self._convert_rag_response_to_sse(rag_response, stream)

        except Exception as e:
            logger.error(f"RAG对话失败，降级到LLM对话: {str(e)}")
            return self.llm_conversation(question, stream=stream)

    def kb_conversation_manual(self, question, kb_name=None, stream=True):
        """知识库对话（指定知识库）- 使用RAG"""
        logger.info(f"RAG对话(指定)请求: {question[:50]}... 知识库: {kb_name}, 模型: {self.model}")

        # 使用集成的知识库服务
        from .kb_service import kb_service

        try:
            if not kb_name:
                # 如果没有指定知识库，获取第一个可用的
                kb_list = kb_service.list_knowledge_bases()
                if not kb_list:
                    logger.warning("没有可用的知识库，降级到LLM对话")
                    return self.llm_conversation(question, stream=stream)
                kb_name = kb_list[0]

            logger.info(f"使用指定知识库进行RAG对话: {kb_name}")

            # 调用真正的RAG功能
            rag_response = kb_service.knowledge_base_chat(
                kb_name=kb_name,
                query=question,
                model=self.model,
                stream=stream,
                top_k=3,
                score_threshold=0.5
            )

            # 转换RAG响应格式为前端期望的格式
            return self._convert_rag_response_to_sse(rag_response, stream)

        except Exception as e:
            logger.error(f"RAG对话失败，降级到LLM对话: {str(e)}")
            return self.llm_conversation(question, stream=stream)

    def _convert_rag_response_to_sse(self, rag_response, stream=True):
        """将RAG响应转换为SSE格式"""
        if not stream:
            # 非流式响应直接返回
            return rag_response

        def sse_converter():
            import json
            try:
                for chunk in rag_response:
                    if isinstance(chunk, dict):
                        if chunk.get("type") == "docs":
                            # 文档信息，可以选择是否传递给前端
                            logger.info(f"RAG检索到 {len(chunk.get('docs', []))} 个文档")
                            continue
                        elif chunk.get("type") == "content" and "answer" in chunk:
                            # 内容块
                            content = chunk["answer"]
                            yield f'data: {json.dumps({"content": content})}\n\n'
                        elif chunk.get("type") == "done":
                            # 完成信号
                            yield f'data: {json.dumps({"type": "done"})}\n\n'
                            break
                        elif chunk.get("type") == "error":
                            # 错误信息
                            error_msg = chunk.get("error", "未知错误")
                            yield f'data: {json.dumps({"error": error_msg})}\n\n'
                            break
            except Exception as e:
                logger.error(f"RAG响应转换失败: {str(e)}")
                yield f'data: {json.dumps({"error": "响应处理失败"})}\n\n'

        return sse_converter()

    def get_available_models(self):
        """获取可用模型列表"""
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取模型列表失败: {response.status_code}")
                return []
        except Exception as e:
            logger.exception(f"获取模型列表异常: {str(e)}")
            return []

    @staticmethod
    def get_ollama_models():
        """获取ollama中已下载的模型列表"""
        cache_key = "ollama_models"
        cached_models = cache.get(cache_key)

        if cached_models:
            return cached_models

        try:
            # 调用ollama API获取模型列表
            ollama_url = "http://127.0.0.1:11434/api/tags"
            response = requests.get(ollama_url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                models = []

                for model in data.get('models', []):
                    model_name = model.get('name', '')
                    model_size = model.get('size', 0)
                    modified_at = model.get('modified_at', '')

                    # 格式化模型信息
                    size_gb = round(model_size / (1024**3), 1) if model_size > 0 else 0

                    models.append({
                        'name': model_name,
                        'display_name': model_name.replace(':latest', ''),
                        'size': size_gb,
                        'modified_at': modified_at,
                        'full_name': model_name
                    })

                # 按名称排序
                models.sort(key=lambda x: x['display_name'])

                # 缓存5分钟
                cache.set(cache_key, models, 300)

                logger.info(f"获取到{len(models)}个ollama模型")
                return models
            else:
                logger.error(f"获取ollama模型失败: HTTP {response.status_code}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"连接ollama失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"获取ollama模型异常: {str(e)}")
            return []
            
    def get_available_databases(self):
        """获取可用知识库列表"""
        try:
            url = f"{self.base_url}/knowledge_base/list"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取知识库列表失败: {response.status_code}")
                return []
        except Exception as e:
            logger.exception(f"获取知识库列表异常: {str(e)}")
            return []