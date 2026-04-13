# Heroku 部署指南

## 🌟 优势
- ✅ 专业级部署
- ✅ 自动扩展
- ✅ 丰富的插件
- ✅ Git集成

## 📋 部署步骤

### 1. 安装Heroku CLI
```bash
# Windows
# 下载并安装: https://devcenter.heroku.com/articles/heroku-cli

# macOS
brew tap heroku/brew && brew install heroku

# Ubuntu
sudo snap install --classic heroku
```

### 2. 登录Heroku
```bash
heroku login
```

### 3. 创建应用
```bash
cd DLR
heroku create your-app-name
```

### 4. 配置环境变量
```bash
heroku config:set DEBUG=False
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set ALLOWED_HOSTS="your-app-name.herokuapp.com"
```

### 5. 添加数据库
```bash
# 添加PostgreSQL数据库
heroku addons:create heroku-postgresql:mini
```

### 6. 部署代码
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### 7. 运行迁移
```bash
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### 8. 访问应用
```bash
heroku open
```

## 💰 费用
- Eco Dyno: $5/月
- Basic Dyno: $7/月
- 数据库: $5/月起
