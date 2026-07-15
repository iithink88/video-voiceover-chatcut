# video-voiceover-chatcut

> 视频配音字幕合成（ChatCut 版）—— 把「一个视频 + 一个文本文件」变成「原视频画面 + 文本朗读语音 + 同步字幕」的成片。

这是「ChatGPT 语音模式卡片 · 口播版」的完整复刻流程，打包成一个可分享的 WorkBuddy 技能。

## 效果

- 输入：一个视频（**可以完全没有声音**）+ 一个 `.txt` 文案
- 输出：原视频画面 + 朗读语音（晓晓声等 edge-tts 中文音色）+ 同步字幕
- 两条合成路径：
  - **② 本地快速版**：本机 ffmpeg 直接烧录字幕 + 混入配音，无需联网、无需 ChatCut
  - **③ ChatCut 精致版**：用 ChatCut（MCP）把口播视频的语音和字幕合并进原视频，字幕由云端转录自动生成、可在 ChatCut 编辑器二次剪辑

> 为什么需要「口播视频」做载体：ChatCut 字幕由语音转录驱动，静音视频本身加不了字幕。所以技能会先用文本生成一个带真实语音的口播视频，再把它当字幕/语音载体合并进原视频。

## 仓库结构

```
video-voiceover-chatcut/
├── SKILL.md              # AI 执行指令（含完整 ChatCut 工具调用流程）
├── README.md             # 你正在看的文件
├── LICENSE               # MIT
├── .gitignore
├── 启动.bat              # 双击打开图形界面
├── 安装依赖.bat          # 一键建 venv + 装 edge_tts/vosk/soundfile + 下 Vosk 模型
├── setup.py              # 同上的 Python 实现
├── scripts/
│   ├── gui.py            # tkinter 图形界面（选语速/播音人）
│   ├── make_narration.py # 第 1 段：文本 → 口播视频
│   ├── merge_local.py    # 第 2 段-lite：本地 ffmpeg 合成成品
│   └── paths.py          # 跨用户路径自动探测（不写死用户名）
└── examples/             # 示例文件（可直接拿来试）
    ├── 原片：ChatGPT 新版语音模式的卡片.mp4
    ├── 字幕：ChatGPT 新版语音模式的卡片.txt
    └── 成品：ChatGPT 新版语音模式的卡片.mp4
```

## 朋友怎么装这个技能（3 种方式）

1. **拖拽安装**：把 `SKILL.md` 直接拖进 WorkBuddy 聊天框，按提示安装。
2. **文件夹安装**：把整个 `video-voiceover-chatcut` 文件夹放进 `~/.workbuddy/skills/`。
3. **命令行安装**：`npx skills add iithink88/video-voiceover-chatcut@video-voiceover-chatcut`

## 朋友怎么用（图形界面，推荐）

1. 装好本技能 + `text-to-clonedvoice-video-full` 技能（提供 `build_video.py`/`generate_voice_edgetts.py`）。
2. 装好 ffmpeg（加入 PATH，或放到 `%USERPROFILE%/bin/ffmpeg/ffmpeg-8.1.2-essentials_build/bin`）。
3. 双击 **`安装依赖.bat`** → 自动建 venv + 装依赖 + 下载 Vosk 中文模型。
4. 双击 **`启动.bat`** → 选原视频 / 文案 / 播音人 / 语速 → 点 ① 生成口播 → 点 ② 本地合成成品。

想走 ChatCut 精致版的朋友，额外需要：连接 ChatCut MCP 并用 ChatCut 账号 OAuth 登录（详见 SKILL.md「前置依赖」）。

## 立即试示例

`examples/` 里已经放好了示例：用「原片」+「字幕 .txt」，按上面步骤就能复现「成品」效果。

## 授权

MIT License © 2026 iithink88
