import time
import re
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .services import LCCService, logger
from django.views.decorators.http import require_http_methods
from .super_chat_service import super_chat_service
import json

CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fa5\uff00-\uffef\u3000-\u303f]')

class ContentFilter:
    """内容过滤器，用于清理和格式化AI响应内容"""

    def __init__(self):
        # 思考标签模式
        self.think_pattern = re.compile(r'<think>.*?</think>', re.DOTALL | re.IGNORECASE)
        # 系统提示词泄露模式
        self.system_patterns = [
            re.compile(r'(?:system|assistant|user):\s*', re.IGNORECASE),
            re.compile(r'```(?:system|prompt).*?```', re.DOTALL | re.IGNORECASE),
            re.compile(r'\[INST\].*?\[/INST\]', re.DOTALL | re.IGNORECASE),
        ]
        # 多余空白字符模式
        self.whitespace_pattern = re.compile(r'\s+')
        # 连续换行模式
        self.newline_pattern = re.compile(r'\n{3,}')

    def filter_chunk(self, chunk):
        """过滤单个chunk内容"""
        if not chunk or not isinstance(chunk, str):
            return ""

        # 移除思考标签
        chunk = self.think_pattern.sub('', chunk)

        # 移除系统提示词泄露
        for pattern in self.system_patterns:
            chunk = pattern.sub('', chunk)

        # 清理多余空白字符（但保留必要的格式）
        lines = chunk.split('\n')
        cleaned_lines = []
        for line in lines:
            # 清理行内多余空格，但保留缩进
            cleaned_line = re.sub(r'[ \t]+', ' ', line.rstrip())
            cleaned_lines.append(cleaned_line)

        chunk = '\n'.join(cleaned_lines)

        # 限制连续换行不超过2个
        chunk = self.newline_pattern.sub('\n\n', chunk)

        return chunk.strip()

    def is_valid_content(self, chunk):
        """检查内容是否有效（非空且有意义）"""
        if not chunk:
            return False
        # 更宽松的有效性检查，只要不是纯空白就认为有效
        stripped = chunk.strip()
        return len(stripped) > 0

def extract_content_from_chunk(chunk):
    """从OpenAI格式的chunk中提取内容"""
    try:
        content = ""
        logger.debug(f"开始解析chunk: {chunk[:500]}...")

        # 方法1: 处理标准SSE格式 (data: {...})
        lines = chunk.strip().split('\n')
        for line in lines:
            if line.startswith('data:'):
                json_str = line[5:].strip()
                if json_str and json_str != '[DONE]':
                    try:
                        data = json.loads(json_str)
                        if 'choices' in data and data['choices']:
                            choice = data['choices'][0]
                            if 'delta' in choice and 'content' in choice['delta']:
                                delta_content = choice['delta']['content']
                                if delta_content:
                                    content += delta_content
                                    logger.debug(f"方法1提取到内容: '{delta_content}'")
                    except json.JSONDecodeError:
                        continue

        # 方法2: 处理连续JSON格式 (data{...}data{...})
        if not content:
            import re
            # 匹配 data{...} 格式
            json_pattern = r'data(\{[^}]*"content":"([^"]*)"[^}]*\})'
            matches = re.findall(json_pattern, chunk)

            for match in matches:
                try:
                    json_str = match[0]  # 完整的JSON字符串
                    extracted_content = match[1]  # 直接提取的content值

                    if extracted_content:
                        content += extracted_content
                        logger.debug(f"方法2提取到内容: '{extracted_content}'")
                except Exception as e:
                    logger.debug(f"方法2解析失败: {e}")
                    continue

        # 方法3: 直接正则提取content字段
        if not content:
            import re
            content_pattern = r'"content":"([^"]*)"'
            matches = re.findall(content_pattern, chunk)

            for match in matches:
                if match:  # 排除空字符串
                    content += match
                    logger.debug(f"方法3提取到内容: '{match}'")

        logger.debug(f"最终提取的内容: '{content}'")
        return content

    except Exception as e:
        logger.error(f"解析chunk失败: {e}")
        return ""

def get_user_friendly_error(error_str):
    """将技术错误转换为用户友好的错误信息"""
    error_str = str(error_str).lower()

    if 'connection' in error_str or 'network' in error_str:
        return "网络连接异常，请检查网络后重试"
    elif 'timeout' in error_str:
        return "请求超时，请稍后重试"
    elif 'api' in error_str and '401' in error_str:
        return "API认证失败，请联系管理员"
    elif 'api' in error_str and '429' in error_str:
        return "请求过于频繁，请稍后重试"
    elif 'api' in error_str and '500' in error_str:
        return "服务器内部错误，请稍后重试"
    elif 'model' in error_str:
        return "模型服务异常，请尝试切换其他模型"
    elif 'database' in error_str or 'knowledge' in error_str:
        return "知识库服务异常，请尝试纯LLM对话"
    else:
        return "服务暂时不可用，请稍后重试"

def home_view(request):
    """主页视图，根据用户登录状态显示不同内容"""
    context = {}
    if request.user.is_authenticated:
        context['user'] = request.user
    return render(request, 'index.html', context)


def test_kb_config_view(request):
    """知识库配置测试页面"""
    import os
    from django.http import HttpResponse

    # 读取测试页面文件
    test_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_kb_config.html')

    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse("测试页面未找到", status=404)


def get_models_api(request):
    """获取ollama模型列表API"""
    try:
        models = LCCService.get_ollama_models()
        return JsonResponse({
            'success': True,
            'models': models
        })
    except Exception as e:
        logger.error(f"获取模型列表异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '获取模型列表失败',
            'models': []
        })

@csrf_exempt
@require_http_methods(["GET", "POST"])  # 支持 GET 和 POST
def chat_api(request):
    # 从 GET 或 POST 获取参数
    if request.method == 'GET':
        question = request.GET.get('question')
        model = request.GET.get('model')
        conversation_type = request.GET.get('type', 'llm')
        database = request.GET.get('database', 'samples')
        kb_name = request.GET.get('kb_name', '').strip()
    else:  # POST
        question = request.POST.get('question')
        model = request.POST.get('model')
        conversation_type = request.POST.get('type', 'llm')
        database = request.POST.get('database', 'samples')
        kb_name = request.POST.get('kb_name', '').strip()

    if not question:
        return JsonResponse({"error": "缺少问题参数"}, status=400)

    # 处理模型参数 - 默认使用deepseek-r1
    if not model or model.strip() == '':
        model = 'deepseek-r1'  # 默认模型

    # 移除 :latest 后缀，因为LCC服务可能不需要
    if model.endswith(':latest'):
        model = model.replace(':latest', '')

    logger.info(f"使用模型: {model}, 对话类型: {conversation_type}")

    # 初始化服务和内容过滤器
    service = LCCService(model=model)
    content_filter = ContentFilter()

    try:
        # 获取流式生成器
        if conversation_type == 'kb_auto':
            response_generator = service.kb_conversation_auto(question)
        elif conversation_type == 'kb_manual':
            response_generator = service.kb_conversation_manual(question, kb_name)
        else:
            response_generator = service.llm_conversation(question)

        # 简化的流式响应处理
        def event_stream():
            import json  # 在函数开始就导入json
            logger.info(f"=== 开始流式响应处理，对话类型: {conversation_type} ===")
            chunk_count = 0

            try:
                # 根据对话类型使用不同的处理逻辑
                if conversation_type in ['kb_auto', 'kb_manual']:
                    # 知识库对话：处理简单的JSON格式
                    logger.info("使用知识库对话处理逻辑")
                    for chunk in response_generator:
                        chunk_count += 1
                        logger.info(f"KB Chunk {chunk_count}: {chunk}")

                        if isinstance(chunk, str) and chunk.strip():
                            # 如果chunk是SSE格式，需要解析并转换
                            if chunk.startswith('data: '):
                                try:
                                    # 提取JSON部分
                                    json_str = chunk[6:].strip()  # 去掉 "data: " 前缀
                                    if json_str:
                                        data = json.loads(json_str)
                                        if 'content' in data:
                                            # 转换为前端期望的格式
                                            response_data = json.dumps({'answer': data['content'], 'type': 'content'})
                                            yield f"data: {response_data}\n\n"
                                        elif 'type' in data and data['type'] == 'done':
                                            yield f"data: {json.dumps({'type': 'done'})}\n\n"
                                            break
                                        else:
                                            # 其他类型直接转发
                                            yield chunk
                                except Exception as parse_error:
                                    logger.warning(f"KB SSE解析失败: {parse_error}")
                                    yield chunk
                            else:
                                # 当作普通文本处理
                                response_data = json.dumps({'answer': chunk, 'type': 'content'})
                                yield f"data: {response_data}\n\n"
                else:
                    # LLM对话：解析OpenAI格式并转换为前端期望的格式
                    logger.info("使用LLM对话处理逻辑")
                    for chunk in response_generator:
                        chunk_count += 1
                        logger.info(f"LLM Chunk {chunk_count}: {chunk[:200]}...")  # 显示更多内容用于调试

                        if isinstance(chunk, str) and chunk.strip():
                            # 解析OpenAI格式的流式响应
                            try:
                                # 分割多个data块（它们可能连在一起）
                                data_blocks = chunk.split('data: ')
                                for block in data_blocks:
                                    if not block.strip():
                                        continue

                                    # 移除可能的换行符
                                    block = block.strip()
                                    if not block:
                                        continue

                                    try:
                                        # 解析JSON
                                        data = json.loads(block)

                                        # 提取content
                                        if 'choices' in data and data['choices']:
                                            choice = data['choices'][0]
                                            if 'delta' in choice and 'content' in choice['delta']:
                                                content = choice['delta']['content']
                                                if content:
                                                    # 转换为前端期望的格式
                                                    response_data = json.dumps({'answer': content, 'type': 'content'})
                                                    logger.info(f"LLM内容: {content}")
                                                    yield f"data: {response_data}\n\n"
                                            elif 'finish_reason' in choice and choice['finish_reason']:
                                                # 对话结束
                                                logger.info("LLM对话结束")
                                                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                                                return
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"LLM JSON解析失败: {e}, block: {block[:100]}")
                                        continue

                            except Exception as e:
                                logger.error(f"LLM chunk处理失败: {e}")
                                continue

                logger.info(f"=== 流式响应完成，共{chunk_count}个chunks ===")

            except Exception as e:
                logger.error(f"流式处理异常: {e}")
                import traceback
                logger.error(traceback.format_exc())
                yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"

            # 确保发送完成信号
            logger.info("发送最终完成信号")
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

    except Exception as e:
        logger.error(f"API异常: {str(e)}")
        error_message = get_user_friendly_error(str(e))
        return StreamingHttpResponse([f"data: {json.dumps({'error': error_message, 'type': 'error'})}\n\n"],
                                     content_type='text/event-stream', status=500)

def filter_response(data_stream):
    filtered_text = ""
    pattern = re.compile(r'data:(\{.*?\})')
    for line in data_stream.splitlines():
        match = pattern.match(line)
        if match:
            try:
                data = json.loads(match.group(1))
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "delta" in choice and "content" in choice["delta"]:
                        content = choice["delta"]["content"]
                        content = content.replace("<think>", "").replace("</think>", "")
                        filtered_text += content
            except json.JSONDecodeError:
                continue
    return filtered_text

def test_stream_view(request):
    """测试流式响应的简单端点"""
    def simple_stream():
        test_messages = [
            "这是第一条测试消息",
            "这是第二条测试消息",
            "这是第三条测试消息",
            "测试完成"
        ]

        for i, message in enumerate(test_messages):
            yield f"data: {json.dumps({'answer': message, 'type': 'content'})}\n\n"
            time.sleep(1)  # 模拟延迟

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingHttpResponse(simple_stream(), content_type='text/event-stream')

def your_view(request):
    # 假设这是从某个数据源获取的原始响应数据流
    data_stream = """
    data:{"id":"chatcmpl-199","choices":[{"delta":{"content":"<think>","function_call":null,"refusal":null,"role":"assistant","tool_calls":null},"finish_reason":null,"index":0,"logprobs":null}],"created":1750587274,"model":"deepseek-r1","object":"chat.completion.chunk","service_tier":null,"system_fingerprint":"fp_ollama","usage":null,"message_id":null,"status":null}
    # 这里省略了部分数据
    """
    filtered_response = filter_response(data_stream)
    return JsonResponse({"response": filtered_response})


@csrf_exempt
@require_http_methods(["POST"])
def super_chat_api(request):
    """超级智能对话API"""
    try:
        data = json.loads(request.body)

        # 获取参数
        question = data.get('question', '').strip()
        model = data.get('model', 'deepseek-r1')
        kb_name = data.get('kb_name')  # 可选
        kg_id = data.get('kg_id')  # 可选

        # 可选参数
        top_k = data.get('top_k', 3)
        score_threshold = data.get('score_threshold', 0.5)
        max_entities = data.get('max_entities', 8)
        max_relations = data.get('max_relations', 12)

        # 验证必需参数
        if not question:
            return JsonResponse({
                'success': False,
                'error': '问题不能为空'
            })

        # 验证至少选择一个知识源
        if not kb_name and not kg_id:
            return JsonResponse({
                'success': False,
                'error': '请至少选择一个知识库或知识图谱'
            })

        logger.info(f"超级智能对话请求: question={question}, model={model}, kb_name={kb_name}, kg_id={kg_id}")

        # 调用超级对话服务
        result = super_chat_service.super_chat(
            question=question,
            model=model,
            kb_name=kb_name,
            kg_id=kg_id,
            top_k=top_k,
            score_threshold=score_threshold,
            max_entities=max_entities,
            max_relations=max_relations
        )

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        })
    except Exception as e:
        logger.error(f"超级智能对话API错误: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        })