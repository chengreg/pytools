#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

def generate_test_directory(base_path: Path, target_str: str = "REMOVE"):
    base_dir = Path(base_path)
    if base_dir.exists():
        print(f"⚠️ 目录已存在: {base_dir.resolve()}")
    else:
        base_dir.mkdir(parents=True)
        print(f"📂 创建目录: {base_dir.resolve()}")

    # 顶层文件
    top_files = [
        f"file_{target_str}_1.txt",
        f"file_2_{target_str}.log",
        f"image_{target_str}.png",
        f"doc_{target_str}_1.docx"
    ]
    for fname in top_files:
        (base_dir / fname).write_text(f"Test file: {fname}", encoding="utf-8")
        print(f"  📄 创建文件: {fname}")

    # 一级子目录（包含目标字符串）
    subdir_a = base_dir / f"subdir_{target_str}_A"
    subdir_a.mkdir(exist_ok=True)
    for fname in [
        f"nested_{target_str}_1.txt",
        f"nested_2_{target_str}.txt"
    ]:
        (subdir_a / fname).write_text(f"Test file: {fname}", encoding="utf-8")
        print(f"  📄 创建文件: {subdir_a/fname}")

    # 二级子目录
    subsub_b = subdir_a / f"subsub_{target_str}_B"
    subsub_b.mkdir(exist_ok=True)
    for fname in [
        f"file_{target_str}_x.csv",
        f"another_{target_str}_y.txt"
    ]:
        (subsub_b / fname).write_text(f"Test file: {fname}", encoding="utf-8")
        print(f"  📄 创建文件: {subsub_b/fname}")

    # 另一个一级子目录（不含目标字符串）
    subdir_b = base_dir / "subdir_B"
    subdir_b.mkdir(exist_ok=True)
    (subdir_b / "normal_file.txt").write_text("Normal file", encoding="utf-8")
    (subdir_b / f"file_{target_str}.pdf").write_text("PDF test file", encoding="utf-8")

    print("✅ 测试目录生成完成！")

if __name__ == "__main__":
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    # 在脚本所在目录生成 test_data
    generate_test_directory(script_dir / "test_data", target_str="REMOVE")
