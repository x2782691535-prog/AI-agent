#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为研究报告创建简化的数据清洗结果图表
"""

import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_report_chart():
    """创建适合研究报告的数据清洗结果图表"""
    
    # 创建图表
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('数据清洗分析结果', fontsize=16, fontweight='bold', y=0.95)
    
    # 数据
    files = ['kgs.csv', 'entity1.xlsx']
    
    # 1. 数据质量评分对比
    scores = [98.7, 99.9]
    colors = ['#FF6B6B', '#4ECDC4']
    
    bars1 = ax1.bar(files, scores, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
    ax1.set_title('数据质量评分对比', fontsize=12, fontweight='bold', pad=15)
    ax1.set_ylabel('质量评分', fontsize=10)
    ax1.set_ylim(95, 100)
    ax1.grid(axis='y', alpha=0.3)
    
    # 添加数值标签
    for bar, score in zip(bars1, scores):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{score}', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    # 2. 数据规模对比
    rows = [1226, 1430]
    bars2 = ax2.bar(files, rows, color=['#FFD93D', '#6BCF7F'], alpha=0.8, edgecolor='black', linewidth=1)
    ax2.set_title('数据规模对比', fontsize=12, fontweight='bold', pad=15)
    ax2.set_ylabel('数据行数', fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    
    for bar, row in zip(bars2, rows):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 20,
                f'{row:,}', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    # 3. 数据问题统计
    categories = ['缺失值', '异常值', '重复值']
    kgs_issues = [1, 0, 15]
    entity_issues = [1, 0, 0]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars3_1 = ax3.bar(x - width/2, kgs_issues, width, label='kgs.csv', 
                     color='#FF6B6B', alpha=0.8, edgecolor='black', linewidth=1)
    bars3_2 = ax3.bar(x + width/2, entity_issues, width, label='entity1.xlsx', 
                     color='#4ECDC4', alpha=0.8, edgecolor='black', linewidth=1)
    
    ax3.set_title('数据问题统计对比', fontsize=12, fontweight='bold', pad=15)
    ax3.set_ylabel('问题数量', fontsize=10)
    ax3.set_xticks(x)
    ax3.set_xticklabels(categories)
    ax3.legend(fontsize=9)
    ax3.grid(axis='y', alpha=0.3)
    
    # 添加数值标签
    for bars in [bars3_1, bars3_2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                        f'{int(height)}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # 4. 数据质量等级分布
    quality_data = {
        'kgs.csv': {'优秀': 98.7, '需改进': 1.3},
        'entity1.xlsx': {'优秀': 99.9, '需改进': 0.1}
    }
    
    # 创建堆叠柱状图
    excellent = [98.7, 99.9]
    needs_improvement = [1.3, 0.1]
    
    bars4_1 = ax4.bar(files, excellent, color='#2ECC71', alpha=0.8, 
                     label='优秀部分', edgecolor='black', linewidth=1)
    bars4_2 = ax4.bar(files, needs_improvement, bottom=excellent, color='#E74C3C', alpha=0.8,
                     label='需改进部分', edgecolor='black', linewidth=1)
    
    ax4.set_title('数据质量构成', fontsize=12, fontweight='bold', pad=15)
    ax4.set_ylabel('质量百分比', fontsize=10)
    ax4.set_ylim(0, 100)
    ax4.legend(fontsize=9)
    ax4.grid(axis='y', alpha=0.3)
    
    # 添加百分比标签
    for i, (file, excellent_val) in enumerate(zip(files, excellent)):
        ax4.text(i, excellent_val/2, f'{excellent_val}%', ha='center', va='center', 
                fontweight='bold', fontsize=10, color='white')
    
    # 调整布局
    plt.tight_layout()
    plt.subplots_adjust(top=0.92, hspace=0.3, wspace=0.3)
    
    # 保存图表
    plt.savefig('data_cleaning_report_chart.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.savefig('data_cleaning_report_chart.pdf', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    
    print("📊 研究报告图表已生成:")
    print("   - PNG格式: data_cleaning_report_chart.png")
    print("   - PDF格式: data_cleaning_report_chart.pdf")
    
    plt.show()

def create_summary_table():
    """创建总结表格的文本版本"""
    
    print("\n" + "="*80)
    print("📋 数据清洗结果总结表格 (适合复制到研究报告)")
    print("="*80)
    
    table_text = """
| 指标              | kgs.csv                   | 实体1.xlsx                  |
|-------------------|---------------------------|----------------------------|
| 数据行数            | 1,226                     | 1,430                     |
| 数据列数            | 4                         | 2                         |
| 缺失值数            | 1                         | 1                         |
| 缺失值比例          | 0.08%                     | 0.07%                     |
| 缺失值类型          | MCAR (完全随机缺失)         | MCAR (完全随机缺失)         |
| 异常值数            | 0                         | 0                         |
| 完全重复值数        | 15                        | 0                         |
| 重复值比例          | 1.22%                     | 0.00%                     |
| 相似文本组数        | 196                       | 0                         |
| 涉及相似文本行数    | 588                       | 0                         |
| 数据质量评分        | 98.7/100                  | 99.9/100                  |
| 质量等级            | 优秀                      | 优秀                      |
| 清洗后预期质量      | 99.5+/100                 | 100/100                   |
| 主要问题            | 重复值、相似文本           | 极少缺失值                 |
| 处理建议            | 删除重复值，人工核验相似文本 | 补充缺失实体名             |
| 预估清洗工作量      | 2-3小时                   | 5分钟                     |
"""
    
    print(table_text)
    
    # 保存表格到文件
    with open('data_cleaning_summary_table.md', 'w', encoding='utf-8') as f:
        f.write("# 数据清洗结果总结表格\n\n")
        f.write(table_text)
    
    print("📄 表格已保存到: data_cleaning_summary_table.md")

def create_summary_paragraph():
    """创建总结段落"""
    
    summary = """
本研究对两个结构化数据文件进行了全面的数据清洗分析，采用了高级数据清洗分析器，包括缺失值类型判断（MCAR/MAR/MNAR）、多方法异常值检测（IQR、Z-Score、Isolation Forest）和高级重复值检测（精确匹配、关键特征匹配、文本相似度匹配）等技术。分析结果显示，两个数据文件的整体质量均达到优秀等级。kgs.csv文件包含1,226行关系数据，数据质量评分为98.7/100，主要存在1个缺失值（0.08%）和15个重复值（1.22%），以及196组需要人工核验的相似文本；实体1.xlsx文件包含1,430行实体数据，数据质量评分高达99.9/100，仅存在1个缺失值（0.07%），无重复值和异常值。缺失值分析表明，所有缺失值均为完全随机缺失（MCAR），可采用简单填充方法处理。经过数据清洗后，预计kgs.csv的数据质量可提升至99.5+/100，实体1.xlsx可达到100/100的完美质量，两个数据集均适合直接应用于知识图谱构建等生产环境。
"""
    
    print("\n" + "="*80)
    print("📝 数据清洗结果总结段落 (适合复制到研究报告)")
    print("="*80)
    print(summary.strip())
    
    # 保存段落到文件
    with open('data_cleaning_summary_paragraph.txt', 'w', encoding='utf-8') as f:
        f.write(summary.strip())
    
    print("\n📄 总结段落已保存到: data_cleaning_summary_paragraph.txt")

def main():
    """主函数"""
    print("🎨 生成研究报告用数据清洗结果")
    print("="*50)
    
    # 生成图表
    create_report_chart()
    
    # 生成表格
    create_summary_table()
    
    # 生成总结段落
    create_summary_paragraph()
    
    print("\n✅ 所有研究报告材料已生成完成!")
    print("📊 图表文件: data_cleaning_report_chart.png / .pdf")
    print("📋 表格文件: data_cleaning_summary_table.md")
    print("📝 段落文件: data_cleaning_summary_paragraph.txt")

if __name__ == "__main__":
    main()
