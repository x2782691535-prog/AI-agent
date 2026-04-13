"""
中文命名实体识别
基于规则和模式匹配的中文NER实现
"""

import re
import logging
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
import jieba
import jieba.posseg as pseg

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """实体类"""
    text: str
    entity_type: str
    start_pos: int
    end_pos: int
    confidence: float
    context: str = ""
    properties: Dict = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class ChineseNER:
    """中文命名实体识别器"""
    
    def __init__(self):
        # 初始化jieba
        jieba.initialize()

        # 先加载基础数据
        self.surnames = self._load_surnames()
        self.location_suffixes = self._load_location_suffixes()
        self.organization_suffixes = self._load_organization_suffixes()
        self.professions = self._load_professions()
        self.degrees = self._load_degrees()

        # 然后加载模式（依赖于基础数据）
        self.patterns = self._load_patterns()
    
    def extract_entities(self, text: str, entity_types: List[str] = None) -> List[Entity]:
        """
        提取实体
        
        Args:
            text: 输入文本
            entity_types: 要提取的实体类型列表，None表示提取所有类型
            
        Returns:
            List[Entity]: 提取的实体列表
        """
        if not text:
            return []
        
        if entity_types is None:
            entity_types = ['PERSON', 'ORGANIZATION', 'LOCATION', 'CONCEPT', 'PRODUCT', 'EVENT', 'TIME']
        
        entities = []
        
        try:
            # 1. 基于规则的实体识别
            for entity_type in entity_types:
                type_entities = self._extract_by_type(text, entity_type)
                entities.extend(type_entities)
            
            # 2. 基于词性标注的实体识别
            pos_entities = self._extract_by_pos(text, entity_types)
            entities.extend(pos_entities)
            
            # 3. 去重和合并重叠实体
            entities = self._merge_overlapping_entities(entities)
            
            # 4. 计算置信度
            entities = self._calculate_confidence(entities, text)
            
            # 5. 按位置排序
            entities.sort(key=lambda x: x.start_pos)
            
            logger.debug(f"提取到 {len(entities)} 个实体")
            
            return entities
            
        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return []
    
    def _extract_by_type(self, text: str, entity_type: str) -> List[Entity]:
        """根据实体类型提取实体"""
        entities = []
        
        if entity_type not in self.patterns:
            return entities
        
        patterns = self.patterns[entity_type]
        
        for pattern_info in patterns:
            pattern = pattern_info['pattern']
            confidence = pattern_info.get('confidence', 0.7)
            
            matches = re.finditer(pattern, text)
            for match in matches:
                entity_text = match.group()
                start_pos = match.start()
                end_pos = match.end()
                
                # 获取上下文
                context_start = max(0, start_pos - 20)
                context_end = min(len(text), end_pos + 20)
                context = text[context_start:context_end]
                
                entity = Entity(
                    text=entity_text,
                    entity_type=entity_type,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    confidence=confidence,
                    context=context,
                    properties={'extraction_method': 'pattern', 'pattern': pattern}
                )
                
                entities.append(entity)
        
        return entities
    
    def _extract_by_pos(self, text: str, entity_types: List[str]) -> List[Entity]:
        """基于词性标注提取实体"""
        entities = []
        
        try:
            words = pseg.cut(text)
            current_pos = 0
            
            for word, pos in words:
                word_start = text.find(word, current_pos)
                if word_start == -1:
                    current_pos += len(word)
                    continue
                
                word_end = word_start + len(word)
                current_pos = word_end
                
                # 根据词性判断实体类型
                entity_type = self._pos_to_entity_type(word, pos)
                
                if entity_type and entity_type in entity_types:
                    # 获取上下文
                    context_start = max(0, word_start - 20)
                    context_end = min(len(text), word_end + 20)
                    context = text[context_start:context_end]
                    
                    entity = Entity(
                        text=word,
                        entity_type=entity_type,
                        start_pos=word_start,
                        end_pos=word_end,
                        confidence=0.6,  # 基于词性的置信度较低
                        context=context,
                        properties={'extraction_method': 'pos', 'pos': pos}
                    )
                    
                    entities.append(entity)
                    
        except Exception as e:
            logger.error(f"基于词性的实体提取失败: {e}")
        
        return entities
    
    def _pos_to_entity_type(self, word: str, pos: str) -> Optional[str]:
        """根据词性判断实体类型"""
        
        # 人名
        if pos in ['nr', 'nrf']:  # 人名
            return 'PERSON'
        
        # 地名
        if pos in ['ns', 'nsf']:  # 地名
            return 'LOCATION'
        
        # 机构名
        if pos in ['nt', 'ntc', 'ntcf', 'ntcb', 'ntch', 'nto', 'ntu', 'nts', 'nth']:
            return 'ORGANIZATION'
        
        # 时间
        if pos in ['t']:
            return 'TIME'
        
        # 其他名词可能是概念或产品
        if pos in ['n', 'nz'] and len(word) > 1:
            # 进一步判断
            if self._is_concept_word(word):
                return 'CONCEPT'
            elif self._is_product_word(word):
                return 'PRODUCT'
        
        return None
    
    def _is_concept_word(self, word: str) -> bool:
        """判断是否为概念词汇"""
        concept_indicators = [
            '技术', '方法', '理论', '算法', '模型', '系统', '平台', '框架',
            '协议', '标准', '规范', '原理', '概念', '思想', '理念', '策略'
        ]
        
        return any(indicator in word for indicator in concept_indicators)
    
    def _is_product_word(self, word: str) -> bool:
        """判断是否为产品词汇"""
        product_indicators = [
            '产品', '服务', '软件', '硬件', '设备', '工具', '应用', '程序',
            '系统', '平台', '设施', '装置', '机器', '仪器', '器械'
        ]
        
        return any(indicator in word for indicator in product_indicators)
    
    def _merge_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """合并重叠的实体"""
        if not entities:
            return entities
        
        # 按起始位置排序
        entities.sort(key=lambda x: x.start_pos)
        
        merged = []
        current = entities[0]
        
        for next_entity in entities[1:]:
            # 检查是否重叠
            if next_entity.start_pos < current.end_pos:
                # 重叠，选择置信度更高的或更长的实体
                if (next_entity.confidence > current.confidence or 
                    (next_entity.confidence == current.confidence and 
                     len(next_entity.text) > len(current.text))):
                    current = next_entity
            else:
                # 不重叠，添加当前实体并更新
                merged.append(current)
                current = next_entity
        
        # 添加最后一个实体
        merged.append(current)
        
        return merged
    
    def _calculate_confidence(self, entities: List[Entity], text: str) -> List[Entity]:
        """计算实体置信度"""
        for entity in entities:
            # 基础置信度
            confidence = entity.confidence
            
            # 长度加权
            if len(entity.text) >= 3:
                confidence += 0.1
            elif len(entity.text) == 1:
                confidence -= 0.2
            
            # 上下文加权
            context_score = self._calculate_context_score(entity, text)
            confidence += context_score * 0.2
            
            # 确保置信度在合理范围内
            entity.confidence = max(0.1, min(1.0, confidence))
        
        return entities
    
    def _calculate_context_score(self, entity: Entity, text: str) -> float:
        """计算上下文得分"""
        context_window = 50
        start = max(0, entity.start_pos - context_window)
        end = min(len(text), entity.end_pos + context_window)
        context = text[start:end]
        
        score = 0.0
        
        # 根据实体类型检查上下文特征
        if entity.entity_type == 'PERSON':
            person_indicators = ['先生', '女士', '教授', '博士', '经理', '主任', '院长', '总裁']
            for indicator in person_indicators:
                if indicator in context:
                    score += 0.3
                    break
        
        elif entity.entity_type == 'ORGANIZATION':
            org_indicators = ['公司', '企业', '机构', '组织', '部门', '学院', '研究所']
            for indicator in org_indicators:
                if indicator in context:
                    score += 0.3
                    break
        
        elif entity.entity_type == 'LOCATION':
            loc_indicators = ['位于', '在', '地区', '城市', '省份', '国家']
            for indicator in loc_indicators:
                if indicator in context:
                    score += 0.3
                    break
        
        return min(1.0, score)
    
    def _load_patterns(self) -> Dict[str, List[Dict]]:
        """加载实体识别模式"""
        patterns = {
            'PERSON': [
                {
                    'pattern': r'[\u4e00-\u9fff]{2,4}(?:先生|女士|教授|博士|工程师|经理|主任|院长|总裁|董事长|CEO|CTO|CFO)',
                    'confidence': 0.9
                },
                {
                    'pattern': r'(?:' + '|'.join(self.surnames) + r')[\u4e00-\u9fff]{1,3}(?=' + 
                             r'[，。！？；：\s]|先生|女士|教授|博士)',
                    'confidence': 0.8
                },
                {
                    'pattern': r'[\u4e00-\u9fff]{2,4}(?:院士|专家|学者|研究员|教师|老师)',
                    'confidence': 0.85
                }
            ],
            'ORGANIZATION': [
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:公司|企业|集团|有限公司|股份公司|责任公司)',
                    'confidence': 0.95
                },
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:大学|学院|研究所|实验室|中心|院)',
                    'confidence': 0.9
                },
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:部|局|委|署|厅|司|处)',
                    'confidence': 0.85
                }
            ],
            'LOCATION': [
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:省|市|县|区|镇|村|街道|路|号)',
                    'confidence': 0.9
                },
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:国|州|洲|岛|山|河|湖|海)',
                    'confidence': 0.85
                }
            ],
            'CONCEPT': [
                {
                    'pattern': r'[\u4e00-\u9fff]{2,8}(?:技术|方法|理论|算法|模型)',
                    'confidence': 0.8
                },
                {
                    'pattern': r'[\u4e00-\u9fff]{2,8}(?:系统|平台|框架|协议|标准)',
                    'confidence': 0.75
                }
            ],
            'PRODUCT': [
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:产品|服务|软件|硬件|设备)',
                    'confidence': 0.8
                },
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:系统|平台|工具|应用)',
                    'confidence': 0.75
                }
            ],
            'EVENT': [
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:会议|大会|论坛|峰会|活动)',
                    'confidence': 0.85
                },
                {
                    'pattern': r'[\u4e00-\u9fff]+(?:发布会|展览|比赛|竞赛)',
                    'confidence': 0.8
                }
            ],
            'TIME': [
                {
                    'pattern': r'\d{4}年\d{1,2}月\d{1,2}日',
                    'confidence': 0.95
                },
                {
                    'pattern': r'\d{4}-\d{1,2}-\d{1,2}',
                    'confidence': 0.9
                },
                {
                    'pattern': r'(?:今天|昨天|明天|前天|后天)',
                    'confidence': 0.8
                }
            ]
        }
        
        return patterns
    
    def _load_surnames(self) -> List[str]:
        """加载常见姓氏"""
        return [
            '王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴',
            '徐', '孙', '朱', '马', '胡', '郭', '林', '何', '高', '梁',
            '郑', '罗', '宋', '谢', '唐', '韩', '曹', '许', '邓', '萧',
            '冯', '曾', '程', '蔡', '彭', '潘', '袁', '于', '董', '余',
            '苏', '叶', '吕', '魏', '蒋', '田', '杜', '丁', '沈', '姜'
        ]
    
    def _load_location_suffixes(self) -> List[str]:
        """加载地名后缀"""
        return [
            '省', '市', '县', '区', '镇', '村', '街道', '路', '街', '巷',
            '号', '国', '州', '洲', '岛', '山', '河', '湖', '海', '港'
        ]
    
    def _load_organization_suffixes(self) -> List[str]:
        """加载组织机构后缀"""
        return [
            '公司', '企业', '集团', '有限公司', '股份公司', '责任公司',
            '大学', '学院', '研究所', '实验室', '中心', '院',
            '部', '局', '委', '署', '厅', '司', '处'
        ]
    
    def _load_professions(self) -> List[str]:
        """加载职业词汇"""
        return [
            '教授', '博士', '硕士', '学士', '工程师', '经理', '主任',
            '院长', '总裁', '董事长', 'CEO', 'CTO', 'CFO', '专家',
            '学者', '研究员', '教师', '老师', '医生', '律师', '会计师'
        ]
    
    def _load_degrees(self) -> List[str]:
        """加载学位词汇"""
        return [
            '博士', '硕士', '学士', '博士后', '院士', '教授', '副教授',
            '讲师', '助教', '研究员', '副研究员', '助理研究员'
        ]
    
    def add_custom_pattern(self, entity_type: str, pattern: str, confidence: float = 0.7):
        """添加自定义识别模式"""
        if entity_type not in self.patterns:
            self.patterns[entity_type] = []
        
        self.patterns[entity_type].append({
            'pattern': pattern,
            'confidence': confidence
        })
        
        logger.info(f"添加自定义模式: {entity_type} - {pattern}")
    
    def get_entity_statistics(self, entities: List[Entity]) -> Dict:
        """获取实体统计信息"""
        if not entities:
            return {}
        
        stats = {
            'total_count': len(entities),
            'type_distribution': {},
            'confidence_distribution': {
                'high': 0,  # >= 0.8
                'medium': 0,  # 0.5 - 0.8
                'low': 0  # < 0.5
            },
            'avg_confidence': 0.0,
            'avg_length': 0.0
        }
        
        # 类型分布
        for entity in entities:
            entity_type = entity.entity_type
            stats['type_distribution'][entity_type] = stats['type_distribution'].get(entity_type, 0) + 1
        
        # 置信度分布
        confidences = [entity.confidence for entity in entities]
        for conf in confidences:
            if conf >= 0.8:
                stats['confidence_distribution']['high'] += 1
            elif conf >= 0.5:
                stats['confidence_distribution']['medium'] += 1
            else:
                stats['confidence_distribution']['low'] += 1
        
        # 平均值
        stats['avg_confidence'] = sum(confidences) / len(confidences)
        stats['avg_length'] = sum(len(entity.text) for entity in entities) / len(entities)
        
        return stats
