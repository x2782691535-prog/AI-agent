#!/usr/bin/env python3
"""
测试知识库聊天功能的脚本
"""

import requests
import json
import time

def test_kb_chat():
    """测试知识库聊天功能"""
    
    print("=" * 60)
    print("测试知识库聊天功能")
    print("=" * 60)
    
    # API配置
    base_url = "http://127.0.0.1:7861"
    
    # 测试数据
    test_data = {
        "messages": [
            {
                "role": "user",
                "content": "什么是单片机？"
            }
        ],
        "model": "qwen2.5-7b-instruct",
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_k": 3,
        "score_threshold": 0.5
    }
    
    try:
        print("🚀 发送知识库聊天请求...")
        print(f"URL: {base_url}/chat/kb/local_kb/microcontroller")
        print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
        
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/chat/kb/local_kb/microcontroller",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        end_time = time.time()
        
        print(f"⏱️  请求耗时: {end_time - start_time:.2f} 秒")
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 请求成功!")
            print(f"📝 响应内容:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # 检查是否有错误
            if "error" in result:
                print(f"❌ 发现错误: {result['error']}")
                return False
            else:
                print("✅ 没有发现错误")
                return True
                
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误，请确保服务正在运行")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

def test_kb_list():
    """测试知识库列表"""
    
    print("\n" + "=" * 60)
    print("测试知识库列表")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:7861"
    
    try:
        print("🚀 获取知识库列表...")
        
        response = requests.get(
            f"{base_url}/knowledge_base/list_knowledge_bases",
            timeout=10
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 获取成功!")
            print(f"📝 知识库列表:")
            
            if "data" in result:
                for kb in result["data"]:
                    print(f"  - {kb}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

def test_simple_query():
    """测试简单查询"""
    
    print("\n" + "=" * 60)
    print("测试简单查询")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:7861"
    
    test_data = {
        "query": "单片机",
        "knowledge_base_name": "microcontroller",
        "top_k": 3,
        "score_threshold": 0.5
    }
    
    try:
        print("🚀 发送文档搜索请求...")
        
        response = requests.post(
            f"{base_url}/knowledge_base/search_docs",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 搜索成功!")
            print(f"📝 搜索结果:")
            
            if isinstance(result, list):
                print(f"找到 {len(result)} 个相关文档")
                for i, doc in enumerate(result[:2]):  # 只显示前2个
                    print(f"  文档 {i+1}:")
                    print(f"    内容: {doc.get('page_content', '')[:100]}...")
                    print(f"    来源: {doc.get('metadata', {}).get('source', 'unknown')}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

if __name__ == "__main__":
    print("开始测试知识库功能...")
    
    # 测试1: 知识库列表
    kb_list_success = test_kb_list()
    
    # 测试2: 简单查询
    if kb_list_success:
        search_success = test_simple_query()
        
        # 测试3: 知识库聊天
        if search_success:
            chat_success = test_kb_chat()
            
            if chat_success:
                print("\n🎉 所有测试通过！知识库功能正常工作。")
            else:
                print("\n❌ 知识库聊天测试失败。")
        else:
            print("\n❌ 文档搜索测试失败。")
    else:
        print("\n❌ 知识库列表测试失败。")
    
    print("\n测试完成。")
