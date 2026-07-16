#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地生成"口播配音"：把文本用 edge-tts 生成 mp3 配音文件。
这是 video-voiceover-chatcut 技能的第 1 段（轻量版，不依赖 text-to-clonedvoice-video-full）。
第 2 段（合并进原视频+烧录字幕）由 merge_local.py 完成。

依赖：仅需要 edge_tts（pip install edge_tts）和 ffmpeg（PATH 中可找到）。
"""
import sys
import os
import asyncio
import argparse

# —— Windows Python 子进程编码铁律：入口强制 UTF-8 ——
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description="生成口播配音（文本→edge-tts → mp3）")
    ap.add_argument("--text", required=True, help="文案文件路径（UTF-8，内容即字幕+朗读稿）")
    ap.add_argument("--output", required=True, help="配音 mp3 输出绝对路径")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="edge-tts 音色")
    ap.add_argument("--speed", type=float, default=1.3, help="配音语速倍率（如 1.3 = 快30%）")
    args = ap.parse_args()

    # 读文案
    text_path = os.path.abspath(args.text)
    if not os.path.isfile(text_path):
        sys.exit(f"[!] 文案文件不存在：{text_path}")
    raw = open(text_path, "r", encoding="utf-8-sig", errors="replace").read().strip()
    if not raw:
        sys.exit(f"[!] 文案为空：{text_path}")

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print(f"[start] edge-tts 配音生成", flush=True)
    print(f"       文案：{text_path}（{len(raw)} 字）", flush=True)
    print(f"       音色：{args.voice}  语速：{args.speed}x", flush=True)
    print(f"       输出：{out_path}", flush=True)

    # 用 edge_tts 直接生成（不调用外部脚本）
    try:
        import edge_tts
    except ImportError:
        sys.exit("[!] 缺少 edge_tts 库。请运行：pip install edge_tts\n"
                 "     或双击本技能目录下的『安装依赖.bat』一键安装。")

    rate = f"+{int((args.speed - 1) * 100)}%" if args.speed >= 1.0 else f"{int((args.speed - 1) * 100)}%"
    communicate = edge_tts.Communicate(raw, args.voice, rate=rate)

    async def _gen():
        await communicate.save(out_path)
    asyncio.run(_gen())

    size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"[ok] 配音已生成：{out_path}（{size / 1024:.0f} KB）", flush=True)
    print(f"     下一步：点『② 本地合成成品』把配音+字幕合并进原视频", flush=True)


if __name__ == "__main__":
    main()
