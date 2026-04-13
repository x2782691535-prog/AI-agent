#!/usr/bin/env python3
"""
RAG检索诊断工具

用于诊断为什么RAG检索时会匹配到整个文档的所有内容。
"""

import requests
import json
import os
from pathlib import Path

def diagnose_knowledge_base(kb_name: str = "microcontroller"):
    """诊断知识库的文档分块情况"""
    
    print("=" * 80)
    print("知识库文档分块诊断")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:7861"
    
    # 1. 检查知识库基本信息
    print("🔍 步骤1: 检查知识库基本信息")
    try:
        response = requests.get(f"{base_url}/knowledge_base/list_knowledge_bases")
        if response.status_code == 200:
            kbs = response.json()
            target_kb = None
            for kb in kbs.get("data", []):
                if kb["kb_name"] == kb_name:
                    target_kb = kb
                    break
            
            if target_kb:
                print(f"✅ 找到知识库: {kb_name}")
                print(f"   📊 文件数量: {target_kb['file_count']}")
                print(f"   🧠 嵌入模型: {target_kb['embed_model']}")
                print(f"   🗄️  向量类型: {target_kb['vs_type']}")
            else:
                print(f"❌ 未找到知识库: {kb_name}")
                return False
        else:
            print(f"❌ 获取知识库列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 检查知识库信息失败: {e}")
        return False
    
    # 2. 检查知识库文件列表
    print(f"\n🔍 步骤2: 检查知识库文件列表")
    try:
        response = requests.get(f"{base_url}/knowledge_base/list_files", 
                              params={"knowledge_base_name": kb_name})
        if response.status_code == 200:
            files = response.json()
            print(f"✅ 知识库文件:")
            for file_info in files.get("data", []):
                print(f"   📄 {file_info['file_name']}")
                print(f"      大小: {file_info.get('file_size', 'unknown')}")
                print(f"      修改时间: {file_info.get('file_mtime', 'unknown')}")
        else:
            print(f"❌ 获取文件列表失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 检查文件列表失败: {e}")
    
    # 3. 测试文档检索 - 不同的查询
    print(f"\n🔍 步骤3: 测试文档检索")
    
    test_queries = [
        {"query": "单片机", "top_k": 3, "description": "基础查询"},
        {"query": "单片机", "top_k": 1, "description": "限制返回1个结果"},
        {"query": "单片机原理", "top_k": 5, "description": "具体查询"},
        {"query": "C51编程", "top_k": 3, "description": "编程相关查询"},
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n   🧪 测试{i}: {test['description']}")
        print(f"      查询: '{test['query']}'")
        print(f"      top_k: {test['top_k']}")
        
        try:
            search_data = {
                "query": test["query"],
                "knowledge_base_name": kb_name,
                "top_k": test["top_k"],
                "score_threshold": 0.5
            }
            
            response = requests.post(
                f"{base_url}/knowledge_base/search_docs",
                json=search_data,
                timeout=15
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"      ✅ 返回 {len(results)} 个结果")
                
                for j, doc in enumerate(results):
                    content_length = len(doc.get("page_content", ""))
                    source = doc.get("metadata", {}).get("source", "unknown")
                    
                    print(f"         📄 文档{j+1}:")
                    print(f"            长度: {content_length} 字符")
                    print(f"            来源: {source}")
                    
                    # 检查是否是超长文档（可能是整个PDF内容）
                    if content_length > 10000:
                        print(f"            ⚠️  警告: 文档过长，可能是整个PDF内容")
                        print(f"            预览: {doc.get('page_content', '')[:200]}...")
                    elif content_length > 0:
                        print(f"            预览: {doc.get('page_content', '')[:150]}...")
                    else:
                        print(f"            ❌ 文档内容为空")
                        
            else:
                print(f"      ❌ 检索失败: {response.status_code}")
                print(f"         错误: {response.text}")
                
        except Exception as e:
            print(f"      ❌ 测试失败: {e}")
    
    # 4. 检查文档分块配置
    print(f"\n🔍 步骤4: 分析可能的问题")
    
    # 检查配置文件
    config_files = [
        "Langchain-Chatchat/kb_settings.yaml",
        "Langchain-Chatchat/basic_settings.yaml"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"\n📋 检查配置文件: {config_file}")
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 查找相关配置
                relevant_configs = [
                    "CHUNK_SIZE", "OVERLAP_SIZE", "TEXT_SPLITTER",
                    "VECTOR_SEARCH_TOP_K", "SCORE_THRESHOLD"
                ]
                
                for config in relevant_configs:
                    if config in content:
                        lines = content.split('\n')
                        for line in lines:
                            if config in line and not line.strip().startswith('#'):
                                print(f"   {line.strip()}")
                                
            except Exception as e:
                print(f"   ❌ 读取配置文件失败: {e}")
    
    return True

def suggest_solutions():
    """提供解决方案建议"""
    
    print(f"\n💡 问题分析和解决方案:")
    print("=" * 80)
    
    print("🔍 常见问题和解决方案:")
    
    print("\n1. 📄 文档分块问题:")
    print("   问题: 整个PDF被当作一个大文档块")
    print("   原因: 文档切分器配置不当或失效")
    print("   解决: 调整CHUNK_SIZE和OVERLAP_SIZE参数")
    print("   建议配置:")
    print("     CHUNK_SIZE: 500-1000")
    print("     OVERLAP_SIZE: 50-150")
    
    print("\n2. 🎯 检索参数问题:")
    print("   问题: top_k设置过大，返回太多结果")
    print("   解决: 调整检索参数")
    print("   建议配置:")
    print("     top_k: 3-5")
    print("     score_threshold: 0.3-0.7")
    
    print("\n3. 🔄 向量库重建:")
    print("   问题: 向量库中存储的是未分块的大文档")
    print("   解决: 重新处理PDF并重建向量库")
    print("   步骤:")
    print("     1. 删除现有向量库")
    print("     2. 调整分块参数")
    print("     3. 重新处理PDF文档")
    
    print("\n4. 🧪 测试和验证:")
    print("   - 使用小的top_k值测试")
    print("   - 检查返回文档的长度")
    print("   - 验证文档内容是否相关")
    
    print("\n🔧 立即可执行的解决步骤:")
    print("1. 检查kb_settings.yaml中的CHUNK_SIZE设置")
    print("2. 如果CHUNK_SIZE过大，调整为500-1000")
    print("3. 重新处理PDF文档以应用新的分块设置")
    print("4. 测试检索效果")

def main():
    """主函数"""
    
    print("🔍 开始RAG检索诊断...")
    
    kb_name = "microcontroller"
    
    success = diagnose_knowledge_base(kb_name)
    
    if success:
        suggest_solutions()
    
    print(f"\n📋 诊断完成。")
    print("请根据诊断结果调整配置或重新处理文档。")

if __name__ == "__main__":
    main()
