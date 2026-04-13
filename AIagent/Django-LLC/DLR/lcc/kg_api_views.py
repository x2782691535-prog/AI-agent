"""
知识图谱构建API视图
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
from django.utils import timezone

from .kg_construction.kg_builder import KnowledgeGraphBuilder
from .models import KnowledgeGraph, ProcessingTask, DocumentSource, EntityType, RelationType
from .models import User
from .kg_qa_service import kg_qa_service
from django.db import transaction
from django.http import StreamingHttpResponse

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@csrf_exempt
def create_knowledge_graph_api(request):
    """创建知识图谱"""
    try:
        data = json.loads(request.body)
        
        # 获取用户（简化处理，实际应该从认证中获取）
        user_id = data.get('user_id', 1)
        user = User.objects.get(id=user_id)
        
        # 创建知识图谱
        kg = KnowledgeGraph.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            domain=data.get('domain', 'general'),
            created_by=user
        )
        
        return JsonResponse({
            'success': True,
            'knowledge_graph_id': kg.id,
            'message': f'知识图谱 "{kg.name}" 创建成功'
        })
        
    except Exception as e:
        logger.error(f"创建知识图谱失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def list_knowledge_graphs_api(request):
    """获取知识图谱列表"""
    try:
        # 获取用户的知识图谱
        user_id = request.GET.get('user_id', 1)
        user = User.objects.get(id=user_id)
        
        kgs = KnowledgeGraph.objects.filter(created_by=user).order_by('-updated_at')
        
        kg_list = []
        for kg in kgs:
            kg_list.append({
                'id': kg.id,
                'name': kg.name,
                'description': kg.description,
                'domain': kg.domain,
                'status': kg.status,
                'entity_count': kg.entity_count,
                'relation_count': kg.relation_count,
                'document_count': kg.document_count,
                'created_at': kg.created_at.isoformat(),
                'updated_at': kg.updated_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'knowledge_graphs': kg_list
        })
        
    except Exception as e:
        logger.error(f"获取知识图谱列表失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def upload_document_api(request):
    """上传文档并构建知识图谱"""
    try:
        # 获取参数
        kg_id = request.POST.get('knowledge_graph_id')
        user_id = request.POST.get('user_id', 1)
        
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
            f'documents/{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # 构建选项
        options = {
            'entity_types': request.POST.get('entity_types', '').split(',') if request.POST.get('entity_types') else None,
            'relation_types': request.POST.get('relation_types', '').split(',') if request.POST.get('relation_types') else None,
            'preprocess_options': {
                'remove_html': True,
                'remove_urls': True,
                'normalize_whitespace': True
            }
        }
        
        # 构建知识图谱
        builder = KnowledgeGraphBuilder()
        result = builder.build_from_document(
            full_file_path, int(kg_id), int(user_id), options
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def process_text_api(request):
    """处理文本并构建知识图谱"""
    try:
        data = json.loads(request.body)
        
        # 获取参数
        kg_id = data.get('knowledge_graph_id')
        user_id = data.get('user_id', 1)
        text = data.get('text')
        title = data.get('title', '文本输入')
        
        if not kg_id or not text:
            return JsonResponse({
                'success': False,
                'error': '缺少必要参数'
            })
        
        # 构建选项
        options = {
            'entity_types': data.get('entity_types'),
            'relation_types': data.get('relation_types'),
            'preprocess_options': data.get('preprocess_options', {
                'remove_html': True,
                'remove_urls': True,
                'normalize_whitespace': True
            })
        }
        
        # 构建知识图谱
        builder = KnowledgeGraphBuilder()
        result = builder.build_from_text(
            text, int(kg_id), int(user_id), title, options
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"处理文本失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_processing_tasks_api(request):
    """获取处理任务列表"""
    try:
        kg_id = request.GET.get('knowledge_graph_id')
        user_id = request.GET.get('user_id', 1)
        
        if kg_id:
            tasks = ProcessingTask.objects.filter(
                knowledge_graph_id=kg_id
            ).order_by('-created_at')[:20]
        else:
            tasks = ProcessingTask.objects.filter(
                created_by_id=user_id
            ).order_by('-created_at')[:20]
        
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task.id,
                'task_name': task.task_name,
                'task_type': task.task_type,
                'status': task.status,
                'progress': task.progress,
                'result_summary': task.result_summary,
                'entities_processed': task.entities_processed,
                'relations_processed': task.relations_processed,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'execution_time': task.execution_time
            })
        
        return JsonResponse({
            'success': True,
            'tasks': task_list
        })
        
    except Exception as e:
        logger.error(f"获取处理任务失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_task_status_api(request, task_id):
    """获取任务状态"""
    try:
        task = ProcessingTask.objects.get(id=task_id)
        
        return JsonResponse({
            'success': True,
            'task': {
                'id': task.id,
                'status': task.status,
                'progress': task.progress,
                'result_summary': task.result_summary,
                'error_message': task.error_message,
                'entities_processed': task.entities_processed,
                'relations_processed': task.relations_processed,
                'execution_time': task.execution_time
            }
        })
        
    except ProcessingTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '任务不存在'
        })
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_kg_statistics_api(request, kg_id):
    """获取知识图谱统计信息"""
    try:
        kg = KnowledgeGraph.objects.get(id=kg_id)
        
        # 获取文档统计
        documents = DocumentSource.objects.filter(knowledge_graph=kg)
        doc_stats = {
            'total': documents.count(),
            'completed': documents.filter(processing_status='completed').count(),
            'processing': documents.filter(processing_status='processing').count(),
            'failed': documents.filter(processing_status='failed').count()
        }
        
        # 获取任务统计
        tasks = ProcessingTask.objects.filter(knowledge_graph=kg)
        task_stats = {
            'total': tasks.count(),
            'completed': tasks.filter(status='completed').count(),
            'running': tasks.filter(status='running').count(),
            'failed': tasks.filter(status='failed').count()
        }
        
        return JsonResponse({
            'success': True,
            'statistics': {
                'knowledge_graph': {
                    'id': kg.id,
                    'name': kg.name,
                    'domain': kg.domain,
                    'status': kg.status,
                    'entity_count': kg.entity_count,
                    'relation_count': kg.relation_count,
                    'document_count': kg.document_count,
                    'created_at': kg.created_at.isoformat(),
                    'updated_at': kg.updated_at.isoformat(),
                    'last_processed_at': kg.last_processed_at.isoformat() if kg.last_processed_at else None
                },
                'documents': doc_stats,
                'tasks': task_stats
            }
        })
        
    except KnowledgeGraph.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '知识图谱不存在'
        })
    except Exception as e:
        logger.error(f"获取知识图谱统计失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_supported_formats_api(request):
    """获取支持的文档格式"""
    try:
        builder = KnowledgeGraphBuilder()
        formats = builder.get_supported_formats()
        
        return JsonResponse({
            'success': True,
            'supported_formats': formats
        })
        
    except Exception as e:
        logger.error(f"获取支持格式失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def validate_document_api(request):
    """验证文档"""
    try:
        data = json.loads(request.body)
        file_path = data.get('file_path')
        
        if not file_path:
            return JsonResponse({
                'success': False,
                'error': '缺少文件路径'
            })
        
        builder = KnowledgeGraphBuilder()
        result = builder.validate_document(file_path)
        
        return JsonResponse({
            'success': True,
            'validation': result
        })
        
    except Exception as e:
        logger.error(f"验证文档失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ==================== 实体类型管理API ====================

@require_http_methods(["GET"])
def get_entity_types_api(request):
    """获取实体类型列表"""
    try:
        entity_types = EntityType.objects.filter(is_active=True).order_by('category', 'name')

        types_list = []
        for et in entity_types:
            types_list.append({
                'id': et.id,
                'name': et.name,
                'label': et.label,
                'description': et.description,
                'category': et.category,
                'color': et.color,
                'icon': et.icon,
                'is_active': et.is_active,
                'created_at': et.created_at.isoformat(),
                'updated_at': et.updated_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'entity_types': types_list
        })

    except Exception as e:
        logger.error(f"获取实体类型列表失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def create_entity_type_api(request):
    """创建实体类型"""
    try:
        data = json.loads(request.body)

        # 验证必需字段
        name = data.get('name', '').strip().upper()
        label = data.get('label', '').strip()

        if not name or not label:
            return JsonResponse({
                'success': False,
                'error': '名称和标签不能为空'
            })

        # 检查名称是否已存在
        if EntityType.objects.filter(name=name).exists():
            return JsonResponse({
                'success': False,
                'error': f'实体类型 "{name}" 已存在'
            })

        # 创建实体类型
        entity_type = EntityType.objects.create(
            name=name,
            label=label,
            description=data.get('description', ''),
            category=data.get('category', 'custom'),
            color=data.get('color', '#cccccc'),
            icon=data.get('icon', ''),
            extraction_patterns=data.get('extraction_patterns', [])
        )

        return JsonResponse({
            'success': True,
            'entity_type': {
                'id': entity_type.id,
                'name': entity_type.name,
                'label': entity_type.label,
                'description': entity_type.description,
                'category': entity_type.category,
                'color': entity_type.color,
                'icon': entity_type.icon
            },
            'message': f'实体类型 "{label}" 创建成功'
        })

    except Exception as e:
        logger.error(f"创建实体类型失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["DELETE"])
@csrf_exempt
def delete_entity_type_api(request, type_id):
    """删除实体类型"""
    try:
        entity_type = EntityType.objects.get(id=type_id)

        # 检查是否有关联的实体记录
        from .models import EntityRecord
        if EntityRecord.objects.filter(entity_type=entity_type).exists():
            return JsonResponse({
                'success': False,
                'error': '该实体类型已被使用，无法删除'
            })

        entity_type_name = entity_type.label
        entity_type.delete()

        return JsonResponse({
            'success': True,
            'message': f'实体类型 "{entity_type_name}" 删除成功'
        })

    except EntityType.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '实体类型不存在'
        })
    except Exception as e:
        logger.error(f"删除实体类型失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ==================== 关系类型管理API ====================

@require_http_methods(["GET"])
def get_relation_types_api(request):
    """获取关系类型列表"""
    try:
        relation_types = RelationType.objects.filter(is_active=True).order_by('category', 'name')

        types_list = []
        for rt in relation_types:
            types_list.append({
                'id': rt.id,
                'name': rt.name,
                'label': rt.label,
                'description': rt.description,
                'category': rt.category,
                'is_symmetric': rt.is_symmetric,
                'is_transitive': rt.is_transitive,
                'is_active': rt.is_active,
                'created_at': rt.created_at.isoformat(),
                'updated_at': rt.updated_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'relation_types': types_list
        })

    except Exception as e:
        logger.error(f"获取关系类型列表失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def create_relation_type_api(request):
    """创建关系类型"""
    try:
        data = json.loads(request.body)

        # 验证必需字段
        name = data.get('name', '').strip().upper()
        label = data.get('label', '').strip()

        if not name or not label:
            return JsonResponse({
                'success': False,
                'error': '名称和标签不能为空'
            })

        # 检查名称是否已存在
        if RelationType.objects.filter(name=name).exists():
            return JsonResponse({
                'success': False,
                'error': f'关系类型 "{name}" 已存在'
            })

        # 创建关系类型
        relation_type = RelationType.objects.create(
            name=name,
            label=label,
            description=data.get('description', ''),
            category=data.get('category', 'custom'),
            is_symmetric=data.get('is_symmetric', False),
            is_transitive=data.get('is_transitive', False),
            extraction_patterns=data.get('extraction_patterns', [])
        )

        return JsonResponse({
            'success': True,
            'relation_type': {
                'id': relation_type.id,
                'name': relation_type.name,
                'label': relation_type.label,
                'description': relation_type.description,
                'category': relation_type.category,
                'is_symmetric': relation_type.is_symmetric,
                'is_transitive': relation_type.is_transitive
            },
            'message': f'关系类型 "{label}" 创建成功'
        })

    except Exception as e:
        logger.error(f"创建关系类型失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["DELETE"])
@csrf_exempt
def delete_relation_type_api(request, type_id):
    """删除关系类型"""
    try:
        relation_type = RelationType.objects.get(id=type_id)

        # 检查是否有关联的关系记录
        from .models import RelationRecord
        if RelationRecord.objects.filter(relation_type=relation_type).exists():
            return JsonResponse({
                'success': False,
                'error': '该关系类型已被使用，无法删除'
            })

        relation_type_name = relation_type.label
        relation_type.delete()

        return JsonResponse({
            'success': True,
            'message': f'关系类型 "{relation_type_name}" 删除成功'
        })

    except RelationType.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '关系类型不存在'
        })
    except Exception as e:
        logger.error(f"删除关系类型失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ==================== 知识图谱清空功能API ====================

@require_http_methods(["POST"])
@csrf_exempt
def clear_knowledge_graph_api(request, kg_id):
    """清空知识图谱中的所有实体和关系"""
    try:
        # 验证知识图谱是否存在
        try:
            knowledge_graph = KnowledgeGraph.objects.get(id=kg_id)
        except KnowledgeGraph.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '知识图谱不存在'
            })

        # 获取清空选项
        data = json.loads(request.body) if request.body else {}
        clear_entities = data.get('clear_entities', True)
        clear_relations = data.get('clear_relations', True)
        clear_documents = data.get('clear_documents', False)

        # 统计清空前的数据
        from .models import EntityRecord, RelationRecord
        entity_count_before = EntityRecord.objects.filter(knowledge_graph=knowledge_graph).count()
        relation_count_before = RelationRecord.objects.filter(knowledge_graph=knowledge_graph).count()
        document_count_before = DocumentSource.objects.filter(knowledge_graph=knowledge_graph).count()

        # 清空Neo4j数据库中的数据
        from .kg_construction.kg_builder import KnowledgeGraphBuilder
        builder = KnowledgeGraphBuilder()

        neo4j_cleared = False
        try:
            # 连接Neo4j并清空指定知识图谱的数据
            if clear_entities or clear_relations:
                neo4j_result = builder.clear_neo4j_data(kg_id, clear_entities, clear_relations)
                neo4j_cleared = neo4j_result.get('success', False)
        except Exception as e:
            logger.warning(f"Neo4j清空失败，继续清空Django数据: {e}")

        # 清空Django数据库中的数据
        cleared_counts = {
            'entities': 0,
            'relations': 0,
            'documents': 0
        }

        if clear_entities:
            # 删除实体记录
            deleted_entities = EntityRecord.objects.filter(knowledge_graph=knowledge_graph).delete()
            cleared_counts['entities'] = deleted_entities[0] if deleted_entities[0] else 0

        if clear_relations:
            # 删除关系记录
            deleted_relations = RelationRecord.objects.filter(knowledge_graph=knowledge_graph).delete()
            cleared_counts['relations'] = deleted_relations[0] if deleted_relations[0] else 0

        if clear_documents:
            # 删除文档记录
            deleted_documents = DocumentSource.objects.filter(knowledge_graph=knowledge_graph).delete()
            cleared_counts['documents'] = deleted_documents[0] if deleted_documents[0] else 0

        # 更新知识图谱统计信息
        try:
            # 使用模型的update_statistics方法重新计算统计信息
            updated_stats = knowledge_graph.update_statistics()
            logger.info(f"清空后统计信息已更新: {updated_stats}")
        except Exception as e:
            logger.warning(f"清空后统计信息更新失败: {e}")
            # 如果更新失败，手动设置统计信息
            if clear_entities:
                knowledge_graph.entity_count = 0
            if clear_relations:
                knowledge_graph.relation_count = 0
            if clear_documents:
                knowledge_graph.document_count = 0
            knowledge_graph.save()

        knowledge_graph.last_processed_at = timezone.now()
        knowledge_graph.save()

        # 创建处理任务记录
        task = ProcessingTask.objects.create(
            knowledge_graph=knowledge_graph,
            task_type='clear',
            status='completed',
            created_by_id=knowledge_graph.created_by_id,
            started_at=timezone.now(),
            completed_at=timezone.now(),
            result_summary={
                'cleared_entities': cleared_counts['entities'],
                'cleared_relations': cleared_counts['relations'],
                'cleared_documents': cleared_counts['documents'],
                'neo4j_cleared': neo4j_cleared,
                'before_counts': {
                    'entities': entity_count_before,
                    'relations': relation_count_before,
                    'documents': document_count_before
                }
            }
        )

        return JsonResponse({
            'success': True,
            'message': f'知识图谱 "{knowledge_graph.name}" 清空成功',
            'task_id': task.id,
            'cleared_counts': cleared_counts,
            'before_counts': {
                'entities': entity_count_before,
                'relations': relation_count_before,
                'documents': document_count_before
            },
            'neo4j_cleared': neo4j_cleared
        })

    except Exception as e:
        logger.error(f"清空知识图谱失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def clear_all_knowledge_graphs_api(request):
    """清空所有知识图谱的数据"""
    try:
        data = json.loads(request.body) if request.body else {}
        user_id = data.get('user_id', 1)
        clear_entities = data.get('clear_entities', True)
        clear_relations = data.get('clear_relations', True)
        clear_documents = data.get('clear_documents', False)

        # 获取用户的所有知识图谱
        knowledge_graphs = KnowledgeGraph.objects.filter(created_by_id=user_id)

        if not knowledge_graphs.exists():
            return JsonResponse({
                'success': False,
                'error': '没有找到知识图谱'
            })

        total_cleared = {
            'entities': 0,
            'relations': 0,
            'documents': 0,
            'graphs': 0
        }

        # 清空每个知识图谱
        for kg in knowledge_graphs:
            try:
                # 统计清空前的数据
                from .models import EntityRecord, RelationRecord
                entity_count = EntityRecord.objects.filter(knowledge_graph=kg).count()
                relation_count = RelationRecord.objects.filter(knowledge_graph=kg).count()
                document_count = DocumentSource.objects.filter(knowledge_graph=kg).count()

                # 清空数据
                if clear_entities:
                    deleted_entities = EntityRecord.objects.filter(knowledge_graph=kg).delete()
                    total_cleared['entities'] += deleted_entities[0] if deleted_entities[0] else 0

                if clear_relations:
                    deleted_relations = RelationRecord.objects.filter(knowledge_graph=kg).delete()
                    total_cleared['relations'] += deleted_relations[0] if deleted_relations[0] else 0

                if clear_documents:
                    deleted_documents = DocumentSource.objects.filter(knowledge_graph=kg).delete()
                    total_cleared['documents'] += deleted_documents[0] if deleted_documents[0] else 0

                # 更新知识图谱统计信息
                try:
                    updated_stats = kg.update_statistics()
                    logger.info(f"知识图谱 {kg.name} 统计信息已更新: {updated_stats}")
                except Exception as e:
                    logger.warning(f"知识图谱 {kg.name} 统计信息更新失败: {e}")
                    # 如果更新失败，手动设置统计信息
                    kg.entity_count = 0 if clear_entities else kg.entity_count
                    kg.relation_count = 0 if clear_relations else kg.relation_count
                    kg.document_count = 0 if clear_documents else kg.document_count
                    kg.save()

                kg.last_processed_at = timezone.now()
                kg.save()

                total_cleared['graphs'] += 1

            except Exception as e:
                logger.error(f"清空知识图谱 {kg.name} 失败: {e}")
                continue

        # 清空Neo4j中的所有数据
        neo4j_cleared = False
        try:
            from .kg_construction.kg_builder import KnowledgeGraphBuilder
            builder = KnowledgeGraphBuilder()
            neo4j_result = builder.clear_all_neo4j_data()
            neo4j_cleared = neo4j_result.get('success', False)
        except Exception as e:
            logger.warning(f"Neo4j全部清空失败: {e}")

        return JsonResponse({
            'success': True,
            'message': f'成功清空 {total_cleared["graphs"]} 个知识图谱',
            'cleared_counts': total_cleared,
            'neo4j_cleared': neo4j_cleared
        })

    except Exception as e:
        logger.error(f"清空所有知识图谱失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["DELETE"])
@csrf_exempt
def delete_knowledge_graph_api(request, kg_id):
    """删除知识图谱"""
    try:
        # 获取知识图谱
        try:
            knowledge_graph = KnowledgeGraph.objects.get(id=kg_id)
        except KnowledgeGraph.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '知识图谱不存在'
            })

        # 记录删除前的信息
        kg_name = knowledge_graph.name
        entity_count = knowledge_graph.entity_count
        relation_count = knowledge_graph.relation_count
        document_count = knowledge_graph.document_count

        # 删除Neo4j中的数据
        from .kg_construction.kg_builder import KnowledgeGraphBuilder
        builder = KnowledgeGraphBuilder()

        neo4j_deleted = False
        try:
            # 清空Neo4j中该知识图谱的所有数据
            neo4j_result = builder.clear_neo4j_data(kg_id, True, True)
            neo4j_deleted = neo4j_result.get('success', False)
        except Exception as e:
            logger.warning(f"Neo4j数据删除失败，继续删除Django数据: {e}")

        # 删除Django数据库中的相关数据
        from .models import EntityRecord, RelationRecord

        # 删除实体记录
        EntityRecord.objects.filter(knowledge_graph=knowledge_graph).delete()

        # 删除关系记录
        RelationRecord.objects.filter(knowledge_graph=knowledge_graph).delete()

        # 删除文档记录
        DocumentSource.objects.filter(knowledge_graph=knowledge_graph).delete()

        # 删除处理任务记录
        ProcessingTask.objects.filter(knowledge_graph=knowledge_graph).delete()

        # 最后删除知识图谱本身
        knowledge_graph.delete()

        logger.info(f"知识图谱删除成功: {kg_name} (ID: {kg_id})")

        return JsonResponse({
            'success': True,
            'message': f'知识图谱 "{kg_name}" 删除成功',
            'deleted_data': {
                'entities': entity_count,
                'relations': relation_count,
                'documents': document_count
            },
            'neo4j_deleted': neo4j_deleted
        })

    except Exception as e:
        logger.error(f"删除知识图谱失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_knowledge_graph_data(request, kg_id):
    """获取知识图谱可视化数据"""
    try:
        # 验证知识图谱是否存在
        try:
            knowledge_graph = KnowledgeGraph.objects.get(id=kg_id)
        except KnowledgeGraph.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '知识图谱不存在'
            })

        # 从Neo4j获取图谱数据
        from .neo4j_manager import Neo4jManager
        neo4j_manager = Neo4jManager()

        try:
            with neo4j_manager.get_session() as session:
                # 分别查询节点和关系，避免LIMIT影响节点数量
                # 1. 查询所有节点
                nodes_query = """
                MATCH (n:Entity {knowledge_graph_id: $kg_id})
                RETURN n
                ORDER BY n.name
                """

                # 2. 查询所有关系
                relations_query = """
                MATCH (source:Entity {knowledge_graph_id: $kg_id})-[r:RELATES]->(target:Entity {knowledge_graph_id: $kg_id})
                RETURN source, r, target
                ORDER BY source.name, target.name
                """

                # 执行节点查询
                nodes_result = session.run(nodes_query, kg_id=int(kg_id))
                # 执行关系查询
                relations_result = session.run(relations_query, kg_id=int(kg_id))

                nodes = {}
                edges = []

                # 处理所有节点
                for record in nodes_result:
                    # 处理节点
                    node = record['n']
                    node_id = node.element_id

                    # 处理节点属性，转换datetime对象
                    node_properties = {}
                    for key, value in dict(node).items():
                        if hasattr(value, 'isoformat'):  # datetime对象
                            node_properties[key] = value.isoformat()
                        else:
                            node_properties[key] = value

                    nodes[node_id] = {
                        'id': node_id,
                        'label': node.get('name', 'Unknown'),
                        'type': node.get('entity_type', 'Unknown'),
                        'properties': node_properties,
                        'group': _get_node_group(node.get('entity_type', 'Unknown'))  # 添加分组信息
                    }

                # 处理所有关系
                for record in relations_result:
                    source_node = record['source']
                    relationship = record['r']
                    target_node = record['target']

                    source_id = source_node.element_id
                    target_id = target_node.element_id

                    # 处理关系属性，转换datetime对象
                    rel_properties = {}
                    for key, value in dict(relationship).items():
                        if hasattr(value, 'isoformat'):  # datetime对象
                            rel_properties[key] = value.isoformat()
                        else:
                            rel_properties[key] = value

                    # 使用关系的type字段作为标签，而不是固定的"RELATES"
                    relation_label = relationship.get('type', 'RELATES')

                    # 生成关系ID
                    relation_id = f"rel_{source_id}_{target_id}_{len(edges)}"

                    edges.append({
                        'id': relation_id,
                        'from': source_id,  # vis.js使用from/to
                        'to': target_id,
                        'source': source_id,  # 前端兼容性
                        'target': target_id,
                        'label': relation_label,
                        'type': relation_label,
                        'properties': rel_properties,
                        'arrows': 'to'  # 添加箭头方向
                    })

                return JsonResponse({
                    'success': True,
                    'data': {
                        'nodes': list(nodes.values()),
                        'edges': edges,
                        'stats': {
                            'total_nodes': len(nodes),
                            'total_edges': len(edges),
                            'node_types': _get_node_type_stats(nodes.values())
                        }
                    },
                    'knowledge_graph': {
                        'id': knowledge_graph.id,
                        'name': knowledge_graph.name,
                        'description': knowledge_graph.description,
                        'entity_count': len(nodes),
                        'relation_count': len(edges)
                    }
                })

        except Exception as neo4j_error:
            logger.error(f"Neo4j查询失败: {neo4j_error}")
            return JsonResponse({
                'success': False,
                'error': f'图数据库查询失败: {str(neo4j_error)}'
            })

    except Exception as e:
        logger.error(f"获取知识图谱数据失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def _get_node_group(node_type):
    """根据节点类型返回分组信息，用于可视化布局"""
    type_groups = {
        '程序结构': 1,
        '存储器': 2,
        '显示器件': 3,
        '接口': 4,
        '数据类型': 5,
        '芯片': 6,
        '硬件组件': 7,
        '编程语言': 8,
        '微控制器': 9,
        '概念': 10
    }
    return type_groups.get(node_type, 0)  # 默认分组

def _get_node_type_stats(nodes):
    """获取节点类型统计信息"""
    type_counts = {}
    for node in nodes:
        node_type = node.get('type', 'Unknown')
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    return type_counts


@require_http_methods(["POST"])
@csrf_exempt
def refresh_kg_statistics_api(request):
    """刷新知识图谱统计信息"""
    try:
        data = json.loads(request.body)
        kg_id = data.get('kg_id')

        if not kg_id:
            return JsonResponse({
                'success': False,
                'error': '缺少知识图谱ID'
            })

        # 获取知识图谱
        try:
            kg = KnowledgeGraph.objects.get(id=kg_id)
        except KnowledgeGraph.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'知识图谱 ID {kg_id} 不存在'
            })

        # 获取更新前的统计信息
        old_stats = {
            'entity_count': kg.entity_count,
            'relation_count': kg.relation_count,
            'document_count': kg.document_count
        }

        # 使用事务更新统计信息
        with transaction.atomic():
            new_stats = kg.update_statistics()

        logger.info(f"知识图谱 {kg.name} 统计信息已更新: {old_stats} -> {new_stats}")

        return JsonResponse({
            'success': True,
            'message': '统计信息已刷新',
            'old_statistics': old_stats,
            'new_statistics': new_stats,
            'changes': {
                'entity_count_changed': old_stats['entity_count'] != new_stats['entity_count'],
                'relation_count_changed': old_stats['relation_count'] != new_stats['relation_count'],
                'document_count_changed': old_stats['document_count'] != new_stats['document_count']
            }
        })

    except Exception as e:
        logger.error(f"刷新知识图谱统计信息失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_kg_statistics_api(request, kg_id):
    """获取知识图谱的实时统计信息"""
    try:
        # 获取知识图谱
        try:
            kg = KnowledgeGraph.objects.get(id=kg_id)
        except KnowledgeGraph.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'知识图谱 ID {kg_id} 不存在'
            })

        # 获取数据库中存储的统计信息
        stored_stats = {
            'entity_count': kg.entity_count,
            'relation_count': kg.relation_count,
            'document_count': kg.document_count
        }

        # 获取实时统计信息
        actual_stats = {
            'entity_count': kg.entityrecord_set.count(),
            'relation_count': kg.relationrecord_set.count(),
            'document_count': kg.documentsource_set.count()
        }

        # 检查是否需要更新
        needs_update = (
            stored_stats['entity_count'] != actual_stats['entity_count'] or
            stored_stats['relation_count'] != actual_stats['relation_count'] or
            stored_stats['document_count'] != actual_stats['document_count']
        )

        return JsonResponse({
            'success': True,
            'stored_statistics': stored_stats,
            'actual_statistics': actual_stats,
            'needs_update': needs_update,
            'kg_info': {
                'id': kg.id,
                'name': kg.name,
                'status': kg.status,
                'updated_at': kg.updated_at.isoformat()
            }
        })

    except Exception as e:
        logger.error(f"获取知识图谱统计信息失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def _get_node_group(node_type):
    """根据节点类型获取分组编号"""
    type_groups = {
        'PROLANGUAGE': 1,
        'INTERFACE': 2,
        'STORAGE': 3,
        'PERIPHERAL': 4,
        'COM': 5,
        'SINGLECHIP': 6,
        'CLOCK': 7,
        'CPU': 8,
        'PIN': 9,
        'TIMER': 10,
        'INTERRUPT': 11,
        'POWER': 12,
        'SENSOR': 13,
        'ACTUATOR': 14
    }
    return type_groups.get(node_type, 0)


def _get_node_type_stats(nodes):
    """获取节点类型统计"""
    type_stats = {}
    for node in nodes:
        node_type = node.get('type', 'Unknown')
        type_stats[node_type] = type_stats.get(node_type, 0) + 1
    return type_stats


# ==================== 知识图谱智能问答API ====================

@require_http_methods(["POST"])
@csrf_exempt
def kg_qa_api(request, kg_id):
    """知识图谱智能问答API"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        model = data.get('model', 'deepseek-r1')
        max_entities = data.get('max_entities', 10)
        max_relations = data.get('max_relations', 20)

        if not question:
            return JsonResponse({
                'success': False,
                'error': '问题不能为空'
            })

        logger.info(f"知识图谱问答请求: KG={kg_id}, 问题={question[:50]}..., 模型={model}")

        # 调用知识图谱问答服务
        result = kg_qa_service.answer_question(
            kg_id=kg_id,
            question=question,
            model=model,
            max_entities=max_entities,
            max_relations=max_relations
        )

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '请求数据格式错误'
        })
    except Exception as e:
        logger.error(f"知识图谱问答失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["POST"])
@csrf_exempt
def kg_qa_stream_api(request, kg_id):
    """知识图谱智能问答流式API"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        model = data.get('model', 'deepseek-r1')
        max_entities = data.get('max_entities', 10)
        max_relations = data.get('max_relations', 20)

        if not question:
            def error_stream():
                yield f'data: {json.dumps({"error": "问题不能为空"})}\n\n'
            return StreamingHttpResponse(error_stream(), content_type='text/event-stream')

        logger.info(f"知识图谱流式问答请求: KG={kg_id}, 问题={question[:50]}..., 模型={model}")

        def qa_stream():
            try:
                # 发送开始信号
                yield f'data: {json.dumps({"type": "start", "message": "正在分析问题..."})}\n\n'

                # 调用知识图谱问答服务
                result = kg_qa_service.answer_question(
                    kg_id=kg_id,
                    question=question,
                    model=model,
                    max_entities=max_entities,
                    max_relations=max_relations
                )

                if result['success']:
                    # 发送上下文信息
                    yield f'data: {json.dumps({"type": "context", "data": result["context"]})}\n\n'

                    # 发送答案（可以分块发送以模拟流式效果）
                    answer = result['answer']
                    chunk_size = 50
                    for i in range(0, len(answer), chunk_size):
                        chunk = answer[i:i+chunk_size]
                        yield f'data: {json.dumps({"type": "content", "content": chunk})}\n\n'

                    # 发送完成信号
                    yield f'data: {json.dumps({"type": "done", "sources": result.get("sources", {})})}\n\n'
                else:
                    yield f'data: {json.dumps({"type": "error", "error": result["error"]})}\n\n'

            except Exception as e:
                logger.error(f"流式问答失败: {e}")
                yield f'data: {json.dumps({"type": "error", "error": str(e)})}\n\n'

        return StreamingHttpResponse(qa_stream(), content_type='text/event-stream')

    except json.JSONDecodeError:
        def error_stream():
            yield f'data: {json.dumps({"error": "请求数据格式错误"})}\n\n'
        return StreamingHttpResponse(error_stream(), content_type='text/event-stream')
    except Exception as e:
        logger.error(f"流式问答初始化失败: {e}")
        def error_stream():
            yield f'data: {json.dumps({"error": str(e)})}\n\n'
        return StreamingHttpResponse(error_stream(), content_type='text/event-stream')


@require_http_methods(["GET"])
def kg_entities_search_api(request, kg_id):
    """搜索知识图谱中的实体"""
    try:
        query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 10))

        if not query:
            return JsonResponse({
                'success': True,
                'entities': []
            })

        # 验证知识图谱
        try:
            kg = KnowledgeGraph.objects.get(id=kg_id)
        except KnowledgeGraph.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '知识图谱不存在'
            })

        # 从Neo4j搜索实体
        from .neo4j_manager import Neo4jManager
        neo4j_manager = Neo4jManager()

        entities = []
        with neo4j_manager.get_session() as session:
            search_query = """
            MATCH (e:Entity {knowledge_graph_id: $kg_id})
            WHERE toLower(e.name) CONTAINS toLower($search_term)
               OR toLower(e.entity_type) CONTAINS toLower($search_term)
            RETURN e.name as name, e.entity_type as type, id(e) as id,
                   e.description as description
            ORDER BY e.name
            LIMIT $limit
            """

            result = session.run(search_query, kg_id=kg_id, search_term=query, limit=limit)
            for record in result:
                entities.append({
                    'id': record['id'],
                    'name': record['name'],
                    'type': record['type'],
                    'description': record.get('description', '')
                })

        return JsonResponse({
            'success': True,
            'entities': entities,
            'total': len(entities)
        })

    except Exception as e:
        logger.error(f"实体搜索失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
