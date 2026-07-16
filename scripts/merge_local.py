#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地合成（段②-lite）：把"口播视频的配音 + 字幕"合并进"原视频画面"。

输入：
  --original   原视频（可静音，画面会被保留）
  --audio      口播配音 mp3（由 make_narration.py 生成，在 _narration_work/narration.mp3）
  --text       文案文件路径（用于生成字幕，UTF-8 / 带 BOM 均可）
  --output     成品输出路径

做法：
  1. 用 ffprobe 取配音时长 + 原视频分辨率/时长
  2. 把文案按句切分，均匀铺到配音时长上 → 生成 .srt（存临时 ASCII 路径，规避中文路径坑）
  3. ffmpeg：原视频画面静音 + 烧录字幕 + 混入配音（短则补静音，长则顺延）
输出与 ChatCut 路径一致的成品：原视频画面 + 口播语音 + 口播字幕。

注：本脚本不依赖 ChatCut MCP，可独立双击运行（GUI 在无 ChatCut 时也能出片）。
"""
import sys, os, argparse, subprocess, re, tempfile
from paths import detect_paths

# —— Windows Python 子进程编码铁律：入口强制 UTF-8 ——
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def ffprobe(field, path, ffprobe_bin):
    """取媒体信息：field 形如 'format=duration' 或 'stream=width'"""
    cmd = [ffprobe_bin, "-v", "error", "-show_entries", field,
           "-of", "default=noprint_wrappers=1:nokey=1", path]
    try:
        out = subprocess.check_output(cmd, encoding="utf-8", errors="replace").strip()
    except Exception:
        return None
    return out


def split_sentences(text):
    """按中英文句末标点 + 换行切句。"""
    parts = re.split(r"(?<=[。！？!?；;…\n])", text)
    return [p.strip().replace("\n", " ") for p in parts if p and p.strip()]


def fmt_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def gen_srt(text, duration, srt_path):
    lines = split_sentences(text)
    n = max(1, len(lines))
    seg = duration / n
    blocks = []
    for i, ln in enumerate(lines):
        start = i * seg
        end = (i + 1) * seg
        blocks.append(f"{i + 1}\n{fmt_time(start)} --> {fmt_time(end)}\n{ln}\n")
    open(srt_path, "w", encoding="utf-8").write("\n".join(blocks))


def main():
    ap = argparse.ArgumentParser(description="本地合成：口播配音+字幕 → 原视频画面")
    ap.add_argument("--original", required=True, help="原视频路径")
    ap.add_argument("--audio", required=True, help="口播配音 mp3 路径")
    ap.add_argument("--text", required=True, help="文案文件路径（生成字幕用）")
    ap.add_argument("--output", required=True, help="成品输出路径")
    ap.add_argument("--ffmpeg-bin", default=None, help="覆盖：ffmpeg.exe 所在目录")
    ap.add_argument("--fontsize", type=float, default=0, help="字幕字号(libass单位，非像素；0=按分辨率自适应)")
    args = ap.parse_args()

    ffmpeg_bin = args.ffmpeg_bin or detect_paths()["ffmpeg_bin"]
    if not ffmpeg_bin or not os.path.isfile(os.path.join(ffmpeg_bin, "ffmpeg.exe")):
        print("[!] 找不到 ffmpeg。请安装 ffmpeg 并加入 PATH，或放到 %USERPROFILE%/bin/ffmpeg/"
              "ffmpeg-8.1.2-essentials_build/bin，或双击本技能的『安装依赖.bat』。", file=sys.stderr)
        sys.exit(1)
    ffmpeg = os.path.join(ffmpeg_bin, "ffmpeg.exe")
    ffprobe_bin = os.path.join(ffmpeg_bin, "ffprobe.exe")

    # —— 1. 取时长/分辨率 ——
    audio_dur = float(ffprobe("format=duration", args.audio, ffprobe_bin) or 0)
    orig_dur = float(ffprobe("format=duration", args.original, ffprobe_bin) or 0)
    vh = int(ffprobe("stream=height", args.original, ffprobe_bin) or 0)
    vw = int(ffprobe("stream=width", args.original, ffprobe_bin) or 0)
    if audio_dur <= 0:
        print("[!] 配音时长为 0，无法对齐字幕。", file=sys.stderr); sys.exit(1)

    # —— 2. 生成字幕（写到独立临时目录，用**相对文件名**引用）——
    # 关键坑：ffmpeg 8.x 的 subtitles 过滤器对绝对路径里的盘符冒号(C:)极敏感，
    # 单引号/转义都不可靠；改用临时目录 + cwd + 相对文件名，彻底避开冒号。
    srt_dir = tempfile.mkdtemp(prefix="cc_srt_")
    srt_name = "subs.srt"
    tmp_srt = os.path.join(srt_dir, srt_name)
    raw = open(args.text, "r", encoding="utf-8-sig", errors="replace").read()
    gen_srt(raw, audio_dur, tmp_srt)
    print(f"[ok] 字幕已生成: {tmp_srt} (配音 {audio_dur:.1f}s, 原视频 {orig_dur:.1f}s)", flush=True)

    # —— 3. 字幕样式：白字黑描边、底部居中、智能换行最多两行 ——
    # ⚠️ ffmpeg/libass 的 FontSize 不是像素值！它基于内部默认 PlayRes(384×288) 缩放。
    #   实际像素 = FontSize × (video_height / 288)
    #   例：1920p 视频，FontSize=4 → 4 × (1920/288) ≈ 27px
    #   所以千万不要传 PlayResX/Y（会破坏这个换算），也不要直接写"像素值"。
    # 默认字号基准：约 60px 实际像素（竖屏清晰可读，不遮挡主体）
    # 换算：实际px = fs × (vh/288) → 要 60px 则 fs = 60×288/vh（1920p 下 ≈ 9）
    fs = args.fontsize or max(4.0, round(60 * 288 / (vh or 1920), 1))
    # 不设 WrapStyle（默认=0 智能换行，长句自动折行到第2行；短句保持一行）
    style = (f"FontName=Microsoft YaHei,FontSize={fs},"
             f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             f"Outline=2,Bold=1,Alignment=2,MarginV=40")
    # 相对文件名（无盘符冒号），ffmpeg 以 srt_dir 为 cwd 解析
    vf = f"subtitles={srt_name}:force_style='{style}'"

    # 最终时长 = 原视频与配音的较大者（配音短则补静音，长则顺延）
    final_dur = max(orig_dur, audio_dur) if orig_dur > 0 else audio_dur

    out_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-i", args.original,
        "-i", args.audio,
        "-filter_complex", f"[0:v]{vf}[v];[1:a]apad[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{final_dur:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        args.output,
    ]
    print("[run] ffmpeg 合成（原画面 + 口播语音 + 字幕）……", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=srt_dir)
    # 清理临时目录（字幕可重建，无需保留）
    try:
        import shutil as _shutil
        _shutil.rmtree(srt_dir, ignore_errors=True)
    except Exception:
        pass
    if r.returncode != 0:
        print("=== STDERR (tail) ===", file=sys.stderr)
        print(r.stderr[-2500:], file=sys.stderr)
        sys.exit(r.returncode)
    print(f"MERGED_VIDEO={args.output} size={os.path.getsize(args.output)}", flush=True)


if __name__ == "__main__":
    main()
