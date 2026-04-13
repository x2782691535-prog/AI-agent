import json
import logging
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.utils import timezone
from .models import User, UserSession
from .utils import get_client_ip, generate_session_key

logger = logging.getLogger(__name__)


def login_page(request):
    """登录页面"""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'auth/login.html')


def register_page(request):
    """注册页面"""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'auth/register.html')


@csrf_exempt
@require_http_methods(["POST"])
def login_api(request):
    """登录API"""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        remember_me = data.get('remember_me', False)
        
        if not username or not password:
            return JsonResponse({
                'success': False,
                'message': '用户名和密码不能为空'
            })
        
        # 查找用户（支持用户名或邮箱登录）
        try:
            if '@' in username:
                user = User.objects.get(email=username, is_active=True)
            else:
                user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '用户名或密码错误'
            })
        
        # 验证密码
        if not user.check_password(password):
            return JsonResponse({
                'success': False,
                'message': '用户名或密码错误'
            })
        
        # 登录成功，创建会话
        login(request, user)
        
        # 设置会话过期时间
        if remember_me:
            request.session.set_expiry(30 * 24 * 60 * 60)  # 30天
        else:
            request.session.set_expiry(24 * 60 * 60)  # 24小时
        
        # 记录登录信息
        client_ip = get_client_ip(request)
        user.last_login_ip = client_ip
        user.last_login = timezone.now()
        user.save(update_fields=['last_login_ip', 'last_login'])
        
        # 创建会话记录
        UserSession.objects.create(
            user=user,
            session_key=request.session.session_key,
            ip_address=client_ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        logger.info(f"用户 {user.username} 登录成功，IP: {client_ip}")
        
        return JsonResponse({
            'success': True,
            'message': '登录成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'nickname': user.get_display_name(),
                'email': user.email,
                'avatar': user.avatar
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        })
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '登录失败，请稍后重试'
        })


@csrf_exempt
@require_http_methods(["POST"])
def register_api(request):
    """注册API"""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        nickname = data.get('nickname', '').strip()
        
        # 基本验证
        if not all([username, email, password, confirm_password]):
            return JsonResponse({
                'success': False,
                'message': '所有字段都是必填的'
            })
        
        if password != confirm_password:
            return JsonResponse({
                'success': False,
                'message': '两次输入的密码不一致'
            })
        
        if len(password) < 6:
            return JsonResponse({
                'success': False,
                'message': '密码长度至少6位'
            })
        
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'message': '用户名已存在'
            })
        
        # 检查邮箱是否已存在
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': '邮箱已被注册'
            })
        
        # 创建用户
        user = User.objects.create(
            username=username,
            email=email,
            nickname=nickname or username
        )
        user.set_password(password)
        user.save()
        
        logger.info(f"新用户注册成功: {username}")
        
        return JsonResponse({
            'success': True,
            'message': '注册成功，请登录'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        })
    except Exception as e:
        logger.error(f"注册异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '注册失败，请稍后重试'
        })


@require_http_methods(["POST"])
def logout_api(request):
    """登出API"""
    if request.user.is_authenticated:
        # 标记会话为非活跃
        try:
            session = UserSession.objects.get(
                session_key=request.session.session_key,
                is_active=True
            )
            session.is_active = False
            session.save()
        except UserSession.DoesNotExist:
            pass
        
        username = request.user.username
        logout(request)
        logger.info(f"用户 {username} 登出")
        
        return JsonResponse({
            'success': True,
            'message': '登出成功'
        })
    
    return JsonResponse({
        'success': False,
        'message': '用户未登录'
    })


@login_required
def user_info_api(request):
    """获取用户信息API"""
    user = request.user
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'nickname': user.get_display_name(),
            'email': user.email,
            'avatar': user.avatar,
            'total_conversations': user.total_conversations,
            'total_messages': user.total_messages,
            'preferred_model': user.preferred_model,
            'created_at': user.created_at.isoformat(),
        }
    })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_profile_api(request):
    """更新用户资料API"""
    try:
        data = json.loads(request.body)
        user = request.user
        
        # 可更新的字段
        updatable_fields = ['nickname', 'preferred_model']
        updated_fields = []
        
        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])
                updated_fields.append(field)
        
        if updated_fields:
            user.save(update_fields=updated_fields)
            
        return JsonResponse({
            'success': True,
            'message': '资料更新成功'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        })
    except Exception as e:
        logger.error(f"更新资料异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '更新失败，请稍后重试'
        })
