#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地生成"口播视频"：把文本用 edge-tts 晓晓声配音，再用 text-to-clonedvoice-video-full
的分镜渲染 + Vosk 字幕对齐，合成一段带配音+字幕的横版口播视频。
这是 video-voiceover-chatcut 技能的第 1 段；第 2 段（合并进原视频）由 ChatCut MCP 完成。
"""
import sys, os, argparse, subprocess, shutil

# —— Windows Python 子进程编码铁律：入口强制 UTF-8 ——
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 默认路径改为自动探测（见 scripts/paths.py），可用参数覆盖
from paths import detect_paths, missing_hints


def run(cmd, env, cwd):
    print("[run]", " ".join(str(c) for c in cmd[:3]), "...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, cwd=cwd)
    if r.returncode != 0:
        print("=== STDERR (tail) ===", file=sys.stderr)
        print(r.stderr[-2500:], file=sys.stderr)
        raise RuntimeError(f"command failed RC={r.returncode}: {' '.join(cmd[:3])}")
    return r


def main():
    ap = argparse.ArgumentParser(description="生成口播视频（文本→晓晓声配音→分镜渲染）")
    ap.add_argument("--text", required=True, help="文案文件路径（UTF-8，内容即字幕+朗读稿）")
    ap.add_argument("--output", required=True, help="口播视频输出绝对路径，如 D:/x/口播视频.mp4")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="edge-tts 音色")
    ap.add_argument("--speed", type=float, default=1.3, help="配音语速倍率")
    ap.add_argument("--workdir", default=None, help="中间文件目录，默认输出目录下的 _narration_work")
    ap.add_argument("--venv-py", default=None, help="覆盖：托管 venv 的 python.exe")
    ap.add_argument("--tts-skill", default=None, help="覆盖：text-to-clonedvoice-video-full/scripts 目录")
    ap.add_argument("--vosk-model", default=None, help="覆盖：vosk-model-small-cn-0.22 目录")
    ap.add_argument("--ffmpeg-bin", default=None, help="覆盖：ffmpeg.exe 所在目录")
    ap.add_argument("--node-bin", default=None, help="覆盖：node.exe 所在目录")
    args = ap.parse_args()

    text_path = os.path.abspath(args.text)
    out_path = os.path.abspath(args.output)
    workdir = args.workdir or os.path.join(os.path.dirname(out_path), "_narration_work")
    os.makedirs(workdir, exist_ok=True)

    # —— 自动探测路径（跨用户可移植）——
    p = detect_paths()
    venv_py = args.venv_py or p["venv_py"]
    tts_skill = args.tts_skill or p["tts_skill"]
    vosk_model = args.vosk_model or p["vosk_model"]
    ffmpeg_bin = args.ffmpeg_bin or p["ffmpeg_bin"]
    node_bin = args.node_bin or p["node_bin"]

    # 依赖校验（给出中文提示，避免看不懂的异常）
    for path, label in [
        (os.path.join(tts_skill, "build_video.py"), "text-to-clonedvoice-video-full 技能"),
        (os.path.join(ffmpeg_bin, "ffmpeg.exe") if ffmpeg_bin else "", "ffmpeg"),
    ]:
        if not os.path.isfile(path):
            sys.exit("[!] 缺少依赖：" + label + "。\n    请先：① 在 WorkBuddy 安装 text-to-clonedvoice-video-full 技能；"
                     "② 安装 ffmpeg 并加入 PATH；或双击本技能的『安装依赖.bat』。\n    详情：\n    " + "\n    ".join(missing_hints(p)))
    if not vosk_model or not os.path.isdir(vosk_model):
        sys.exit("[!] 缺少 Vosk 中文模型。请双击『安装依赖.bat』自动下载，或设置 VOSK_MODEL 环境变量。\n    详情：\n    " + "\n    ".join(missing_hints(p)))

    # 组装运行环境（ffmpeg/node 进 PATH，Vosk 模型进 env）
    env = dict(os.environ)
    env["PATH"] = ffmpeg_bin + os.pathsep + node_bin + os.pathsep + env.get("PATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env["VOSK_MODEL"] = vosk_model

    py = venv_py
    skill = tts_skill
    mp3 = os.path.join(workdir, "narration.mp3")

    # —— 第 1 步：edge-tts 生成配音 ——
    run([py, os.path.join(skill, "generate_voice_edgetts.py"),
         "--text", text_path, "--out", mp3, "--voice", args.voice], env=env, cwd=workdir)

    # —— 第 2 步：分镜渲染 + 字幕对齐 + 合成口播视频 ——
    # 注意：build_video 必须同时传 --audio（配音）和 --input（文案，用于切句做分镜/字幕对齐）
    built = os.path.join(workdir, "_narration_out.mp4")
    run([py, os.path.join(skill, "build_video.py"),
         "--audio", mp3,
         "--input", text_path,
         "--speed", str(args.speed),
         "--workdir", workdir,
         "--output", built], env=env, cwd=workdir)

    # 兼容 build_video 把产物写到 cwd 的情况：扫描 workdir 找最新 mp4
    if not os.path.exists(built):
        cands = [f for f in os.listdir(workdir) if f.lower().endswith(".mp4")]
        if cands:
            built = os.path.join(workdir, sorted(
                cands, key=lambda f: os.path.getmtime(os.path.join(workdir, f)))[-1])

    if built != out_path:
        shutil.copy(built, out_path)

    size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"NARRATION_VIDEO={out_path} size={size}", flush=True)


if __name__ == "__main__":
    main()
