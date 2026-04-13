#!/usr/bin/env python3
"""
PDF文档处理诊断工具

用于诊断PDF文档处理过程中的问题，分析为什么397页PDF只生成了1个空文档。
"""

import os
import sys
import time
from pathlib import Path

def diagnose_pdf_file(pdf_path: str):
    """诊断PDF文件"""
    
    print("=" * 80)
    print("PDF文件诊断")
    print("=" * 80)
    
    # 基本文件信息
    print(f"📄 PDF文件路径: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF文件不存在！")
        return False
    
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
    print(f"📊 文件大小: {file_size:.2f} MB")
    
    # 测试1: 使用PyMuPDF检查PDF基本信息
    print(f"\n🔍 测试1: PDF基本信息检查")
    try:
        import fitz
        doc = fitz.open(pdf_path)
        
        print(f"✅ PDF可以正常打开")
        print(f"📖 总页数: {doc.page_count}")
        print(f"🔒 是否加密: {doc.is_encrypted}")
        print(f"📝 是否可编辑: {doc.can_save_incrementally()}")
        
        # 检查前几页的内容
        print(f"\n📄 前3页内容预览:")
        for i in range(min(3, doc.page_count)):
            page = doc[i]
            text = page.get_text()
            print(f"  第{i+1}页文本长度: {len(text)} 字符")
            if text.strip():
                print(f"  第{i+1}页文本预览: {text[:100]}...")
            else:
                print(f"  第{i+1}页: 无文本内容（可能是扫描版）")
        
        doc.close()
        
    except ImportError:
        print("❌ PyMuPDF (fitz) 未安装")
        return False
    except Exception as e:
        print(f"❌ PDF检查失败: {e}")
        return False
    
    # 测试2: 使用RapidOCRPDFLoader测试
    print(f"\n🔍 测试2: RapidOCRPDFLoader测试")
    try:
        # 添加项目路径
        project_root = Path(__file__).parent / "Langchain-Chatchat" / "libs" / "chatchat-server"
        if project_root.exists():
            sys.path.insert(0, str(project_root))
        
        from chatchat.server.file_rag.document_loaders.mypdfloader import RapidOCRPDFLoader
        
        print("✅ RapidOCRPDFLoader 导入成功")
        
        # 测试不同配置
        configs = [
            {"skip_ocr": True, "max_pages": 5, "name": "跳过OCR，前5页"},
            {"skip_ocr": False, "max_pages": 3, "name": "包含OCR，前3页"},
        ]
        
        for config in configs:
            print(f"\n  📋 测试配置: {config['name']}")
            try:
                loader = RapidOCRPDFLoader(
                    file_path=pdf_path,
                    max_pages=config.get('max_pages'),
                    skip_ocr=config.get('skip_ocr', False)
                )
                
                start_time = time.time()
                docs = loader.load()
                end_time = time.time()
                
                print(f"    ⏱️  处理时间: {end_time - start_time:.2f} 秒")
                print(f"    📊 生成文档数: {len(docs)}")
                
                if docs:
                    for i, doc in enumerate(docs[:2]):  # 只显示前2个
                        content_length = len(doc.page_content)
                        print(f"    📄 文档{i+1}: {content_length} 字符")
                        if content_length > 0:
                            print(f"    📝 内容预览: {doc.page_content[:150]}...")
                        else:
                            print(f"    ⚠️  文档{i+1}内容为空")
                        print(f"    🏷️  元数据: {doc.metadata}")
                else:
                    print(f"    ❌ 未生成任何文档")
                    
            except Exception as e:
                print(f"    ❌ 配置测试失败: {e}")
                import traceback
                traceback.print_exc()
        
    except ImportError as e:
        print(f"❌ RapidOCRPDFLoader 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ RapidOCRPDFLoader 测试失败: {e}")
        return False
    
    # 测试3: 文档分割测试
    print(f"\n🔍 测试3: 文档分割测试")
    try:
        from chatchat.server.knowledge_base.utils import KnowledgeFile
        
        kb_file = KnowledgeFile(
            filename=os.path.basename(pdf_path),
            knowledge_base_name="test"
        )
        
        print("✅ KnowledgeFile 创建成功")
        
        # 测试文档加载
        print("  📖 测试文档加载...")
        docs = kb_file.file2docs()
        print(f"  📊 原始文档数: {len(docs)}")
        
        if docs:
            for i, doc in enumerate(docs[:2]):
                print(f"    文档{i+1}: {len(doc.page_content)} 字符")
                if doc.page_content.strip():
                    print(f"    预览: {doc.page_content[:100]}...")
        
        # 测试文档分割
        print("  ✂️  测试文档分割...")
        split_docs = kb_file.file2text(chunk_size=500, chunk_overlap=50)
        print(f"  📊 分割后文档数: {len(split_docs)}")
        
        if split_docs:
            for i, doc in enumerate(split_docs[:3]):
                print(f"    分割文档{i+1}: {len(doc.page_content)} 字符")
                if doc.page_content.strip():
                    print(f"    预览: {doc.page_content[:100]}...")
        
    except Exception as e:
        print(f"❌ 文档分割测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    return True

def suggest_solutions():
    """提供解决方案建议"""
    
    print(f"\n💡 解决方案建议:")
    print("=" * 80)
    
    print("1. 📄 如果PDF是扫描版（无文本内容）:")
    print("   - 必须启用OCR处理")
    print("   - 使用: --skip_ocr False")
    print("   - 注意：OCR处理会很慢，但能提取图片中的文字")
    
    print("\n2. 🔧 如果PDF有文本但处理失败:")
    print("   - 检查PDF是否损坏")
    print("   - 尝试用其他PDF阅读器打开验证")
    print("   - 考虑重新下载或获取PDF文件")
    
    print("\n3. ⚙️ 如果文档分割有问题:")
    print("   - 调整chunk_size和chunk_overlap参数")
    print("   - 尝试不同的文本分割器")
    print("   - 检查文档内容是否包含特殊字符")
    
    print("\n4. 🚀 推荐的处理策略:")
    print("   - 先用小页数测试（如前10页）")
    print("   - 确认内容提取正常后再处理全部")
    print("   - 对于扫描版PDF，分批处理以避免超时")
    
    print("\n5. 🔍 进一步诊断:")
    print("   - 使用PDF阅读器检查文档结构")
    print("   - 尝试复制粘贴文本验证是否可选择")
    print("   - 检查PDF是否有密码保护")

def main():
    """主函数"""
    
    # PDF文件路径
    pdf_path = "D:\\chatchat_data\\data\\knowledge_base\\microcontroller\\content\\单片机原理及接口技术-C51编程-张毅刚.pdf"
    
    print("🔍 开始PDF文档处理诊断...")
    
    success = diagnose_pdf_file(pdf_path)
    
    if success:
        suggest_solutions()
    
    print(f"\n📋 诊断完成。")
    print("请根据诊断结果调整PDF处理策略。")

if __name__ == "__main__":
    main()
