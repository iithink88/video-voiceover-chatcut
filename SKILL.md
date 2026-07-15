---
name: video-voiceover-chatcut
description: 视频配音字幕合成（ChatCut 版）。输入一个视频（可以没有声音）和一个文本文件：先用 text-to-clonedvoice-video-full 把文本做成带晓晓声配音+字幕的口播视频，再用 ChatCut（MCP）把口播视频的语音和字幕合并进原视频——最终成品 = 原视频画面 + 朗读语音 + 同步字幕。这是「ChatGPT语音模式卡片-口播版」的复刻流程。触发词：“用 ChatCut 给视频加配音字幕”“把文本做成口播再合进视频”“视频配语音和字幕（ChatCut）”“复刻口播版视频”。
agent_created: true
---

# 视频配音字幕合成（ChatCut 版）video-voiceover-chatcut

## 概览

把 **「一个视频 + 一个文本文件」** 变成 **「原视频画面 + 文本朗读语音 + 同步字幕」** 的成片。

流程分两段：
1. **本地生成口播视频**（脚本化）：文本 → edge-tts 晓晓声配音 → text-to-clonedvoice-video-full 分镜渲染 → 带配音+字幕的横版口播视频。
2. **ChatCut 合并**（MCP 工具调用）：原视频画面铺底，口播视频隐藏画面只留语音，启用口播的 transcript 作为字幕，导出成片。

> 为什么走 ChatCut 而不是直接烧录字幕：用户要的就是 ChatCut 合成效果（原画面 + 口播语音 + 自动转录字幕，可后续在 ChatCut 编辑器二次剪辑）。注意：ChatCut 字幕由「语音转录」驱动，**静音视频本身加不了字幕**——所以必须先用第 1 段生成一个「有真实语音」的口播视频作为字幕/语音载体。

## 分享给朋友（把技能拷过去就能用）

本技能已做成**跨用户可移植**：所有路径（python / ffmpeg / vosk 模型 / 技能目录）都由 `scripts/paths.py` 自动探测，不写死任何用户名。把整个 `video-voiceover-chatcut` 文件夹拷给朋友即可。

朋友 3 步部署：
1. **装 text-to-clonedvoice-video-full 技能**：在 WorkBuddy 里安装该技能（提供 `build_video.py` / `generate_voice_edgetts.py`），或把它的 `scripts/` 目录放到 `~/.workbuddy/skills/text-to-clonedvoice-video-full/scripts`。
2. **装 ffmpeg**：下载 ffmpeg 并加入系统 PATH；或放到 `%USERPROFILE%/bin/ffmpeg/ffmpeg-8.1.2-essentials_build/bin`（脚本会自动找到）。
3. **双击 `安装依赖.bat`**：自动建 venv + 装 edge_tts / vosk / soundfile + 下载 Vosk 中文模型。
4. 双击 **`启动.bat`** 即可用图形界面（缺依赖会弹窗提示，不会闪退）。

> 仅用本地合成（② 按钮）无需 ChatCut；想走 ChatCut 精致版的朋友额外需要：连接 ChatCut MCP 并用账号 OAuth 登录（见「前置依赖」）。

## 图形界面（双击即用，推荐）

不想记命令？直接双击技能目录里的 **`启动.bat`**，弹出窗口后：

1. **原视频**（可静音）：浏览选择要配字幕配音的视频
2. **文案**：选 txt 文件，或点「粘贴…」直接贴文本
3. **播音人**：下拉选 edge-tts 中文音色（晓晓/晓伊/云希/云扬/云健/东北/陕西/台湾）
4. **语速**：滑块 0.8x~2.0x（默认 1.3x）
5. 点 **▶ ① 生成口播视频** → 后台跑第 1 段（约 2~5 分钟，进度在日志框）
6. 点 **▶ ② 本地合成成品** → 用本机 ffmpeg 直接出片（原画面+语音+字幕，**无需 ChatCut、无需联网**）
7. 或点 **⬆ ③ 导出 ChatCut 工程** → 写 `_chatcut_job.json` 并把指令复制到剪贴板，拿去给 AI 走 ChatCut 高质量合并

> GUI 第 ② 步是「本地快速版」：效果等同之前的 `-带字幕.mp4`（硬字幕烧录 + 混入配音），适合马上要成片；第 ③ 步是「ChatCut 精致版」，字幕由云端转录自动生成、可在 ChatCut 编辑器二次剪辑。两条路都基于同一个口播视频。

GUI 文件：`scripts/gui.py`（tkinter，托管 venv 自带 tkinter 8.6）。防闪退要点：用托管 python（`envs/default`）+ `python.exe`、入口 UTF-8 重配置、重活放后台线程、顶层 try/except 弹窗报错。

## 前置依赖

- **ChatCut MCP 已连接**：`~/.workbuddy/mcp.json` 里有 `chatcut`（type:http，url=`https://api.chatcut.io/api/external-mcp/mcp`，header `x-chatcut-mcp-surface: codex`），且用户已在连接器页**信任并 OAuth 登录**（无静态 token）。未登录则 mcp__chatcut__* 工具不可用。
- **text-to-clonedvoice-video-full 技能已装**（提供 `scripts/generate_voice_edgetts.py` 与 `build_video.py`）。
- **托管 venv** 已装 `edge_tts` / `vosk` / `soundfile`：默认 `~/.workbuddy/binaries/python/envs/default`（双击 `安装依赖.bat` 会自动建好）。
- **Vosk 模型**：默认 `~/.cache/vosk-models/vosk-model-small-cn-0.22`（安装脚本会自动下载）；也可设环境变量 `VOSK_MODEL` 指向自定义目录。
- **ffmpeg**：需在 PATH 中，或放到 `%USERPROFILE%/bin/ffmpeg/ffmpeg-8.1.2-essentials_build/bin`。
- 以上路径全部由 `scripts/paths.py` 自动探测，无需手动改配置（也都能用命令行参数 `--venv-py` / `--ffmpeg-bin` 等覆盖）。
- **chatcut-asset-import 技能**已装（提供 `scripts/upload-media.mjs` 上传脚本）。
- 联网（edge-tts 微软 CDN + ChatCut 云端）。

## 第 1 段：生成口播视频（本地，脚本化）

用本技能自带的 `scripts/make_narration.py`：

```bash
# 推荐直接双击 启动.bat 走图形界面；下面是无头命令版（路径均自动探测，无需写死）
PY="$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe"   # 含 edge_tts 的 python
SKILL="$HOME/.workbuddy/skills/video-voiceover-chatcut/scripts"

"$PY" "$SKILL/make_narration.py" \
  --text  "你的文案.txt" \
  --output "口播视频.mp4" \
  --voice "zh-CN-XiaoxiaoNeural" --speed 1.3
```

输出：`口播视频.mp4`（1920×1080 横版，含 aac 配音 + 字幕轨）。约需 2~5 分钟（首次会下载 Chromium 渲染分镜）。

**坑位**：`build_video.py` 必须同时传 `--audio`（配音 mp3）和 `--input`（文案文件，用于切句做分镜/字幕对齐），只传 `--audio` 会报错要求 `--input`。这些 make_narration.py 已处理好。

## 第 2 段：ChatCut 合并（MCP 工具调用）

下面每一步都是**你来调用对应的 `mcp__chatcut__*` 工具**（参数已验证）。

### 2.1 检测原视频比例
先用 ffprobe 取原视频分辨率，决定 ChatCut 画布比例：
- 竖屏（如 1080×1440）→ `ratio="3:4"`
- 横屏（如 1920×1080）→ `ratio="16:9"`

### 2.2 创建项目
`mcp__chatcut__create_project`：`name` 任取，`compositionWidth/Height/fps` 先随便填（下一步改比例）。记下返回的 `projectId`。

### 2.3 把画布改成原视频比例
`mcp__chatcut__manage_timelines`：`action="update"`，`ratio=<上面算的比例>`，`fit="contain"`。
（否则导出会把原视频压成黑边横屏。）

### 2.4 上传原视频到 ChatCut
1. `mcp__chatcut__import_media`：`action="create_session"`，`projectId=...` → 返回 `token` + `endpoint`。
2. 用 Node 跑官方上传脚本（需设 FFMPEG_PATH/FFPROBE_PATH 环境变量）：
```powershell
# 下面路径用 $env:USERPROFILE 表示用户目录（AI 执行时替换为实际路径）
$env:FFMPEG_PATH="$env:USERPROFILE\bin\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"
$env:FFPROBE_PATH="$env:USERPROFILE\bin\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffprobe.exe"
$node="$env:USERPROFILE\.workbuddy\binaries\node\versions\22.22.2\node.exe"
$script="$env:USERPROFILE\.workbuddy\skills\chatcut-asset-import\scripts\upload-media.mjs"
& $node $script --token "<token>" --endpoint "<endpoint>" "原视频.mp4"
```
3. 记下返回的 `assetId`（原视频，记为 **A1**）。视频进入素材库，转录对静音视频会 skipped（正常）。

### 2.5 上传口播视频到同一项目
同上 `create_session` → `upload-media.mjs` → 记下 `assetId`（口播视频，记为 **A2**）。
上传后口播视频有真实语音，ChatCut 会异步转录；稍后查 `mcp__chatcut__read_project`（`assetId=A2`）确认 `transcription.status="ready"` 再继续。

### 2.6 把两个视频放到时间轴
`mcp__chatcut__edit_item`：`projectId=...`，`adds` 两项：
- 原视频：`{ "type":"video", "assetId": A1, "trackId":"V1", "fromFrame":0, "fit":"cover", "muted":true }`（铺满画面、静音）
- 口播视频：`{ "type":"video", "assetId": A2, "fromFrame":0, "opacity":0, "muted":false }`（**隐藏横版画面、保留语音**）

### 2.7 启用字幕并限定为口播音源
1. `mcp__chatcut__edit_captions`：`action="enable"`。
2. `action="source_set"`，`json='{"sources":[{"trackId":"V2"}]}'`（字幕只来自口播音频，忽略静音原视频）。
3. `action="style"`，`json` 设样式（竖屏示例）：
```json
{"sizePx":68,"color":"#FFFFFF","strokeColor":"#000000","strokeWidth":4,
 "backgroundColor":"#000000","backgroundOpacity":0.45,"backgroundRadius":10,
 "maxLines":2,"maxCharactersPerLine":22,"shadowStrength":40}
```
（横屏把 sizePx 调到 40 左右、maxCharactersPerLine 调到 30+。）

### 2.8 导出并下载
1. `mcp__chatcut__submit_export`：`format="video"`，`codec="h264"`，`name="<成片名>"`，`resolution="1080p"` → 返回 `renderId`。
2. `mcp__chatcut__track_export`：`action="wait"`，`renderIds="<renderId>"`，`timeoutSeconds=300` → 返回下载 URL（S3）。
3. 用 curl 把 URL 下载到桌面：
```bash
curl -s -L --max-time 180 -o "<成片名>.mp4" "<S3_URL>"
```

## 备选：本地一键合成（无需 ChatCut / 无需联网）

若不想走 ChatCut（或没登录），用本技能自带的 `scripts/merge_local.py` 直接出片——把第 1 段生成的口播配音 + 字幕烧进原视频画面：

```bash
# 路径自动探测；用托管 venv 的 python（已含依赖）
PY="$HOME/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

# 先生成口播视频（第 1 段）
"$PY" "$SKILL/make_narration.py" --text "文案.txt" --output "口播视频.mp4" \
  --voice "zh-CN-XiaoxiaoNeural" --speed 1.3

# 再本地合成：原视频画面 + 口播配音 + 字幕
"$PY" "$SKILL/merge_local.py" \
  --original "原视频.mp4" \
  --audio   "_narration_work/narration.mp3" \
  --text    "文案.txt" \
  --output  "原视频-口播版.mp4"
```

`merge_local.py` 做的事：ffprobe 取配音时长 → 文案按句切分均匀铺到字幕时间轴（生成临时 `.srt`）→ ffmpeg 原画面静音 + 烧录字幕（竖屏大字号、白字黑描边、底部居中）+ 混入配音（配音短则补静音，长则顺延）。成品与 ChatCut 路径一致：**原视频画面 + 朗读语音 + 同步字幕**。

## 已知限制 / 坑位

- **ChatCut 必须 OAuth 登录**：连接器页信任 `chatcut` 并用 ChatCut 账号授权，无静态 token 可绕过。登录后再新开（或重载）对话，mcp__chatcut__* 工具才可用。
- **原视频比例必须手动匹配**（2.3）：ChatCut 创建项目默认横屏，竖屏原视频不改正会被压黑边。
- **口播视频转录是异步的**：上传后 `transcription` 可能先显示 `skipped`/`pending`，稍等再查 `read_project(assetId=A2)` 直到 `ready` 才启用字幕。
- **edit_item 的 adds 是一次性原子提交**：两个视频一起放，分别设 `V1 muted / V2 opacity:0 muted:false`。
- **upload-media.mjs 必须设 FFMPEG_PATH / FFPROBE_PATH**，否则 ffmpeg probe 失败。
- **文本文件 UTF-8 无 BOM**；带 BOM 首字会异常。
- 若原视频本身有声音且想保留，把 2.6 原视频的 `muted` 改为 `false`（会与原口播语音叠加）。

## 示例

用户：「把这个静音录屏（桌面 a.mp4）配上桌面文案 b.txt 的配音和字幕，用 ChatCut 合成」
→ 第 1 段 make_narration.py 生成口播视频 → 第 2 段 ChatCut 合并导出 → 桌面得到「a-口播版.mp4」。
