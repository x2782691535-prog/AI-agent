#!/usr/bin/env python
"""
高级数据清洗功能演示
展示缺失值类型判断、异常值检测、重复值识别等功能
"""

import os
import sys
import tempfile
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


def create_sample_data_with_issues():
    """创建包含各种数据质量问题的示例数据"""
    
    # 创建实体数据
    entity_data = {
        '实体名': [
            '张三', '李四', '王五', '张三',  # 重复
            '', None, '赵六', '钱七',  # 缺失值
            '孙八', '周九', '吴十', '郑十一',
            '王十二', '李十三', '张十四', '刘十五',
            '陈十六', '杨十七', '黄十八', '赵十九'
        ],
        '类型': [
            '人物', '人物', '人物', '人物',
            '人物', '人物', '', '人物',  # 缺失值
            '人物', '人物', '组织', '组织',
            '地点', '地点', '地点', '地点',
            '事件', '事件', '概念', '概念'
        ],
        '年龄': [
            25, 30, 35, 25,  # 重复
            np.nan, 28, 45, 32,  # 缺失值
            29, 31, np.nan, 40,
            150, -5, 33, 27,  # 异常值
            26, 38, 42, 29
        ],
        '描述': [
            '软件工程师，专注于AI开发',
            '数据科学家，擅长机器学习',
            '产品经理，负责产品规划',
            '软件工程师，专注于AI开发',  # 重复
            '', None, '项目经理，管理团队',
            '软件工程师，专注于人工智能开发',  # 相似文本
            '系统架构师', '前端开发工程师',
            '北京大学计算机学院', '清华大学软件学院',
            '北京市海淀区', '上海市浦东新区',
            '深圳市南山区', '广州市天河区',
            '人工智能大会', 'AI技术峰会',
            '机器学习概念', '深度学习理论'
        ]
    }
    
    # 创建关系数据
    relation_data = {
        '源实体': [
            '张三', '李四', '王五', '张三',  # 重复关系
            '', None, '赵六', '钱七',  # 缺失值
            '孙八', '周九', '吴十', '郑十一'
        ],
        '关系': [
            '工作于', '研究于', '管理', '工作于',  # 重复
            '学习于', '毕业于', '', '隶属于',  # 缺失值
            '位于', '参与', '开发', '发表'
        ],
        '目标实体': [
            '北京大学', '清华大学', '某科技公司', '北京大学',  # 重复
            '中科院', '', '某研究所', None,  # 缺失值
            '北京市', '人工智能大会', '推荐系统', '学术论文'
        ],
        '证据文本': [
            '张三在北京大学计算机学院工作',
            '李四在清华大学进行机器学习研究',
            '王五管理某科技公司的产品团队',
            '张三在北京大学计算机学院工作',  # 重复
            '', None, '赵六在某研究所担任项目经理',
            '钱七隶属于某技术部门',  # 相似文本
            '孙八位于北京市海淀区',
            '周九参与了人工智能大会的组织工作',
            '吴十开发了一套推荐系统',
            '郑十一发表了关于深度学习的学术论文'
        ]
    }
    
    return pd.DataFrame(entity_data), pd.DataFrame(relation_data)


def demo_missing_value_analysis():
    """演示缺失值分析功能"""
    print("\n" + "🎯" * 30)
    print("缺失值类型判断演示 (MCAR/MAR/MNAR)")
    print("🎯" * 30)
    
    # 创建包含不同类型缺失值的数据
    np.random.seed(42)
    n_samples = 200
    
    # 创建基础数据
    data = {
        'id': range(1, n_samples + 1),
        'age': np.random.normal(35, 10, n_samples),
        'income': np.random.normal(50000, 15000, n_samples),
        'education': np.random.choice(['高中', '本科', '硕士', '博士'], n_samples),
        'city': np.random.choice(['北京', '上海', '广州', '深圳'], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # 1. 创建MCAR缺失值（完全随机）
    mcar_indices = np.random.choice(df.index, size=20, replace=False)
    df.loc[mcar_indices, 'education'] = np.nan
    
    # 2. 创建MAR缺失值（与其他变量相关）
    # 高收入人群更可能不透露收入信息
    high_income_indices = df[df['income'] > 60000].index
    mar_indices = np.random.choice(high_income_indices, size=15, replace=False)
    df.loc[mar_indices, 'income'] = np.nan
    
    # 3. 创建MNAR缺失值（与自身值相关）
    # 年龄较大的人更可能不透露年龄
    old_age_indices = df[df['age'] > 50].index
    mnar_indices = np.random.choice(old_age_indices, size=12, replace=False)
    df.loc[mnar_indices, 'age'] = np.nan
    
    # 执行分析
    analyzer = AdvancedDataAnalyzer()
    missing_analysis = analyzer.analyze_missing_patterns(df)
    
    return missing_analysis


def demo_outlier_detection():
    """演示异常值检测功能"""
    print("\n" + "🚨" * 30)
    print("异常值检测演示")
    print("🚨" * 30)
    
    # 创建包含异常值的数据
    np.random.seed(42)
    n_samples = 100
    
    data = {
        'normal_data': np.random.normal(50, 10, n_samples),
        'with_outliers': np.concatenate([
            np.random.normal(50, 10, 90),
            [150, 200, -50, -100, 300, 250, -80, 180, 220, -60]  # 异常值
        ]),
        'skewed_data': np.random.exponential(2, n_samples),
        'categorical': np.random.choice(['A', 'B', 'C'], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # 执行异常值检测
    analyzer = AdvancedDataAnalyzer()
    outlier_analysis = analyzer.detect_outliers(df)
    
    return outlier_analysis


def demo_duplicate_detection():
    """演示重复值检测功能"""
    print("\n" + "🔄" * 30)
    print("高级重复值检测演示")
    print("🔄" * 30)
    
    entity_df, relation_df = create_sample_data_with_issues()
    
    analyzer = AdvancedDataAnalyzer()
    
    print("=" * 50)
    print("实体数据重复检测")
    print("=" * 50)
    
    # 检测实体数据的重复值
    entity_duplicates = analyzer.detect_duplicates_advanced(
        entity_df, 
        text_columns=['描述']
    )
    
    print("\n" + "=" * 50)
    print("关系数据重复检测")
    print("=" * 50)
    
    # 检测关系数据的重复值
    relation_duplicates = analyzer.detect_duplicates_advanced(
        relation_df,
        text_columns=['证据文本']
    )
    
    return entity_duplicates, relation_duplicates


def demo_comprehensive_analysis():
    """演示综合数据清洗分析"""
    print("\n" + "📊" * 30)
    print("综合数据清洗分析演示")
    print("📊" * 30)
    
    entity_df, relation_df = create_sample_data_with_issues()
    
    analyzer = AdvancedDataAnalyzer()
    
    print("=" * 60)
    print("实体数据综合分析")
    print("=" * 60)
    
    # 对实体数据进行综合分析
    entity_report = analyzer.generate_comprehensive_report(
        entity_df,
        text_columns=['描述']
    )
    
    print("\n" + "=" * 60)
    print("关系数据综合分析")
    print("=" * 60)
    
    # 对关系数据进行综合分析
    relation_report = analyzer.generate_comprehensive_report(
        relation_df,
        text_columns=['证据文本']
    )
    
    return entity_report, relation_report


def main():
    """主函数"""
    print("🚀 高级数据清洗功能演示")
    print("=" * 80)
    print("本演示将展示以下功能:")
    print("1. 缺失值类型判断 (MCAR/MAR/MNAR)")
    print("2. 多方法异常值检测 (IQR/Z-Score/Isolation Forest)")
    print("3. 高级重复值检测 (精确匹配/关键特征/文本相似度)")
    print("4. 综合数据质量分析")
    print("=" * 80)
    
    try:
        # 1. 缺失值分析演示
        missing_analysis = demo_missing_value_analysis()
        
        # 2. 异常值检测演示
        outlier_analysis = demo_outlier_detection()
        
        # 3. 重复值检测演示
        entity_duplicates, relation_duplicates = demo_duplicate_detection()
        
        # 4. 综合分析演示
        entity_report, relation_report = demo_comprehensive_analysis()
        
        print("\n" + "🎉" * 30)
        print("演示完成总结")
        print("🎉" * 30)
        
        print("\n✅ 功能验证完成:")
        print("   1. ✅ 缺失值类型自动判断 (MCAR/MAR/MNAR)")
        print("   2. ✅ 多方法异常值检测")
        print("   3. ✅ 精确和模糊重复检测")
        print("   4. ✅ 文本相似度分析")
        print("   5. ✅ 综合数据质量评估")
        print("   6. ✅ 智能处理建议生成")
        
        print("\n📊 分析结果特点:")
        print("   - 终端表格化输出，清晰易读")
        print("   - 多维度数据质量评估")
        print("   - 基于统计学的缺失值类型判断")
        print("   - 多算法融合的异常值检测")
        print("   - 基于TF-IDF的文本相似度计算")
        print("   - 针对性的数据清洗建议")
        
        print("\n🔧 使用方法:")
        print("   from lcc.data_cleaning.advanced_analyzer import AdvancedDataAnalyzer")
        print("   analyzer = AdvancedDataAnalyzer()")
        print("   report = analyzer.generate_comprehensive_report(df, text_columns=['描述'])")
        
        return True
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
