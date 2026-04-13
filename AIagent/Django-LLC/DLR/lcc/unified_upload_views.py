#!/usr/bin/env python
"""
统一文件上传视图 - 提供统一的文件上传和处理接口
"""

import os
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()

from .file_processors.unified_file_processor import UnifiedFileProcessor
from .kg_construction.structured_kg_builder import StructuredKGBuilder
from .models import KnowledgeGraph

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@csrf_exempt
def unified_file_upload_api(request):
    """
    统一文件上传接口
    自动识别文件类型并路由到相应的处理流程
    """
    try:
        # 获取参数
        kg_id = request.POST.get('knowledge_graph_id')
        user_id = request.POST.get('user_id', 1)
        file_type_hint = request.POST.get('file_type_hint')  # 'entity', 'relation', 'document'
        
        # 获取处理选项
        entity_types = request.POST.get('entity_types', '').split(',') if request.POST.get('entity_types') else None
        relation_types = request.POST.get('relation_types', '').split(',') if request.POST.get('relation_types') else None
        
        options = {
            'entity_types': entity_types,
            'relation_types': relation_types,
            'preprocess_options': {
                'remove_html': True,
                'remove_urls': True,
                'normalize_whitespace': True
            }
        }
        
        if not kg_id:
            return JsonResponse({
                'success': False,
                'error': '缺少知识图谱ID'
            })
        
        # 检查文件
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': '没有上传文件'
            })
        
        uploaded_file = request.FILES['file']
        
        # 保存文件
        file_path = default_storage.save(
            f'uploads/{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # 使用统一文件处理器
        processor = UnifiedFileProcessor()
        result = processor.process_file(
            full_file_path, int(kg_id), int(user_id), options, file_type_hint
        )
        
        # 清理临时文件
        try:
            os.remove(full_file_path)
        except:
            pass
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"统一文件上传失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def validate_file_api(request):
    """
    文件验证接口
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': '没有上传文件'
            })
        
        uploaded_file = request.FILES['file']
        file_type_hint = request.POST.get('file_type_hint')
        
        # 保存临时文件
        file_path = default_storage.save(
            f'temp/{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # 验证文件
        processor = UnifiedFileProcessor()
        validation_result = processor.validate_file(full_file_path, file_type_hint)
        
        # 清理临时文件
        try:
            os.remove(full_file_path)
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        logger.error(f"文件验证失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_file_type_info_api(request):
    """
    获取文件类型信息接口
    """
    try:
        file_name = request.GET.get('file_name', '')
        
        if not file_name:
            return JsonResponse({
                'success': False,
                'error': '缺少文件名'
            })
        
        processor = UnifiedFileProcessor()
        file_type_info = processor.identify_file_type(file_name)
        
        return JsonResponse({
            'success': True,
            'file_type': file_type_info
        })
        
    except Exception as e:
        logger.error(f"获取文件类型信息失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_supported_formats_api(request):
    """
    获取支持的文件格式接口
    """
    try:
        processor = UnifiedFileProcessor()
        formats = processor.get_supported_formats()
        
        return JsonResponse({
            'success': True,
            'formats': formats
        })
        
    except Exception as e:
        logger.error(f"获取支持格式失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def build_structured_kg_from_files_api(request):
    """
    从多个结构化文件构建知识图谱
    支持同时上传实体文件和关系文件
    """
    try:
        # 获取参数
        kg_name = request.POST.get('kg_name')
        kg_description = request.POST.get('kg_description', '')
        user_id = request.POST.get('user_id', 1)
        knowledge_graph_id = request.POST.get('knowledge_graph_id')

        # 如果提供了knowledge_graph_id，则更新现有图谱；否则创建新图谱
        if knowledge_graph_id:
            try:
                kg = KnowledgeGraph.objects.get(id=knowledge_graph_id)
                kg_name = kg.name
                kg_description = kg.description
                logger.info(f"更新现有知识图谱: {kg_name} (ID: {knowledge_graph_id})")
            except KnowledgeGraph.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'知识图谱ID {knowledge_graph_id} 不存在'
                })
        elif not kg_name:
            return JsonResponse({
                'success': False,
                'error': '缺少知识图谱名称或ID'
            })
        
        # 检查文件
        if 'entity_file' not in request.FILES or 'relation_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': '需要同时上传实体文件和关系文件'
            })
        
        entity_file = request.FILES['entity_file']
        relation_file = request.FILES['relation_file']
        
        # 保存文件
        entity_path = default_storage.save(
            f'structured/entities/{entity_file.name}',
            ContentFile(entity_file.read())
        )
        
        relation_path = default_storage.save(
            f'structured/relations/{relation_file.name}',
            ContentFile(relation_file.read())
        )
        
        # 获取完整路径
        entity_full_path = os.path.join(settings.MEDIA_ROOT, entity_path)
        relation_full_path = os.path.join(settings.MEDIA_ROOT, relation_path)
        
        # 验证文件
        processor = UnifiedFileProcessor()
        
        entity_validation = processor.validate_file(entity_full_path, 'entity')
        if not entity_validation['valid']:
            return JsonResponse({
                'success': False,
                'error': f'实体文件验证失败: {entity_validation["message"]}'
            })
        
        relation_validation = processor.validate_file(relation_full_path, 'relation')
        if not relation_validation['valid']:
            return JsonResponse({
                'success': False,
                'error': f'关系文件验证失败: {relation_validation["message"]}'
            })
        
        # 构建知识图谱
        builder = StructuredKGBuilder()

        if knowledge_graph_id:
            # 更新现有知识图谱
            result = builder.update_knowledge_graph_from_files(
                knowledge_graph_id=int(knowledge_graph_id),
                entity_file_path=entity_full_path,
                relation_file_path=relation_full_path,
                user=request.user if request.user.is_authenticated else None
            )
        else:
            # 创建新知识图谱
            result = builder.build_knowledge_graph_from_files(
                kg_name=kg_name,
                kg_description=kg_description,
                entity_file_path=entity_full_path,
                relation_file_path=relation_full_path,
                user=request.user if request.user.is_authenticated else None
            )
        
        # 清理临时文件
        try:
            os.remove(entity_full_path)
            os.remove(relation_full_path)
        except:
            pass
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"结构化知识图谱构建失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'构建失败: {str(e)}'
        })


@require_http_methods(["POST"])
@csrf_exempt
def batch_file_upload_api(request):
    """
    批量文件上传接口
    支持同时上传多个文件
    """
    try:
        kg_id = request.POST.get('knowledge_graph_id')
        user_id = request.POST.get('user_id', 1)
        
        if not kg_id:
            return JsonResponse({
                'success': False,
                'error': '缺少知识图谱ID'
            })
        
        # 获取所有上传的文件
        uploaded_files = request.FILES.getlist('files')
        
        if not uploaded_files:
            return JsonResponse({
                'success': False,
                'error': '没有上传文件'
            })
        
        processor = UnifiedFileProcessor()
        results = []
        
        for uploaded_file in uploaded_files:
            try:
                # 保存文件
                file_path = default_storage.save(
                    f'batch_uploads/{uploaded_file.name}',
                    ContentFile(uploaded_file.read())
                )
                
                full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
                
                # 处理文件
                result = processor.process_file(
                    full_file_path, int(kg_id), int(user_id)
                )
                
                result['file_name'] = uploaded_file.name
                results.append(result)
                
                # 清理临时文件
                try:
                    os.remove(full_file_path)
                except:
                    pass
                    
            except Exception as file_error:
                results.append({
                    'success': False,
                    'file_name': uploaded_file.name,
                    'error': str(file_error)
                })
        
        # 统计结果
        success_count = sum(1 for r in results if r.get('success', False))
        total_count = len(results)
        
        return JsonResponse({
            'success': True,
            'results': results,
            'summary': {
                'total_files': total_count,
                'success_files': success_count,
                'failed_files': total_count - success_count
            }
        })
        
    except Exception as e:
        logger.error(f"批量文件上传失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def sync_kg_statistics_api(request):
    """
    同步知识图谱统计信息接口
    """
    try:
        kg_id = request.POST.get('knowledge_graph_id')

        if not kg_id:
            return JsonResponse({
                'success': False,
                'error': '缺少知识图谱ID'
            })

        # 使用结构化构建器的同步方法
        from .kg_construction.structured_kg_builder import StructuredKGBuilder
        builder = StructuredKGBuilder()

        result = builder.sync_statistics_with_neo4j(int(kg_id))

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"统计信息同步失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
