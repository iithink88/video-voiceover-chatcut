#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地生成"口播配音"：把文本用 edge-tts 生成 mp3 配音文件。
这是 video-voiceover-chatcut 技能的第 1 段（轻量版，不依赖 text-to-clonedvoice-video-full）。
第 2 段（合并进原视频+烧录字幕）由 merge_local.py 完成。

音画同步（2026-07-17 修复）：
  本技能里"画面"是原视频（时长固定），配音是 edge-tts 生成的、长短和视频无关。
  一旦配音比视频长，合并时 ffmpeg 会用最后一帧冻结补长 → "声音还在念、画面已卡住"。
  因此这里支持 --target-duration：迭代两遍合成，用"时长随语速近似反比"的线性模型，
  把配音时长压到≈原视频时长（语速限定 0.5x~2.0x 防失真）。配音与原视频等长 → 合并后音画
  严格同步、无冻结帧。

依赖：仅需要 edge_tts（pip install edge_tts）和 ffmpeg（PATH 中可找到，ffprobe 用于测时长）。
"""
import sys
import os
import time
import asyncio
import argparse
import subprocess

try:
    from paths import detect_paths
except Exception:
    detect_paths = lambda: {}

# —— Windows Python 子进程编码铁律：入口强制 UTF-8 ——
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def rate_str(speed):
    """把语速倍率转成 edge-tts 的 rate 字符串，如 1.3 → '+30%'、0.8 → '-20%'。"""
    pct = int(round((speed - 1) * 100))
    return (f"+{pct}%" if pct >= 0 else f"{pct}%")


def probe_dur(path, ffprobe_bin, retries=5):
    """用 ffprobe 取媒体时长（秒）；带重试以避开 Windows Defender 刚写完文件的瞬时锁。失败返回 None。"""
    if not ffprobe_bin or not os.path.isfile(os.path.join(ffprobe_bin, "ffprobe.exe")):
        return None
    fp = os.path.join(ffprobe_bin, "ffprobe.exe")
    for _ in range(retries):
        try:
            out = subprocess.check_output(
                [fp, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                encoding="utf-8", errors="replace").strip()
            if out:
                return float(out)
        except Exception:
            pass
        time.sleep(0.3)
    return None


def synthesize(raw, voice, rate, out_path):
    """调用 edge-tts 把文本合成到 out_path。"""
    import edge_tts
    communicate = edge_tts.Communicate(raw, voice, rate=rate)
    asyncio.run(communicate.save(out_path))


def main():
    ap = argparse.ArgumentParser(description="生成口播配音（文本→edge-tts → mp3，可适配目标时长）")
    ap.add_argument("--text", required=True, help="文案文件路径（UTF-8，内容即字幕+朗读稿）")
    ap.add_argument("--output", required=True, help="配音 mp3 输出绝对路径")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="edge-tts 音色")
    ap.add_argument("--speed", type=float, default=1.3, help="配音语速倍率（如 1.3 = 快30%）")
    ap.add_argument("--target-duration", type=float, default=0,
                    help="目标时长(秒)：配音自动适配到此长度，使配音与原视频等长（音画同步）。"
                         "不传则按 --speed 直接生成（向后兼容）。")
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

    speed = args.speed
    print(f"[start] edge-tts 配音生成", flush=True)
    print(f"       文案：{text_path}（{len(raw)} 字）", flush=True)
    print(f"       音色：{args.voice}  语速：{speed}x", flush=True)
    print(f"       输出：{out_path}", flush=True)

    # 用 edge_tts 直接生成（不调用外部脚本）
    try:
        import edge_tts  # noqa: F401（synthesize 内也会 import，这里提前给友好提示）
    except ImportError:
        sys.exit("[!] 缺少 edge_tts 库。请运行：pip install edge_tts\n"
                 "     或双击本技能目录下的『安装依赖.bat』一键安装。")

    target = args.target_duration
    ffmpeg_bin = detect_paths().get("ffmpeg_bin")
    # 注意：ffprobe_bin 传【目录】，probe_dur 内部再拼 "ffprobe.exe"（避免重复拼接导致路径错误）
    ffprobe_bin = ffmpeg_bin if ffmpeg_bin else None

    if target and target > 0 and ffprobe_bin:
        # —— 迭代适配：用"时长≈与语速成反比"线性模型，把配音时长压到≈目标时长 ——
        cur_rate = speed
        d = None
        clamped = False
        for _ in range(2):  # 最多 2 遍：第 1 遍按用户语速，第 2 遍按修正后的语速
            synthesize(raw, args.voice, rate_str(cur_rate), out_path)
            d = probe_dur(out_path, ffprobe_bin)
            if d and d > 0 and abs(d - target) / target <= 0.04:
                break  # 已足够接近，无需再调
            if not d:
                break  # 测不到时长，放弃迭代（保留当前结果）
            # 按线性模型修正语速：cur_rate × (d / target)
            cur_rate = cur_rate * (d / target)
            lo, hi = 0.5, 2.0
            if cur_rate < lo or cur_rate > hi:
                cur_rate = max(lo, min(hi, cur_rate))
                clamped = True
        # 报告
        d = d or (probe_dur(out_path, ffprobe_bin) or 0.0)
        if clamped:
            print(f"[fit] 注意：文案在合理语速范围(0.5x~2.0x)内无法恰好填满 {target:.1f}s，"
                  f"已用极限语速 {cur_rate:.2f}x；成品将以视频时长为准掐断/补静音。", flush=True)
        else:
            print(f"[fit] 配音已适配到原视频时长：{d:.1f}s / 目标 {target:.1f}s"
                  f"（语速 {cur_rate:.2f}x）", flush=True)
    else:
        if target and target > 0 and not ffprobe_bin:
            print("[fit] 未找到 ffprobe，无法测时长，改按 --speed 直接生成（建议确认 ffmpeg 已安装）。", flush=True)
        # 不拟合：按用户语速直接生成
        synthesize(raw, args.voice, rate_str(speed), out_path)

    size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"[ok] 配音已生成：{out_path}（{size / 1024:.0f} KB）", flush=True)
    print(f"     下一步：点『② 本地合成成品』把配音+字幕合并进原视频", flush=True)


if __name__ == "__main__":
    main()
