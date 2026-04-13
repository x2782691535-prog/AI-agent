#!/usr/bin/env python
"""
结构化数据处理视图
"""

import os
import json
import logging
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required

from .models import KnowledgeGraph
from .kg_construction.structured_kg_builder import StructuredKGBuilder
from .file_processors.structured_data_processor import StructuredDataProcessor

logger = logging.getLogger(__name__)


def kg_build_home(request):
    """知识图谱构建主页面"""
    return render(request, 'lcc/kg_build_home.html')


@login_required
def structured_kg_upload(request):
    """结构化数据上传页面"""
    return render(request, 'lcc/structured_kg_upload.html')


def unstructured_kg_upload(request):
    """非结构化数据上传页面"""
    return render(request, 'lcc/unstructured_kg_upload.html')


@csrf_exempt
@require_http_methods(["POST"])
def upload_structured_files(request):
    """上传结构化文件"""
    try:
        # 获取表单数据
        kg_name = request.POST.get('kg_name', '').strip()
        kg_description = request.POST.get('kg_description', '').strip()
        
        if not kg_name:
            return JsonResponse({
                'success': False,
                'error': '请输入知识图谱名称'
            })
        
        # 检查文件
        entity_file = request.FILES.get('entity_file')
        relation_file = request.FILES.get('relation_file')
        
        if not entity_file:
            return JsonResponse({
                'success': False,
                'error': '请上传实体Excel文件'
            })
        
        if not relation_file:
            return JsonResponse({
                'success': False,
                'error': '请上传关系CSV文件'
            })
        
        # 验证文件格式
        if not entity_file.name.endswith(('.xlsx', '.xls')):
            return JsonResponse({
                'success': False,
                'error': '实体文件必须是Excel格式(.xlsx或.xls)'
            })
        
        if not relation_file.name.endswith('.csv'):
            return JsonResponse({
                'success': False,
                'error': '关系文件必须是CSV格式(.csv)'
            })
        
        # 保存文件
        upload_dir = 'structured_uploads'
        os.makedirs(os.path.join('media', upload_dir), exist_ok=True)
        
        entity_path = default_storage.save(
            f'{upload_dir}/entity_{entity_file.name}',
            ContentFile(entity_file.read())
        )
        
        relation_path = default_storage.save(
            f'{upload_dir}/relation_{relation_file.name}',
            ContentFile(relation_file.read())
        )
        
        # 获取完整路径
        entity_full_path = os.path.join('media', entity_path)
        relation_full_path = os.path.join('media', relation_path)
        
        # 验证文件内容
        processor = StructuredDataProcessor()
        
        entity_validation = processor.validate_entity_file(entity_full_path)
        if not entity_validation['valid']:
            return JsonResponse({
                'success': False,
                'error': f'实体文件格式错误: {entity_validation["message"]}'
            })
        
        relation_validation = processor.validate_relation_file(relation_full_path)
        if not relation_validation['valid']:
            return JsonResponse({
                'success': False,
                'error': f'关系文件格式错误: {relation_validation["message"]}'
            })
        
        # 获取文件统计
        stats = processor.get_file_statistics(entity_full_path, relation_full_path)
        
        return JsonResponse({
            'success': True,
            'message': '文件上传成功',
            'entity_path': entity_path,
            'relation_path': relation_path,
            'entity_validation': entity_validation,
            'relation_validation': relation_validation,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'文件上传失败: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def build_structured_kg(request):
    """构建结构化知识图谱"""
    try:
        data = json.loads(request.body)
        
        kg_name = data.get('kg_name', '').strip()
        kg_description = data.get('kg_description', '').strip()
        entity_path = data.get('entity_path', '')
        relation_path = data.get('relation_path', '')
        
        if not all([kg_name, entity_path, relation_path]):
            return JsonResponse({
                'success': False,
                'error': '缺少必要参数'
            })
        
        # 检查知识图谱名称是否已存在
        if KnowledgeGraph.objects.filter(name=kg_name).exists():
            return JsonResponse({
                'success': False,
                'error': f'知识图谱名称 "{kg_name}" 已存在，请使用其他名称'
            })
        
        # 获取完整路径
        entity_full_path = os.path.join('media', entity_path)
        relation_full_path = os.path.join('media', relation_path)
        
        # 构建知识图谱
        builder = StructuredKGBuilder()
        result = builder.build_knowledge_graph_from_files(
            kg_name=kg_name,
            kg_description=kg_description,
            entity_file_path=entity_full_path,
            relation_file_path=relation_full_path,
            user=request.user if request.user.is_authenticated else None
        )
        
        if result['success']:
            # 清理临时文件
            try:
                os.remove(entity_full_path)
                os.remove(relation_full_path)
            except:
                pass
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"构建知识图谱失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'构建失败: {str(e)}'
        })


@require_http_methods(["GET"])
def download_sample_files(request):
    """下载示例文件"""
    try:
        processor = StructuredDataProcessor()
        
        # 创建示例文件
        sample_dir = os.path.join('media', 'samples')
        sample_files = processor.create_sample_files(sample_dir)
        
        return JsonResponse({
            'success': True,
            'entity_file_url': f'/media/samples/entities_sample.xlsx',
            'relation_file_url': f'/media/samples/relations_sample.csv',
            'message': '示例文件已生成'
        })
        
    except Exception as e:
        logger.error(f"生成示例文件失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'生成示例文件失败: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def validate_structured_file(request):
    """验证结构化文件"""
    try:
        file_type = request.POST.get('file_type')  # 'entity' or 'relation'
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            return JsonResponse({
                'success': False,
                'error': '请选择文件'
            })
        
        # 保存临时文件
        temp_dir = 'temp_validation'
        os.makedirs(os.path.join('media', temp_dir), exist_ok=True)
        
        temp_path = default_storage.save(
            f'{temp_dir}/temp_{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        temp_full_path = os.path.join('media', temp_path)
        
        # 验证文件
        processor = StructuredDataProcessor()
        
        if file_type == 'entity':
            validation = processor.validate_entity_file(temp_full_path)
        elif file_type == 'relation':
            validation = processor.validate_relation_file(temp_full_path)
        else:
            return JsonResponse({
                'success': False,
                'error': '无效的文件类型'
            })
        
        # 清理临时文件
        try:
            os.remove(temp_full_path)
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'validation': validation
        })
        
    except Exception as e:
        logger.error(f"文件验证失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'文件验证失败: {str(e)}'
        })


def kg_list(request):
    """知识图谱列表页面"""
    return render(request, 'lcc/kg_list.html')


def structured_kg_list(request):
    """结构化知识图谱列表"""
    # 获取所有知识图谱，按创建时间倒序
    knowledge_graphs = KnowledgeGraph.objects.all().order_by('-created_at')

    # 标记哪些是从结构化数据创建的
    for kg in knowledge_graphs:
        # 检查是否有结构化数据来源的文档
        has_structured_source = kg.documentsource_set.filter(
            file_type='structured'
        ).exists()
        kg.is_structured = has_structured_source

    context = {
        'knowledge_graphs': knowledge_graphs,
        'page_title': '知识图谱管理'
    }

    return render(request, 'lcc/structured_kg_list.html', context)


@require_http_methods(["GET"])
def get_kg_statistics(request, kg_id):
    """获取知识图谱统计信息"""
    try:
        kg = KnowledgeGraph.objects.get(id=kg_id)
        
        # 获取实体类型统计
        entity_types = {}
        for entity in kg.entityrecord_set.all():
            entity_type = entity.entity_type.name
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # 获取关系类型统计
        relation_types = {}
        for relation in kg.relationrecord_set.all():
            relation_type = relation.relation_type.name
            relation_types[relation_type] = relation_types.get(relation_type, 0) + 1
        
        return JsonResponse({
            'success': True,
            'statistics': {
                'total_entities': kg.entity_count,
                'total_relations': kg.relation_count,
                'entity_types': entity_types,
                'relation_types': relation_types,
                'created_at': kg.created_at.isoformat(),
                'updated_at': kg.updated_at.isoformat()
            }
        })
        
    except KnowledgeGraph.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '知识图谱不存在'
        })
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'获取统计信息失败: {str(e)}'
        })


def kg_detail(request, kg_id):
    """知识图谱详情和可视化页面"""
    try:
        kg = get_object_or_404(KnowledgeGraph, id=kg_id)

        context = {
            'knowledge_graph': kg,
            'kg_id': kg_id
        }

        return render(request, 'lcc/kg_detail.html', context)

    except Exception as e:
        logger.error(f"获取知识图谱详情失败: {e}")
        messages.error(request, f'获取知识图谱详情失败: {str(e)}')
        return redirect('kg-list')
