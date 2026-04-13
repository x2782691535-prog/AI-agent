#!/usr/bin/env python
"""
数据清洗报告生成器
专门用于生成报告中的数据清洗统计信息
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DLR.settings')
import django
django.setup()

from lcc.data_cleaning.advanced_analyzer import AdvancedDataAnalyzer


def analyze_csv_file(file_path: str, text_columns: list = None):
    """
    分析CSV文件的数据质量
    
    Args:
        file_path: CSV文件路径
        text_columns: 需要进行文本相似度分析的列名列表
    """
    
    print(f"\n📊 正在分析文件: {file_path}")
    print("=" * 80)
    
    try:
        # 读取数据
        df = pd.read_csv(file_path, encoding='utf-8')
        print(f"✅ 成功读取数据: {len(df)} 行 × {len(df.columns)} 列")
        
        # 创建分析器
        analyzer = AdvancedDataAnalyzer()
        
        # 生成综合报告
        report = analyzer.generate_comprehensive_report(df, text_columns)
        
        return report
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return None


def generate_summary_statistics(report: dict):
    """
    生成汇总统计信息，适合在报告中展示
    """
    
    print("\n" + "📋" * 30)
    print("数据清洗汇总统计")
    print("📋" * 30)
    
    dataset_info = report['dataset_info']
    missing_analysis = report['missing_analysis']
    outlier_analysis = report['outlier_analysis']
    duplicate_analysis = report['duplicate_analysis']
    
    # 基本信息
    print(f"\n📊 数据集基本信息:")
    print(f"   - 总行数: {dataset_info['rows']}")
    print(f"   - 总列数: {dataset_info['columns']}")
    print(f"   - 分析时间: {dataset_info['analysis_time'][:19]}")
    
    # 缺失值统计
    print(f"\n🔍 缺失值处理统计:")
    total_missing = 0
    missing_columns = 0
    
    if missing_analysis['missing_by_column']:
        for col, info in missing_analysis['missing_by_column'].items():
            if info['count'] > 0:
                missing_columns += 1
                total_missing += info['count']
                print(f"   - {col}: {info['count']} 个缺失值 ({info['rate']:.2f}%)")
    
    if total_missing == 0:
        print("   - ✅ 未发现缺失值")
    else:
        print(f"   - 📊 总计: {total_missing} 个缺失值，涉及 {missing_columns} 列")
    
    # 缺失值类型分析
    if missing_analysis.get('missing_type_assessment'):
        print(f"\n🎯 缺失值类型分析:")
        type_counts = {'MCAR': 0, 'MAR': 0, 'MNAR': 0}
        for col, assessment in missing_analysis['missing_type_assessment'].items():
            type_counts[assessment['type']] += 1
        
        for missing_type, count in type_counts.items():
            if count > 0:
                type_desc = {
                    'MCAR': '完全随机缺失',
                    'MAR': '随机缺失', 
                    'MNAR': '非随机缺失'
                }
                print(f"   - {type_desc[missing_type]} ({missing_type}): {count} 列")
    
    # 异常值统计
    print(f"\n🚨 异常值检测统计:")
    total_outliers = 0
    outlier_columns = 0
    
    if outlier_analysis['outliers_by_column']:
        for col, outliers in outlier_analysis['outliers_by_column'].items():
            # 计算总异常值数量（去重）
            all_outliers = set()
            all_outliers.update(outliers['iqr_outliers'])
            all_outliers.update(outliers['zscore_outliers'])
            all_outliers.update(outliers['isolation_outliers'])
            col_outliers = len(all_outliers)
            
            if col_outliers > 0:
                outlier_columns += 1
                total_outliers += col_outliers
                print(f"   - {col}: {col_outliers} 个异常值")
                print(f"     * IQR方法: {outliers['iqr_count']} 个")
                print(f"     * Z-Score方法: {outliers['zscore_count']} 个")
                print(f"     * Isolation Forest: {outliers['isolation_count']} 个")
    
    if total_outliers == 0:
        print("   - ✅ 未发现异常值")
    else:
        print(f"   - 📊 总计: {total_outliers} 个异常值，涉及 {outlier_columns} 列")
    
    # 重复值统计
    print(f"\n🔄 重复值检测统计:")
    
    # 精确重复
    if duplicate_analysis.get('exact_duplicates'):
        exact_count = duplicate_analysis['exact_duplicates']['count']
        exact_rate = duplicate_analysis['exact_duplicates']['rate']
        print(f"   - 完全重复行: {exact_count} 行 ({exact_rate:.2f}%)")
    else:
        print("   - 完全重复行: 0 行")
    
    # 关键特征重复
    if duplicate_analysis.get('key_feature_duplicates'):
        for data_type, info in duplicate_analysis['key_feature_duplicates'].items():
            features = '+'.join(info['features'])
            count = info['count']
            print(f"   - 基于 {features} 的重复: {count} 行")
    
    # 文本相似度重复
    if duplicate_analysis.get('similarity_duplicates'):
        total_similar_groups = 0
        total_similar_rows = 0
        for col, info in duplicate_analysis['similarity_duplicates'].items():
            groups = len(info['groups'])
            rows = sum(len(group['indices']) for group in info['groups'])
            total_similar_groups += groups
            total_similar_rows += rows
            if groups > 0:
                print(f"   - {col} 相似文本: {groups} 组，涉及 {rows} 行")
        
        if total_similar_groups == 0:
            print("   - 文本相似度重复: 未发现")
    
    # 数据质量评分
    quality_score = 100
    if missing_analysis['missing_by_column']:
        total_missing_rate = sum(info['count'] for info in missing_analysis['missing_by_column'].values()) / dataset_info['rows']
        quality_score -= total_missing_rate * 100
    
    if duplicate_analysis.get('exact_duplicates'):
        duplicate_rate = duplicate_analysis['exact_duplicates']['rate']
        quality_score -= duplicate_rate
    
    quality_score = max(0, quality_score)
    
    print(f"\n💯 数据质量评分: {quality_score:.1f}/100")
    
    if quality_score >= 90:
        quality_level = "优秀"
        quality_color = "🟢"
    elif quality_score >= 75:
        quality_level = "良好"
        quality_color = "🟡"
    elif quality_score >= 60:
        quality_level = "一般"
        quality_color = "🟠"
    else:
        quality_level = "较差"
        quality_color = "🔴"
    
    print(f"   数据质量等级: {quality_color} {quality_level}")
    
    # 处理建议汇总
    print(f"\n💡 主要处理建议:")
    recommendations = report.get('overall_recommendations', [])
    for i, rec in enumerate(recommendations[:5], 1):  # 只显示前5条建议
        print(f"   {i}. {rec}")
    
    return {
        'total_rows': dataset_info['rows'],
        'total_columns': dataset_info['columns'],
        'missing_values': total_missing,
        'missing_columns': missing_columns,
        'outliers': total_outliers,
        'outlier_columns': outlier_columns,
        'exact_duplicates': duplicate_analysis.get('exact_duplicates', {}).get('count', 0),
        'quality_score': quality_score,
        'quality_level': quality_level
    }


def main():
    """主函数 - 演示如何使用"""
    
    print("🚀 数据清洗报告生成器")
    print("=" * 60)
    print("本工具可以分析CSV文件并生成详细的数据清洗统计报告")
    print("适用于在研究报告中展示数据预处理过程")
    print("=" * 60)
    
    # 示例：分析实体数据
    print("\n📋 示例1: 分析实体数据")
    
    # 创建示例数据
    entity_data = {
        '实体名': ['张三', '李四', '', '张三', None, '王五', '赵六'],
        '类型': ['人物', '人物', '人物', '人物', '人物', '', '人物'],
        '年龄': [25, 30, np.nan, 25, 28, 150, 32],  # 包含缺失值和异常值
        '描述': ['软件工程师', '数据科学家', '', '软件工程师', None, '项目经理', '系统架构师']
    }
    
    df = pd.DataFrame(entity_data)
    
    # 保存为临时文件
    temp_file = 'temp_entity_data.csv'
    df.to_csv(temp_file, index=False, encoding='utf-8')
    
    try:
        # 分析数据
        report = analyze_csv_file(temp_file, text_columns=['描述'])
        
        if report:
            # 生成汇总统计
            summary = generate_summary_statistics(report)
            
            print(f"\n📊 汇总结果:")
            print(f"   - 处理了 {summary['missing_values']} 个缺失值")
            print(f"   - 检测了 {summary['outliers']} 个异常值")
            print(f"   - 发现了 {summary['exact_duplicates']} 个重复值")
            print(f"   - 数据质量评分: {summary['quality_score']:.1f}/100 ({summary['quality_level']})")
    
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    print(f"\n✅ 演示完成！")
    print(f"\n🔧 使用方法:")
    print(f"   python data_cleaning_report_generator.py")
    print(f"   # 然后调用 analyze_csv_file('your_data.csv', ['text_column1', 'text_column2'])")


if __name__ == "__main__":
    main()
