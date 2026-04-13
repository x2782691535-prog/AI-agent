"""
文本预处理器
包含文本清洗、分句、分词等预处理功能
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
import jieba
import jieba.posseg as pseg

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """文本预处理器"""
    
    def __init__(self):
        # 初始化jieba
        jieba.initialize()
        
        # 中文标点符号
        self.chinese_punctuation = '，。！？；：""''（）【】《》〈〉「」『』〔〕…—–'
        
        # 英文标点符号
        self.english_punctuation = ',.!?;:"\'()[]<>{}-_'
        
        # 所有标点符号
        self.all_punctuation = self.chinese_punctuation + self.english_punctuation
        
        # 句子分割符
        self.sentence_delimiters = '。！？；!?;'
        
        # 停用词（可以从文件加载）
        self.stopwords = self._load_stopwords()
    
    def preprocess_text(self, text: str, options: Dict = None) -> Dict:
        """
        文本预处理主函数
        
        Args:
            text: 原始文本
            options: 预处理选项
            
        Returns:
            Dict: 预处理结果
        """
        if not text or not text.strip():
            return {
                'original_text': text,
                'cleaned_text': '',
                'sentences': [],
                'tokens': [],
                'statistics': {
                    'original_length': 0,
                    'cleaned_length': 0,
                    'sentence_count': 0,
                    'token_count': 0
                }
            }
        
        options = options or {}
        
        try:
            # 1. 文本清洗
            cleaned_text = self.clean_text(text, options.get('clean_options', {}))
            
            # 2. 分句
            sentences = self.split_sentences(cleaned_text)
            
            # 3. 分词
            tokens = []
            for sentence in sentences:
                sentence_tokens = self.tokenize(sentence, options.get('tokenize_options', {}))
                tokens.extend(sentence_tokens)
            
            # 4. 统计信息
            statistics = {
                'original_length': len(text),
                'cleaned_length': len(cleaned_text),
                'sentence_count': len(sentences),
                'token_count': len(tokens)
            }
            
            result = {
                'original_text': text,
                'cleaned_text': cleaned_text,
                'sentences': sentences,
                'tokens': tokens,
                'statistics': statistics
            }
            
            logger.debug(f"文本预处理完成，原始长度: {statistics['original_length']}, "
                        f"清洗后长度: {statistics['cleaned_length']}, "
                        f"句子数: {statistics['sentence_count']}, "
                        f"词汇数: {statistics['token_count']}")
            
            return result
            
        except Exception as e:
            logger.error(f"文本预处理失败: {e}")
            return {
                'original_text': text,
                'cleaned_text': text,
                'sentences': [text],
                'tokens': [],
                'statistics': {
                    'original_length': len(text),
                    'cleaned_length': len(text),
                    'sentence_count': 1,
                    'token_count': 0
                },
                'error': str(e)
            }
    
    def clean_text(self, text: str, options: Dict = None) -> str:
        """
        文本清洗
        
        Args:
            text: 原始文本
            options: 清洗选项
            
        Returns:
            str: 清洗后的文本
        """
        options = options or {}
        
        # 移除HTML标签
        if options.get('remove_html', True):
            text = re.sub(r'<[^>]+>', '', text)
        
        # 移除URL
        if options.get('remove_urls', True):
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # 移除邮箱
        if options.get('remove_emails', True):
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # 移除电话号码
        if options.get('remove_phones', True):
            text = re.sub(r'1[3-9]\d{9}', '', text)  # 中国手机号
            text = re.sub(r'\d{3,4}-\d{7,8}', '', text)  # 固定电话
        
        # 移除多余的空白字符
        if options.get('normalize_whitespace', True):
            text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符（保留中英文、数字、基本标点）
        if options.get('remove_special_chars', False):
            text = re.sub(r'[^\u4e00-\u9fff\u0041-\u005a\u0061-\u007a0-9\s' + 
                         re.escape(self.all_punctuation) + r']', '', text)
        
        # 移除过短的行
        if options.get('min_line_length', 0) > 0:
            lines = text.split('\n')
            lines = [line for line in lines if len(line.strip()) >= options['min_line_length']]
            text = '\n'.join(lines)
        
        return text.strip()
    
    def split_sentences(self, text: str) -> List[str]:
        """
        分句
        
        Args:
            text: 文本
            
        Returns:
            List[str]: 句子列表
        """
        if not text:
            return []
        
        # 使用正则表达式分句
        # 匹配中英文句号、感叹号、问号等
        pattern = r'[。！？；!?;]+'
        
        # 分割句子
        sentences = re.split(pattern, text)
        
        # 清理和过滤句子
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 1:  # 过滤过短的句子
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def tokenize(self, text: str, options: Dict = None) -> List[Dict]:
        """
        分词
        
        Args:
            text: 文本
            options: 分词选项
            
        Returns:
            List[Dict]: 词汇列表，包含词汇、词性等信息
        """
        options = options or {}
        
        if not text:
            return []
        
        tokens = []
        
        try:
            # 使用jieba进行分词和词性标注
            words = pseg.cut(text)
            
            for word, pos in words:
                word = word.strip()
                
                # 过滤条件
                if not word:
                    continue
                
                # 过滤停用词
                if options.get('remove_stopwords', True) and word in self.stopwords:
                    continue
                
                # 过滤标点符号
                if options.get('remove_punctuation', True) and word in self.all_punctuation:
                    continue
                
                # 过滤单字符（除了有意义的单字）
                if options.get('filter_single_char', False) and len(word) == 1:
                    if not self._is_meaningful_single_char(word):
                        continue
                
                # 过滤纯数字
                if options.get('filter_numbers', False) and word.isdigit():
                    continue
                
                token_info = {
                    'word': word,
                    'pos': pos,
                    'length': len(word)
                }
                
                tokens.append(token_info)
                
        except Exception as e:
            logger.error(f"分词失败: {e}")
            # 简单分词作为备选
            words = text.split()
            for word in words:
                if word.strip():
                    tokens.append({
                        'word': word.strip(),
                        'pos': 'unknown',
                        'length': len(word.strip())
                    })
        
        return tokens
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[Dict]:
        """
        提取关键词
        
        Args:
            text: 文本
            top_k: 返回前k个关键词
            
        Returns:
            List[Dict]: 关键词列表
        """
        try:
            import jieba.analyse
            
            # 使用TF-IDF提取关键词
            keywords_tfidf = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
            
            # 使用TextRank提取关键词
            keywords_textrank = jieba.analyse.textrank(text, topK=top_k, withWeight=True)
            
            # 合并结果
            keywords = []
            
            for word, weight in keywords_tfidf:
                keywords.append({
                    'word': word,
                    'tfidf_weight': weight,
                    'textrank_weight': 0.0,
                    'method': 'tfidf'
                })
            
            # 添加TextRank结果
            textrank_dict = dict(keywords_textrank)
            for keyword in keywords:
                if keyword['word'] in textrank_dict:
                    keyword['textrank_weight'] = textrank_dict[keyword['word']]
                    keyword['method'] = 'both'
            
            # 按权重排序
            keywords.sort(key=lambda x: x['tfidf_weight'], reverse=True)
            
            return keywords[:top_k]
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []
    
    def _load_stopwords(self) -> set:
        """加载停用词"""
        # 基础停用词列表
        basic_stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '里', '就是', '还', '把', '比', '或者', '什么', '怎么',
            '这个', '那个', '这样', '那样', '这里', '那里', '现在', '已经', '可以',
            '但是', '因为', '所以', '如果', '虽然', '然后', '而且', '不过', '只是',
            '还是', '或者', '以及', '以后', '以前', '之后', '之前', '当时', '时候'
        }
        
        # 可以从文件加载更多停用词
        try:
            # 这里可以加载外部停用词文件
            pass
        except:
            pass
        
        return basic_stopwords
    
    def _is_meaningful_single_char(self, char: str) -> bool:
        """判断单字符是否有意义"""
        meaningful_chars = {
            '我', '你', '他', '她', '它', '们',
            '大', '小', '高', '低', '长', '短', '新', '老',
            '好', '坏', '多', '少', '快', '慢',
            '是', '有', '无', '能', '会', '要', '想',
            '年', '月', '日', '时', '分', '秒',
            '元', '角', '分', '万', '千', '百', '十'
        }
        return char in meaningful_chars
    
    def get_text_statistics(self, text: str) -> Dict:
        """
        获取文本统计信息
        
        Args:
            text: 文本
            
        Returns:
            Dict: 统计信息
        """
        if not text:
            return {}
        
        # 基础统计
        char_count = len(text)
        char_count_no_space = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))
        
        # 中英文字符统计
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        digits = len(re.findall(r'\d', text))
        punctuation_count = len(re.findall(r'[' + re.escape(self.all_punctuation) + r']', text))
        
        # 句子和段落统计
        sentences = self.split_sentences(text)
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        # 词汇统计
        tokens = self.tokenize(text)
        unique_words = set(token['word'] for token in tokens)
        
        return {
            'char_count': char_count,
            'char_count_no_space': char_count_no_space,
            'chinese_chars': chinese_chars,
            'english_chars': english_chars,
            'digits': digits,
            'punctuation_count': punctuation_count,
            'sentence_count': len(sentences),
            'paragraph_count': len(paragraphs),
            'word_count': len(tokens),
            'unique_word_count': len(unique_words),
            'avg_sentence_length': char_count / len(sentences) if sentences else 0,
            'avg_word_length': sum(token['length'] for token in tokens) / len(tokens) if tokens else 0
        }
