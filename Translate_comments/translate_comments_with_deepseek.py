#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量翻译“注释为中文（英文原文保留、中文逐行插入）”，不改动源文件。
目录约定（均在脚本同级）：
- pending_sources/     放待处理的源码（可包含子目录）
- translated_sources/  输出处理后的源码（镜像目录结构）

新增：
- 实时进度显示（整体进度、文件进度、批次进度）
- --verbose 显示详细日志
- --preview N 显示每个批次翻译的前 N 行中英对照预览

运行：
  export DEEPSEEK_API_KEY="你的密钥" # Windows 用 set 或 setx
  python translate_comments_with_deepseek.py --verbose --preview 3
"""

import os
import re
import json
import time
import argparse
import requests
from pathlib import Path
from typing import List, Tuple

# ========== 目录与基本配置 ==========
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_ROOT = SCRIPT_DIR / "pending_sources"
OUTPUT_ROOT = SCRIPT_DIR / "translated_sources"

SUPPORTED_EXTS = {
    ".h", ".hpp", ".hh",
    ".cpp", ".cc", ".c", ".inl",
    ".cs", ".js", ".ts",
    ".java", ".swift",
    ".m", ".mm",
}

EXCLUDE_DIRS = {".git", ".svn", ".hg", "__pycache__", "node_modules", "build", "Binaries", "Intermediate"}

# ========== DeepSeek API 配置 ==========
DEFAULT_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_ENDPOINT = os.environ.get("DEEPSEEK_ENDPOINT", "/chat/completions")
DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
TIMEOUT_SEC = 60
RETRY = 3
RETRY_BACKOFF = 2.0

# 每批次限额，避免上下文过长
MAX_LINES_PER_BATCH = 120
MAX_CHARS_PER_BATCH = 6000

# 正则：注释识别
LINE_COMMENT_RE = re.compile(r'^(\s*)(//)(.*)$')
BLOCK_COMMENT_START_RE = re.compile(r'^(\s*)/\*\*?')   # /* 或 /**
BLOCK_COMMENT_END_RE = re.compile(r'.*\*/\s*$')
BLOCK_INNER_LINE_RE = re.compile(r'^(\s*\*)(\s?)(.*)$')  # 诸如 " * xxx"

# ========== 打印进度工具 ==========
def format_pct(numer, denom):
    pct = (numer / denom * 100.0) if denom else 100.0
    return f"{pct:6.2f}%"

def progress_bar(numer, denom, width=30):
    if denom <= 0:
        return "[" + "=" * width + "]"
    filled = int(width * numer / denom)
    return "[" + "=" * filled + ">" + "." * (width - filled - 1 if width - filled - 1 >= 0 else 0) + "]"

def print_overwrite(msg: str):
    print("\r" + msg, end="", flush=True)

def println(msg: str = ""):
    print(msg, flush=True)

# ========== 注释块提取 ==========
def split_into_comment_spans(lines: List[str]) -> List[Tuple[str, int, int]]:
    """扫描文件，返回所有注释区间 (kind, start_idx, end_idx)。kind in {"line","block"}"""
    spans = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        # 块注释
        if BLOCK_COMMENT_START_RE.search(line):
            start = i
            j = i
            while j < n:
                if BLOCK_COMMENT_END_RE.search(lines[j]):
                    break
                j += 1
            end = min(j, n - 1)
            spans.append(("block", start, end))
            i = end + 1
            continue
        # 连续 // 合并为一段
        if LINE_COMMENT_RE.match(line):
            start = i
            j = i + 1
            while j < n and LINE_COMMENT_RE.match(lines[j]):
                j += 1
            spans.append(("line", start, j - 1))
            i = j
            continue
        i += 1
    return spans

def build_batches_from_spans(lines: List[str], spans: List[Tuple[str, int, int]]):
    """将注释区间按体积分批，控制每次请求大小"""
    batches, cur = [], []
    chars = 0
    count = 0
    for kind, s, e in spans:
        chunk_len = sum(len(lines[k]) for k in range(s, e + 1))
        chunk_lines = e - s + 1
        if cur and (count + chunk_lines > MAX_LINES_PER_BATCH or chars + chunk_len > MAX_CHARS_PER_BATCH):
            batches.append(cur); cur = []; chars = 0; count = 0
        cur.append((kind, s, e))
        chars += chunk_len; count += chunk_lines
    if cur:
        batches.append(cur)
    return batches

# ========== DeepSeek 调用 ==========
def deepseek_translate(text_block: str, model: str) -> str:
    """调用 DeepSeek Chat Completions，将英文逐行翻成中文（行数与顺序保持一致）"""
    url = DEFAULT_BASE_URL.rstrip("/") + DEFAULT_ENDPOINT
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未设置。")

    sys_prompt = (
        "You are a professional translator for source code comments. "
        "Translate from English to Simplified Chinese. "
        "STRICT RULES:\n"
        "1) Preserve the exact number of lines and their order.\n"
        "2) Do not merge or split lines.\n"
        "3) Do not translate code, only the given comment text.\n"
        "4) Do not add explanations or extra punctuation.\n"
        "5) Keep Unreal Engine terms consistent (Delegate, Blueprint, UObject, etc.).\n"
    )
    user_msg = "Translate each line to Simplified Chinese, same count/order.\nINPUT LINES:\n" + text_block

    payload = {
        "model": model or DEFAULT_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for attempt in range(1, RETRY + 1):
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT_SEC)
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            if attempt >= RETRY:
                raise
            time.sleep(RETRY_BACKOFF ** attempt)
    return ""

# ========== 注释抽取/回填 ==========
def extract_comment_text_for_translation(lines: List[str], span: Tuple[str, int, int]):
    """抽取一个注释区间的“待翻译文本”和“行前缀”，用于保持格式。"""
    kind, s, e = span
    texts, prefixes = [], []
    if kind == "line":
        for i in range(s, e + 1):
            m = LINE_COMMENT_RE.match(lines[i])
            indent, slashes, content = m.group(1), m.group(2), m.group(3)
            content = content[1:] if content.startswith(" ") else content
            texts.append(content.rstrip("\n"))
            prefixes.append(f"{indent}{slashes} ")
    else:
        for i in range(s + 1, e):  # 仅处理内部行；首尾 /* 与 */ 原样保留
            line = lines[i].rstrip("\n")
            m2 = BLOCK_INNER_LINE_RE.match(line)
            if m2:
                star_prefix, space_opt, content = m2.group(1), m2.group(2), m2.group(3)
                pref = star_prefix + (space_opt if space_opt else " ")
                texts.append(content)
                prefixes.append(pref)
            else:
                leading = re.match(r'^(\s*)', line).group(1)
                body = line.strip()
                texts.append(body)
                prefixes.append(leading + "* ")
    return texts, prefixes

def merge_translation_back(lines: List[str], span: Tuple[str, int, int], cn_lines: List[str], prefixes: List[str]):
    """把中文翻译插回到英文注释行的下一行。"""
    kind, s, e = span
    if kind == "line":
        insert_offset = 0
        for idx, i in enumerate(range(s, e + 1)):
            target = i + insert_offset + 1
            lines.insert(target, prefixes[idx] + cn_lines[idx] + "\n")
            insert_offset += 1
    else:
        insert_offset = 0
        for k, i in enumerate(range(s + 1, e)):
            target = i + insert_offset + 1
            lines.insert(target, prefixes[k] + cn_lines[k] + "\n")
            insert_offset += 1

# ========== 文件处理 ==========
def process_one_file(input_path: Path, output_root: Path, input_root: Path, model: str,
                     verbose: bool, preview_lines: int) -> Tuple[Path, int, int]:
    """处理单个文件：读取 -> 翻译注释 -> 镜像写入到 output_root 下
       返回：(输出文件路径, 批次数, 成功批次数)"""
    with input_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    spans = split_into_comment_spans(lines)
    batches = build_batches_from_spans(lines, spans) if spans else []
    total_batches = len(batches)
    ok_batches = 0

    if total_batches and verbose:
        println(f"  批次数：{total_batches}")

    # 翻译与回填
    if batches:
        all_results = {}
        for bi, batch in enumerate(batches, start=1):
            # 组装批次输入
            SEP = "\n<<<__BLOCK_SEP__>>>\n"
            INPUTS, META = [], []
            for span in batch:
                texts, prefixes = extract_comment_text_for_translation(lines, span)
                INPUTS.append("\n".join(texts) if texts else "")
                META.append((span, texts, prefixes))
            joined = SEP.join(INPUTS)

            # 批次进度展示
            msg = f"    批次 {bi}/{total_batches} {progress_bar(bi-1, total_batches)} {format_pct(bi-1, total_batches)} 正在翻译..."
            print_overwrite(msg)

            # 翻译
            translated = None
            if joined.strip():
                try:
                    translated = deepseek_translate(joined, model=model)
                except Exception as e:
                    if verbose:
                        println(f"\n    该批次调用失败：{e}")

            # 处理结果
            if translated is None:
                for (span, texts, prefixes) in META:
                    all_results[span] = (texts, prefixes)  # 回退：保留英文
            else:
                parts = translated.split("<<<__BLOCK_SEP__>>>")
                if len(parts) != len(META):
                    for (span, texts, prefixes) in META:
                        all_results[span] = (texts, prefixes)
                else:
                    ok_batches += 1
                    # 可选预览
                    if verbose and preview_lines > 0:
                        println("")  # 换行落下进度提示
                        println(f"      ✓ 批次 {bi} 翻译完成（预览前 {preview_lines} 行）：")
                    for part, (span, texts, prefixes) in zip(parts, META):
                        cn_lines = [l.rstrip("\n") for l in part.splitlines()]
                        if len(cn_lines) != len(texts):
                            all_results[span] = (texts, prefixes)
                        else:
                            all_results[span] = (cn_lines, prefixes)
                            if verbose and preview_lines > 0:
                                # 只预览首个 span 的前几行，避免过多输出
                                for i, (en, cn) in enumerate(zip(texts[:preview_lines], cn_lines[:preview_lines]), start=1):
                                    println(f"        EN{i}: {en}")
                                    println(f"        CN{i}: {cn}")
                                # 只对第一个 span 预览一次
                                preview_lines = 0
                    # 更新批次进度到“已完成”
            msg_done = f"    批次 {bi}/{total_batches} {progress_bar(bi, total_batches)} {format_pct(bi, total_batches)} 完成"
            print_overwrite(msg_done)
            println("")  # 换行

        # 回填（从后往前插入，避免索引错位）
        for span in sorted(spans, key=lambda x: x[1], reverse=True):
            texts, prefixes = all_results.get(span, (None, None))
            if not texts or not prefixes:
                continue
            merge_translation_back(lines, span, texts, prefixes)

    # 输出（镜像 pending_sources 的相对路径）
    rel_path = input_path.relative_to(input_root)
    out_path = output_root / rel_path.parent / (rel_path.stem + "_zh_annotated" + rel_path.suffix)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fo:
        fo.writelines(lines)

    return out_path, total_batches, ok_batches

# ========== 目录扫描 ==========
def should_skip_dir(p: Path) -> bool:
    return p.name in EXCLUDE_DIRS

def should_process_file(p: Path) -> bool:
    return p.suffix.lower() in SUPPORTED_EXTS and p.is_file()

# ========== 主流程 ==========
def main():
    ap = argparse.ArgumentParser(description="Translate only code comments to Chinese with realtime progress.")
    ap.add_argument("--verbose", action="store_true", help="显示更详细的翻译日志与批次进度")
    ap.add_argument("--preview", type=int, default=2, help="每批翻译预览前 N 行（默认2，0为不预览）")
    args = ap.parse_args()

    if not INPUT_ROOT.exists():
        println(f"⚠️ 未找到待处理目录：{INPUT_ROOT}")
        println("请在脚本同级创建 pending_sources/，并将源码文件放入其中。")
        return

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    files = []
    for path in INPUT_ROOT.rglob("*"):
        if path.is_dir():
            if should_skip_dir(path):
                continue
        else:
            if should_process_file(path):
                files.append(path)

    if not files:
        println(f"🤔 在 {INPUT_ROOT} 未发现可处理的源码文件。支持后缀：{', '.join(sorted(SUPPORTED_EXTS))}")
        return

    total_files = len(files)
    println(f"🔧 待处理文件数：{total_files}")
    ok_files, fail_files = 0, 0
    total_batches_all = 0
    ok_batches_all = 0

    for idx, f in enumerate(files, start=1):
        rel = f.relative_to(INPUT_ROOT)
        head = f"[{idx}/{total_files}] {rel}"
        print_overwrite(f"{head} {progress_bar(idx-1, total_files)} {format_pct(idx-1, total_files)} 正在处理...")
        try:
            if args.verbose:
                println("")  # 换行，开始详细日志
                println(f"📄 文件：{rel}")

            out, total_batches, ok_batches = process_one_file(
                f, OUTPUT_ROOT, INPUT_ROOT, DEFAULT_MODEL, args.verbose, args.preview
            )
            total_batches_all += total_batches
            ok_batches_all += ok_batches
            ok_files += 1
            print_overwrite(f"{head} {progress_bar(idx, total_files)} {format_pct(idx, total_files)} 完成 -> {out.relative_to(OUTPUT_ROOT)}")
            println("")
        except Exception as e:
            fail_files += 1
            print_overwrite(f"{head} 失败：{e}")
            println("")

    println("\n================ 统计 =================")
    println(f"文件：成功 {ok_files} / {total_files}，失败 {fail_files}")
    if total_batches_all:
        println(f"批次（注释块翻译）：成功 {ok_batches_all} / {total_batches_all}（{format_pct(ok_batches_all, total_batches_all).strip()}）")
    println(f"输出目录：{OUTPUT_ROOT}")

if __name__ == "__main__":
    main()
