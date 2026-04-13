#!/usr/bin/env python
"""
类型配置管理器 - 管理实体和关系类型的配置
"""

import json
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


class TypeConfigManager:
    """类型配置管理器"""
    
    def __init__(self):
        self.config_dir = Path(settings.BASE_DIR) / 'lcc' / 'kg_construction' / 'type_configs'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认类型配置
        self.default_entity_types = [
            'PERSON',      # 人物
            'ORGANIZATION', # 组织机构
            'LOCATION',    # 地点
            'CONCEPT',     # 概念
            'EVENT',       # 事件
            'TIME',        # 时间
            'PRODUCT',     # 产品
            'TECHNOLOGY',  # 技术
            'FIELD',       # 领域
            'METHOD'       # 方法
        ]
        
        self.default_relation_types = [
            'IS_A',        # 是一个
            'PART_OF',     # 属于
            'LOCATED_IN',  # 位于
            'WORKS_FOR',   # 工作于
            'RELATED_TO',  # 相关
            'CAUSES',      # 导致
            'USES',        # 使用
            'CREATES',     # 创建
            'INCLUDES',    # 包含
            'DEPENDS_ON'   # 依赖于
        ]
        
        # 中英文类型映射
        self.chinese_entity_mapping = {
            '人物': 'PERSON',
            '人': 'PERSON',
            '组织': 'ORGANIZATION',
            '机构': 'ORGANIZATION',
            '公司': 'ORGANIZATION',
            '地点': 'LOCATION',
            '地方': 'LOCATION',
            '概念': 'CONCEPT',
            '事件': 'EVENT',
            '时间': 'TIME',
            '产品': 'PRODUCT',
            '技术': 'TECHNOLOGY',
            '领域': 'FIELD',
            '方法': 'METHOD'
        }
        
        self.chinese_relation_mapping = {
            '是': 'IS_A',
            '属于': 'PART_OF',
            '位于': 'LOCATED_IN',
            '工作于': 'WORKS_FOR',
            '相关': 'RELATED_TO',
            '导致': 'CAUSES',
            '使用': 'USES',
            '创建': 'CREATES',
            '包含': 'INCLUDES',
            '依赖': 'DEPENDS_ON'
        }
    
    def get_default_entity_types(self) -> List[str]:
        """获取默认实体类型"""
        return self.default_entity_types.copy()
    
    def get_default_relation_types(self) -> List[str]:
        """获取默认关系类型"""
        return self.default_relation_types.copy()
    
    def get_chinese_mappings(self) -> Dict[str, Dict[str, str]]:
        """获取中英文映射"""
        return {
            'entity': self.chinese_entity_mapping.copy(),
            'relation': self.chinese_relation_mapping.copy()
        }
    
    def save_custom_config(self, config_name: str, entity_types: List[str] = None,
                          relation_types: List[str] = None, 
                          type_mapping: Dict[str, str] = None,
                          description: str = "") -> bool:
        """
        保存自定义配置
        
        Args:
            config_name: 配置名称
            entity_types: 实体类型列表
            relation_types: 关系类型列表
            type_mapping: 类型映射
            description: 配置描述
            
        Returns:
            是否保存成功
        """
        try:
            config = {
                'name': config_name,
                'description': description,
                'entity_types': entity_types or [],
                'relation_types': relation_types or [],
                'type_mapping': type_mapping or {},
                'created_at': str(Path().cwd()),  # 简单的时间戳替代
                'version': '1.0'
            }
            
            config_file = self.config_dir / f"{config_name}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已保存: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def load_custom_config(self, config_name: str) -> Optional[Dict]:
        """
        加载自定义配置
        
        Args:
            config_name: 配置名称
            
        Returns:
            配置字典或None
        """
        try:
            config_file = self.config_dir / f"{config_name}.json"
            if not config_file.exists():
                logger.warning(f"配置文件不存在: {config_file}")
                return None
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"配置已加载: {config_name}")
            return config
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return None
    
    def list_custom_configs(self) -> List[Dict]:
        """列出所有自定义配置"""
        try:
            configs = []
            for config_file in self.config_dir.glob("*.json"):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    configs.append({
                        'name': config.get('name', config_file.stem),
                        'description': config.get('description', ''),
                        'entity_count': len(config.get('entity_types', [])),
                        'relation_count': len(config.get('relation_types', [])),
                        'file_path': str(config_file)
                    })
                except Exception as e:
                    logger.warning(f"读取配置文件失败 {config_file}: {e}")
            
            return configs
            
        except Exception as e:
            logger.error(f"列出配置失败: {e}")
            return []
    
    def delete_custom_config(self, config_name: str) -> bool:
        """删除自定义配置"""
        try:
            config_file = self.config_dir / f"{config_name}.json"
            if config_file.exists():
                config_file.unlink()
                logger.info(f"配置已删除: {config_name}")
                return True
            else:
                logger.warning(f"配置文件不存在: {config_name}")
                return False
                
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return False
    
    def create_domain_config(self, domain: str) -> Dict:
        """
        为特定领域创建配置
        
        Args:
            domain: 领域名称 ('medical', 'legal', 'technology', 'business', etc.)
            
        Returns:
            领域配置
        """
        domain_configs = {
            'medical': {
                'entity_types': [
                    'DISEASE', 'SYMPTOM', 'TREATMENT', 'MEDICINE', 'DOCTOR',
                    'HOSPITAL', 'PATIENT', 'BODY_PART', 'MEDICAL_DEVICE'
                ],
                'relation_types': [
                    'TREATS', 'CAUSES', 'PREVENTS', 'DIAGNOSED_WITH',
                    'PRESCRIBED_FOR', 'LOCATED_IN', 'WORKS_AT'
                ]
            },
            'legal': {
                'entity_types': [
                    'LAW', 'CASE', 'COURT', 'JUDGE', 'LAWYER', 'DEFENDANT',
                    'PLAINTIFF', 'CONTRACT', 'REGULATION'
                ],
                'relation_types': [
                    'GOVERNS', 'VIOLATES', 'REPRESENTS', 'JUDGES',
                    'APPEALS', 'CITES', 'OVERRULES'
                ]
            },
            'technology': {
                'entity_types': [
                    'SOFTWARE', 'HARDWARE', 'ALGORITHM', 'PROTOCOL',
                    'LANGUAGE', 'FRAMEWORK', 'DATABASE', 'API'
                ],
                'relation_types': [
                    'IMPLEMENTS', 'USES', 'EXTENDS', 'DEPENDS_ON',
                    'COMMUNICATES_WITH', 'STORES', 'PROCESSES'
                ]
            },
            'business': {
                'entity_types': [
                    'COMPANY', 'PRODUCT', 'SERVICE', 'MARKET', 'CUSTOMER',
                    'COMPETITOR', 'STRATEGY', 'REVENUE', 'COST'
                ],
                'relation_types': [
                    'COMPETES_WITH', 'SELLS_TO', 'PARTNERS_WITH',
                    'INVESTS_IN', 'ACQUIRES', 'SUPPLIES'
                ]
            }
        }
        
        if domain in domain_configs:
            config = domain_configs[domain]
            config['name'] = f"{domain}_domain"
            config['description'] = f"{domain.title()} domain configuration"
            return config
        else:
            # 返回通用配置
            return {
                'name': 'general_domain',
                'description': 'General domain configuration',
                'entity_types': self.default_entity_types,
                'relation_types': self.default_relation_types
            }
    
    def merge_configs(self, config_names: List[str]) -> Dict:
        """
        合并多个配置
        
        Args:
            config_names: 配置名称列表
            
        Returns:
            合并后的配置
        """
        try:
            merged_entity_types = set()
            merged_relation_types = set()
            merged_mapping = {}
            descriptions = []
            
            for config_name in config_names:
                config = self.load_custom_config(config_name)
                if config:
                    merged_entity_types.update(config.get('entity_types', []))
                    merged_relation_types.update(config.get('relation_types', []))
                    merged_mapping.update(config.get('type_mapping', {}))
                    if config.get('description'):
                        descriptions.append(config['description'])
            
            return {
                'name': f"merged_{'_'.join(config_names)}",
                'description': f"Merged from: {', '.join(descriptions)}",
                'entity_types': list(merged_entity_types),
                'relation_types': list(merged_relation_types),
                'type_mapping': merged_mapping
            }
            
        except Exception as e:
            logger.error(f"合并配置失败: {e}")
            return {
                'entity_types': self.default_entity_types,
                'relation_types': self.default_relation_types,
                'type_mapping': {}
            }
    
    def validate_config(self, config: Dict) -> Dict:
        """验证配置的有效性"""
        try:
            issues = []
            warnings = []
            
            # 检查必要字段
            if 'entity_types' not in config:
                issues.append("缺少entity_types字段")
            if 'relation_types' not in config:
                issues.append("缺少relation_types字段")
            
            # 检查类型有效性
            entity_types = config.get('entity_types', [])
            relation_types = config.get('relation_types', [])
            
            for entity_type in entity_types:
                if not isinstance(entity_type, str) or not entity_type.strip():
                    issues.append(f"无效的实体类型: {entity_type}")
            
            for relation_type in relation_types:
                if not isinstance(relation_type, str) or not relation_type.strip():
                    issues.append(f"无效的关系类型: {relation_type}")
            
            # 检查重复
            if len(set(entity_types)) != len(entity_types):
                warnings.append("实体类型中存在重复")
            if len(set(relation_types)) != len(relation_types):
                warnings.append("关系类型中存在重复")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'warnings': warnings,
                'message': '配置验证完成' if len(issues) == 0 else f'发现{len(issues)}个问题'
            }
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return {
                'valid': False,
                'issues': [str(e)],
                'warnings': [],
                'message': '验证过程出错'
            }
