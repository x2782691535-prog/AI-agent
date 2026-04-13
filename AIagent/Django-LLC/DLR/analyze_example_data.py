#!/usr/bin/env python
"""
分析docs/examples目录下的结构化数据文件
使用高级数据清洗功能进行分析并生成可视化结果
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DLR.settings')
import django
django.setup()

from lcc.data_cleaning.advanced_analyzer import AdvancedDataAnalyzer

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def analyze_kgs_csv():
    """分析kgs.csv文件"""
    print("🔍 正在分析 kgs.csv 文件")
    print("=" * 80)
    
    file_path = "docs/examples/kgs.csv"
    
    try:
        # 读取CSV文件
        df = pd.read_csv(file_path, encoding='utf-8')
        print(f"✅ 成功读取文件: {len(df)} 行 × {len(df.columns)} 列")
        print(f"📋 列名: {list(df.columns)}")
        
        # 显示前几行数据
        print(f"\n📊 数据预览:")
        print(df.head().to_string())
        
        # 创建分析器
        analyzer = AdvancedDataAnalyzer()
        
        # 进行综合分析，指定text列进行文本相似度分析
        report = analyzer.generate_comprehensive_report(df, text_columns=['text'])
        
        return df, report
        
    except Exception as e:
        print(f"❌ 分析kgs.csv失败: {e}")
        return None, None

def analyze_entity_xlsx():
    """分析实体1.xlsx文件"""
    print("\n🔍 正在分析 实体1.xlsx 文件")
    print("=" * 80)
    
    file_path = "docs/examples/实体1.xlsx"
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        print(f"✅ 成功读取文件: {len(df)} 行 × {len(df.columns)} 列")
        print(f"📋 列名: {list(df.columns)}")
        
        # 显示前几行数据
        print(f"\n📊 数据预览:")
        print(df.head().to_string())
        
        # 创建分析器
        analyzer = AdvancedDataAnalyzer()
        
        # 根据列名确定文本列
        text_columns = []
        for col in df.columns:
            if any(keyword in str(col).lower() for keyword in ['描述', 'description', 'text', '内容', '说明']):
                text_columns.append(col)
        
        print(f"📝 检测到文本列: {text_columns}")
        
        # 进行综合分析
        report = analyzer.generate_comprehensive_report(df, text_columns=text_columns)
        
        return df, report
        
    except Exception as e:
        print(f"❌ 分析实体1.xlsx失败: {e}")
        return None, None

def generate_visualization_summary(df, report, filename):
    """生成可视化总结"""
    print(f"\n📊 生成 {filename} 的可视化总结")
    print("=" * 60)
    
    dataset_info = report['dataset_info']
    missing_analysis = report['missing_analysis']
    outlier_analysis = report['outlier_analysis']
    duplicate_analysis = report['duplicate_analysis']
    
    # 1. 基本统计信息
    print(f"\n📋 数据集基本信息:")
    print(f"   - 文件名: {filename}")
    print(f"   - 总行数: {dataset_info['rows']:,}")
    print(f"   - 总列数: {dataset_info['columns']}")
    print(f"   - 分析时间: {dataset_info['analysis_time'][:19]}")
    
    # 2. 缺失值统计
    print(f"\n🔍 缺失值统计:")
    total_missing = 0
    missing_cols = []
    
    if missing_analysis['missing_by_column']:
        for col, info in missing_analysis['missing_by_column'].items():
            if info['count'] > 0:
                missing_cols.append(col)
                total_missing += info['count']
                print(f"   - {col}: {info['count']} 个缺失值 ({info['rate']:.2f}%)")
    
    if total_missing == 0:
        print("   ✅ 未发现缺失值")
    else:
        print(f"   📊 总计: {total_missing} 个缺失值，涉及 {len(missing_cols)} 列")
    
    # 3. 缺失值类型分析
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
    
    # 4. 异常值统计
    print(f"\n🚨 异常值统计:")
    total_outliers = 0
    outlier_cols = []
    
    if outlier_analysis['outliers_by_column']:
        for col, outliers in outlier_analysis['outliers_by_column'].items():
            # 计算总异常值数量（去重）
            all_outliers = set()
            all_outliers.update(outliers['iqr_outliers'])
            all_outliers.update(outliers['zscore_outliers'])
            all_outliers.update(outliers['isolation_outliers'])
            col_outliers = len(all_outliers)
            
            if col_outliers > 0:
                outlier_cols.append(col)
                total_outliers += col_outliers
                print(f"   - {col}: {col_outliers} 个异常值")
    
    if total_outliers == 0:
        print("   ✅ 未发现异常值")
    else:
        print(f"   📊 总计: {total_outliers} 个异常值，涉及 {len(outlier_cols)} 列")
    
    # 5. 重复值统计
    print(f"\n🔄 重复值统计:")
    
    exact_duplicates = 0
    if duplicate_analysis.get('exact_duplicates'):
        exact_duplicates = duplicate_analysis['exact_duplicates']['count']
        exact_rate = duplicate_analysis['exact_duplicates']['rate']
        print(f"   - 完全重复行: {exact_duplicates} 行 ({exact_rate:.2f}%)")
    else:
        print("   - 完全重复行: 0 行")
    
    # 关键特征重复
    key_duplicates = 0
    if duplicate_analysis.get('key_feature_duplicates'):
        for data_type, info in duplicate_analysis['key_feature_duplicates'].items():
            features = '+'.join(info['features'])
            count = info['count']
            key_duplicates += count
            print(f"   - 基于 {features} 的重复: {count} 行")
    
    # 文本相似度重复
    similar_groups = 0
    similar_rows = 0
    if duplicate_analysis.get('similarity_duplicates'):
        for col, info in duplicate_analysis['similarity_duplicates'].items():
            groups = len(info['groups'])
            rows = sum(len(group['indices']) for group in info['groups'])
            similar_groups += groups
            similar_rows += rows
            if groups > 0:
                print(f"   - {col} 相似文本: {groups} 组，涉及 {rows} 行")
    
    if similar_groups == 0:
        print("   - 文本相似度重复: 未发现")
    
    # 6. 数据质量评分
    quality_score = 100
    if total_missing > 0:
        missing_rate = total_missing / dataset_info['rows']
        quality_score -= missing_rate * 100
    
    if exact_duplicates > 0:
        duplicate_rate = (exact_duplicates / dataset_info['rows']) * 100
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
    
    # 7. 数据分布分析
    print(f"\n📊 数据分布分析:")
    
    # 分析关系数据的分布（如果是关系文件）
    if '关系' in df.columns or 'relation' in df.columns:
        relation_col = '关系' if '关系' in df.columns else 'relation'
        relation_counts = df[relation_col].value_counts().head(10)
        print(f"   关系类型分布 (前10):")
        for relation, count in relation_counts.items():
            print(f"   - {relation}: {count} 次")
    
    # 分析实体类型分布（如果是实体文件）
    if '类型' in df.columns or 'type' in df.columns:
        type_col = '类型' if '类型' in df.columns else 'type'
        type_counts = df[type_col].value_counts()
        print(f"   实体类型分布:")
        for entity_type, count in type_counts.items():
            print(f"   - {entity_type}: {count} 个")
    
    # 8. 处理建议
    print(f"\n💡 数据清洗建议:")
    recommendations = report.get('overall_recommendations', [])
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"   {i}. {rec}")
    
    return {
        'filename': filename,
        'total_rows': dataset_info['rows'],
        'total_columns': dataset_info['columns'],
        'missing_values': total_missing,
        'missing_columns': len(missing_cols),
        'outliers': total_outliers,
        'outlier_columns': len(outlier_cols),
        'exact_duplicates': exact_duplicates,
        'key_duplicates': key_duplicates,
        'similar_groups': similar_groups,
        'similar_rows': similar_rows,
        'quality_score': quality_score,
        'quality_level': quality_level
    }

def create_comparison_chart(summary1, summary2):
    """创建两个文件的对比图表"""
    print(f"\n📊 生成对比可视化图表")
    print("=" * 60)
    
    # 准备数据
    files = [summary1['filename'], summary2['filename']]
    metrics = {
        '数据行数': [summary1['total_rows'], summary2['total_rows']],
        '缺失值数': [summary1['missing_values'], summary2['missing_values']],
        '异常值数': [summary1['outliers'], summary2['outliers']],
        '重复值数': [summary1['exact_duplicates'], summary2['exact_duplicates']],
        '质量评分': [summary1['quality_score'], summary2['quality_score']]
    }
    
    # 创建对比表格
    print(f"\n📋 数据清洗结果对比表:")
    print("+" + "-" * 78 + "+")
    print(f"| {'指标':<15} | {files[0]:<25} | {files[1]:<25} |")
    print("+" + "-" * 78 + "+")
    
    for metric, values in metrics.items():
        if metric == '质量评分':
            print(f"| {metric:<15} | {values[0]:<23.1f} | {values[1]:<23.1f} |")
        else:
            print(f"| {metric:<15} | {values[0]:<25,} | {values[1]:<25,} |")
    
    print("+" + "-" * 78 + "+")
    
    # 生成处理建议对比
    print(f"\n💡 综合处理建议:")
    
    total_issues_1 = summary1['missing_values'] + summary1['outliers'] + summary1['exact_duplicates']
    total_issues_2 = summary2['missing_values'] + summary2['outliers'] + summary2['exact_duplicates']
    
    print(f"   📊 {files[0]}:")
    print(f"      - 数据质量: {summary1['quality_level']} ({summary1['quality_score']:.1f}/100)")
    print(f"      - 总问题数: {total_issues_1:,} 个")
    if total_issues_1 > 0:
        print(f"      - 建议: 需要进行数据清洗处理")
    else:
        print(f"      - 建议: 数据质量良好，可直接使用")
    
    print(f"   📊 {files[1]}:")
    print(f"      - 数据质量: {summary2['quality_level']} ({summary2['quality_score']:.1f}/100)")
    print(f"      - 总问题数: {total_issues_2:,} 个")
    if total_issues_2 > 0:
        print(f"      - 建议: 需要进行数据清洗处理")
    else:
        print(f"      - 建议: 数据质量良好，可直接使用")
    
    # 确定哪个文件质量更好
    if summary1['quality_score'] > summary2['quality_score']:
        print(f"   🏆 {files[0]} 的数据质量更好")
    elif summary2['quality_score'] > summary1['quality_score']:
        print(f"   🏆 {files[1]} 的数据质量更好")
    else:
        print(f"   ⚖️ 两个文件的数据质量相当")

def main():
    """主函数"""
    print("🚀 开始分析 docs/examples 目录下的结构化数据文件")
    print("=" * 80)
    print("本分析将使用高级数据清洗功能对以下文件进行分析:")
    print("1. kgs.csv - 关系数据文件")
    print("2. 实体1.xlsx - 实体数据文件")
    print("=" * 80)
    
    # 分析第一个文件
    df1, report1 = analyze_kgs_csv()
    
    # 分析第二个文件
    df2, report2 = analyze_entity_xlsx()
    
    if df1 is not None and report1 is not None and df2 is not None and report2 is not None:
        # 生成可视化总结
        summary1 = generate_visualization_summary(df1, report1, "kgs.csv")
        summary2 = generate_visualization_summary(df2, report2, "实体1.xlsx")
        
        # 创建对比图表
        create_comparison_chart(summary1, summary2)
        
        print(f"\n🎉 数据清洗分析完成!")
        print("=" * 80)
        print("📊 分析结果总结:")
        print(f"   ✅ 成功分析了 2 个结构化数据文件")
        print(f"   📋 生成了详细的数据质量报告")
        print(f"   🔍 识别了缺失值、异常值、重复值等数据质量问题")
        print(f"   💡 提供了针对性的数据清洗建议")
        print(f"   📊 生成了可视化的对比分析结果")
        
        return True
    else:
        print(f"\n❌ 分析过程中出现错误，请检查文件格式和内容")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
