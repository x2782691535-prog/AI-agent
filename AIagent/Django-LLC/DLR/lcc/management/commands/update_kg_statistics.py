#!/usr/bin/env python
"""
更新知识图谱统计信息的管理命令
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from lcc.models import KnowledgeGraph
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '更新知识图谱的统计信息（实体数量、关系数量、文档数量）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--kg-id',
            type=int,
            help='指定要更新的知识图谱ID，如果不指定则更新所有知识图谱'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制更新，即使统计信息看起来正确'
        )

    def handle(self, *args, **options):
        kg_id = options.get('kg_id')
        force = options.get('force', False)

        self.stdout.write(
            self.style.SUCCESS('🔄 开始更新知识图谱统计信息...')
        )

        try:
            if kg_id:
                # 更新指定的知识图谱
                try:
                    kg = KnowledgeGraph.objects.get(id=kg_id)
                    self.update_single_kg(kg, force)
                except KnowledgeGraph.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'❌ 知识图谱 ID {kg_id} 不存在')
                    )
                    return
            else:
                # 更新所有知识图谱
                knowledge_graphs = KnowledgeGraph.objects.all()
                total_count = knowledge_graphs.count()
                
                self.stdout.write(f'📊 找到 {total_count} 个知识图谱需要更新')
                
                updated_count = 0
                for i, kg in enumerate(knowledge_graphs, 1):
                    self.stdout.write(f'[{i}/{total_count}] 处理: {kg.name}')
                    
                    if self.update_single_kg(kg, force):
                        updated_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 完成！共更新了 {updated_count} 个知识图谱')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 更新失败: {str(e)}')
            )
            logger.error(f"更新知识图谱统计信息失败: {e}")

    def update_single_kg(self, kg, force=False):
        """更新单个知识图谱的统计信息"""
        try:
            # 获取当前统计信息
            old_stats = {
                'entity_count': kg.entity_count,
                'relation_count': kg.relation_count,
                'document_count': kg.document_count
            }
            
            # 计算实际统计信息
            actual_entity_count = kg.entityrecord_set.count()
            actual_relation_count = kg.relationrecord_set.count()
            actual_document_count = kg.documentsource_set.count()
            
            actual_stats = {
                'entity_count': actual_entity_count,
                'relation_count': actual_relation_count,
                'document_count': actual_document_count
            }
            
            # 检查是否需要更新
            needs_update = (
                force or 
                old_stats['entity_count'] != actual_stats['entity_count'] or
                old_stats['relation_count'] != actual_stats['relation_count'] or
                old_stats['document_count'] != actual_stats['document_count']
            )
            
            if needs_update:
                # 使用事务确保数据一致性
                with transaction.atomic():
                    new_stats = kg.update_statistics()
                
                self.stdout.write(
                    f'  📈 统计信息已更新:'
                )
                self.stdout.write(
                    f'    实体: {old_stats["entity_count"]} → {new_stats["entity_count"]}'
                )
                self.stdout.write(
                    f'    关系: {old_stats["relation_count"]} → {new_stats["relation_count"]}'
                )
                self.stdout.write(
                    f'    文档: {old_stats["document_count"]} → {new_stats["document_count"]}'
                )
                
                return True
            else:
                self.stdout.write('  ✅ 统计信息已是最新，无需更新')
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ 更新失败: {str(e)}')
            )
            logger.error(f"更新知识图谱 {kg.name} 统计信息失败: {e}")
            return False
