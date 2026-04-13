# 高级数据清洗功能使用指南

## 概述

本项目实现了高级数据清洗分析功能，包括：

1. **缺失值类型判断** - 自动识别MCAR、MAR、MNAR三种缺失类型
2. **多方法异常值检测** - 使用IQR、Z-Score、Isolation Forest等方法
3. **高级重复值检测** - 精确匹配、关键特征匹配、文本相似度匹配
4. **综合数据质量评估** - 自动计算质量分数并提供改进建议

## 功能特点

### 1. 缺失值类型判断

- **MCAR (完全随机缺失)**: 缺失与其他变量无关，可使用简单填充方法
- **MAR (随机缺失)**: 缺失与其他观察到的变量有关，建议使用预测模型填充
- **MNAR (非随机缺失)**: 缺失与变量自身值有关，需要专门的处理策略

### 2. 异常值检测方法

- **IQR方法**: 基于四分位数范围检测异常值
- **Z-Score方法**: 基于标准分数检测异常值
- **Isolation Forest**: 基于机器学习的异常检测

### 3. 重复值检测策略

- **精确匹配**: 检测完全相同的行
- **关键特征匹配**: 基于实体名+类型、源实体+关系+目标实体等关键特征
- **文本相似度**: 使用TF-IDF和余弦相似度检测相似文本

## 使用方法

### 1. 基本使用

```python
from lcc.data_cleaning.advanced_analyzer import AdvancedDataAnalyzer
import pandas as pd

# 读取数据
df = pd.read_csv('your_data.csv')

# 创建分析器
analyzer = AdvancedDataAnalyzer()

# 生成综合报告
report = analyzer.generate_comprehensive_report(
    df, 
    text_columns=['描述', '证据文本']  # 指定需要进行文本相似度分析的列
)
```

### 2. 单独分析功能

```python
# 只进行缺失值分析
missing_analysis = analyzer.analyze_missing_patterns(df)

# 只进行异常值检测
outlier_analysis = analyzer.detect_outliers(df)

# 只进行重复值检测
duplicate_analysis = analyzer.detect_duplicates_advanced(df, text_columns=['描述'])
```

### 3. 使用报告生成器

```python
# 使用专门的报告生成器
from data_cleaning_report_generator import analyze_csv_file, generate_summary_statistics

# 分析CSV文件
report = analyze_csv_file('data.csv', text_columns=['描述', '证据文本'])

# 生成汇总统计
summary = generate_summary_statistics(report)
```

## 输出结果说明

### 1. 缺失值分析结果

```
🔍 缺失值模式分析
📊 数据集基本信息:
   总行数: 200
   总列数: 5

📋 各列缺失值统计:
+-----------+--------+--------+
| 列名        |   缺失数量 | 缺失率    |
+===========+========+========+
| age       |     12 | 6.00%  |
| income    |     15 | 7.50%  |
| education |     20 | 10.00% |
+-----------+--------+--------+

🎯 缺失值类型评估:
   列 'age':
   - 缺失数量: 12 (6.00%)
   - 评估类型: MCAR
   - 置信度: 1.00
   - 原因分析: 缺失值在其他变量上的分布与非缺失值相似，可能是完全随机缺失
   - 建议处理: 可以使用均值/中位数/众数填充，或使用插值方法
```

### 2. 异常值检测结果

```
🚨 异常值检测分析
📊 检测 3 个数值型列的异常值
+---------------+-------+--------+--------+-------------------------+
| 列名            |   数据量 |   异常值数 | 异常率    | IQR/Z-Score/Isolation   |
+===============+=======+========+========+=========================+
| with_outliers |   100 |     10 | 10.00% | 10 / 4 / 10             |
+---------------+-------+--------+--------+-------------------------+
```

### 3. 重复值检测结果

```
🔄 高级重复值检测分析
📋 精确重复检测:
   完全重复行数: 1 (5.00%)

🔑 关键特征重复检测:
   基于 实体名+类型 的重复: 1 行

📝 文本相似度检测:
   列 '描述' 相似文本组数: 1
   涉及行数: 3
```

### 4. 综合质量评估

```
💯 数据质量评分: 75.0/100
   数据质量等级: 🟡 良好

💡 主要处理建议:
   1. 列 age, income 为完全随机缺失，可使用简单填充方法
   2. 发现 1 行完全重复数据，建议直接删除
   3. 发现 1 组相似文本，建议人工核验后决定是否合并
```

## 在报告中的应用

### 1. 数据预处理章节

可以在研究报告的数据预处理章节中包含以下内容：

```
数据清洗过程统计：
- 原始数据：1000行 × 8列
- 处理缺失值：45个（涉及3列）
  * 完全随机缺失(MCAR)：2列，使用中位数填充
  * 随机缺失(MAR)：1列，使用回归预测填充
- 检测异常值：12个（涉及2列）
  * 数据录入错误：8个，已修正
  * 真实离群值：4个，保留并标记
- 处理重复值：8个完全重复行，已删除
- 文本相似度去重：3组相似描述，人工核验后合并
- 最终数据质量评分：87.5/100（良好）
```

### 2. 数据质量评估表格

| 数据质量指标 | 原始数据 | 清洗后数据 | 改善程度 |
|------------|---------|-----------|---------|
| 缺失值数量 | 45个 | 0个 | 100% |
| 异常值数量 | 12个 | 4个 | 67% |
| 重复值数量 | 8个 | 0个 | 100% |
| 质量评分 | 65.2/100 | 87.5/100 | +22.3 |

## 命令行使用

### 1. 运行完整演示

```bash
cd DLR
python advanced_data_cleaning_demo.py
```

### 2. 生成报告

```bash
cd DLR
python data_cleaning_report_generator.py
```

### 3. 分析自己的数据

```python
# 在Python脚本中
from data_cleaning_report_generator import analyze_csv_file

# 分析实体数据
entity_report = analyze_csv_file('entities.csv', text_columns=['描述'])

# 分析关系数据  
relation_report = analyze_csv_file('relations.csv', text_columns=['证据文本'])
```

## 配置选项

### 1. 相似度阈值调整

```python
analyzer = AdvancedDataAnalyzer()
analyzer.similarity_threshold = 0.9  # 默认0.8，越高越严格
```

### 2. 异常值检测参数

```python
# 可以在_detect_column_outliers方法中调整参数
# IQR倍数：默认1.5
# Z-Score阈值：默认3
# Isolation Forest污染率：默认0.1
```

## 注意事项

1. **数据量要求**: 建议数据量至少10行以上，否则统计分析可能不准确
2. **中文支持**: 已配置中文字体支持，可正常显示中文图表
3. **内存使用**: 大数据集（>10万行）可能需要较多内存
4. **文本相似度**: 仅支持字符串类型的文本列
5. **异常值检测**: 仅对数值型列进行异常值检测

## 依赖包

确保安装以下依赖包：

```
pandas==2.0.3
numpy==1.24.4
scipy==1.10.1
scikit-learn==1.3.2
matplotlib==3.7.5
seaborn==0.13.2
tabulate==0.9.0
```

## 技术支持

如有问题，请检查：
1. 数据格式是否正确（CSV，UTF-8编码）
2. 列名是否包含特殊字符
3. 数据类型是否符合预期
4. 依赖包是否正确安装
