#!/usr/bin/env python3
"""
文件统计器 - 统计指定目录中的文件数量
支持递归统计子目录中的文件
"""

import os
import argparse
from pathlib import Path
from typing import Tuple


def count_files(directory: str, include_subdirs: bool = False) -> Tuple[int, int, dict]:
    """
    统计指定目录中的文件数量和类型分布
    
    Args:
        directory: 要统计的目录路径
        include_subdirs: 是否包含子目录中的文件
        
    Returns:
        Tuple[int, int, dict]: (文件总数, 目录总数, 文件类型分布)
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"目录不存在: {directory}")
    
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"路径不是目录: {directory}")
    
    file_count = 0
    dir_count = 0
    file_types = {}
    
    try:
        if include_subdirs:
            # 递归遍历所有子目录
            for root, dirs, files in os.walk(directory):
                file_count += len(files)
                dir_count += len(dirs)
                # 统计文件类型
                for file in files:
                    file_ext = get_file_extension(file)
                    file_types[file_ext] = file_types.get(file_ext, 0) + 1
        else:
            # 只统计当前目录
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file():
                        file_count += 1
                        file_ext = get_file_extension(entry.name)
                        file_types[file_ext] = file_types.get(file_ext, 0) + 1
                    elif entry.is_dir():
                        dir_count += 1
                        
    except PermissionError as e:
        print(f"警告: 无法访问某些目录或文件: {e}")
    except Exception as e:
        print(f"统计过程中出现错误: {e}")
    
    return file_count, dir_count, file_types


def print_file_type_chart(file_types: dict, total_files: int):
    """
    打印文件类型分布的简单文本图表
    
    Args:
        file_types: 文件类型统计字典
        total_files: 文件总数
    """
    if not file_types:
        return
    
    print(f"\n📊 文件类型分布图表:")
    print("=" * 60)
    
    # 按数量排序
    sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)
    
    # 找到最大数量用于计算图表长度
    max_count = max(file_types.values())
    max_bar_length = 40  # 最大图表长度
    
    for file_type, count in sorted_types:
        percentage = (count / total_files) * 100
        bar_length = int((count / max_count) * max_bar_length)
        bar = "█" * bar_length
        print(f"{file_type:15} | {bar} {count:4,} ({percentage:5.1f}%)")
    
    print("=" * 60)


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        str: 文件扩展名（包含点号）
    """
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        return f'.{ext}'
    else:
        return '无扩展名'


def format_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def get_directory_size(directory: str, include_subdirs: bool = False) -> int:
    """获取目录的总大小（字节）"""
    total_size = 0
    
    try:
        if include_subdirs:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            total_size += os.path.getsize(file_path)
                    except (OSError, PermissionError):
                        continue
        else:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            total_size += entry.stat().st_size
                        except (OSError, PermissionError):
                            continue
    except Exception:
        pass
    
    return total_size


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="统计指定目录中的文件数量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python file_counter.py /path/to/directory           # 完整统计 (默认包含所有功能)
  python file_counter.py /path/to/directory --no-recursive  # 不包含子目录
  python file_counter.py /path/to/directory --no-chart      # 不显示图表
  python file_counter.py /path/to/directory --no-size       # 不显示大小
  python file_counter.py /path/to/directory --no-verbose    # 不显示详细信息
        """
    )
    
    parser.add_argument(
        "directory",
        help="要统计的目录路径"
    )
    
    parser.add_argument(
        "-r", "--recursive",
        action="store_const",
        const=True,
        default=True,
        help="是否包含子目录中的文件 (默认: 是)"
    )
    
    parser.add_argument(
        "-s", "--size",
        action="store_const",
        const=True,
        default=True,
        help="显示目录总大小 (默认: 是)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_const",
        const=True,
        help="显示详细信息 (默认: 是)"
    )
    
    parser.add_argument(
        "-c", "--chart",
        action="store_const",
        const=True,
        default=True,
        help="显示文件类型分布图表 (默认: 是)"
    )
    
    # 反向参数，用于关闭默认功能
    parser.add_argument(
        "--no-recursive",
        action="store_const",
        const=False,
        dest="recursive",
        help="不包含子目录中的文件"
    )
    
    parser.add_argument(
        "--no-size",
        action="store_const",
        const=False,
        dest="size",
        help="不显示目录总大小"
    )
    
    parser.add_argument(
        "--no-verbose",
        action="store_const",
        const=False,
        dest="verbose",
        help="不显示详细信息"
    )
    
    parser.add_argument(
        "--no-chart",
        action="store_const",
        const=False,
        dest="chart",
        help="不显示文件类型分布图表"
    )
    
    args = parser.parse_args()
    
    try:
        # 获取绝对路径
        abs_directory = os.path.abspath(args.directory)
        
        print(f"正在统计目录: {abs_directory}")
        print(f"包含子目录: {'是' if args.recursive else '否'}")
        print("-" * 50)
        
        # 统计文件数量和类型分布
        file_count, dir_count, file_types = count_files(abs_directory, args.recursive)
        
        # 显示统计结果
        print(f"文件总数: {file_count:,}")
        if args.recursive:
            print(f"目录总数: {dir_count:,}")
        
        # 显示文件类型分布
        if file_types:
            if args.chart:
                # 显示图表
                print_file_type_chart(file_types, file_count)
            else:
                # 显示列表
                print(f"\n文件类型分布:")
                # 按数量排序
                sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)
                for file_type, count in sorted_types:
                    percentage = (count / file_count) * 100
                    print(f"  {file_type}: {count:,} 个 ({percentage:.1f}%)")
        
        # 显示目录大小
        if args.size:
            total_size = get_directory_size(abs_directory, args.recursive)
            print(f"目录总大小: {format_size(total_size)}")
        
        # 显示详细信息
        if args.verbose:
            print("\n详细信息:")
            print(f"绝对路径: {abs_directory}")
            if os.path.exists(abs_directory):
                print(f"目录权限: {oct(os.stat(abs_directory).st_mode)[-3:]}")
                print(f"所有者: {os.stat(abs_directory).st_uid}")
        
        print("-" * 50)
        print("统计完成!")
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return 1
    except NotADirectoryError as e:
        print(f"错误: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        return 1
    except Exception as e:
        print(f"发生未知错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
