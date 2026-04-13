from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import bcrypt


class User(AbstractUser):
    """扩展用户模型"""
    email = models.EmailField(unique=True, verbose_name="邮箱")
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name="手机号")
    avatar = models.URLField(blank=True, null=True, verbose_name="头像")
    nickname = models.CharField(max_length=50, blank=True, null=True, verbose_name="昵称")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    last_login_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name="最后登录IP")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")

    # 聊天相关字段
    total_conversations = models.IntegerField(default=0, verbose_name="总对话数")
    total_messages = models.IntegerField(default=0, verbose_name="总消息数")
    preferred_model = models.CharField(max_length=50, default="deepseek-r1", verbose_name="偏好模型")

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'lcc_users'  # 添加应用前缀避免与MySQL保留字冲突
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def set_password(self, raw_password):
        """使用bcrypt加密密码"""
        if raw_password:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(raw_password.encode('utf-8'), salt)
            self.password = hashed.decode('utf-8')

    def check_password(self, raw_password):
        """验证密码"""
        if not raw_password or not self.password:
            return False
        return bcrypt.checkpw(raw_password.encode('utf-8'), self.password.encode('utf-8'))

    def get_display_name(self):
        """获取显示名称"""
        return self.nickname or self.username

    def increment_message_count(self):
        """增加消息计数"""
        self.total_messages += 1
        self.save(update_fields=['total_messages'])


class Conversation(models.Model):
    """对话记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    title = models.CharField(max_length=200, verbose_name="对话标题")
    model_name = models.CharField(max_length=50, verbose_name="使用的模型")
    conversation_type = models.CharField(max_length=20, default='llm', verbose_name="对话类型")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    message_count = models.IntegerField(default=0, verbose_name="消息数量")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")

    class Meta:
        db_table = 'lcc_conversations'
        verbose_name = "对话"
        verbose_name_plural = "对话"
        ordering = ['-updated_at']


class Message(models.Model):
    """消息记录"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', 'AI助手'),
        ('system', '系统'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, verbose_name="对话")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name="角色")
    content = models.TextField(verbose_name="消息内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    token_count = models.IntegerField(default=0, verbose_name="Token数量")
    generation_time = models.FloatField(default=0, verbose_name="生成时间(秒)")

    class Meta:
        db_table = 'lcc_messages'
        verbose_name = "消息"
        verbose_name_plural = "消息"
        ordering = ['created_at']


# ==================== 知识图谱相关模型 ====================

class KnowledgeGraph(models.Model):
    """知识图谱"""
    DOMAIN_CHOICES = [
        ('general', '通用领域'),
        ('technology', '科技领域'),
        ('medical', '医学领域'),
        ('legal', '法律领域'),
        ('finance', '金融领域'),
        ('education', '教育领域'),
        ('business', '商业领域'),
        ('science', '科学领域'),
        ('culture', '文化领域'),
        ('sports', '体育领域'),
    ]

    STATUS_CHOICES = [
        ('creating', '创建中'),
        ('active', '活跃'),
        ('inactive', '非活跃'),
        ('error', '错误'),
        ('archived', '已归档'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="图谱名称")
    description = models.TextField(blank=True, verbose_name="图谱描述")
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES, default='general', verbose_name="应用领域")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='creating', verbose_name="状态")

    # 统计信息
    entity_count = models.IntegerField(default=0, verbose_name="实体数量")
    relation_count = models.IntegerField(default=0, verbose_name="关系数量")
    document_count = models.IntegerField(default=0, verbose_name="文档数量")

    # 配置信息
    neo4j_database = models.CharField(max_length=50, default='neo4j', verbose_name="Neo4j数据库名")
    entity_confidence_threshold = models.FloatField(default=0.7, verbose_name="实体置信度阈值")
    relation_confidence_threshold = models.FloatField(default=0.6, verbose_name="关系置信度阈值")

    # 元数据
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    last_processed_at = models.DateTimeField(null=True, blank=True, verbose_name="最后处理时间")

    # 扩展配置
    config = models.JSONField(default=dict, verbose_name="扩展配置")

    class Meta:
        db_table = 'lcc_knowledge_graphs'
        verbose_name = "知识图谱"
        verbose_name_plural = "知识图谱"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.domain})"

    def update_statistics(self):
        """更新知识图谱的统计信息"""
        from django.db import models

        # 重新计算实体数量
        self.entity_count = self.entityrecord_set.count()

        # 重新计算关系数量
        self.relation_count = self.relationrecord_set.count()

        # 重新计算文档数量
        self.document_count = self.documentsource_set.count()

        # 保存更新
        self.save(update_fields=['entity_count', 'relation_count', 'document_count', 'updated_at'])

        return {
            'entity_count': self.entity_count,
            'relation_count': self.relation_count,
            'document_count': self.document_count
        }


class DocumentSource(models.Model):
    """文档来源"""
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF文档'),
        ('docx', 'Word文档'),
        ('doc', 'Word文档(旧版)'),
        ('txt', '文本文档'),
        ('html', 'HTML文档'),
        ('md', 'Markdown文档'),
        ('xlsx', 'Excel文档'),
        ('pptx', 'PowerPoint文档'),
    ]

    PROCESSING_STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '处理失败'),
        ('skipped', '已跳过'),
    ]

    knowledge_graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, verbose_name="所属图谱")

    # 文件信息
    title = models.CharField(max_length=255, verbose_name="文档标题")
    file_name = models.CharField(max_length=255, verbose_name="文件名")
    file_path = models.CharField(max_length=500, unique=True, verbose_name="文件路径")
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, verbose_name="文件类型")
    file_size = models.BigIntegerField(verbose_name="文件大小(字节)")
    file_hash = models.CharField(max_length=64, verbose_name="文件哈希值")

    # 内容信息
    content = models.TextField(blank=True, verbose_name="文档内容")
    summary = models.TextField(blank=True, verbose_name="文档摘要")
    language = models.CharField(max_length=10, default='zh', verbose_name="语言")
    author = models.CharField(max_length=100, blank=True, verbose_name="作者")
    publish_date = models.DateField(null=True, blank=True, verbose_name="发布日期")

    # 处理状态
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='pending', verbose_name="处理状态")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="处理时间")
    processing_time = models.FloatField(default=0, verbose_name="处理耗时(秒)")
    error_message = models.TextField(blank=True, verbose_name="错误信息")

    # 提取统计
    entity_extracted = models.IntegerField(default=0, verbose_name="提取实体数")
    relation_extracted = models.IntegerField(default=0, verbose_name="提取关系数")

    # 元数据
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="上传者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    # 扩展信息
    metadata = models.JSONField(default=dict, verbose_name="扩展元数据")

    class Meta:
        db_table = 'lcc_document_sources'
        verbose_name = "文档来源"
        verbose_name_plural = "文档来源"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.file_type})"


class EntityType(models.Model):
    """实体类型定义"""
    CATEGORY_CHOICES = [
        ('basic', '基础类型'),
        ('domain', '领域类型'),
        ('custom', '自定义类型'),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name="类型名称")
    label = models.CharField(max_length=100, verbose_name="显示标签")
    description = models.TextField(blank=True, verbose_name="类型描述")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='basic', verbose_name="类型分类")
    color = models.CharField(max_length=7, default='#cccccc', verbose_name="显示颜色")
    icon = models.CharField(max_length=50, blank=True, verbose_name="图标")

    # 配置信息
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    extraction_patterns = models.JSONField(default=list, verbose_name="提取模式")
    validation_rules = models.JSONField(default=dict, verbose_name="验证规则")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'lcc_entity_types'
        verbose_name = "实体类型"
        verbose_name_plural = "实体类型"
        ordering = ['category', 'name']

    def __str__(self):
        return self.label


class RelationType(models.Model):
    """关系类型定义"""
    CATEGORY_CHOICES = [
        ('basic', '基础关系'),
        ('semantic', '语义关系'),
        ('temporal', '时间关系'),
        ('spatial', '空间关系'),
        ('social', '社会关系'),
        ('domain', '领域关系'),
        ('custom', '自定义关系'),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name="关系名称")
    label = models.CharField(max_length=100, verbose_name="显示标签")
    description = models.TextField(blank=True, verbose_name="关系描述")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='basic', verbose_name="关系分类")

    # 关系约束
    source_types = models.ManyToManyField(EntityType, related_name='source_relations', blank=True, verbose_name="源实体类型")
    target_types = models.ManyToManyField(EntityType, related_name='target_relations', blank=True, verbose_name="目标实体类型")
    is_symmetric = models.BooleanField(default=False, verbose_name="是否对称关系")
    is_transitive = models.BooleanField(default=False, verbose_name="是否传递关系")

    # 配置信息
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    extraction_patterns = models.JSONField(default=list, verbose_name="提取模式")
    validation_rules = models.JSONField(default=dict, verbose_name="验证规则")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'lcc_relation_types'
        verbose_name = "关系类型"
        verbose_name_plural = "关系类型"
        ordering = ['category', 'name']

    def __str__(self):
        return self.label


class EntityRecord(models.Model):
    """实体记录（Django中的实体元数据）"""
    knowledge_graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, verbose_name="所属图谱")
    entity_type = models.ForeignKey(EntityType, on_delete=models.CASCADE, verbose_name="实体类型")

    # 基础信息
    neo4j_id = models.CharField(max_length=100, verbose_name="Neo4j节点ID")
    name = models.CharField(max_length=200, verbose_name="实体名称")
    description = models.TextField(blank=True, verbose_name="实体描述")
    confidence = models.FloatField(verbose_name="置信度")

    # 来源信息
    source_document = models.ForeignKey(DocumentSource, on_delete=models.CASCADE, null=True, blank=True, verbose_name="来源文档")
    source_text = models.TextField(blank=True, verbose_name="来源文本")
    extraction_method = models.CharField(max_length=50, verbose_name="提取方法")

    # 状态信息
    is_verified = models.BooleanField(default=False, verbose_name="是否已验证")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")

    # 元数据
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="验证者")

    # 扩展属性
    properties = models.JSONField(default=dict, verbose_name="扩展属性")

    class Meta:
        db_table = 'lcc_entity_records'
        verbose_name = "实体记录"
        verbose_name_plural = "实体记录"
        unique_together = ['knowledge_graph', 'neo4j_id']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.entity_type.label})"


class RelationRecord(models.Model):
    """关系记录（Django中的关系元数据）"""
    knowledge_graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, verbose_name="所属图谱")
    relation_type = models.ForeignKey(RelationType, on_delete=models.CASCADE, verbose_name="关系类型")

    # 关系信息
    neo4j_id = models.CharField(max_length=100, verbose_name="Neo4j关系ID")
    source_entity = models.ForeignKey(EntityRecord, on_delete=models.CASCADE, related_name='source_relations', verbose_name="源实体")
    target_entity = models.ForeignKey(EntityRecord, on_delete=models.CASCADE, related_name='target_relations', verbose_name="目标实体")
    confidence = models.FloatField(verbose_name="置信度")

    # 来源信息
    source_document = models.ForeignKey(DocumentSource, on_delete=models.CASCADE, null=True, blank=True, verbose_name="来源文档")
    source_text = models.TextField(blank=True, verbose_name="来源文本")
    extraction_method = models.CharField(max_length=50, verbose_name="提取方法")

    # 状态信息
    is_verified = models.BooleanField(default=False, verbose_name="是否已验证")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")

    # 元数据
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="验证者")

    # 扩展属性
    properties = models.JSONField(default=dict, verbose_name="扩展属性")

    class Meta:
        db_table = 'lcc_relation_records'
        verbose_name = "关系记录"
        verbose_name_plural = "关系记录"
        unique_together = ['knowledge_graph', 'neo4j_id']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.source_entity.name} -> {self.relation_type.label} -> {self.target_entity.name}"


class ProcessingTask(models.Model):
    """处理任务"""
    TASK_TYPE_CHOICES = [
        ('document_upload', '文档上传'),
        ('entity_extraction', '实体提取'),
        ('relation_extraction', '关系提取'),
        ('graph_construction', '图谱构建'),
        ('graph_update', '图谱更新'),
        ('graph_merge', '图谱合并'),
        ('data_import', '数据导入'),
        ('data_export', '数据导出'),
    ]

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]

    knowledge_graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, verbose_name="所属图谱")

    # 任务信息
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="任务类型")
    task_name = models.CharField(max_length=200, verbose_name="任务名称")
    description = models.TextField(blank=True, verbose_name="任务描述")

    # 状态信息
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="任务状态")
    progress = models.IntegerField(default=0, verbose_name="进度百分比")

    # 执行信息
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    execution_time = models.FloatField(default=0, verbose_name="执行时间(秒)")

    # 结果信息
    result_summary = models.TextField(blank=True, verbose_name="结果摘要")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    entities_processed = models.IntegerField(default=0, verbose_name="处理实体数")
    relations_processed = models.IntegerField(default=0, verbose_name="处理关系数")

    # 元数据
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="创建者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    # 配置和结果
    config = models.JSONField(default=dict, verbose_name="任务配置")
    result_data = models.JSONField(default=dict, verbose_name="结果数据")

    class Meta:
        db_table = 'lcc_processing_tasks'
        verbose_name = "处理任务"
        verbose_name_plural = "处理任务"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task_name} ({self.status})"


class QueryHistory(models.Model):
    """查询历史"""
    QUERY_TYPE_CHOICES = [
        ('entity_search', '实体搜索'),
        ('relation_query', '关系查询'),
        ('path_finding', '路径查找'),
        ('graph_analysis', '图分析'),
        ('qa_query', '问答查询'),
        ('cypher_query', 'Cypher查询'),
    ]

    knowledge_graph = models.ForeignKey(KnowledgeGraph, on_delete=models.CASCADE, verbose_name="所属图谱")

    # 查询信息
    query_type = models.CharField(max_length=20, choices=QUERY_TYPE_CHOICES, verbose_name="查询类型")
    query_text = models.TextField(verbose_name="查询文本")
    cypher_query = models.TextField(blank=True, verbose_name="Cypher查询")

    # 结果信息
    result_count = models.IntegerField(default=0, verbose_name="结果数量")
    execution_time = models.FloatField(default=0, verbose_name="执行时间(毫秒)")
    is_successful = models.BooleanField(default=True, verbose_name="是否成功")
    error_message = models.TextField(blank=True, verbose_name="错误信息")

    # 元数据
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="查询用户")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="查询时间")

    # 查询参数和结果
    query_params = models.JSONField(default=dict, verbose_name="查询参数")
    result_data = models.JSONField(default=dict, verbose_name="结果数据")

    class Meta:
        db_table = 'lcc_query_history'
        verbose_name = "查询历史"
        verbose_name_plural = "查询历史"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.query_type} - {self.query_text[:50]}..."


class UserSession(models.Model):
    """用户会话记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    session_key = models.CharField(max_length=40, unique=True, verbose_name="会话Key")
    ip_address = models.GenericIPAddressField(verbose_name="IP地址")
    user_agent = models.TextField(verbose_name="用户代理")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="最后活动时间")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")

    class Meta:
        db_table = 'lcc_user_sessions'
        verbose_name = "用户会话"
        verbose_name_plural = "用户会话"
