#!/usr/bin/env python
"""
统一文件处理器 - 自动识别文件类型并路由到相应的处理流程
支持结构化数据（CSV、Excel）和非结构化数据（PDF、Word、TXT等）
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from django.core.files.uploadedfile import UploadedFile

from .structured_data_processor import StructuredDataProcessor
from ..kg_construction.kg_builder import KnowledgeGraphBuilder
from ..text_processing.document_parser import DocumentParser

logger = logging.getLogger(__name__)


class UnifiedFileProcessor:
    """统一文件处理器"""
    
    def __init__(self):
        self.structured_processor = StructuredDataProcessor()
        self.kg_builder = KnowledgeGraphBuilder()
        self.document_parser = DocumentParser()
        
        # 定义文件类型映射
        self.structured_formats = {
            # 实体文件格式
            'entity': ['.xlsx', '.xls', '.csv'],
            # 关系文件格式  
            'relation': ['.csv', '.txt']
        }
        
        self.unstructured_formats = [
            '.pdf', '.docx', '.doc', '.txt', '.md', '.rtf', '.odt'
        ]
        
        # 所有支持的格式
        self.all_supported_formats = (
            self.structured_formats['entity'] + 
            self.structured_formats['relation'] + 
            self.unstructured_formats
        )
        
        # 去重
        self.all_supported_formats = list(set(self.all_supported_formats))
    
    def identify_file_type(self, file_path: str, file_content: bytes = None) -> Dict:
        """
        智能识别文件类型

        Args:
            file_path: 文件路径
            file_content: 文件内容（可选）

        Returns:
            Dict: {
                'type': 'structured' | 'unstructured',
                'subtype': 'entity' | 'relation' | 'document',
                'format': 文件扩展名,
                'confidence': 置信度,
                'reason': 判断原因
            }
        """
        try:
            file_ext = Path(file_path).suffix.lower()
            file_name = Path(file_path).name.lower()

            # 基于扩展名的初步判断
            if file_ext in self.structured_formats['entity']:
                # 智能判断是实体文件还是关系文件
                return self._identify_structured_subtype(file_path, file_name, file_ext, file_content)

            elif file_ext in self.unstructured_formats:
                return {
                    'type': 'unstructured',
                    'subtype': 'document',
                    'format': file_ext,
                    'confidence': 0.9,
                    'reason': f'文档格式{file_ext}识别为非结构化数据'
                }

            else:
                return {
                    'type': 'unknown',
                    'subtype': 'unknown',
                    'format': file_ext,
                    'confidence': 0.0,
                    'reason': f'不支持的文件格式: {file_ext}'
                }

        except Exception as e:
            logger.error(f"文件类型识别失败: {e}")
            return {
                'type': 'error',
                'subtype': 'error',
                'format': '',
                'confidence': 0.0,
                'reason': f'识别过程出错: {str(e)}'
            }

    def _identify_structured_subtype(self, file_path: str, file_name: str, file_ext: str, file_content: bytes = None) -> Dict:
        """智能识别结构化数据的子类型"""
        confidence = 0.5
        subtype = 'entity'  # 默认
        reasons = []

        # 1. 基于文件名的关键词识别
        entity_keywords = ['entity', 'entities', '实体', 'node', 'nodes', '节点', 'vertex', 'vertices']
        relation_keywords = ['relation', 'relations', '关系', 'edge', 'edges', '边', 'link', 'links', '连接']

        entity_score = sum(1 for keyword in entity_keywords if keyword in file_name)
        relation_score = sum(1 for keyword in relation_keywords if keyword in file_name)

        if entity_score > relation_score:
            subtype = 'entity'
            confidence += 0.3
            reasons.append(f'文件名包含实体关键词({entity_score}个)')
        elif relation_score > entity_score:
            subtype = 'relation'
            confidence += 0.3
            reasons.append(f'文件名包含关系关键词({relation_score}个)')

        # 2. 基于文件扩展名的默认规则
        if file_ext == '.csv':
            if subtype == 'entity':
                confidence -= 0.1  # CSV更可能是关系文件
                reasons.append('CSV文件通常用于关系数据')
            else:
                confidence += 0.1
                reasons.append('CSV文件适合关系数据')
        elif file_ext in ['.xlsx', '.xls']:
            if subtype == 'entity':
                confidence += 0.1
                reasons.append('Excel文件适合实体数据')
            else:
                confidence -= 0.1
                reasons.append('Excel文件通常用于实体数据')

        # 3. 基于文件内容的智能分析（如果提供了内容）
        if file_content or os.path.exists(file_path):
            try:
                content_analysis = self._analyze_file_content(file_path, file_ext)
                if content_analysis:
                    if content_analysis['likely_type'] == 'entity':
                        if subtype == 'entity':
                            confidence += 0.2
                        else:
                            confidence -= 0.1
                        reasons.append(f"内容分析: {content_analysis['reason']}")
                    elif content_analysis['likely_type'] == 'relation':
                        if subtype == 'relation':
                            confidence += 0.2
                        else:
                            confidence -= 0.1
                        reasons.append(f"内容分析: {content_analysis['reason']}")
            except Exception as e:
                logger.warning(f"内容分析失败: {e}")

        # 4. 如果没有明确指示，使用默认规则
        if confidence < 0.7:
            if file_ext == '.csv':
                subtype = 'relation'
                confidence = 0.6
                reasons.append('CSV文件默认识别为关系文件')
            else:
                subtype = 'entity'
                confidence = 0.6
                reasons.append('Excel文件默认识别为实体文件')

        # 确保置信度在合理范围内
        confidence = min(max(confidence, 0.1), 0.95)

        return {
            'type': 'structured',
            'subtype': subtype,
            'format': file_ext,
            'confidence': confidence,
            'reason': '; '.join(reasons)
        }

    def _analyze_file_content(self, file_path: str, file_ext: str) -> Dict:
        """分析文件内容以判断类型"""
        try:
            import pandas as pd

            # 读取文件的前几行进行分析
            if file_ext == '.csv':
                df = pd.read_csv(file_path, nrows=5, encoding='utf-8')
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path, nrows=5)
            else:
                return None

            if len(df.columns) < 2:
                return None

            # 分析列数和列名
            col_count = len(df.columns)
            col_names = [str(col).lower() for col in df.columns]

            # 实体文件通常有2列：实体名和类型
            # 关系文件通常有3-4列：源实体、关系、目标实体、(文本)
            if col_count == 2:
                return {
                    'likely_type': 'entity',
                    'reason': f'2列数据，可能是实体-类型格式',
                    'confidence': 0.7
                }
            elif col_count >= 3:
                # 检查是否有关系相关的列名
                relation_indicators = ['relation', '关系', 'edge', 'link', 'source', 'target', '源', '目标']
                relation_score = sum(1 for indicator in relation_indicators
                                   for col in col_names if indicator in col)

                if relation_score > 0:
                    return {
                        'likely_type': 'relation',
                        'reason': f'{col_count}列数据，包含关系相关列名',
                        'confidence': 0.8
                    }
                else:
                    return {
                        'likely_type': 'relation',
                        'reason': f'{col_count}列数据，符合关系文件格式',
                        'confidence': 0.6
                    }

            return None

        except Exception as e:
            logger.warning(f"文件内容分析失败: {e}")
            return None
    
    def validate_file(self, file_path: str, expected_type: str = None) -> Dict:
        """
        验证文件格式和内容
        
        Args:
            file_path: 文件路径
            expected_type: 期望的文件类型 ('entity', 'relation', 'document')
            
        Returns:
            验证结果
        """
        try:
            file_type_info = self.identify_file_type(file_path)
            
            if file_type_info['type'] == 'error':
                return {
                    'valid': False,
                    'message': file_type_info['reason'],
                    'file_type': file_type_info
                }
            
            if file_type_info['type'] == 'unknown':
                return {
                    'valid': False,
                    'message': f"不支持的文件格式: {file_type_info['format']}",
                    'file_type': file_type_info
                }
            
            # 如果指定了期望类型，检查是否匹配
            if expected_type and file_type_info['subtype'] != expected_type:
                return {
                    'valid': False,
                    'message': f"文件类型不匹配，期望: {expected_type}, 实际: {file_type_info['subtype']}",
                    'file_type': file_type_info
                }
            
            # 根据文件类型进行具体验证
            if file_type_info['type'] == 'structured':
                if file_type_info['subtype'] == 'entity':
                    validation_result = self.structured_processor.validate_entity_file(file_path)
                elif file_type_info['subtype'] == 'relation':
                    validation_result = self.structured_processor.validate_relation_file(file_path)
                else:
                    validation_result = {'valid': False, 'message': '未知的结构化数据类型'}
            
            elif file_type_info['type'] == 'unstructured':
                # 使用文档解析器验证
                validation_result = self._validate_document_file(file_path)
            
            else:
                validation_result = {'valid': False, 'message': '未知的文件类型'}
            
            # 添加文件类型信息
            validation_result['file_type'] = file_type_info
            return validation_result
            
        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return {
                'valid': False,
                'message': f'验证过程出错: {str(e)}',
                'file_type': {'type': 'error', 'subtype': 'error'}
            }
    
    def _validate_document_file(self, file_path: str) -> Dict:
        """验证文档文件"""
        try:
            # 检查文件是否存在和可读
            if not os.path.exists(file_path):
                return {'valid': False, 'message': '文件不存在'}
            
            if not os.access(file_path, os.R_OK):
                return {'valid': False, 'message': '文件不可读'}
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {'valid': False, 'message': '文件为空'}
            
            if file_size > 50 * 1024 * 1024:  # 50MB
                return {'valid': False, 'message': '文件过大（超过50MB）'}
            
            # 尝试解析文档
            try:
                parse_result = self.document_parser.parse_document(file_path)
                if not parse_result.get('success', False):
                    return {'valid': False, 'message': f"文档解析失败: {parse_result.get('error', '未知错误')}"}
                
                text_content = parse_result.get('text', '')
                if len(text_content.strip()) < 10:
                    return {'valid': False, 'message': '文档内容过少'}
                
                return {
                    'valid': True,
                    'message': '文档验证通过',
                    'file_size': file_size,
                    'text_length': len(text_content),
                    'preview': text_content[:200] + '...' if len(text_content) > 200 else text_content
                }
                
            except Exception as parse_error:
                return {'valid': False, 'message': f'文档解析错误: {str(parse_error)}'}
            
        except Exception as e:
            return {'valid': False, 'message': f'验证过程出错: {str(e)}'}
    
    def process_file(self, file_path: str, knowledge_graph_id: int, user_id: int, 
                    options: Dict = None, file_type_hint: str = None) -> Dict:
        """
        处理文件并构建知识图谱
        
        Args:
            file_path: 文件路径
            knowledge_graph_id: 知识图谱ID
            user_id: 用户ID
            options: 处理选项
            file_type_hint: 文件类型提示 ('entity', 'relation', 'document')
            
        Returns:
            处理结果
        """
        try:
            # 验证文件
            validation_result = self.validate_file(file_path, file_type_hint)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['message'],
                    'file_type': validation_result.get('file_type')
                }
            
            file_type_info = validation_result['file_type']
            options = options or {}
            
            # 根据文件类型选择处理方式
            if file_type_info['type'] == 'structured':
                return self._process_structured_file(
                    file_path, knowledge_graph_id, user_id, file_type_info, options
                )
            
            elif file_type_info['type'] == 'unstructured':
                return self._process_unstructured_file(
                    file_path, knowledge_graph_id, user_id, options
                )
            
            else:
                return {
                    'success': False,
                    'error': f"不支持的文件类型: {file_type_info['type']}",
                    'file_type': file_type_info
                }
                
        except Exception as e:
            logger.error(f"文件处理失败: {e}")
            return {
                'success': False,
                'error': f'处理过程出错: {str(e)}'
            }
    
    def _process_structured_file(self, file_path: str, knowledge_graph_id: int, 
                               user_id: int, file_type_info: Dict, options: Dict) -> Dict:
        """处理结构化文件"""
        # 这里需要调用结构化知识图谱构建器
        # 由于当前的结构化构建器需要同时提供实体和关系文件，
        # 这里返回解析结果，让调用者决定如何处理
        try:
            if file_type_info['subtype'] == 'entity':
                entities = self.structured_processor.process_entity_file(file_path)
                return {
                    'success': True,
                    'type': 'structured',
                    'subtype': 'entity',
                    'data': entities,
                    'count': len(entities),
                    'message': f'成功解析 {len(entities)} 个实体'
                }
            
            elif file_type_info['subtype'] == 'relation':
                relations = self.structured_processor.process_relation_file(file_path)
                return {
                    'success': True,
                    'type': 'structured',
                    'subtype': 'relation', 
                    'data': relations,
                    'count': len(relations),
                    'message': f'成功解析 {len(relations)} 个关系'
                }
            
            else:
                return {
                    'success': False,
                    'error': f"未知的结构化数据子类型: {file_type_info['subtype']}"
                }
                
        except Exception as e:
            logger.error(f"结构化文件处理失败: {e}")
            return {
                'success': False,
                'error': f'结构化文件处理失败: {str(e)}'
            }
    
    def _process_unstructured_file(self, file_path: str, knowledge_graph_id: int, 
                                 user_id: int, options: Dict) -> Dict:
        """处理非结构化文件"""
        try:
            # 调用知识图谱构建器
            result = self.kg_builder.build_from_document(
                file_path, knowledge_graph_id, user_id, options
            )
            return result
            
        except Exception as e:
            logger.error(f"非结构化文件处理失败: {e}")
            return {
                'success': False,
                'error': f'非结构化文件处理失败: {str(e)}'
            }
    
    def get_supported_formats(self) -> Dict:
        """获取支持的文件格式"""
        return {
            'structured': {
                'entity': self.structured_formats['entity'],
                'relation': self.structured_formats['relation']
            },
            'unstructured': self.unstructured_formats,
            'all': self.all_supported_formats
        }
