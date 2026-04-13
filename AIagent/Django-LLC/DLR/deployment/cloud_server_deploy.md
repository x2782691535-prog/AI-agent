# 云服务器部署指南（阿里云/腾讯云）

## 🌟 优势
- ✅ 完全控制
- ✅ 高性能
- ✅ 可扩展
- ✅ 国内访问快

## 📋 部署步骤

### 1. 购买服务器
- **阿里云ECS**: https://ecs.console.aliyun.com/
- **腾讯云CVM**: https://console.cloud.tencent.com/cvm
- 推荐配置: 2核4G，Ubuntu 20.04

### 2. 连接服务器
```bash
# 使用SSH连接
ssh root@your-server-ip
```

### 3. 安装基础环境
```bash
# 更新系统
apt update && apt upgrade -y

# 安装Python和依赖
apt install python3 python3-pip python3-venv nginx supervisor git -y

# 安装MySQL
apt install mysql-server mysql-client libmysqlclient-dev -y
```

### 4. 配置MySQL
```bash
# 安全配置
mysql_secure_installation

# 创建数据库
mysql -u root -p
CREATE DATABASE dlr_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'dlr_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON dlr_db.* TO 'dlr_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. 部署应用
```bash
# 创建应用目录
mkdir -p /var/www/dlr
cd /var/www/dlr

# 克隆代码
git clone https://github.com/yourusername/DLR.git .

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn mysqlclient
```

### 6. 配置Django
```bash
# 收集静态文件
python manage.py collectstatic --noinput

# 运行迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

### 7. 配置Gunicorn
```bash
# 测试Gunicorn
gunicorn --bind 0.0.0.0:8000 DLR.wsgi:application
```

### 8. 配置Nginx
```nginx
# /etc/nginx/sites-available/dlr
server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /var/www/dlr;
    }
    
    location /media/ {
        root /var/www/dlr;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/dlr/dlr.sock;
    }
}
```

### 9. 配置Supervisor
```ini
# /etc/supervisor/conf.d/dlr.conf
[program:dlr]
command=/var/www/dlr/venv/bin/gunicorn --workers 3 --bind unix:/var/www/dlr/dlr.sock DLR.wsgi:application
directory=/var/www/dlr
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/dlr.log
```

### 10. 启动服务
```bash
# 启用站点
ln -s /etc/nginx/sites-available/dlr /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 启动Supervisor
supervisorctl reread
supervisorctl update
supervisorctl start dlr
```

## 💰 费用
- 服务器: ¥100-300/月
- 域名: ¥50-100/年
- SSL证书: 免费（Let's Encrypt）
