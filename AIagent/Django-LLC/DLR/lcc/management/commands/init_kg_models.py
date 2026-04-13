"""
初始化知识图谱数据模型 (已完全禁用)
"""

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = '此命令已被完全禁用'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.ERROR('此命令已被完全禁用，请手动创建所需的类型')
        )
        self.stdout.write('使用Django Admin或API接口创建实体类型和关系类型')
