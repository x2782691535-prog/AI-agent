"""
知识图谱测试视图
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .neo4j_manager import neo4j_manager
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def test_neo4j_connection(request):
    """测试Neo4j连接"""
    try:
        # 测试连接
        connection_result = neo4j_manager.test_connection()
        
        if connection_result['success']:
            # 获取数据库统计
            stats = neo4j_manager.get_database_stats()
            
            return JsonResponse({
                'success': True,
                'message': connection_result['message'],
                'version': connection_result['version'],
                'stats': stats
            })
        else:
            return JsonResponse({
                'success': False,
                'error': connection_result['error']
            })
            
    except Exception as e:
        logger.error(f"Neo4j连接测试失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["GET"])
def get_test_graph_data(request):
    """获取测试图数据"""
    try:
        with neo4j_manager.get_session() as session:
            # 首先检查是否有测试数据
            check_query = "MATCH (n {source: 'test_data'}) RETURN count(n) as count"
            result = session.run(check_query)
            test_node_count = result.single()['count']

            if test_node_count == 0:
                return JsonResponse({
                    'success': True,
                    'data': {
                        'nodes': [],
                        'edges': []
                    },
                    'message': '没有测试数据'
                })

            # 获取测试数据的节点和关系
            query = """
            MATCH (n {source: 'test_data'})-[r {source: 'test_data'}]->(m {source: 'test_data'})
            RETURN n, r, m
            UNION
            MATCH (n {source: 'test_data'})
            WHERE NOT (n)-[{source: 'test_data'}]-()
            RETURN n, null as r, null as m
            """
            
            result = session.run(query)
            
            nodes = {}
            edges = []
            
            for record in result:
                # 处理起始节点
                start_node = record['n']
                start_id = start_node.element_id
                if start_id not in nodes:
                    # 处理节点属性，转换datetime对象
                    start_properties = {}
                    for key, value in dict(start_node).items():
                        if hasattr(value, 'isoformat'):  # datetime对象
                            start_properties[key] = value.isoformat()
                        else:
                            start_properties[key] = value

                    nodes[start_id] = {
                        'id': start_id,
                        'label': start_node.get('name', 'Unknown'),
                        'type': start_node.get('type', 'Unknown'),
                        'properties': start_properties
                    }

                # 处理结束节点（如果存在）
                end_node = record['m']
                if end_node is not None:
                    end_id = end_node.element_id
                    if end_id not in nodes:
                        # 处理节点属性，转换datetime对象
                        end_properties = {}
                        for key, value in dict(end_node).items():
                            if hasattr(value, 'isoformat'):  # datetime对象
                                end_properties[key] = value.isoformat()
                            else:
                                end_properties[key] = value

                        nodes[end_id] = {
                            'id': end_id,
                            'label': end_node.get('name', 'Unknown'),
                            'type': end_node.get('type', 'Unknown'),
                            'properties': end_properties
                        }

                # 处理关系（如果存在）
                relationship = record['r']
                if relationship is not None:
                    # 处理关系属性，转换datetime对象
                    rel_properties = {}
                    for key, value in dict(relationship).items():
                        if hasattr(value, 'isoformat'):  # datetime对象
                            rel_properties[key] = value.isoformat()
                        else:
                            rel_properties[key] = value

                    edges.append({
                        'from': start_id,
                        'to': end_id,
                        'label': relationship.type,
                        'type': relationship.get('type', relationship.type),
                        'properties': rel_properties
                    })
            
            return JsonResponse({
                'success': True,
                'data': {
                    'nodes': list(nodes.values()),
                    'edges': edges
                }
            })
            
    except Exception as e:
        logger.error(f"获取测试图数据失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["POST"])
@csrf_exempt
def create_test_data(request):
    """创建测试数据"""
    try:
        with neo4j_manager.get_session() as session:
            # 检查是否已有测试数据
            check_query = "MATCH (n {source: 'test_data'}) RETURN count(n) as count"
            result = session.run(check_query)
            existing_count = result.single()['count']
            
            if existing_count > 0:
                return JsonResponse({
                    'success': True,
                    'message': f'测试数据已存在 ({existing_count} 个节点)',
                    'existing_nodes': existing_count
                })
            
            # 创建测试数据的Cypher查询
            create_query = """
            // 创建人物实体
            CREATE (p1:Person:Entity {
                name: '张教授',
                type: 'PERSON',
                domain: 'academic',
                profession: '教授',
                description: '人工智能领域专家',
                created_at: datetime(),
                source: 'test_data'
            })
            
            CREATE (p2:Person:Entity {
                name: '王博士',
                type: 'PERSON',
                domain: 'academic', 
                profession: '研究员',
                description: '机器学习研究员',
                created_at: datetime(),
                source: 'test_data'
            })
            
            // 创建机构实体
            CREATE (o1:Organization:Entity {
                name: '清华大学',
                type: 'ORGANIZATION',
                domain: 'education',
                category: '高等院校',
                description: '中国顶尖理工科大学',
                created_at: datetime(),
                source: 'test_data'
            })
            
            // 创建概念实体
            CREATE (c1:Concept:Entity {
                name: '深度学习',
                type: 'CONCEPT',
                domain: 'technology',
                description: '机器学习的重要分支',
                created_at: datetime(),
                source: 'test_data'
            })
            
            // 创建关系
            CREATE (p1)-[:WORKS_FOR {
                type: 'WORKS_FOR',
                confidence: 0.95,
                created_at: datetime(),
                source: 'test_data'
            }]->(o1)
            
            CREATE (p1)-[:RESEARCHES {
                type: 'RESEARCHES',
                expertise_level: 'expert',
                confidence: 0.90,
                created_at: datetime(),
                source: 'test_data'
            }]->(c1)
            
            CREATE (p2)-[:COLLABORATES_WITH {
                type: 'COLLABORATES_WITH',
                confidence: 0.85,
                created_at: datetime(),
                source: 'test_data'
            }]->(p1)
            
            RETURN count(*) as created_count
            """
            
            result = session.run(create_query)
            created_count = result.single()['created_count']
            
            return JsonResponse({
                'success': True,
                'message': '测试数据创建成功',
                'created_nodes': created_count
            })
            
    except Exception as e:
        logger.error(f"创建测试数据失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_http_methods(["POST"])
@csrf_exempt
def clear_test_data(request):
    """清空测试数据"""
    try:
        with neo4j_manager.get_session() as session:
            # 首先检查有多少测试数据
            check_query = "MATCH (n {source: 'test_data'}) RETURN count(n) as count"
            result = session.run(check_query)
            existing_count = result.single()['count']

            if existing_count == 0:
                return JsonResponse({
                    'success': True,
                    'message': '没有测试数据需要清空',
                    'deleted_nodes': 0,
                    'deleted_relationships': 0
                })

            # 统计关系数量
            rel_count_query = "MATCH ()-[r {source: 'test_data'}]-() RETURN count(r) as count"
            result = session.run(rel_count_query)
            rel_count = result.single()['count']

            # 删除测试数据（DETACH DELETE会同时删除节点和关系）
            delete_query = "MATCH (n {source: 'test_data'}) DETACH DELETE n"
            session.run(delete_query)

            # 验证删除结果
            verify_query = "MATCH (n {source: 'test_data'}) RETURN count(n) as remaining"
            result = session.run(verify_query)
            remaining_count = result.single()['remaining']

            if remaining_count > 0:
                logger.warning(f"清空后仍有 {remaining_count} 个测试节点残留")
                return JsonResponse({
                    'success': False,
                    'error': f'清空不完整，仍有 {remaining_count} 个节点残留'
                })

            return JsonResponse({
                'success': True,
                'message': '测试数据已完全清空',
                'deleted_nodes': existing_count,
                'deleted_relationships': rel_count
            })

    except Exception as e:
        logger.error(f"清空测试数据失败: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
