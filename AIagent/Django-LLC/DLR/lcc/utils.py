import hashlib
import secrets
import string
from django.core.cache import cache


def get_client_ip(request):
    """获取客户端真实IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_session_key(length=32):
    """生成会话密钥"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_token(user_id, timestamp):
    """生成用户令牌"""
    data = f"{user_id}:{timestamp}:{secrets.token_hex(16)}"
    return hashlib.sha256(data.encode()).hexdigest()


def rate_limit_check(key, limit=60, window=60):
    """简单的频率限制检查"""
    current_count = cache.get(key, 0)
    if current_count >= limit:
        return False
    
    cache.set(key, current_count + 1, window)
    return True


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def truncate_text(text, max_length=100, suffix="..."):
    """截断文本

    Args:
        text: 要截断的文本
        max_length: 最大长度，默认100字符
        suffix: 截断后的后缀，默认"..."
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def generate_conversation_title(first_message, max_length=50):
    """根据第一条消息生成对话标题"""
    if not first_message:
        return "新对话"
    
    # 清理消息内容
    title = first_message.strip()
    
    # 移除换行符
    title = title.replace('\n', ' ').replace('\r', ' ')
    
    # 截断长度
    if len(title) > max_length:
        title = title[:max_length] + "..."
    
    return title or "新对话"
