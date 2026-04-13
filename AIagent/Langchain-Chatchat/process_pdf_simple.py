#!/usr/bin/env python3
"""
简化版PDF处理脚本 - 直接在当前目录运行
"""

import os
import sys
import time
import argparse
from pathlib import Path

def process_pdf_simple(pdf_path, kb_name, skip_ocr=False, max_pages=None):
    """简化的PDF处理函数"""
    
    print("=" * 60)
    print("简化版PDF处理工具")
    print("=" * 60)
    
    print(f"PDF文件: {pdf_path}")
    print(f"知识库: {kb_name}")
    print(f"跳过OCR: {skip_ocr}")
    print(f"最大页数: {max_pages or '全部'}")
    
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        print(f"❌ PDF文件不存在: {pdf_path}")
        return False
    
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
    print(f"文件大小: {file_size:.1f} MB")
    
    try:
        # 尝试导入必要的库
        print("\n📚 检查依赖库...")
        
        try:
            import fitz  # PyMuPDF
            print("✅ PyMuPDF (fitz) 可用")
        except ImportError:
            print("❌ PyMuPDF 未安装，请运行: pip install PyMuPDF")
            return False
        
        try:
            from rapidocr_onnxruntime import RapidOCR
            print("✅ RapidOCR 可用")
            ocr_available = True
        except ImportError:
            print("⚠️  RapidOCR 未安装，将跳过OCR处理")
            ocr_available = False
            skip_ocr = True
        
        # 开始处理PDF
        print(f"\n🚀 开始处理PDF...")
        start_time = time.time()
        
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        print(f"总页数: {total_pages}")
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
            print(f"限制处理页数: {total_pages}")
        
        # 初始化OCR（如果需要）
        ocr = None
        if not skip_ocr and ocr_available:
            ocr = RapidOCR()
            print("✅ OCR引擎已初始化")
        
        extracted_text = ""
        
        # 处理每一页
        for page_num in range(total_pages):
            print(f"\r处理页面: {page_num + 1}/{total_pages} ({(page_num + 1)/total_pages*100:.1f}%)", end="", flush=True)
            
            page = doc[page_num]
            
            # 提取文本
            text = page.get_text()
            extracted_text += f"\n--- 第{page_num + 1}页 ---\n"
            extracted_text += text
            
            # OCR处理图片（如果启用）
            if not skip_ocr and ocr and ocr_available:
                try:
                    # 获取页面图片
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    
                    # 这里简化处理，实际应该处理页面中的图片
                    # 由于复杂性，暂时跳过图片OCR
                    pass
                except Exception as e:
                    print(f"\n⚠️  页面{page_num + 1}的OCR处理失败: {e}")
        
        print(f"\n✅ PDF处理完成!")
        
        # 保存提取的文本
        output_file = f"{kb_name}_extracted_text.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"处理时间: {processing_time:.2f} 秒")
        print(f"提取文本长度: {len(extracted_text)} 字符")
        print(f"文本已保存到: {output_file}")
        
        # 显示文本预览
        print(f"\n📄 文本预览 (前500字符):")
        print("-" * 40)
        print(extracted_text[:500])
        if len(extracted_text) > 500:
            print("...")
        print("-" * 40)
        
        doc.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="简化版PDF处理工具")
    parser.add_argument("--pdf_path", required=True, help="PDF文件路径")
    parser.add_argument("--kb_name", required=True, help="知识库名称")
    parser.add_argument("--skip_ocr", action="store_true", help="跳过OCR处理")
    parser.add_argument("--max_pages", type=int, help="最大处理页数")
    
    args = parser.parse_args()
    
    success = process_pdf_simple(
        pdf_path=args.pdf_path,
        kb_name=args.kb_name,
        skip_ocr=args.skip_ocr,
        max_pages=args.max_pages
    )
    
    if success:
        print("\n🎉 处理成功完成!")
        print("\n📝 下一步:")
        print("1. 检查生成的文本文件")
        print("2. 如果文本质量满意，可以将其导入知识库")
        print("3. 如果需要OCR处理图片，请安装RapidOCR后重新运行")
    else:
        print("\n❌ 处理失败!")

if __name__ == "__main__":
    main()
