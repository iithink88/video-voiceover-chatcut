#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨用户路径探测（video-voiceover-chatcut）
=========================================
本技能要分享给不同用户，不能写死 C:/Users/xxx。这里统一探测 5 个关键路径，
优先用 PATH 里的可执行文件，否则退回 WorkBuddy 标准目录（~/.workbuddy/...）。

探测顺序：
  venv_py    : shutil.which("python") → WorkBuddy 托管 venv
  tts_skill  : ~/.workbuddy/skills/text-to-clonedvoice-video-full/scripts
  vosk_model : 环境变量 VOSK_MODEL → ~/.cache/vosk-models → ~/.workbuddy/models → 项目目录(兜底)
  ffmpeg_bin : shutil.which("ffmpeg") → 常见安装位置
  node_bin   : shutil.which("node") → WorkBuddy 托管 node 最新版本
"""
import os
import shutil


def detect_paths():
    home = os.path.expanduser("~")

    # 1. venv python（WorkBuddy 托管环境，已装 edge_tts/vosk/soundfile）
    venv_py = (
        shutil.which("python")
        or shutil.which("python3")
        or os.path.join(home, ".workbuddy", "binaries", "python",
                        "envs", "default", "Scripts", "python.exe")
    )

    # 2. text-to-clonedvoice-video-full 技能脚本目录（WorkBuddy 标准位置）
    tts_skill = os.path.join(
        home, ".workbuddy", "skills",
        "text-to-clonedvoice-video-full", "scripts"
    )

    # 3. Vosk 中文模型（环境变量优先，其次标准缓存/模型目录）
    vosk = os.environ.get("VOSK_MODEL")
    if not vosk:
        for cand in [
            os.path.join(home, ".cache", "vosk-models", "vosk-model-small-cn-0.22"),
            os.path.join(home, ".workbuddy", "models", "vosk-model-small-cn-0.22"),
            os.path.join(home, "WorkBuddy", "Claw", "_vosk_model", "vosk-model-small-cn-0.22"),
        ]:
            if os.path.isdir(cand):
                vosk = cand
                break

    # 4. ffmpeg（优先 PATH，否则常见安装位置）
    ffmpeg_bin = None
    fw = shutil.which("ffmpeg")
    if fw:
        ffmpeg_bin = os.path.dirname(fw)
    else:
        for cand in [
            os.path.join(home, "bin", "ffmpeg", "ffmpeg-8.1.2-essentials_build", "bin"),
            r"C:/ffmpeg/bin",
            r"C:/Program Files/ffmpeg/bin",
        ]:
            if os.path.exists(os.path.join(cand, "ffmpeg.exe")):
                ffmpeg_bin = cand
                break

    # 5. node（优先 PATH，否则 WorkBuddy 托管 node 目录下的任意版本）
    node_bin = None
    nw = shutil.which("node")
    if nw:
        node_bin = os.path.dirname(nw)
    else:
        nb = os.path.join(home, ".workbuddy", "binaries", "node", "versions")
        if os.path.isdir(nb):
            try:
                vers = sorted(os.listdir(nb))
                if vers:
                    node_bin = os.path.join(nb, vers[-1])
            except Exception:
                pass

    return {
        "venv_py": venv_py,
        "tts_skill": tts_skill,
        "vosk_model": vosk,
        "ffmpeg_bin": ffmpeg_bin,
        "node_bin": node_bin,
    }


# 依赖缺失时给中文提示，避免用户面对一堆看不懂的异常
def missing_hints(p):
    miss = []
    if not os.path.isfile(os.path.join(p["tts_skill"], "build_video.py")):
        miss.append(
            "text-to-clonedvoice-video-full 技能：请在 WorkBuddy 中安装该技能，或把它的 scripts "
            "目录放到 ~/.workbuddy/skills/text-to-clonedvoice-video-full/scripts"
        )
    if not p["ffmpeg_bin"] or not os.path.isfile(os.path.join(p["ffmpeg_bin"], "ffmpeg.exe")):
        miss.append(
            "ffmpeg：请安装 ffmpeg 并加入 PATH，或放到 %USERPROFILE%/bin/ffmpeg/"
            "ffmpeg-8.1.2-essentials_build/bin"
        )
    if not p["vosk_model"] or not os.path.isdir(p["vosk_model"]):
        miss.append(
            "Vosk 中文模型：请双击『安装依赖.bat』自动下载，或设置环境变量 VOSK_MODEL 指向 "
            "vosk-model-small-cn-0.22 目录"
        )
    return miss


if __name__ == "__main__":
    import json
    print(json.dumps(detect_paths(), ensure_ascii=False, indent=2))
