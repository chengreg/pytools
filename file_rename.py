#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重命名文件程序
可以去除文件名中指定的字符串，让文件名更加简洁
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple


class FileRenamer:
    """文件重命名器类"""
    
    def __init__(self, directory: str, remove_string: str, dry_run: bool = False):
        """
        初始化重命名器
        
        Args:
            directory: 目标目录路径
            remove_string: 要移除的字符串
            dry_run: 是否为预览模式（不实际重命名）
        """
        self.directory = Path(directory)
        self.remove_string = remove_string
        self.dry_run = dry_run
        self.renamed_files: List[Tuple[str, str]] = []
        self.errors: List[str] = []
    
    def validate_directory(self) -> bool:
        """验证目录是否存在且可访问"""
        if not self.directory.exists():
            self.errors.append(f"目录不存在: {self.directory}")
            return False
        if not self.directory.is_dir():
            self.errors.append(f"路径不是目录: {self.directory}")
            return False
        return True
    
    def get_files_to_rename(self) -> List[Path]:
        """获取需要重命名的文件列表"""
        files = []
        try:
            for item in self.directory.iterdir():
                if item.is_file():  # 只处理文件，不处理目录
                    files.append(item)
        except PermissionError:
            self.errors.append(f"没有权限访问目录: {self.directory}")
        return files
    
    def generate_new_name(self, old_name: str) -> str:
        """生成新的文件名"""
        # 分离文件名和扩展名
        name, ext = os.path.splitext(old_name)
        
        # 移除指定的字符串
        new_name = name.replace(self.remove_string, "")
        
        # 清理多余的空格和连字符
        new_name = new_name.strip(" -_")
        
        # 如果新文件名为空，使用原文件名
        if not new_name:
            new_name = name
        
        return new_name + ext
    
    def rename_file(self, file_path: Path) -> bool:
        """重命名单个文件"""
        try:
            old_name = file_path.name
            new_name = self.generate_new_name(old_name)
            
            # 如果文件名没有变化，跳过
            if old_name == new_name:
                return True
            
            new_path = file_path.parent / new_name
            
            # 检查新文件名是否已存在
            if new_path.exists():
                self.errors.append(f"目标文件已存在，跳过重命名: {old_name} -> {new_name}")
                return False
            
            if self.dry_run:
                # 预览模式：只记录，不实际重命名
                self.renamed_files.append((old_name, new_name))
                return True
            
            # 实际重命名文件
            file_path.rename(new_path)
            self.renamed_files.append((old_name, new_name))
            return True
            
        except Exception as e:
            self.errors.append(f"重命名文件失败 {file_path.name}: {str(e)}")
            return False
    
    def process_files(self) -> bool:
        """处理所有文件"""
        if not self.validate_directory():
            return False
        
        files = self.get_files_to_rename()
        if not files:
            print(f"目录 {self.directory} 中没有找到文件")
            return True
        
        print(f"找到 {len(files)} 个文件")
        print(f"将移除字符串: '{self.remove_string}'")
        print("-" * 50)
        
        success_count = 0
        for file_path in files:
            if self.rename_file(file_path):
                success_count += 1
        
        return success_count > 0
    
    def print_results(self):
        """打印重命名结果"""
        if self.renamed_files:
            print(f"\n{'预览模式' if self.dry_run else '重命名完成'}!")
            print(f"共处理 {len(self.renamed_files)} 个文件:")
            print("-" * 50)
            
            for old_name, new_name in self.renamed_files:
                print(f"  {old_name}")
                print(f"  -> {new_name}")
                print()
        else:
            print("\n没有文件需要重命名")
        
        if self.errors:
            print(f"\n遇到 {len(self.errors)} 个错误:")
            print("-" * 50)
            for error in self.errors:
                print(f"  {error}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量重命名文件，去除文件名中指定的字符串",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python file_rename.py /path/to/directory "Unreal Engine 5 C++- Advanced Action RPG - "
  python file_rename.py /path/to/directory "前缀字符串" --dry-run
  python file_rename.py . "要移除的字符串" --verbose
        """
    )
    
    parser.add_argument(
        "directory",
        nargs="?",  # 使目录参数变为可选
        help="目标目录路径"
    )
    
    parser.add_argument(
        "remove_string",
        nargs="?",  # 使移除字符串参数变为可选
        help="要从文件名中移除的字符串"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：显示将要进行的重命名操作，但不实际执行"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出模式"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互式模式：逐步输入参数"
    )
    
    args = parser.parse_args()
    
    # 如果参数不完整或指定了交互式模式，进入交互式输入
    if args.interactive or args.directory is None or args.remove_string is None:
        print("=== 批量重命名工具 - 交互式模式 ===\n")
        
        # 获取目录路径
        while True:
            if args.directory:
                directory = args.directory
                print(f"使用指定目录: {directory}")
            else:
                print("💡 提示：")
                print("   - 可以直接粘贴完整路径")
                print("   - 支持相对路径（如 . 表示当前目录）")
                print("   - 支持用户路径（如 ~/Documents）")
                print("   - 路径中包含空格时，程序会自动处理")
                print()
                directory = input("请输入目标目录路径: ").strip()
            
            if directory:
                # 展开用户路径（如 ~ 展开为实际路径）
                directory = os.path.expanduser(directory)
                if os.path.exists(directory) and os.path.isdir(directory):
                    break
                else:
                    print(f"❌ 目录不存在或不是有效目录: {directory}")
                    if args.directory:  # 如果是指定参数，清空它
                        args.directory = None
            else:
                print("❌ 目录路径不能为空")
        
        # 获取要移除的字符串
        while True:
            if args.remove_string:
                remove_string = args.remove_string
                print(f"使用指定字符串: '{remove_string}'")
            else:
                print("\n💡 提示：")
                print("   - 输入要移除的完整字符串")
                print("   - 例如：'Unreal Engine 5 C++- Advanced Action RPG - '")
                print("   - 程序会精确匹配并移除这个字符串")
                print()
                remove_string = input("请输入要从文件名中移除的字符串: ").strip()
            
            if remove_string:
                break
            else:
                print("❌ 要移除的字符串不能为空")
                if args.remove_string:  # 如果是指定参数，清空它
                    args.remove_string = None
        
        # 确认操作
        print(f"\n📋 操作摘要:")
        print(f"   目标目录: {directory}")
        print(f"   移除字符串: '{remove_string}'")
        print(f"   预览模式: {'是' if args.dry_run else '否'}")
        
        if not args.dry_run:
            print(f"\n⚠️  即将执行实际重命名操作！")
            print(f"   建议先使用 --dry-run 参数预览效果")
            confirm = input("是否继续？(y/N): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print("操作已取消")
                return
        
        # 更新参数
        args.directory = directory
        args.remove_string = remove_string
    
    # 创建重命名器实例
    renamer = FileRenamer(
        directory=args.directory,
        remove_string=args.remove_string,
        dry_run=args.dry_run
    )
    
    # 处理文件
    if renamer.process_files():
        renamer.print_results()
        
        if args.dry_run:
            print(f"\n这是预览模式。要实际执行重命名，请移除 --dry-run 参数")
        else:
            print(f"\n重命名完成！")
    else:
        print("处理失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
