"""
知识库管理视图
"""

import json
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .kb_service import kb_service

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def list_knowledge_bases_api(request):
    """获取知识库列表API"""
    try:
        kb_list = kb_service.list_knowledge_bases()
        logger.info(f"获取到知识库列表: {kb_list}")

        # 获取每个知识库的详细信息
        detailed_list = []
        for kb_name in kb_list:
            try:
                summary = kb_service.get_kb_summary(kb_name)
                logger.info(f"知识库 {kb_name} 摘要: {summary}")
                detailed_list.append(summary)
            except Exception as e:
                logger.error(f"获取知识库 {kb_name} 摘要失败: {str(e)}")
                # 添加基本信息，即使获取详细信息失败
                detailed_list.append({
                    "name": kb_name,
                    "file_count": 0,
                    "files": [],
                    "total_files": 0,
                    "error": str(e)
                })

        return JsonResponse({
            'success': True,
            'knowledge_bases': detailed_list
        })
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取知识库列表失败: {str(e)}',
            'knowledge_bases': []
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def create_knowledge_base_api(request):
    """创建知识库API"""
    try:
        data = json.loads(request.body)
        kb_name = data.get('name', '').strip()
        vector_store = data.get('vector_store', 'faiss')
        embed_model = data.get('embed_model', 'bge-m3')
        
        if not kb_name:
            return JsonResponse({
                'success': False,
                'message': '知识库名称不能为空'
            })
        
        result = kb_service.create_knowledge_base(kb_name, vector_store, embed_model)
        
        return JsonResponse({
            'success': True,
            'message': f'知识库 "{kb_name}" 创建成功',
            'data': result
        })
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'创建知识库失败: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_knowledge_base_api(request):
    """删除知识库API"""
    try:
        data = json.loads(request.body)
        kb_name = data.get('name', '').strip()
        
        if not kb_name:
            return JsonResponse({
                'success': False,
                'message': '知识库名称不能为空'
            })
        
        result = kb_service.delete_knowledge_base(kb_name)
        
        return JsonResponse({
            'success': True,
            'message': f'知识库 "{kb_name}" 删除成功',
            'data': result
        })
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'删除知识库失败: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["GET"])
def list_files_api(request):
    """获取知识库文件列表API"""
    try:
        kb_name = request.GET.get('kb_name', '').strip()
        
        if not kb_name:
            return JsonResponse({
                'success': False,
                'message': '知识库名称不能为空'
            })
        
        files = kb_service.list_files(kb_name)
        
        return JsonResponse({
            'success': True,
            'data': files
        })
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取文件列表失败: {str(e)}',
            'data': []
        })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def upload_file_api(request):
    """上传文件到知识库API"""
    try:
        kb_name = request.POST.get('kb_name', '').strip()
        override = request.POST.get('override', 'false').lower() == 'true'
        
        if not kb_name:
            return JsonResponse({
                'success': False,
                'message': '知识库名称不能为空'
            })
        
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': '请选择要上传的文件'
            })
        
        uploaded_file = request.FILES['file']
        file_content = uploaded_file.read()
        
        result = kb_service.upload_file(kb_name, uploaded_file.name, file_content, override)

        return JsonResponse({
            'success': True,
            'message': f'文件 "{uploaded_file.name}" 上传成功',
            'data': result
        })
    except Exception as e:
        error_msg = str(e)
        logger.error(f"上传文件失败: {error_msg}")

        # 根据错误类型提供更友好的错误信息
        if "timeout" in error_msg.lower() or "超时" in error_msg:
            return JsonResponse({
                'success': False,
                'message': f'文档上传超时，文件可能较大，向量化处理需要更多时间。请尝试上传较小的文件或稍后重试。'
            })
        elif "connection" in error_msg.lower() or "连接" in error_msg:
            return JsonResponse({
                'success': False,
                'message': f'无法连接到知识库服务器，请确保Chatchat服务正在运行。'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'上传文件失败: {error_msg}'
            })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_file_api(request):
    """删除知识库文件API"""
    try:
        data = json.loads(request.body)
        kb_name = data.get('kb_name', '').strip()
        file_name = data.get('file_name', '').strip()
        
        if not kb_name or not file_name:
            return JsonResponse({
                'success': False,
                'message': '知识库名称和文件名不能为空'
            })
        
        result = kb_service.delete_file(kb_name, file_name)
        
        return JsonResponse({
            'success': True,
            'message': f'文件 "{file_name}" 删除成功',
            'data': result
        })
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'删除文件失败: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["GET", "POST"])
def search_docs_api(request):
    """搜索知识库文档API"""
    try:
        if request.method == "GET":
            # 支持GET请求，从查询参数获取数据
            data = {
                'kb_name': request.GET.get('kb_name', ''),
                'query': request.GET.get('query', ''),
                'top_k': int(request.GET.get('top_k', 3)),
                'score_threshold': float(request.GET.get('score_threshold', 0.5))
            }
        else:
            # POST请求，从body获取数据
            data = json.loads(request.body)
        kb_name = data.get('kb_name', '').strip()
        query = data.get('query', '').strip()
        top_k = data.get('top_k', 3)  # 默认返回3个文档
        score_threshold = data.get('score_threshold', 0.5)
        max_content_length = data.get('max_content_length', 0)  # 默认不限制长度

        if not kb_name or not query:
            return JsonResponse({
                'success': False,
                'message': '知识库名称和查询内容不能为空'
            })

        results = kb_service.search_docs(kb_name, query, top_k, score_threshold)

        # 处理搜索结果，添加格式化信息
        formatted_results = []
        valid_results = []

        # 首先收集所有有效的结果，确保不超过top_k个
        for result in results:
            if isinstance(result, dict) and 'page_content' in result and result.get('page_content', '').strip():
                valid_results.append(result)
                # 如果已经达到了top_k个文档，就停止添加
                if len(valid_results) >= top_k:
                    break

        # 然后按照连续编号处理这些结果
        for i, result in enumerate(valid_results, 1):
            # 复制原始结果
            formatted_result = result.copy()

            # 获取文件名信息
            metadata = result.get('metadata', {})
            filename = None

            # 尝试获取文件名
            possible_filename_fields = ['source', 'file_name', 'filename', 'document_name']
            for field in possible_filename_fields:
                if field in result and result[field]:
                    filename = result[field]
                    break
                elif isinstance(metadata, dict) and field in metadata and metadata[field]:
                    filename = metadata[field]
                    break

            if filename:
                import os
                filename = os.path.basename(str(filename))
            else:
                filename = "未知文档"

            # 添加格式化的出处信息，确保出处后有空格
            formatted_result['source_info'] = f"出处 [{i}] {filename}"
            formatted_result['source_index'] = i  # 添加索引以便前端排序

            # 处理内容长度限制
            if max_content_length > 0 and 'page_content' in formatted_result:
                content = formatted_result['page_content']
                if len(content) > max_content_length:
                    formatted_result['page_content'] = content[:max_content_length] + "..."
                    formatted_result['content_truncated'] = True
                else:
                    formatted_result['content_truncated'] = False
            else:
                formatted_result['content_truncated'] = False

            formatted_results.append(formatted_result)

        return JsonResponse({
            'success': True,
            'data': formatted_results
        })
    except Exception as e:
        logger.error(f"搜索文档失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'搜索文档失败: {str(e)}',
            'data': []
        })


@csrf_exempt
@require_http_methods(["GET"])
def knowledge_base_chat_api(request):
    """知识库对话API - 使用RAG生成"""
    try:
        kb_name = request.GET.get('kb_name', '').strip()
        query = request.GET.get('query', '').strip()
        model = request.GET.get('model', 'deepseek-r1')

        # 获取高级设置参数
        max_content_length = int(request.GET.get('max_content_length', 4000))  # 上下文最大长度
        top_k = int(request.GET.get('top_k', 3))  # 默认返回3个文档
        score_threshold = float(request.GET.get('score_threshold', 0.5))

        logger.info(f"RAG对话请求: kb_name={kb_name}, query={query}, model={model}")
        logger.info(f"RAG参数: max_context_length={max_content_length}, top_k={top_k}, score_threshold={score_threshold}")

        if not kb_name or not query:
            return JsonResponse({
                'success': False,
                'message': '知识库名称和查询内容不能为空'
            })

        # 使用新的RAG功能
        try:
            logger.info(f"开始调用RAG功能...")
            rag_response = kb_service.knowledge_base_chat(
                kb_name=kb_name,
                query=query,
                model=model,
                stream=False,  # API接口使用非流式响应
                top_k=top_k,
                score_threshold=score_threshold,
                max_context_length=max_content_length
            )

            logger.info(f"RAG响应类型: {type(rag_response)}")
            logger.info(f"RAG响应内容: {str(rag_response)[:200]}...")

            # 处理RAG响应
            if isinstance(rag_response, dict):
                answer = rag_response.get('answer', '')
                docs_count = len(rag_response.get('docs', []))
                structured_docs = rag_response.get('structured_docs', [])

                logger.info(f"RAG字典响应 - 回答长度: {len(answer)}, 文档数量: {docs_count}, 结构化文档: {len(structured_docs)}")

                return JsonResponse({
                    'success': True,
                    'answer': answer,
                    'docs_count': docs_count,
                    'structured_docs': structured_docs,  # 添加结构化文档信息
                    'type': 'rag'
                })
            else:
                # 如果是生成器，收集所有内容
                logger.info("RAG返回生成器，开始收集内容...")
                answer_parts = []
                docs_count = 0

                for chunk in rag_response:
                    logger.info(f"处理chunk: {chunk}")
                    if isinstance(chunk, dict):
                        if chunk.get('type') == 'docs':
                            docs_count = len(chunk.get('docs', []))
                            logger.info(f"找到文档数量: {docs_count}")
                        elif chunk.get('type') == 'content' and 'answer' in chunk:
                            answer_parts.append(chunk['answer'])
                        elif chunk.get('type') == 'done':
                            logger.info("RAG生成完成")
                            break

                final_answer = ''.join(answer_parts)
                logger.info(f"最终回答长度: {len(final_answer)}")

                return JsonResponse({
                    'success': True,
                    'answer': final_answer,
                    'docs_count': docs_count,
                    'type': 'rag'
                })

        except Exception as e:
            logger.error(f"RAG对话失败: {str(e)}")
            # 降级到简单搜索模式
            try:
                search_results = kb_service.search_docs(kb_name, query, top_k, score_threshold)
                if search_results:
                    # 构建简单的文档拼接回答
                    answer_parts = ["基于知识库搜索，找到以下相关信息：\n"]

                    for i, doc in enumerate(search_results[:top_k], 1):
                        content = ""
                        if isinstance(doc, dict):
                            content = doc.get('page_content', '')
                        elif isinstance(doc, str):
                            content = doc

                        if content:
                            summary = content[:300] + "..." if len(content) > 300 else content
                            answer_parts.append(f"{i}. {summary}")

                    answer_parts.append("\n以上信息来自知识库中的相关文档。")
                    fallback_answer = "\n\n".join(answer_parts)

                    return JsonResponse({
                        'success': True,
                        'answer': fallback_answer,
                        'docs_count': len(search_results),
                        'type': 'fallback'
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'answer': f'在知识库 {kb_name} 中未找到关于 "{query}" 的相关信息',
                        'docs_count': 0,
                        'type': 'no_results'
                    })
            except Exception as fallback_error:
                logger.error(f"降级搜索也失败: {str(fallback_error)}")
                return JsonResponse({
                    'success': False,
                    'message': f'对话失败: {str(e)}'
                })

    except Exception as e:
        logger.error(f"知识库对话失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'知识库对话失败: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["GET"])
def knowledge_base_chat_stream_api(request):
    """知识库对话流式API - 使用RAG生成"""
    try:
        kb_name = request.GET.get('kb_name', '').strip()
        query = request.GET.get('query', '').strip()
        model = request.GET.get('model', 'deepseek-r1')

        # 获取高级设置参数
        max_content_length = int(request.GET.get('max_content_length', 4000))
        top_k = int(request.GET.get('top_k', 3))
        score_threshold = float(request.GET.get('score_threshold', 0.5))

        logger.info(f"RAG流式对话请求: kb_name={kb_name}, query={query}, model={model}")

        if not kb_name or not query:
            def error_stream():
                import json
                error_msg = '知识库名称和查询内容不能为空'
                yield f'data: {json.dumps({"error": error_msg})}\n\n'

            return StreamingHttpResponse(error_stream(), content_type='text/event-stream')

        # 使用RAG流式响应
        def rag_stream():
            import json
            try:
                rag_response = kb_service.knowledge_base_chat(
                    kb_name=kb_name,
                    query=query,
                    model=model,
                    stream=True,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    max_context_length=max_content_length
                )

                for chunk in rag_response:
                    if isinstance(chunk, dict):
                        if chunk.get("type") == "docs":
                            # 可以选择是否发送文档信息给前端
                            docs_info = {
                                "type": "docs_info",
                                "count": len(chunk.get('docs', []))
                            }
                            yield f'data: {json.dumps(docs_info)}\n\n'
                        elif chunk.get("type") == "content" and "answer" in chunk:
                            # 发送内容块
                            content_data = {
                                "answer": chunk["answer"],
                                "type": "content"
                            }
                            yield f'data: {json.dumps(content_data)}\n\n'
                        elif chunk.get("type") == "done":
                            # 发送完成信号
                            yield f'data: {json.dumps({"type": "done"})}\n\n'
                            break
                        elif chunk.get("type") == "error":
                            # 发送错误信息
                            error_data = {
                                "error": chunk.get("error", "未知错误"),
                                "type": "error"
                            }
                            yield f'data: {json.dumps(error_data)}\n\n'
                            break

            except Exception as e:
                logger.error(f"RAG流式响应失败: {str(e)}")
                error_data = {
                    "error": f"生成失败: {str(e)}",
                    "type": "error"
                }
                yield f'data: {json.dumps(error_data)}\n\n'

        return StreamingHttpResponse(rag_stream(), content_type='text/event-stream')

    except Exception as e:
        logger.error(f"RAG流式API异常: {str(e)}")
        def error_stream():
            import json
            error_data = {
                "error": f"系统异常: {str(e)}",
                "type": "error"
            }
            yield f'data: {json.dumps(error_data)}\n\n'

        return StreamingHttpResponse(error_stream(), content_type='text/event-stream')


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def delete_file_api(request):
    """删除知识库文件API"""
    try:
        if request.method == 'DELETE':
            # 从URL参数获取
            kb_name = request.GET.get('kb_name', '').strip()
            file_name = request.GET.get('file_name', '').strip()
        else:  # POST
            # 从请求体获取
            data = json.loads(request.body)
            kb_name = data.get('kb_name', '').strip()
            file_name = data.get('file_name', '').strip()

        logger.info(f"删除文件请求: kb_name={kb_name}, file_name={file_name}")

        if not kb_name or not file_name:
            return JsonResponse({
                'success': False,
                'message': '知识库名称和文件名不能为空'
            })

        # 调用知识库服务删除文件
        success = kb_service.delete_file(kb_name, file_name)

        if success:
            return JsonResponse({
                'success': True,
                'message': f'文件 "{file_name}" 删除成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'文件 "{file_name}" 删除失败'
            })

    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'删除文件失败: {str(e)}'
        })
