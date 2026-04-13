#!/usr/bin/env python3
"""
重建向量库工具

用于删除现有向量库并重新处理文档，解决文档分块问题。
"""

import os
import shutil
import requests
import json
import time

def rebuild_vector_store(kb_name: str = "microcontroller"):
    """重建向量库"""
    
    print("=" * 80)
    print("重建向量库工具")
    print("=" * 80)
    
    base_url = "http://127.0.0.1:7861"
    
    # 步骤1: 删除现有向量库
    print("🗑️  步骤1: 删除现有向量库")
    
    vector_store_path = f"D:\\chatchat_data\\data\\knowledge_base\\{kb_name}\\vector_store"
    
    if os.path.exists(vector_store_path):
        try:
            shutil.rmtree(vector_store_path)
            print(f"✅ 成功删除向量库目录: {vector_store_path}")
        except Exception as e:
            print(f"❌ 删除向量库目录失败: {e}")
            return False
    else:
        print(f"⚠️  向量库目录不存在: {vector_store_path}")
    
    # 步骤2: 通过API删除知识库中的文档
    print(f"\n📄 步骤2: 删除知识库中的文档")
    
    try:
        # 获取文件列表
        response = requests.get(f"{base_url}/knowledge_base/list_files", 
                              params={"knowledge_base_name": kb_name})
        
        if response.status_code == 200:
            files = response.json()
            file_names = [f["file_name"] for f in files.get("data", [])]
            
            if file_names:
                print(f"📋 找到 {len(file_names)} 个文件:")
                for file_name in file_names:
                    print(f"   - {file_name}")
                
                # 删除文件
                delete_data = {
                    "knowledge_base_name": kb_name,
                    "file_names": file_names
                }
                
                response = requests.post(
                    f"{base_url}/knowledge_base/delete_docs",
                    json=delete_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    print("✅ 成功删除知识库中的文档")
                else:
                    print(f"❌ 删除文档失败: {response.status_code}")
                    print(f"   错误信息: {response.text}")
            else:
                print("📋 知识库中没有文档")
        else:
            print(f"❌ 获取文件列表失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 删除文档失败: {e}")
    
    # 步骤3: 重新上传和处理文档
    print(f"\n📤 步骤3: 重新上传和处理文档")
    
    pdf_path = f"D:\\chatchat_data\\data\\knowledge_base\\{kb_name}\\content\\单片机原理及接口技术-C51编程-张毅刚.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF文件不存在: {pdf_path}")
        return False
    
    try:
        # 上传文档
        print("📤 上传文档...")
        
        with open(pdf_path, 'rb') as f:
            files = {'files': (os.path.basename(pdf_path), f, 'application/pdf')}
            data = {
                'knowledge_base_name': kb_name,
                'override': 'true',
                'to_vector_store': 'true',
                'chunk_size': 750,
                'chunk_overlap': 150,
                'zh_title_enhance': 'false'
            }
            
            print("⏳ 开始上传和处理文档（这可能需要很长时间）...")
            start_time = time.time()
            
            response = requests.post(
                f"{base_url}/knowledge_base/upload_docs",
                files=files,
                data=data,
                timeout=7200  # 2小时超时
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"⏱️  处理耗时: {processing_time/60:.1f} 分钟")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 文档上传和处理成功!")
                print(f"📊 处理结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            else:
                print(f"❌ 文档处理失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("❌ 文档处理超时")
        return False
    except Exception as e:
        print(f"❌ 文档处理失败: {e}")
        return False
    
    # 步骤4: 验证重建结果
    print(f"\n🧪 步骤4: 验证重建结果")
    
    try:
        # 等待一下让系统稳定
        time.sleep(5)
        
        # 测试检索
        search_data = {
            "query": "单片机",
            "knowledge_base_name": kb_name,
            "top_k": 3,
            "score_threshold": 0.5
        }
        
        response = requests.post(
            f"{base_url}/knowledge_base/search_docs",
            json=search_data,
            timeout=15
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ 检索测试成功，返回 {len(results)} 个结果")
            
            for i, doc in enumerate(results):
                content_length = len(doc.get("page_content", ""))
                print(f"   📄 文档{i+1}: {content_length} 字符")
                
                if content_length > 5000:
                    print(f"      ⚠️  警告: 文档仍然过长")
                elif content_length > 0:
                    print(f"      ✅ 文档长度正常")
                    print(f"      预览: {doc.get('page_content', '')[:100]}...")
                else:
                    print(f"      ❌ 文档内容为空")
        else:
            print(f"❌ 检索测试失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    
    return True

def main():
    """主函数"""
    
    print("🔄 开始重建向量库...")
    
    kb_name = "microcontroller"
    
    print(f"📋 目标知识库: {kb_name}")
    print(f"⚠️  警告: 此操作将删除现有向量库并重新处理文档")
    print(f"⏱️  预计耗时: 1-2小时（取决于PDF大小和OCR处理）")
    
    try:
        response = input(f"\n是否继续？(y/n): ")
        if response.lower() not in ['y', 'yes', '是']:
            print("操作取消")
            return
    except KeyboardInterrupt:
        print("\n操作取消")
        return
    
    success = rebuild_vector_store(kb_name)
    
    if success:
        print(f"\n🎉 向量库重建完成!")
        print(f"\n📝 后续步骤:")
        print("1. 测试RAG问答功能")
        print("2. 检查返回的文档块大小是否合理")
        print("3. 验证检索结果的相关性")
    else:
        print(f"\n❌ 向量库重建失败!")
        print(f"\n🔧 故障排除:")
        print("1. 检查服务是否正常运行")
        print("2. 确保PDF文件存在且可访问")
        print("3. 检查磁盘空间是否充足")

if __name__ == "__main__":
    main()
