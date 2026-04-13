# 🚀 DLR知识图谱系统部署指南

## 📋 部署方案对比

| 方案 | 难度 | 费用 | 性能 | 推荐度 |
|------|------|------|------|--------|
| PythonAnywhere | ⭐ | 免费/¥35月 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Heroku | ⭐⭐ | ¥35/月 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 云服务器 | ⭐⭐⭐ | ¥100/月 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Docker | ⭐⭐⭐⭐ | 服务器费用 | ⭐⭐⭐⭐⭐ | ⭐⭐ |

## 🎯 推荐部署方案

### 🥇 新手推荐: PythonAnywhere
- **优势**: 零配置，免费套餐，简单易用
- **适合**: 个人项目，学习演示
- **访问**: `yourusername.pythonanywhere.com`

### 🥈 进阶推荐: 阿里云/腾讯云
- **优势**: 完全控制，高性能，国内访问快
- **适合**: 正式项目，商业应用
- **访问**: 自定义域名

### 🥉 专业推荐: Docker + 云服务器
- **优势**: 容器化，易扩展，专业级
- **适合**: 大型项目，团队开发
- **访问**: 自定义域名 + HTTPS

## 📁 部署文件说明

```
DLR/
├── deployment/
│   ├── pythonanywhere_deploy.md    # PythonAnywhere部署指南
│   ├── heroku_deploy.md           # Heroku部署指南
│   ├── cloud_server_deploy.md     # 云服务器部署指南
│   └── deploy.sh                  # 自动部署脚本
├── Dockerfile                     # Docker镜像配置
├── docker-compose.yml            # Docker编排配置
├── nginx.conf                    # Nginx配置
├── .env.example                  # 环境变量示例
├── requirements.txt              # Python依赖
└── DLR/
    ├── settings_production.py    # 生产环境配置
    └── urls.py                   # 添加了健康检查
```

## 🚀 快速开始

### 1. 选择部署方案
```bash
# 新手用户
cd deployment
cat pythonanywhere_deploy.md

# 进阶用户
cat cloud_server_deploy.md

# 专业用户
cd ..
docker-compose up -d
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
nano .env
```

### 3. 部署应用
```bash
# 自动部署（云服务器）
chmod +x deployment/deploy.sh
./deployment/deploy.sh production

# 手动部署（按照对应指南）
```

## 🔧 部署后配置

### 1. 创建管理员账号
```bash
python manage.py createsuperuser
```

### 2. 配置Neo4j
```bash
# 安装Neo4j
# 配置连接信息
# 导入初始数据
```

### 3. 测试功能
- 访问 `/health/` 检查系统状态
- 访问 `/admin/` 管理后台
- 测试知识图谱构建功能
- 测试可视化功能

## 🌐 域名和HTTPS

### 1. 域名配置
```bash
# 购买域名
# 配置DNS解析
# 更新ALLOWED_HOSTS
```

### 2. SSL证书
```bash
# 免费证书（Let's Encrypt）
sudo certbot --nginx -d your-domain.com

# 或使用云服务商提供的证书
```

## 📊 监控和维护

### 1. 日志监控
```bash
# 查看应用日志
tail -f /var/www/dlr/logs/django.log

# 查看Nginx日志
tail -f /var/log/nginx/access.log
```

### 2. 性能监控
- 使用Sentry监控错误
- 配置邮件报警
- 定期备份数据库

### 3. 更新部署
```bash
# 使用自动部署脚本
./deployment/deploy.sh production

# 或手动更新
git pull
pip install -r requirements.txt
python manage.py migrate
sudo supervisorctl restart dlr
```

## 🆘 常见问题

### Q: 部署后无法访问？
A: 检查防火墙设置，确保80/443端口开放

### Q: 静态文件无法加载？
A: 运行 `python manage.py collectstatic`

### Q: 数据库连接失败？
A: 检查数据库配置和网络连接

### Q: Neo4j连接失败？
A: 确保Neo4j服务运行，检查连接配置

## 📞 技术支持

如果遇到部署问题，请：
1. 查看对应的部署指南
2. 检查日志文件
3. 确认环境配置
4. 联系技术支持

## 🎉 部署成功

部署成功后，您的知识图谱系统将具备：
- ✅ 文档上传和处理
- ✅ 知识图谱构建
- ✅ 图谱可视化
- ✅ 智能问答
- ✅ 用户管理
- ✅ 数据管理

**恭喜！您的知识图谱系统已成功部署上线！** 🎊
