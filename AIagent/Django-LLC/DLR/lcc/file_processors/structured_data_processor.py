#!/usr/bin/env python
"""
结构化数据处理器 - 处理Excel实体文件和CSV关系文件
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import uuid
import re
import unicodedata
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class StructuredDataProcessor:
    """结构化数据处理器"""

    def __init__(self):
        self.supported_entity_formats = ['.xlsx', '.xls', '.csv', '.txt']
        self.supported_relation_formats = ['.csv', '.txt', '.tsv']
        self.supported_formats = list(set(self.supported_entity_formats + self.supported_relation_formats))

        # 数据验证规则
        self.validation_rules = {
            'entity': {
                'min_columns': 2,
                'max_columns': 10,
                'required_columns': ['name', 'type'],  # 可选的标准列名
                'min_rows': 1
            },
            'relation': {
                'min_columns': 3,
                'max_columns': 10,
                'required_columns': ['source', 'relation', 'target'],  # 可选的标准列名
                'min_rows': 1
            }
        }

    def normalize_entity_name(self, name: str) -> str:
        """
        标准化实体名称，处理空格、特殊字符等差异

        Args:
            name: 原始实体名称

        Returns:
            标准化后的实体名称
        """
        if not name or pd.isna(name):
            return ""

        # 转换为字符串并去除首尾空格
        name = str(name).strip()

        # 如果是空字符串，直接返回
        if not name:
            return ""

        # 1. 统一Unicode标准化（处理不同编码的相同字符）
        name = unicodedata.normalize('NFKC', name)

        # 2. 去除多余的空格（将多个连续空格替换为单个空格）
        name = re.sub(r'\s+', ' ', name)

        # 3. 标准化数字前后的空格
        # 处理数字与中文/英文之间的空格，统一为无空格
        # 例如："方式 1 译码" -> "方式1译码", "P 1 口" -> "P1口"
        name = re.sub(r'(\w)\s+(\d)', r'\1\2', name)  # 字母/中文 + 空格 + 数字
        name = re.sub(r'(\d)\s+(\w)', r'\1\2', name)  # 数字 + 空格 + 字母/中文

        # 4. 标准化中文词汇之间的空格（去除中文字符间的空格）
        # 例如："译码 显示 命令" -> "译码显示命令"
        name = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', name)

        # 5. 标准化标点符号前后的空格
        # 去除常见标点符号前后的空格
        name = re.sub(r'\s*([，。、；：！？（）【】《》""''/\\-])\s*', r'\1', name)
        # 特别处理斜杠
        name = re.sub(r'\s*/\s*', '/', name)

        # 6. 再次处理中文词汇间的空格（递归处理多个空格的情况）
        # 重复处理直到没有中文间空格
        while re.search(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', name):
            name = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', name)

        # 7. 标准化特殊符号
        # 统一破折号和连字符
        name = re.sub(r'[—–−]', '-', name)

        # 8. 处理全角半角字符统一
        # 全角数字转半角
        name = re.sub(r'[０-９]', lambda m: chr(ord(m.group()) - ord('０') + ord('0')), name)
        # 全角字母转半角
        name = re.sub(r'[Ａ-Ｚａ-ｚ]', lambda m: chr(ord(m.group()) - ord('Ａ') + ord('A')) if m.group() <= 'Ｚ' else chr(ord(m.group()) - ord('ａ') + ord('a')), name)

        # 9. 最终去除首尾空格
        name = name.strip()

        return name

    def process_entity_file(self, file_path: str) -> List[Dict]:
        """
        处理实体文件（支持Excel和CSV）

        Args:
            file_path: 文件路径（.xlsx, .xls, .csv）

        Returns:
            实体列表，格式: [{'name': '实体名', 'type': '类别'}, ...]
        """
        try:
            logger.info(f"开始处理实体文件: {file_path}")

            # 根据文件扩展名选择读取方式
            file_ext = Path(file_path).suffix.lower()
            if file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif file_ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8')
            elif file_ext == '.txt':
                # 尝试不同的分隔符
                df = self._read_txt_file(file_path)
            else:
                raise ValueError(f"不支持的实体文件格式: {file_ext}")
            
            # 检查列名
            if len(df.columns) < 2:
                raise ValueError("Excel文件至少需要两列：实体和类别")
            
            # 获取前两列，不管列名是什么
            entity_col = df.columns[0]
            type_col = df.columns[1]
            
            logger.info(f"检测到列名: 实体列='{entity_col}', 类别列='{type_col}'")
            
            entities = []
            seen_entities = set()  # 用于去重

            for index, row in df.iterrows():
                # 使用标准化函数处理实体名称
                entity_name = self.normalize_entity_name(row[entity_col])
                entity_type = str(row[type_col]).strip()

                # 跳过空行或无效数据
                if not entity_name or entity_name.lower() in ['nan', 'none', '']:
                    continue

                # 去重：如果实体名称已经存在，跳过
                if entity_name in seen_entities:
                    logger.info(f"跳过重复实体: {entity_name}")
                    continue

                seen_entities.add(entity_name)
                
                entities.append({
                    'name': entity_name,
                    'type': entity_type,
                    'confidence': 1.0,  # 手动标注的实体置信度为1.0
                    'data_source': 'manual_annotation'  # 修改字段名避免冲突
                })
            
            logger.info(f"成功解析 {len(entities)} 个实体")
            return entities
            
        except Exception as e:
            logger.error(f"处理实体文件失败: {e}")
            raise
    
    def process_relation_file(self, file_path: str) -> List[Dict]:
        """
        处理关系文件（支持CSV和TXT）

        Args:
            file_path: 文件路径（.csv, .txt）

        Returns:
            关系列表，格式: [{'source': '开始节点', 'relation': '关系', 'target': '结束节点', 'text': '文本'}, ...]
        """
        try:
            logger.info(f"开始处理关系文件: {file_path}")

            # 根据文件扩展名选择读取方式
            file_ext = Path(file_path).suffix.lower()
            if file_ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8')
            elif file_ext == '.txt':
                # 智能识别分隔符
                df = self._read_txt_file(file_path)
            elif file_ext == '.tsv':
                df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            else:
                raise ValueError(f"不支持的关系文件格式: {file_ext}")
            
            # 检查列数
            if len(df.columns) < 3:
                raise ValueError("CSV文件至少需要三列：开始节点,关系,结束节点")
            
            # 获取列名（支持中英文）
            columns = df.columns.tolist()
            
            # 智能识别列名
            source_col = columns[0]  # 第一列作为开始节点
            relation_col = columns[1]  # 第二列作为关系
            target_col = columns[2]  # 第三列作为结束节点
            text_col = columns[3] if len(columns) > 3 else None  # 第四列作为文本（可选）
            
            logger.info(f"检测到列名: 开始节点='{source_col}', 关系='{relation_col}', 结束节点='{target_col}', 文本='{text_col}'")
            
            relations = []
            for index, row in df.iterrows():
                # 使用标准化函数处理实体名称
                source_entity = self.normalize_entity_name(row[source_col])
                target_entity = self.normalize_entity_name(row[target_col])
                relation_type = str(row[relation_col]).strip()
                evidence_text = str(row[text_col]).strip() if text_col and pd.notna(row[text_col]) else f"{source_entity} {relation_type} {target_entity}"
                
                # 跳过空行
                if not source_entity or not relation_type or not target_entity:
                    continue
                
                if source_entity.lower() in ['nan', 'none'] or target_entity.lower() in ['nan', 'none']:
                    continue
                
                relations.append({
                    'source': source_entity,
                    'relation': relation_type,
                    'target': target_entity,
                    'text': evidence_text,
                    'confidence': 1.0,  # 手动标注的关系置信度为1.0
                    'data_source': 'manual_annotation'  # 修改字段名避免冲突
                })
            
            logger.info(f"成功解析 {len(relations)} 个关系")
            return relations
            
        except Exception as e:
            logger.error(f"处理关系文件失败: {e}")
            raise
    
    def validate_entity_file(self, file_path: str) -> Dict:
        """验证实体文件格式"""
        try:
            # 根据文件扩展名选择读取方式
            file_ext = Path(file_path).suffix.lower()
            if file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif file_ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8')
            elif file_ext == '.txt':
                df = self._read_txt_file(file_path)
            else:
                raise ValueError(f"不支持的实体文件格式: {file_ext}")
            
            validation_result = {
                'valid': True,
                'message': '',
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'sample_data': df.head(3).to_dict('records') if len(df) > 0 else []
            }
            
            if len(df.columns) < 2:
                validation_result['valid'] = False
                validation_result['message'] = '文件至少需要两列：实体和类别'
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'文件读取失败: {str(e)}',
                'row_count': 0,
                'column_count': 0,
                'columns': [],
                'sample_data': []
            }
    
    def validate_relation_file(self, file_path: str) -> Dict:
        """验证关系文件格式"""
        try:
            # 根据文件扩展名选择读取方式
            file_ext = Path(file_path).suffix.lower()
            if file_ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8')
            elif file_ext == '.txt':
                df = self._read_txt_file(file_path)
            elif file_ext == '.tsv':
                df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            else:
                raise ValueError(f"不支持的关系文件格式: {file_ext}")
            
            validation_result = {
                'valid': True,
                'message': '',
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': df.columns.tolist(),
                'sample_data': df.head(3).to_dict('records') if len(df) > 0 else []
            }
            
            if len(df.columns) < 3:
                validation_result['valid'] = False
                validation_result['message'] = '文件至少需要三列：开始节点,关系,结束节点'
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'文件读取失败: {str(e)}',
                'row_count': 0,
                'column_count': 0,
                'columns': [],
                'sample_data': []
            }
    
    def create_sample_files(self, output_dir: str):
        """创建示例文件"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 创建示例实体文件
            entity_data = {
                '实体': ['张三', '北京大学', '计算机科学', '人工智能', '机器学习', '深度学习'],
                '类别': ['PERSON', 'ORGANIZATION', 'CONCEPT', 'CONCEPT', 'CONCEPT', 'CONCEPT']
            }
            entity_df = pd.DataFrame(entity_data)
            entity_file = output_path / 'entities_sample.xlsx'
            entity_df.to_excel(entity_file, index=False)
            
            # 创建示例关系文件
            relation_data = {
                '开始节点': ['张三', '张三', '人工智能', '机器学习', '北京大学'],
                '关系': ['WORKS_FOR', 'RESEARCHES', 'INCLUDES', 'IS_A', 'OFFERS'],
                '结束节点': ['北京大学', '人工智能', '机器学习', '深度学习', '计算机科学'],
                'text': [
                    '张三在北京大学工作',
                    '张三研究人工智能技术',
                    '人工智能包含机器学习',
                    '机器学习是深度学习的基础',
                    '北京大学提供计算机科学课程'
                ]
            }
            relation_df = pd.DataFrame(relation_data)
            relation_file = output_path / 'relations_sample.csv'
            relation_df.to_csv(relation_file, index=False, encoding='utf-8')
            
            logger.info(f"示例文件已创建: {entity_file}, {relation_file}")
            return {
                'entity_file': str(entity_file),
                'relation_file': str(relation_file)
            }
            
        except Exception as e:
            logger.error(f"创建示例文件失败: {e}")
            raise
    
    def get_file_statistics(self, entity_file: str = None, relation_file: str = None) -> Dict:
        """获取文件统计信息"""
        stats = {
            'entity_stats': None,
            'relation_stats': None
        }
        
        if entity_file:
            try:
                df = pd.read_excel(entity_file)
                entity_types = df.iloc[:, 1].value_counts().to_dict() if len(df.columns) > 1 else {}
                stats['entity_stats'] = {
                    'total_entities': len(df),
                    'entity_types': entity_types,
                    'unique_types': len(entity_types)
                }
            except Exception as e:
                logger.error(f"获取实体文件统计失败: {e}")
        
        if relation_file:
            try:
                df = pd.read_csv(relation_file, encoding='utf-8')
                relation_types = df.iloc[:, 1].value_counts().to_dict() if len(df.columns) > 1 else {}
                stats['relation_stats'] = {
                    'total_relations': len(df),
                    'relation_types': relation_types,
                    'unique_types': len(relation_types)
                }
            except Exception as e:
                logger.error(f"获取关系文件统计失败: {e}")
        
        return stats

    def _read_txt_file(self, file_path: str) -> pd.DataFrame:
        """
        智能读取TXT文件，自动识别分隔符
        """
        try:
            # 读取文件的前几行来识别分隔符
            with open(file_path, 'r', encoding='utf-8') as f:
                sample_lines = [f.readline().strip() for _ in range(3)]

            # 过滤空行
            sample_lines = [line for line in sample_lines if line]

            if not sample_lines:
                raise ValueError("文件为空或无有效内容")

            # 尝试不同的分隔符
            separators = ['\t', ',', '|', ';', ' ']
            best_separator = '\t'  # 默认制表符
            max_columns = 0

            for sep in separators:
                try:
                    # 计算使用该分隔符时的平均列数
                    column_counts = [len(line.split(sep)) for line in sample_lines]
                    avg_columns = sum(column_counts) / len(column_counts)

                    # 选择能产生最多且一致列数的分隔符
                    if avg_columns > max_columns and max(column_counts) - min(column_counts) <= 1:
                        max_columns = avg_columns
                        best_separator = sep
                except:
                    continue

            logger.info(f"TXT文件使用分隔符: '{best_separator}' (检测到{max_columns}列)")

            # 使用最佳分隔符读取文件
            df = pd.read_csv(file_path, sep=best_separator, encoding='utf-8')

            return df

        except Exception as e:
            logger.error(f"读取TXT文件失败: {e}")
            # 回退到制表符分隔
            try:
                return pd.read_csv(file_path, sep='\t', encoding='utf-8')
            except:
                # 最后尝试逗号分隔
                return pd.read_csv(file_path, sep=',', encoding='utf-8')

    def validate_data_quality(self, data: List[Dict], data_type: str) -> Dict:
        """
        验证数据质量

        Args:
            data: 数据列表
            data_type: 数据类型 ('entity' | 'relation')

        Returns:
            验证结果
        """
        try:
            if not data:
                return {
                    'valid': False,
                    'message': '数据为空',
                    'issues': ['数据列表为空']
                }

            issues = []
            warnings = []

            # 检查数据完整性
            if data_type == 'entity':
                for i, entity in enumerate(data):
                    if not entity.get('name') or str(entity['name']).strip() == '':
                        issues.append(f'第{i+1}行: 实体名为空')
                    if not entity.get('type') or str(entity['type']).strip() == '':
                        warnings.append(f'第{i+1}行: 实体类型为空')

            elif data_type == 'relation':
                for i, relation in enumerate(data):
                    if not relation.get('source') or str(relation['source']).strip() == '':
                        issues.append(f'第{i+1}行: 源实体为空')
                    if not relation.get('target') or str(relation['target']).strip() == '':
                        issues.append(f'第{i+1}行: 目标实体为空')
                    if not relation.get('relation') or str(relation['relation']).strip() == '':
                        issues.append(f'第{i+1}行: 关系类型为空')

            # 检查重复数据
            if data_type == 'entity':
                names = [entity.get('name', '').strip() for entity in data]
                duplicates = [name for name in set(names) if names.count(name) > 1 and name]
                if duplicates:
                    warnings.append(f'发现重复实体: {", ".join(duplicates[:5])}{"..." if len(duplicates) > 5 else ""}')

            elif data_type == 'relation':
                relations = [(r.get('source', ''), r.get('relation', ''), r.get('target', '')) for r in data]
                duplicates = [rel for rel in set(relations) if relations.count(rel) > 1 and all(rel)]
                if duplicates:
                    warnings.append(f'发现重复关系: {len(duplicates)}个')

            # 统计信息
            stats = {
                'total_count': len(data),
                'valid_count': len(data) - len(issues),
                'issue_count': len(issues),
                'warning_count': len(warnings)
            }

            if data_type == 'entity':
                types = [entity.get('type', '') for entity in data if entity.get('type')]
                stats['unique_types'] = len(set(types))
                stats['type_distribution'] = {t: types.count(t) for t in set(types)}

            elif data_type == 'relation':
                relations = [rel.get('relation', '') for rel in data if rel.get('relation')]
                stats['unique_relations'] = len(set(relations))
                stats['relation_distribution'] = {r: relations.count(r) for r in set(relations)}

            return {
                'valid': len(issues) == 0,
                'message': f'数据质量检查完成: {stats["valid_count"]}/{stats["total_count"]} 条有效数据',
                'issues': issues,
                'warnings': warnings,
                'statistics': stats
            }

        except Exception as e:
            logger.error(f"数据质量验证失败: {e}")
            return {
                'valid': False,
                'message': f'验证过程出错: {str(e)}',
                'issues': [str(e)],
                'warnings': []
            }


def test_structured_data_processor():
    """测试结构化数据处理器"""
    processor = StructuredDataProcessor()
    
    # 创建示例文件
    sample_files = processor.create_sample_files('sample_data')
    
    # 测试实体文件处理
    entities = processor.process_entity_file(sample_files['entity_file'])
    print(f"解析实体: {len(entities)} 个")
    for entity in entities[:3]:
        print(f"  {entity}")
    
    # 测试关系文件处理
    relations = processor.process_relation_file(sample_files['relation_file'])
    print(f"解析关系: {len(relations)} 个")
    for relation in relations[:3]:
        print(f"  {relation}")
    
    # 获取统计信息
    stats = processor.get_file_statistics(
        sample_files['entity_file'],
        sample_files['relation_file']
    )
    print(f"统计信息: {stats}")


if __name__ == "__main__":
    test_structured_data_processor()
