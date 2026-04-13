from django.urls import path
from .views import home_view, chat_api, your_view, test_stream_view, get_models_api, test_kb_config_view, super_chat_api
from .auth_views import (
    login_page, register_page, login_api, register_api,
    logout_api, user_info_api, update_profile_api
)
from .kb_views import (
    list_knowledge_bases_api, create_knowledge_base_api, delete_knowledge_base_api,
    list_files_api, upload_file_api, delete_file_api, search_docs_api,
    knowledge_base_chat_api, knowledge_base_chat_stream_api
)
from .kg_test_views import test_neo4j_connection, get_test_graph_data, create_test_data, clear_test_data
from .kg_api_views import (
    create_knowledge_graph_api, list_knowledge_graphs_api, upload_document_api,
    process_text_api, get_processing_tasks_api, get_task_status_api,
    get_kg_statistics_api, get_supported_formats_api, validate_document_api,
    get_entity_types_api, create_entity_type_api, delete_entity_type_api,
    get_relation_types_api, create_relation_type_api, delete_relation_type_api,
    clear_knowledge_graph_api, clear_all_knowledge_graphs_api,
    delete_knowledge_graph_api, get_knowledge_graph_data,
    refresh_kg_statistics_api, kg_qa_api, kg_qa_stream_api, kg_entities_search_api
)
# 注意：独立页面视图已删除，功能集成在主页中
from .unified_upload_views import (
    unified_file_upload_api, validate_file_api, get_file_type_info_api,
    get_supported_formats_api, build_structured_kg_from_files_api,
    batch_file_upload_api, sync_kg_statistics_api
)

urlpatterns = [
    # 主页
    path('', home_view, name='home'),

    # 测试页面
    path('test/kb-config/', test_kb_config_view, name='test-kb-config'),

    # 聊天API
    path('api/chat/', chat_api, name='chat-api'),
    path('api/models/', get_models_api, name='get-models'),
    path('api/test-stream/', test_stream_view, name='test-stream'),
    path('api/filtered-chat/', your_view, name='filtered-chat'),

    # 知识库管理API
    path('api/kb/list/', list_knowledge_bases_api, name='list-knowledge-bases'),
    path('api/kb/create/', create_knowledge_base_api, name='create-knowledge-base'),
    path('api/kb/delete/', delete_knowledge_base_api, name='delete-knowledge-base'),
    path('api/kb/files/', list_files_api, name='list-files'),
    path('api/kb/upload/', upload_file_api, name='upload-file'),
    path('api/kb/delete-file/', delete_file_api, name='delete-file'),
    path('api/kb/search/', search_docs_api, name='search-docs'),
    path('api/kb/chat/', knowledge_base_chat_api, name='knowledge-base-chat'),
    path('api/kb/chat/stream/', knowledge_base_chat_stream_api, name='knowledge-base-chat-stream'),

    # Neo4j知识图谱测试API
    path('api/kg/test-connection/', test_neo4j_connection, name='test-neo4j-connection'),
    path('api/kg/test-data/', get_test_graph_data, name='get-test-graph-data'),
    path('api/kg/create-test-data/', create_test_data, name='create-test-data'),
    path('api/kg/clear-test-data/', clear_test_data, name='clear-test-data'),

    # 知识图谱构建API
    path('api/kg/create/', create_knowledge_graph_api, name='create-knowledge-graph'),
    path('api/kg/list/', list_knowledge_graphs_api, name='list-knowledge-graphs'),
    path('api/kg/upload-document/', upload_document_api, name='upload-document'),
    path('api/kg/process-text/', process_text_api, name='process-text'),
    path('api/kg/tasks/', get_processing_tasks_api, name='get-processing-tasks'),
    path('api/kg/task/<int:task_id>/', get_task_status_api, name='get-task-status'),
    path('api/kg/<int:kg_id>/statistics/', get_kg_statistics_api, name='get-kg-statistics'),
    path('api/kg/supported-formats/', get_supported_formats_api, name='get-supported-formats'),
    path('api/kg/validate-document/', validate_document_api, name='validate-document'),

    # 实体类型管理API
    path('api/kg/entity-types/', get_entity_types_api, name='get-entity-types'),
    path('api/kg/entity-types/create/', create_entity_type_api, name='create-entity-type'),
    path('api/kg/entity-types/<int:type_id>/delete/', delete_entity_type_api, name='delete-entity-type'),

    # 关系类型管理API
    path('api/kg/relation-types/', get_relation_types_api, name='get-relation-types'),
    path('api/kg/relation-types/create/', create_relation_type_api, name='create-relation-type'),
    path('api/kg/relation-types/<int:type_id>/delete/', delete_relation_type_api, name='delete-relation-type'),

    # 知识图谱清空和删除API
    path('api/kg/<int:kg_id>/clear/', clear_knowledge_graph_api, name='clear-knowledge-graph'),
    path('api/kg/clear-all/', clear_all_knowledge_graphs_api, name='clear-all-knowledge-graphs'),
    path('api/kg/<int:kg_id>/delete/', delete_knowledge_graph_api, name='delete-knowledge-graph'),

    # 知识图谱可视化API
    path('api/kg/<int:kg_id>/data/', get_knowledge_graph_data, name='get-knowledge-graph-data'),

    # 知识图谱智能问答API
    path('api/kg/<int:kg_id>/qa/', kg_qa_api, name='kg-qa'),
    path('api/kg/<int:kg_id>/qa/stream/', kg_qa_stream_api, name='kg-qa-stream'),
    path('api/kg/<int:kg_id>/entities/search/', kg_entities_search_api, name='kg-entities-search'),

    # 知识图谱统计信息API
    path('api/kg/<int:kg_id>/statistics/', get_kg_statistics_api, name='get-kg-statistics-detail'),
    path('api/kg/refresh-statistics/', refresh_kg_statistics_api, name='refresh-kg-statistics'),

    # 统一文件上传API
    path('api/kg/unified-upload/', unified_file_upload_api, name='unified-file-upload'),
    path('api/kg/validate-file/', validate_file_api, name='validate-file'),
    path('api/kg/file-type-info/', get_file_type_info_api, name='get-file-type-info'),
    path('api/kg/supported-formats/', get_supported_formats_api, name='get-supported-formats-unified'),
    path('api/kg/build-structured/', build_structured_kg_from_files_api, name='build-structured-kg-files'),
    path('api/kg/batch-upload/', batch_file_upload_api, name='batch-file-upload'),
    path('api/kg/sync-statistics/', sync_kg_statistics_api, name='sync-kg-statistics'),

    # 注意：独立的知识图谱页面已删除，所有功能集成在主页中

    # 认证页面
    path('auth/login/', login_page, name='login-page'),
    path('auth/register/', register_page, name='register-page'),

    # 认证API
    path('auth/api/login/', login_api, name='login-api'),
    path('auth/api/register/', register_api, name='register-api'),
    path('auth/api/logout/', logout_api, name='logout-api'),
    path('auth/api/user-info/', user_info_api, name='user-info-api'),
    path('auth/api/update-profile/', update_profile_api, name='update-profile-api'),

    # 超级智能对话API
    path('api/super-chat/', super_chat_api, name='super_chat_api'),
]