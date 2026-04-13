#!/usr/bin/env python3
"""
扫描版PDF处理工具

专门用于处理扫描版PDF文档，启用OCR功能提取图片中的文字。
"""

import os
import sys
import time
import argparse
from pathlib import Path

def process_scanned_pdf(
    pdf_path: str,
    kb_name: str,
    max_pages: int = None,
    batch_size: int = 10,
    start_page: int = 0,
):
    """
    处理扫描版PDF文件
    
    Args:
        pdf_path: PDF文件路径
        kb_name: 知识库名称
        max_pages: 最大处理页数
        batch_size: 批量处理大小
        start_page: 起始页数（用于断点续传）
    """
    
    print("=" * 80)
    print("扫描版PDF处理工具")
    print("=" * 80)
    
    print(f"📄 PDF文件: {pdf_path}")
    print(f"📚 知识库: {kb_name}")
    print(f"📖 最大页数: {max_pages or '全部'}")
    print(f"📦 批量大小: {batch_size}")
    print(f"🚀 起始页: {start_page}")
    print(f"🔍 OCR处理: 启用")
    
    # 检查文件
    if not os.path.exists(pdf_path):
        print(f"❌ PDF文件不存在: {pdf_path}")
        return False
    
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"📊 文件大小: {file_size:.2f} MB")
    
    # 检查PDF页数
    try:
        import fitz
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        print(f"📖 总页数: {total_pages}")
        
        # 检查是否为扫描版
        sample_pages = min(3, total_pages)
        text_pages = 0
        for i in range(sample_pages):
            page = doc[i]
            text = page.get_text().strip()
            if text:
                text_pages += 1
        
        if text_pages == 0:
            print("✅ 确认为扫描版PDF，需要OCR处理")
        else:
            print(f"⚠️  检测到 {text_pages}/{sample_pages} 页有文本，可能是混合版PDF")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ PDF检查失败: {e}")
        return False
    
    # 确定实际处理页数
    if max_pages:
        actual_pages = min(max_pages, total_pages - start_page)
    else:
        actual_pages = total_pages - start_page
    
    print(f"📋 实际处理页数: {actual_pages} (从第{start_page + 1}页开始)")
    
    # 预估处理时间
    estimated_time_per_page = 15  # 秒/页（OCR处理）
    estimated_total_time = actual_pages * estimated_time_per_page / 60  # 分钟
    print(f"⏱️  预估处理时间: {estimated_total_time:.1f} 分钟")
    
    # 询问用户确认
    try:
        response = input(f"\n是否继续处理？这将需要较长时间。(y/n): ")
        if response.lower() not in ['y', 'yes', '是']:
            print("操作取消")
            return False
    except KeyboardInterrupt:
        print("\n操作取消")
        return False
    
    # 开始处理
    print(f"\n🚀 开始处理扫描版PDF...")
    start_time = time.time()
    
    try:
        # 添加项目路径
        project_root = Path(__file__).parent / "Langchain-Chatchat" / "libs" / "chatchat-server"
        if project_root.exists():
            sys.path.insert(0, str(project_root))
        
        from chatchat.settings import Settings
        from chatchat.server.knowledge_base.kb_service.base import KBServiceFactory
        from chatchat.server.knowledge_base.utils import KnowledgeFile
        from chatchat.server.file_rag.document_loaders.mypdfloader import RapidOCRPDFLoader
        
        # 检查知识库
        kb = KBServiceFactory.get_service_by_name(kb_name)
        if kb is None:
            print(f"❌ 知识库不存在: {kb_name}")
            return False
        
        # 创建知识文件对象
        kb_file = KnowledgeFile(
            filename=os.path.basename(pdf_path),
            knowledge_base_name=kb_name
        )
        
        # 使用RapidOCRPDFLoader处理
        loader = RapidOCRPDFLoader(
            file_path=pdf_path,
            max_pages=max_pages,
            skip_ocr=False  # 启用OCR
        )
        
        print("📖 开始加载和OCR处理...")
        docs = loader.load()
        
        if not docs:
            print("❌ 未能从PDF中提取到任何内容")
            return False
        
        print(f"✅ 成功提取 {len(docs)} 个文档片段")
        
        # 显示内容预览
        if docs:
            print(f"\n📄 内容预览:")
            for i, doc in enumerate(docs[:2]):
                content_length = len(doc.page_content)
                print(f"  文档{i+1}: {content_length} 字符")
                if content_length > 0:
                    preview = doc.page_content[:200].replace('\n', ' ')
                    print(f"  预览: {preview}...")
                else:
                    print(f"  ⚠️  文档{i+1}内容为空")
        
        # 分批添加到知识库
        if len(docs) > batch_size:
            print(f"\n📦 分批处理文档...")
            total_batches = (len(docs) + batch_size - 1) // batch_size
            
            for i in range(0, len(docs), batch_size):
                batch_docs = docs[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                print(f"  处理第 {batch_num}/{total_batches} 批 ({len(batch_docs)} 个文档)")
                
                try:
                    kb.add_doc(kb_file, docs=batch_docs, not_refresh_vs_cache=True)
                    print(f"  ✅ 第 {batch_num} 批处理完成")
                except Exception as e:
                    print(f"  ❌ 第 {batch_num} 批处理失败: {e}")
                    # 继续处理下一批
        else:
            print(f"\n📦 一次性处理所有文档...")
            kb.add_doc(kb_file, docs=docs, not_refresh_vs_cache=True)
        
        # 保存向量库
        print("💾 保存向量库...")
        kb.save_vector_store()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n🎉 扫描版PDF处理完成！")
        print(f"⏱️  总耗时: {processing_time/60:.1f} 分钟")
        print(f"📊 处理文档数: {len(docs)}")
        print(f"📈 平均每个文档耗时: {processing_time/len(docs):.1f} 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="扫描版PDF处理工具")
    parser.add_argument("--pdf_path", required=True, help="PDF文件路径")
    parser.add_argument("--kb_name", required=True, help="知识库名称")
    parser.add_argument("--max_pages", type=int, help="最大处理页数")
    parser.add_argument("--batch_size", type=int, default=10, help="批量处理大小")
    parser.add_argument("--start_page", type=int, default=0, help="起始页数")
    
    args = parser.parse_args()
    
    success = process_scanned_pdf(
        pdf_path=args.pdf_path,
        kb_name=args.kb_name,
        max_pages=args.max_pages,
        batch_size=args.batch_size,
        start_page=args.start_page,
    )
    
    if success:
        print("\n✅ 扫描版PDF处理成功完成！")
        print("\n📝 后续步骤:")
        print("1. 重启Chatchat服务")
        print("2. 在Web界面中测试知识库问答")
        print("3. 验证OCR识别的文字质量")
    else:
        print("\n❌ 扫描版PDF处理失败！")
        print("\n🔧 故障排除:")
        print("1. 检查PDF文件是否完整")
        print("2. 确保有足够的内存和磁盘空间")
        print("3. 考虑分批处理或减少batch_size")

if __name__ == "__main__":
    main()
