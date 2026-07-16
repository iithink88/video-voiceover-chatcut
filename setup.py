#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video-voiceover-chatcut 一键安装依赖（给朋友用）
===============================================
做三件事：
  1. 建虚拟环境  ~/.workbuddy/binaries/python/envs/default
  2. 装 edge_tts / vosk / soundfile（清华镜像，国内快）
  3. 下载 Vosk 中文模型到 ~/.cache/vosk-models/vosk-model-small-cn-0.22

注意：ffmpeg 二进制较大且需单独下载，本脚本不自动装，请按 SKILL.md 说明自行安装
并加入 PATH（或放到 %USERPROFILE%/bin/ffmpeg/ffmpeg-8.1.2-essentials_build/bin）。
"""
import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess


home = os.path.expanduser("~")
venv = os.path.join(home, ".workbuddy", "binaries", "python", "envs", "default")
py = os.path.join(venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv, "bin", "python")


def run(msg, cmd):
    print(f"[*] {msg} ...", flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"[!] {msg} 失败（返回码 {r.returncode}）")
        sys.exit(1)


# 1. 建 venv（若尚未存在）
if not os.path.exists(py):
    print(f"[*] 创建虚拟环境：{venv}", flush=True)
    base = sys.executable
    r = subprocess.run([base, "-m", "venv", venv])
    if r.returncode != 0:
        alt = shutil.which("python") or shutil.which("python3")
        if alt:
            r = subprocess.run([alt, "-m", "venv", venv])
        if r.returncode != 0:
            print("[!] 无法创建虚拟环境，请先安装 Python 3.11+。")
            sys.exit(1)

# 2. 装依赖
run("安装 edge_tts / vosk / soundfile（清华镜像）",
    [py, "-m", "pip", "install", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
     "edge_tts", "vosk", "soundfile"])

# 3. 下载 Vosk 中文模型
model_name = "vosk-model-small-cn-0.22"
model_dir = os.path.join(home, ".cache", "vosk-models", model_name)
if os.path.isdir(model_dir):
    print(f"[*] Vosk 模型已存在：{model_dir}，跳过下载", flush=True)
else:
    url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
    parent = os.path.dirname(model_dir)
    os.makedirs(parent, exist_ok=True)
    zip_path = os.path.join(parent, model_name + ".zip")
    print(f"[*] 下载 Vosk 模型（约 40MB）：{url}", flush=True)
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("[*] 解压模型...", flush=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(parent)
        os.remove(zip_path)
    except Exception as e:
        print(f"[!] 模型下载失败：{e}")
        print(f"    请手动下载 {url} 解压到 {model_dir}", flush=True)
        sys.exit(1)

print("\n[完成] 依赖已安装。", flush=True)
print(f"    若仍提示找不到 Vosk 模型，请设置环境变量 VOSK_MODEL={model_dir}", flush=True)
print("    ffmpeg 仍需自行安装并加入 PATH（或放到 %USERPROFILE%/bin/ffmpeg/ffmpeg-8.1.2-essentials_build/bin）", flush=True)
