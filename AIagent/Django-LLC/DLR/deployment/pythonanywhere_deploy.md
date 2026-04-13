# PythonAnywhere 部署指南

## 🌟 优势
- ✅ 免费套餐可用
- ✅ 零配置服务器
- ✅ 自动HTTPS
- ✅ 简单易用

## 📋 部署步骤

### 1. 注册账号
1. 访问 https://www.pythonanywhere.com/
2. 注册免费账号
3. 登录控制台

### 2. 上传代码
```bash
# 方法1: 使用Git（推荐）
git clone https://github.com/yourusername/DLR.git

# 方法2: 直接上传文件
# 在Files页面上传项目文件
```

### 3. 安装依赖
```bash
# 在Console中执行
cd DLR
pip3.10 install --user -r requirements.txt
```

### 4. 配置数据库
```bash
# 创建数据库
python manage.py migrate
python manage.py createsuperuser
```

### 5. 配置Web应用
1. 进入Web页面
2. 点击"Add a new web app"
3. 选择Django
4. 设置项目路径: `/home/yourusername/DLR`
5. 设置WSGI文件路径: `/home/yourusername/DLR/DLR/wsgi.py`

### 6. 配置静态文件
```python
# 在WSGI配置中添加
import os
import sys

path = '/home/yourusername/DLR'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'DLR.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 7. 访问网站
- 免费域名: `yourusername.pythonanywhere.com`
- 自定义域名: 付费套餐支持

## 💰 费用
- 免费套餐: 1个Web应用，512MB存储
- 付费套餐: $5/月起，更多资源和功能
