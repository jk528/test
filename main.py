#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB转TXT工具 - 主入口脚本
功能：使用单个脚本统一启动，支持命令行参数
"""

import os
import sys
import argparse

# 添加当前目录到Python路径，确保可以导入epub_to_txt模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from epub_to_txt import create_gui, convert_with_ebooklib, convert_with_epub2txt, batch_convert


def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(
        description='EPUB转TXT工具',
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 单个文件转换命令
    single_parser = subparsers.add_parser('convert', help='转换单个EPUB文件')
    single_parser.add_argument('epub_path', help='EPUB文件路径')
    single_parser.add_argument('output_path', help='输出TXT文件路径')
    single_parser.add_argument('--method', choices=['ebooklib', 'epub2txt'], default='ebooklib', help='转换方法')
    single_parser.add_argument('--no-jump', action='store_true', help='不生成跳转标记')
    single_parser.add_argument('--split', action='store_true', help='拆分多文本为单独文件')
    single_parser.add_argument('--split-size', type=float, default=10, help='按大小分割文本（MB）')
    single_parser.add_argument('--line-length', type=int, default=500, help='长行分割长度（字符）')
    single_parser.add_argument('--output-zip', action='store_true', help='以ZIP格式输出')
    single_parser.add_argument('--zip-split', action='store_true', help='分割后单独压缩')
    single_parser.add_argument('--multi-book-mode', choices=['merge', 'split'], default='merge', help='多书籍拆分模式')
    
    # 批量转换命令
    batch_parser = subparsers.add_parser('batch', help='批量转换EPUB文件')
    batch_parser.add_argument('epub_dir', help='EPUB文件目录')
    batch_parser.add_argument('output_dir', help='输出目录')
    batch_parser.add_argument('--method', choices=['ebooklib', 'epub2txt'], default='ebooklib', help='转换方法')
    batch_parser.add_argument('--no-jump', action='store_true', help='不生成跳转标记')
    
    # GUI命令
    gui_parser = subparsers.add_parser('gui', help='启动GUI界面')
    
    # 目录修复命令
    toc_parser = subparsers.add_parser('fix-toc', help='修复重复目录问题')
    toc_parser.add_argument('input_file', help='输入TXT文件路径')
    toc_parser.add_argument('output_file', help='输出修复后文件路径')
    
    return parser.parse_args()


def main():
    """
    主函数
    """
    print("EPUB转TXT工具 v1.0")
    print("=" * 50)
    
    # 解析命令行参数
    args = parse_arguments()
    
    if args.command == 'convert':
        # 单个文件转换
        print(f"转换文件: {args.epub_path}")
        print(f"输出路径: {args.output_path}")
        print(f"转换方法: {args.method}")
        print(f"生成跳转标记: {not args.no_jump}")
        print(f"拆分多文本: {args.split}")
        print(f"分割大小: {args.split_size} MB")
        print(f"长行分割长度: {args.line_length} 字符")
        print(f"输出ZIP: {args.output_zip}")
        print(f"ZIP分割: {args.zip_split}")
        print(f"多书籍模式: {args.multi_book_mode}")
        print("=" * 50)
        
        # 检查文件存在
        if not os.path.exists(args.epub_path):
            print(f"错误: 文件 {args.epub_path} 不存在")
            return 1
        
        # 执行转换
        generate_jump_marks = not args.no_jump
        split_files = args.split
        multi_book_mode = args.multi_book_mode
        split_by_size = args.split_size > 0
        max_file_size = args.split_size * 1024 * 1024  # 转换为字节
        output_zip = args.output_zip
        zip_split = args.zip_split
        line_split_length = args.line_length
        
        if args.method == 'epub2txt':
            success = convert_with_epub2txt(args.epub_path, args.output_path)
        else:
            success = convert_with_ebooklib(
                args.epub_path,
                args.output_path,
                generate_jump_marks,
                split_files,
                multi_book_mode,
                None,  # 命令行模式下不使用进度回调
                split_by_size,
                max_file_size,
                output_zip,
                zip_split,
                line_split_length
            )
        
        if success:
            print("\n转换完成！")
        else:
            print("\n转换失败！")
            return 1
    
    elif args.command == 'batch':
        # 批量转换
        print(f"批量转换目录: {args.epub_dir}")
        print(f"输出目录: {args.output_dir}")
        print(f"转换方法: {args.method}")
        print(f"生成跳转标记: {not args.no_jump}")
        print("=" * 50)
        
        # 检查目录存在
        if not os.path.exists(args.epub_dir):
            print(f"错误: 目录 {args.epub_dir} 不存在")
            return 1
        
        # 执行批量转换
        generate_jump_marks = not args.no_jump
        success = batch_convert(args.epub_dir, args.output_dir, args.method, generate_jump_marks)
        
        if success:
            print("\n批量转换完成！")
        else:
            print("\n批量转换失败！")
            return 1
    
    elif args.command == 'gui' or args.command is None:
        # 启动GUI界面
        print("启动GUI界面...")
        create_gui()
    
    elif args.command == 'fix-toc':
        # 修复重复目录
        print(f"修复重复目录: {args.input_file}")
        print(f"输出路径: {args.output_file}")
        print("=" * 50)
        
        # 检查文件存在
        if not os.path.exists(args.input_file):
            print(f"错误: 文件 {args.input_file} 不存在")
            return 1
        
        # 执行修复
        from epub_to_txt import fix_toc
        success = fix_toc(args.input_file, args.output_file)
        
        if success:
            print("\n修复完成！")
        else:
            print("\n修复失败！")
            return 1
    
    else:
        # 无命令行参数，启动GUI
        print("无命令行参数，启动GUI界面...")
        create_gui()
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
