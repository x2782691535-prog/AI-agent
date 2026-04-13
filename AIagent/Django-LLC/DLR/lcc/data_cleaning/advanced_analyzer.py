"""
高级数据清洗分析器
实现缺失值类型判断（MCAR、MAR、MNAR）、异常值检测、重复值识别等高级功能
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import json
from scipy import stats
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt
import seaborn as sns
from tabulate import tabulate
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class AdvancedDataAnalyzer:
    """高级数据清洗分析器"""
    
    def __init__(self):
        self.missing_patterns = {}
        self.outlier_info = {}
        self.duplicate_info = {}
        self.similarity_threshold = 0.8
    
    def analyze_missing_patterns(self, df: pd.DataFrame) -> Dict:
        """
        分析缺失值模式，判断缺失类型（MCAR、MAR、MNAR）
        """
        print("\n" + "="*60)
        print("🔍 缺失值模式分析")
        print("="*60)
        
        missing_analysis = {
            'total_missing': 0,
            'missing_by_column': {},
            'missing_patterns': {},
            'missing_type_assessment': {},
            'correlation_analysis': {},
            'recommendations': []
        }
        
        # 1. 基本缺失值统计
        missing_counts = df.isnull().sum()
        total_rows = len(df)
        
        print(f"📊 数据集基本信息:")
        print(f"   总行数: {total_rows}")
        print(f"   总列数: {len(df.columns)}")
        
        # 缺失值统计表
        missing_stats = []
        for col in df.columns:
            missing_count = missing_counts[col]
            missing_rate = (missing_count / total_rows) * 100
            missing_stats.append([col, missing_count, f"{missing_rate:.2f}%"])
            missing_analysis['missing_by_column'][col] = {
                'count': int(missing_count),
                'rate': missing_rate
            }
        
        print(f"\n📋 各列缺失值统计:")
        headers = ["列名", "缺失数量", "缺失率"]
        print(tabulate(missing_stats, headers=headers, tablefmt="grid"))
        
        # 2. 缺失值模式分析
        missing_pattern = df.isnull()
        pattern_counts = missing_pattern.value_counts()
        
        print(f"\n🔍 缺失值模式分析:")
        print(f"   发现 {len(pattern_counts)} 种不同的缺失模式")
        
        # 显示主要缺失模式
        top_patterns = pattern_counts.head(5)
        pattern_table = []
        for i, (pattern, count) in enumerate(top_patterns.items()):
            pattern_desc = []
            for col, is_missing in zip(df.columns, pattern):
                if is_missing:
                    pattern_desc.append(f"{col}:缺失")
                else:
                    pattern_desc.append(f"{col}:完整")
            pattern_str = " | ".join(pattern_desc)
            pattern_table.append([f"模式{i+1}", count, f"{(count/total_rows)*100:.2f}%", pattern_str[:80] + "..." if len(pattern_str) > 80 else pattern_str])
        
        headers = ["模式", "数量", "占比", "描述"]
        print(tabulate(pattern_table, headers=headers, tablefmt="grid"))
        
        # 3. 缺失值类型评估
        print(f"\n🎯 缺失值类型评估:")
        
        for col in df.columns:
            if missing_counts[col] > 0:
                assessment = self._assess_missing_type(df, col)
                missing_analysis['missing_type_assessment'][col] = assessment
                
                print(f"\n   列 '{col}':")
                print(f"   - 缺失数量: {missing_counts[col]} ({(missing_counts[col]/total_rows)*100:.2f}%)")
                print(f"   - 评估类型: {assessment['type']}")
                print(f"   - 置信度: {assessment['confidence']:.2f}")
                print(f"   - 原因分析: {assessment['reason']}")
                print(f"   - 建议处理: {assessment['recommendation']}")
        
        # 4. 相关性分析
        if len([col for col in df.columns if missing_counts[col] > 0]) > 1:
            correlation_matrix = missing_pattern.corr()
            print(f"\n📈 缺失值相关性分析:")
            
            # 找出高相关性的列对
            high_corr_pairs = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    corr_val = correlation_matrix.iloc[i, j]
                    if abs(corr_val) > 0.3:  # 相关性阈值
                        col1 = correlation_matrix.columns[i]
                        col2 = correlation_matrix.columns[j]
                        high_corr_pairs.append([col1, col2, f"{corr_val:.3f}"])
            
            if high_corr_pairs:
                headers = ["列1", "列2", "相关系数"]
                print(tabulate(high_corr_pairs, headers=headers, tablefmt="grid"))
            else:
                print("   未发现显著的缺失值相关性")
        
        # 5. 生成建议
        recommendations = self._generate_missing_recommendations(missing_analysis)
        missing_analysis['recommendations'] = recommendations
        
        print(f"\n💡 处理建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        return missing_analysis
    
    def _assess_missing_type(self, df: pd.DataFrame, column: str) -> Dict:
        """评估单列的缺失值类型"""
        missing_mask = df[column].isnull()
        
        # 基本统计
        missing_rate = missing_mask.sum() / len(df)
        
        # 1. 检查是否完全随机（MCAR）
        # 如果缺失值在其他变量上的分布与非缺失值相似，可能是MCAR
        mcar_score = 0
        mar_score = 0
        mnar_score = 0
        
        # 检查与其他列的关系
        other_cols = [col for col in df.columns if col != column and df[col].dtype in ['int64', 'float64']]
        
        if other_cols:
            for other_col in other_cols[:3]:  # 只检查前3列以避免过度计算
                try:
                    # 比较缺失组和非缺失组在其他变量上的分布
                    missing_group = df[missing_mask][other_col].dropna()
                    non_missing_group = df[~missing_mask][other_col].dropna()
                    
                    if len(missing_group) > 5 and len(non_missing_group) > 5:
                        # 使用KS检验比较分布
                        ks_stat, p_value = stats.ks_2samp(missing_group, non_missing_group)
                        
                        if p_value > 0.05:  # 分布相似
                            mcar_score += 1
                        else:  # 分布不同
                            mar_score += 1
                except:
                    pass
        
        # 2. 检查缺失模式
        if missing_rate > 0.5:
            mnar_score += 2  # 高缺失率可能表示MNAR
        elif missing_rate < 0.1:
            mcar_score += 1  # 低缺失率可能是随机的
        
        # 3. 检查缺失值的位置模式
        missing_positions = df.index[missing_mask].tolist()
        if len(missing_positions) > 1:
            # 检查是否有连续缺失（可能表示系统性问题）
            consecutive_count = 0
            for i in range(1, len(missing_positions)):
                if missing_positions[i] - missing_positions[i-1] == 1:
                    consecutive_count += 1
            
            if consecutive_count > len(missing_positions) * 0.3:
                mnar_score += 2  # 连续缺失可能是系统性的
        
        # 确定最可能的类型
        scores = {'MCAR': mcar_score, 'MAR': mar_score, 'MNAR': mnar_score}
        predicted_type = max(scores, key=scores.get)
        confidence = scores[predicted_type] / max(sum(scores.values()), 1)
        
        # 生成原因和建议
        if predicted_type == 'MCAR':
            reason = "缺失值在其他变量上的分布与非缺失值相似，可能是完全随机缺失"
            recommendation = "可以使用均值/中位数/众数填充，或使用插值方法"
        elif predicted_type == 'MAR':
            reason = "缺失值与其他观察到的变量有关，但与自身值无关"
            recommendation = "建议使用基于其他变量的预测模型进行填充"
        else:  # MNAR
            reason = "缺失值可能与变量自身的值有关，或存在系统性缺失模式"
            recommendation = "需要领域专家判断，可能需要特殊处理或建模时考虑缺失机制"
        
        return {
            'type': predicted_type,
            'confidence': confidence,
            'reason': reason,
            'recommendation': recommendation,
            'scores': scores
        }
    
    def _generate_missing_recommendations(self, analysis: Dict) -> List[str]:
        """生成缺失值处理建议"""
        recommendations = []
        
        # 基于缺失率的建议
        high_missing_cols = [col for col, info in analysis['missing_by_column'].items() 
                           if info['rate'] > 50]
        if high_missing_cols:
            recommendations.append(f"列 {', '.join(high_missing_cols)} 缺失率超过50%，建议考虑删除或重新收集数据")
        
        # 基于缺失类型的建议
        mcar_cols = [col for col, info in analysis['missing_type_assessment'].items() 
                    if info['type'] == 'MCAR']
        if mcar_cols:
            recommendations.append(f"列 {', '.join(mcar_cols)} 为完全随机缺失，可使用简单填充方法")
        
        mar_cols = [col for col, info in analysis['missing_type_assessment'].items() 
                   if info['type'] == 'MAR']
        if mar_cols:
            recommendations.append(f"列 {', '.join(mar_cols)} 为随机缺失，建议使用预测模型填充")
        
        mnar_cols = [col for col, info in analysis['missing_type_assessment'].items() 
                    if info['type'] == 'MNAR']
        if mnar_cols:
            recommendations.append(f"列 {', '.join(mnar_cols)} 为非随机缺失，需要专门的处理策略")
        
        return recommendations
    
    def detect_outliers(self, df: pd.DataFrame) -> Dict:
        """
        检测异常值
        """
        print("\n" + "="*60)
        print("🚨 异常值检测分析")
        print("="*60)
        
        outlier_analysis = {
            'methods_used': ['IQR', 'Z-Score', 'Isolation Forest'],
            'outliers_by_column': {},
            'outlier_summary': {},
            'recommendations': []
        }
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            print("   ⚠️ 未发现数值型列，跳过异常值检测")
            return outlier_analysis
        
        print(f"📊 检测 {len(numeric_cols)} 个数值型列的异常值")
        
        outlier_summary_table = []
        
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) < 10:
                continue
                
            outliers = self._detect_column_outliers(col_data, col)
            outlier_analysis['outliers_by_column'][col] = outliers
            
            # 计算总异常值数量（去重）
            all_outliers = set()
            all_outliers.update(outliers['iqr_outliers'])
            all_outliers.update(outliers['zscore_outliers'])
            all_outliers.update(outliers['isolation_outliers'])
            total_outliers = len(all_outliers)
            outlier_rate = (total_outliers / len(col_data)) * 100
            
            outlier_summary_table.append([
                col, 
                len(col_data), 
                total_outliers, 
                f"{outlier_rate:.2f}%",
                f"{outliers['iqr_count']} / {outliers['zscore_count']} / {outliers['isolation_count']}"
            ])
        
        headers = ["列名", "数据量", "异常值数", "异常率", "IQR/Z-Score/Isolation"]
        print(tabulate(outlier_summary_table, headers=headers, tablefmt="grid"))
        
        # 生成异常值处理建议
        recommendations = self._generate_outlier_recommendations(outlier_analysis)
        outlier_analysis['recommendations'] = recommendations
        
        print(f"\n💡 异常值处理建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        return outlier_analysis
    
    def _detect_column_outliers(self, data: pd.Series, column_name: str) -> Dict:
        """检测单列的异常值"""
        outliers = {
            'iqr_outliers': [],
            'zscore_outliers': [],
            'isolation_outliers': [],
            'iqr_count': 0,
            'zscore_count': 0,
            'isolation_count': 0
        }
        
        # 1. IQR方法
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        iqr_outliers = data[(data < lower_bound) | (data > upper_bound)].index.tolist()
        outliers['iqr_outliers'] = iqr_outliers
        outliers['iqr_count'] = len(iqr_outliers)
        
        # 2. Z-Score方法
        z_scores = np.abs(stats.zscore(data))
        zscore_outliers = data[z_scores > 3].index.tolist()
        outliers['zscore_outliers'] = zscore_outliers
        outliers['zscore_count'] = len(zscore_outliers)
        
        # 3. Isolation Forest方法
        try:
            from sklearn.ensemble import IsolationForest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            outlier_pred = iso_forest.fit_predict(data.values.reshape(-1, 1))
            isolation_outliers = data[outlier_pred == -1].index.tolist()
            outliers['isolation_outliers'] = isolation_outliers
            outliers['isolation_count'] = len(isolation_outliers)
        except ImportError:
            outliers['isolation_count'] = 0
        
        return outliers
    
    def _generate_outlier_recommendations(self, analysis: Dict) -> List[str]:
        """生成异常值处理建议"""
        recommendations = []
        
        high_outlier_cols = []
        for col, outliers in analysis['outliers_by_column'].items():
            # 计算总异常值数量（去重）
            all_outliers = set()
            all_outliers.update(outliers['iqr_outliers'])
            all_outliers.update(outliers['zscore_outliers'])
            all_outliers.update(outliers['isolation_outliers'])
            total_outliers = len(all_outliers)

            if total_outliers > 0:
                outlier_rate = (total_outliers / 100) * 100  # 假设数据量
                if outlier_rate > 10:
                    high_outlier_cols.append(col)
        
        if high_outlier_cols:
            recommendations.append(f"列 {', '.join(high_outlier_cols)} 异常值比例较高，建议人工核验")
        
        recommendations.append("对于数据录入错误的异常值，建议修正；对于真实离群值，建议标记保留")
        recommendations.append("可以使用多种方法综合判断异常值，避免误删重要信息")
        
        return recommendations

    def detect_duplicates_advanced(self, df: pd.DataFrame, text_columns: List[str] = None) -> Dict:
        """
        高级重复值检测，包括精确匹配和相似度匹配
        """
        print("\n" + "="*60)
        print("🔄 高级重复值检测分析")
        print("="*60)

        duplicate_analysis = {
            'exact_duplicates': {},
            'similarity_duplicates': {},
            'key_feature_duplicates': {},
            'recommendations': []
        }

        # 1. 精确重复检测
        print("📋 精确重复检测:")
        exact_duplicates = df.duplicated()
        exact_count = exact_duplicates.sum()

        print(f"   完全重复行数: {exact_count} ({(exact_count/len(df))*100:.2f}%)")

        if exact_count > 0:
            duplicate_analysis['exact_duplicates'] = {
                'count': int(exact_count),
                'indices': df[exact_duplicates].index.tolist(),
                'rate': (exact_count/len(df))*100
            }

        # 2. 基于关键特征的重复检测
        print(f"\n🔑 关键特征重复检测:")

        # 对于实体数据：实体名称+类型
        if 'name' in df.columns or '实体名' in df.columns:
            entity_col = 'name' if 'name' in df.columns else '实体名'
            type_col = 'type' if 'type' in df.columns else ('类型' if '类型' in df.columns else None)

            if type_col:
                key_features = [entity_col, type_col]
                key_duplicates = df.duplicated(subset=key_features)
                key_count = key_duplicates.sum()

                print(f"   基于 {'+'.join(key_features)} 的重复: {key_count} 行")

                duplicate_analysis['key_feature_duplicates']['entity'] = {
                    'features': key_features,
                    'count': int(key_count),
                    'indices': df[key_duplicates].index.tolist()
                }

        # 对于关系数据：源实体+关系+目标实体
        relation_cols = ['source', 'relation', 'target']
        chinese_relation_cols = ['源实体', '关系', '目标实体']

        if all(col in df.columns for col in relation_cols):
            rel_duplicates = df.duplicated(subset=relation_cols)
            rel_count = rel_duplicates.sum()
            print(f"   基于 {'+'.join(relation_cols)} 的重复: {rel_count} 行")

            duplicate_analysis['key_feature_duplicates']['relation'] = {
                'features': relation_cols,
                'count': int(rel_count),
                'indices': df[rel_duplicates].index.tolist()
            }
        elif all(col in df.columns for col in chinese_relation_cols):
            rel_duplicates = df.duplicated(subset=chinese_relation_cols)
            rel_count = rel_duplicates.sum()
            print(f"   基于 {'+'.join(chinese_relation_cols)} 的重复: {rel_count} 行")

            duplicate_analysis['key_feature_duplicates']['relation'] = {
                'features': chinese_relation_cols,
                'count': int(rel_count),
                'indices': df[rel_duplicates].index.tolist()
            }

        # 3. 文本相似度检测
        if text_columns:
            print(f"\n📝 文本相似度检测:")
            for col in text_columns:
                if col in df.columns:
                    similarity_duplicates = self._detect_text_similarity(df[col].dropna(), col)
                    duplicate_analysis['similarity_duplicates'][col] = similarity_duplicates

                    print(f"   列 '{col}' 相似文本组数: {len(similarity_duplicates['groups'])}")
                    print(f"   涉及行数: {sum(len(group) for group in similarity_duplicates['groups'])}")

        # 4. 生成重复值处理建议
        recommendations = self._generate_duplicate_recommendations(duplicate_analysis)
        duplicate_analysis['recommendations'] = recommendations

        print(f"\n💡 重复值处理建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")

        return duplicate_analysis

    def _detect_text_similarity(self, text_series: pd.Series, column_name: str) -> Dict:
        """检测文本相似度"""
        similarity_info = {
            'groups': [],
            'similarity_matrix': None,
            'method': 'TF-IDF + Cosine Similarity'
        }

        texts = text_series.astype(str).tolist()
        if len(texts) < 2:
            return similarity_info

        try:
            # 使用TF-IDF向量化
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,
                ngram_range=(1, 2)
            )

            tfidf_matrix = vectorizer.fit_transform(texts)

            # 计算余弦相似度
            similarity_matrix = cosine_similarity(tfidf_matrix)
            similarity_info['similarity_matrix'] = similarity_matrix

            # 找出相似文本组
            processed = set()
            similar_groups = []

            for i in range(len(texts)):
                if i in processed:
                    continue

                similar_indices = [i]
                for j in range(i+1, len(texts)):
                    if j not in processed and similarity_matrix[i][j] > self.similarity_threshold:
                        similar_indices.append(j)
                        processed.add(j)

                if len(similar_indices) > 1:
                    # 转换为原始索引
                    original_indices = [text_series.index[idx] for idx in similar_indices]
                    similar_groups.append({
                        'indices': original_indices,
                        'texts': [texts[idx] for idx in similar_indices],
                        'similarity_scores': [similarity_matrix[similar_indices[0]][idx] for idx in similar_indices[1:]]
                    })

                processed.add(i)

            similarity_info['groups'] = similar_groups

        except Exception as e:
            logger.warning(f"文本相似度检测失败: {e}")

        return similarity_info

    def _generate_duplicate_recommendations(self, analysis: Dict) -> List[str]:
        """生成重复值处理建议"""
        recommendations = []

        if analysis['exact_duplicates']:
            count = analysis['exact_duplicates']['count']
            recommendations.append(f"发现 {count} 行完全重复数据，建议直接删除")

        if analysis['key_feature_duplicates']:
            for data_type, info in analysis['key_feature_duplicates'].items():
                count = info['count']
                features = '+'.join(info['features'])
                recommendations.append(f"发现 {count} 行基于 {features} 的重复，建议保留信息最完整的记录")

        if analysis['similarity_duplicates']:
            total_groups = sum(len(info['groups']) for info in analysis['similarity_duplicates'].values())
            if total_groups > 0:
                recommendations.append(f"发现 {total_groups} 组相似文本，建议人工核验后决定是否合并")

        recommendations.append("建议建立数据唯一性约束，防止未来出现重复数据")

        return recommendations

    def generate_comprehensive_report(self, df: pd.DataFrame, text_columns: List[str] = None) -> Dict:
        """
        生成综合数据清洗报告
        """
        print("\n" + "="*80)
        print("📊 综合数据清洗分析报告")
        print("="*80)

        print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 数据集信息: {len(df)} 行 × {len(df.columns)} 列")

        # 执行各项分析
        missing_analysis = self.analyze_missing_patterns(df)
        outlier_analysis = self.detect_outliers(df)
        duplicate_analysis = self.detect_duplicates_advanced(df, text_columns)

        # 综合报告
        comprehensive_report = {
            'dataset_info': {
                'rows': len(df),
                'columns': len(df.columns),
                'analysis_time': datetime.now().isoformat()
            },
            'missing_analysis': missing_analysis,
            'outlier_analysis': outlier_analysis,
            'duplicate_analysis': duplicate_analysis,
            'overall_recommendations': []
        }

        # 生成综合建议
        overall_recommendations = []

        # 基于缺失值分析的建议
        if missing_analysis['recommendations']:
            overall_recommendations.extend(missing_analysis['recommendations'])

        # 基于异常值分析的建议
        if outlier_analysis['recommendations']:
            overall_recommendations.extend(outlier_analysis['recommendations'])

        # 基于重复值分析的建议
        if duplicate_analysis['recommendations']:
            overall_recommendations.extend(duplicate_analysis['recommendations'])

        # 数据质量评估
        total_issues = 0
        if missing_analysis['missing_by_column']:
            total_issues += sum(info['count'] for info in missing_analysis['missing_by_column'].values())

        if duplicate_analysis['exact_duplicates']:
            total_issues += duplicate_analysis['exact_duplicates']['count']

        quality_score = max(0, 100 - (total_issues / len(df)) * 100)

        overall_recommendations.append(f"数据质量评分: {quality_score:.1f}/100")

        if quality_score >= 90:
            overall_recommendations.append("数据质量优秀，可直接用于分析")
        elif quality_score >= 70:
            overall_recommendations.append("数据质量良好，建议进行轻度清洗")
        elif quality_score >= 50:
            overall_recommendations.append("数据质量一般，需要进行中度清洗")
        else:
            overall_recommendations.append("数据质量较差，需要进行深度清洗")

        comprehensive_report['overall_recommendations'] = overall_recommendations

        print(f"\n" + "="*80)
        print("📋 综合分析总结")
        print("="*80)

        print(f"\n💯 数据质量评分: {quality_score:.1f}/100")
        print(f"\n📝 综合建议:")
        for i, rec in enumerate(overall_recommendations, 1):
            print(f"   {i}. {rec}")

        return comprehensive_report
