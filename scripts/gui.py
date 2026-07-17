#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video-voiceover-chatcut 图形界面（tkinter）
============================================
把"文本→口播视频→合并进原视频(配语音+字幕)"做成双击可用的窗口。

功能：
  · 选原视频（可静音）
  · 选文案（文件或粘贴）
  · 选播音人（edge-tts 中文音色下拉）
  · 拖语速滑块
  · ① 生成配音（本地：edge-tts 文本→mp3，自动适配原视频时长，仅需 edge_tts 库）
  · ② 本地合成成品（ffmpeg：原画面 + 口播语音 + 字幕，无需 ChatCut/Node/Vosk）
  · ③ 导出 ChatCut 工程（写 job 文件 + 复制指令，交给 AI 走 ChatCut 高质量合并）

防闪退要点：入口 UTF-8 重配置；顶层 try/except 弹窗报错；重活放后台线程，UI 线程安全更新。
"""
import sys, os, subprocess, threading, json, tempfile, tkinter as tk
from paths import detect_paths, missing_hints
from tkinter import filedialog, messagebox, ttk, scrolledtext

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
# 自动探测路径（跨用户可移植），见 scripts/paths.py
DEFAULTS = detect_paths()

VOICES = [
    ("晓晓（女·温柔知性）", "zh-CN-XiaoxiaoNeural"),
    ("晓伊（女·亲切活泼）", "zh-CN-XiaoyiNeural"),
    ("云希（男·阳光少年）", "zh-CN-YunxiNeural"),
    ("云扬（男·沉稳新闻）", "zh-CN-YunyangNeural"),
    ("云健（男·运动激昂）", "zh-CN-YunjianNeural"),
    ("辽宁·小贝（女·东北话）", "zh-CN-liaoning-XiaobeiNeural"),
    ("陕西·小妮（女·陕西方言）", "zh-CN-shaanxi-XiaoniNeural"),
    ("台湾·小玉（女·台湾腔）", "zh-TW-HsiaoYuNeural"),
]


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("视频配音字幕合成器  (video-voiceover-chatcut)")
        self.root.geometry("760x620")
        try:
            self.root.iconbitmap()  # 无图标也不报错
        except Exception:
            pass

        self.original_path = tk.StringVar()
        self.text_path = tk.StringVar()       # 文案文件（也可能是粘贴后写的临时文件）
        self.text_pasted = ""                  # 粘贴内容缓存
        self.voice_var = tk.StringVar(value=VOICES[0][0])
        self.speed_var = tk.DoubleVar(value=1.3)
        self.speed_label = tk.StringVar(value="1.3x")
        self.out_info = tk.StringVar(value="输出将放在原视频同目录")

        self.narration_video = None
        self.narration_mp3 = None
        self.busy = False

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        f = ttk.Frame(self.root, padding=10)
        f.pack(fill="both", expand=True)

        row = 0
        ttk.Label(f, text="① 原视频（可静音）：").grid(row=row, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.original_path, width=52).grid(row=row, column=1, sticky="we")
        ttk.Button(f, text="浏览…", command=self.pick_original).grid(row=row, column=2, padx=4)
        row += 1

        ttk.Label(f, text="② 文案：").grid(row=row, column=0, sticky="w")
        ttk.Entry(f, textvariable=self.text_path, width=52).grid(row=row, column=1, sticky="we")
        ttk.Button(f, text="选文件…", command=self.pick_textfile).grid(row=row, column=2, padx=2)
        ttk.Button(f, text="粘贴…", command=self.paste_text).grid(row=row, column=3, padx=2)
        row += 1

        ttk.Label(f, text="③ 播音人：").grid(row=row, column=0, sticky="w")
        cb = ttk.Combobox(f, textvariable=self.voice_var, width=30, state="readonly")
        cb["values"] = [v[0] for v in VOICES]
        cb.grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(f, text="④ 语速：").grid(row=row, column=0, sticky="w")
        sl = ttk.Scale(f, from_=0.8, to=2.0, variable=self.speed_var, orient="horizontal",
                       length=240, command=self._on_speed)
        sl.grid(row=row, column=1, sticky="w")
        ttk.Label(f, textvariable=self.speed_label, width=8).grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(f, textvariable=self.out_info, foreground="#555").grid(row=row, column=0, columnspan=4, sticky="w", pady=4)
        row += 1

        bf = ttk.Frame(f)
        bf.grid(row=row, column=0, columnspan=4, sticky="w", pady=6)
        self.btn_gen = ttk.Button(bf, text="▶ ① 生成配音", command=self.on_generate, width=18)
        self.btn_gen.pack(side="left", padx=4)
        self.btn_merge = ttk.Button(bf, text="▶ ② 本地合成成品", command=self.on_merge, width=18)
        self.btn_merge.pack(side="left", padx=4)
        self.btn_cc = ttk.Button(bf, text="⬆ ③ 导出 ChatCut 工程", command=self.on_export_chatcut, width=20)
        self.btn_cc.pack(side="left", padx=4)
        row += 1

        ttk.Label(f, text="运行日志：").grid(row=row, column=0, sticky="w")
        row += 1
        self.log = scrolledtext.ScrolledText(f, height=18, wrap="word")
        self.log.grid(row=row, column=0, columnspan=4, sticky="nsew")
        f.rowconfigure(row, weight=1)
        f.columnconfigure(1, weight=1)

    def _on_speed(self, *_):
        self.speed_label.set(f"{self.speed_var.get():.1f}x")

    # ---------- 选择文件 ----------
    def pick_original(self):
        p = filedialog.askopenfilename(title="选择原视频",
                                       filetypes=[("视频", "*.mp4 *.mov *.mkv *.avi *.m4v"), ("全部", "*.*")])
        if p:
            self.original_path.set(p)
            d = os.path.dirname(p)
            self.out_info.set(f"输出目录：{d}")

    def pick_textfile(self):
        p = filedialog.askopenfilename(title="选择文案 txt",
                                       filetypes=[("文本", "*.txt *.md"), ("全部", "*.*")])
        if p:
            self.text_path.set(p)
            self.text_pasted = ""

    def paste_text(self):
        win = tk.Toplevel(self.root)
        win.title("粘贴文案")
        win.geometry("560x360")
        st = scrolledtext.ScrolledText(win, wrap="word")
        st.insert("1.0", self.text_pasted)
        st.pack(fill="both", expand=True, padx=8, pady=8)
        bb = ttk.Frame(win); bb.pack(pady=6)

        def ok():
            self.text_pasted = st.get("1.0", "end").strip()
            if self.text_pasted:
                d = os.path.dirname(self.original_path.get()) or tempfile.gettempdir()
                tp = os.path.join(d, "_narration_文案.txt")
                open(tp, "w", encoding="utf-8").write(self.text_pasted)
                self.text_path.set(tp)
                self.log_ui(f"[ok] 已用粘贴文本（{len(self.text_pasted)} 字）")
            win.destroy()

        ttk.Button(bb, text="确定", command=ok).pack(side="left", padx=8)
        ttk.Button(bb, text="取消", command=win.destroy).pack(side="left", padx=8)

    # ---------- 校验 ----------
    def _validate(self):
        if not self.original_path.get() or not os.path.exists(self.original_path.get()):
            messagebox.showerror("缺原视频", "请先选择原视频文件。")
            return False
        if not self.text_path.get() or not os.path.exists(self.text_path.get()):
            messagebox.showerror("缺文案", "请先选择或粘贴文案文本。")
            return False
        return True

    def _voice_id(self):
        label = self.voice_var.get()
        for name, vid in VOICES:
            if name == label:
                return vid
        return VOICES[0][1]

    def _orig_dur(self):
        """探测原视频时长（秒），用于让配音适配原视频、实现音画同步。"""
        ff = DEFAULTS.get("ffmpeg_bin")
        if not ff:
            return 0.0
        fp = os.path.join(ff, "ffprobe.exe")
        if not os.path.isfile(fp):
            return 0.0
        try:
            out = subprocess.check_output(
                [fp, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", self.original_path.get()],
                encoding="utf-8", errors="replace").strip()
            return float(out)
        except Exception:
            return 0.0

    # ---------- 运行包装（后台线程） ----------
    def _run_thread(self, target, btn_enable=True):
        if self.busy:
            return
        self.busy = True
        for b in (self.btn_gen, self.btn_merge, self.btn_cc):
            b.config(state="disabled")
        t = threading.Thread(target=self._wrap, args=(target, btn_enable), daemon=True)
        t.start()

    def _wrap(self, target, btn_enable):
        try:
            target()
        except Exception as e:
            self.log_ui(f"[错误] {e}")
            self.root.after(0, lambda: messagebox.showerror("运行出错", str(e)))
        finally:
            self.busy = False
            if btn_enable:
                self.root.after(0, self._enable_buttons)

    def _enable_buttons(self):
        for b in (self.btn_gen, self.btn_merge, self.btn_cc):
            b.config(state="normal")

    def log_ui(self, msg):
        self.root.after(0, lambda: self._append(msg))

    def _append(self, msg):
        self.log.insert("end", str(msg).rstrip() + "\n")
        self.log.see("end")

    def _run_capture(self, cmd, env, cwd):
        """实时把子进程输出打到日志（线程内调用，log_ui 负责线程安全）。"""
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              encoding="utf-8", errors="replace", env=env, cwd=cwd)
        for line in p.stdout:
            self.log_ui(line.rstrip())
        p.wait()
        if p.returncode != 0:
            raise RuntimeError(f"步骤失败（返回码 {p.returncode}）")
        return p.returncode

    def _env(self):
        env = dict(os.environ)
        # 核心流程只需要 ffmpeg；node/vosk 仅在完整版 text-to-clonedvoice-video-full 路径需要
        ff = DEFAULTS.get("ffmpeg_bin")
        if ff:
            env["PATH"] = ff + os.pathsep + env.get("PATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        if DEFAULTS.get("vosk_model"):
            env["VOSK_MODEL"] = DEFAULTS["vosk_model"]
        return env

    # ---------- ① 生成口播视频 ----------
    def on_generate(self):
        if not self._validate():
            return
        self._run_thread(self._do_generate)

    def _do_generate(self):
        orig = self.original_path.get()
        txt = self.text_path.get()
        workdir = os.path.join(os.path.dirname(os.path.abspath(orig)), "_narration_work")
        os.makedirs(workdir, exist_ok=True)
        out = os.path.join(workdir, "narration.mp3")
        self.log_ui(f"[开始] 生成配音 → {out}")
        self.log_ui(f"       播音人={self._voice_id()}  语速={self.speed_var.get():.1f}x")

        env = self._env()
        py = DEFAULTS["venv_py"]
        make = os.path.join(SCRIPTS, "make_narration.py")
        # 音画同步：取原视频时长，让配音自动适配（与原视频等长）
        target = self._orig_dur()
        cmd = [
            py, make,
            "--text", txt,
            "--output", out,
            "--voice", self._voice_id(),
            "--speed", str(self.speed_var.get()),
        ]
        if target and target > 0:
            cmd += ["--target-duration", f"{target:.3f}"]
            self.log_ui(f"       原视频时长={target:.1f}s → 配音将自动适配到此长度（音画同步）")
        self._run_capture(cmd, env, workdir)

        self.narration_video = out  # 兼容：此处实际是 mp3
        self.narration_mp3 = out
        self.log_ui(f"[完成] 配音已生成：{out}")
        self.log_ui(f"        下一步点『② 本地合成成品』合并原视频+语音+字幕")

    # ---------- ② 本地合成成品 ----------
    def on_merge(self):
        if not self._validate():
            return
        # 若还没生成口播视频，先生成
        if not (self.narration_video and os.path.exists(self.narration_video)):
            self.log_ui("[提示] 尚未生成口播视频，先执行①……")
            self._do_generate()
            if not (self.narration_video and os.path.exists(self.narration_video)):
                raise RuntimeError("口播视频未生成，无法合成。")
        self._run_thread(self._do_merge, btn_enable=False)

    def _do_merge(self):
        orig = self.original_path.get()
        txt = self.text_path.get()
        workdir = os.path.join(os.path.dirname(os.path.abspath(orig)), "_narration_work")
        os.makedirs(workdir, exist_ok=True)
        mp3 = self.narration_mp3 or os.path.join(workdir, "narration.mp3")

        # 若还没生成配音，自动先生成
        if not os.path.exists(mp3):
            self.log_ui("[提示] 尚未生成配音，先自动执行①……")
            self._do_generate()
            if not os.path.exists(mp3):
                raise RuntimeError("配音未生成，无法合成。")
        base = os.path.splitext(os.path.basename(orig))[0]
        out = os.path.join(os.path.dirname(os.path.abspath(orig)), f"{base}-口播版.mp4")
        self.log_ui(f"[开始] 本地合成成品 → {out}")

        env = self._env()
        merge = os.path.join(SCRIPTS, "merge_local.py")
        self._run_capture([
            DEFAULTS["venv_py"], merge,
            "--original", orig,
            "--audio", mp3,
            "--text", txt,
            "--output", out,
        ], env, os.path.dirname(os.path.abspath(orig)))

        self.log_ui(f"[完成] 成品已生成：{out}")
        self.root.after(0, lambda: messagebox.showinfo("完成", f"成品已生成：\n{out}"))

    # ---------- ③ 导出 ChatCut 工程 ----------
    def on_export_chatcut(self):
        if not self._validate():
            return
        if not (self.narration_video and os.path.exists(self.narration_video)):
            messagebox.showinfo("先生成口播视频", "请先点『① 生成口播视频』，再导出 ChatCut 工程。")
            return
        orig = self.original_path.get()
        txt = self.text_path.get()
        d = os.path.dirname(os.path.abspath(orig))
        job = {
            "original_video": orig,
            "narration_video": self.narration_video,
            "text_file": txt,
            "voice": self._voice_id(),
            "speed": self.speed_var.get(),
            "output_name": f"{os.path.splitext(os.path.basename(orig))[0]}-口播版.mp4",
            "canvas": "auto(按原视频比例：竖屏3:4/横屏16:9)",
            "chatcut_steps": [
                "import_media 上传 narration_video 到项目",
                "edit_item: V1=原视频(cover,muted) + V2=口播视频(opacity:0,muted:false)",
                "edit_captions enable + source_set{V2} + style(竖屏大字白字描边)",
                "submit_export h264 → track_export wait → 下载",
            ],
        }
        job_path = os.path.join(d, "_chatcut_job.json")
        open(job_path, "w", encoding="utf-8").write(json.dumps(job, ensure_ascii=False, indent=2))

        instr = (f"用 video-voiceover-chatcut 技能完成 ChatCut 合并：\n"
                 f"原视频：{orig}\n"
                 f"口播视频：{self.narration_video}\n"
                 f"文案：{txt}\n"
                 f"要求：原视频画面铺底(静音) + 口播视频隐藏画面只留语音 + 启用口播 transcript 字幕，"
                 f"画布按原视频比例，导出竖屏/横屏成品。job 详情见 {job_path}")
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(instr)
            clip_hint = "（已复制到剪贴板）"
        except Exception:
            clip_hint = ""
        self.log_ui(f"[ok] ChatCut 工程已导出：{job_path} {clip_hint}")
        messagebox.showinfo("已导出 ChatCut 工程",
                            f"已写好工程文件：\n{job_path}\n\n"
                            f"把下面的指令发给 AI 即可走 ChatCut 高质量合并：\n\n{instr}")


def main():
    try:
        root = tk.Tk()
        # 轻量级启动检查：只确认 python 可用，不强制要求 text-to-clonedvoice-video-full / vosk
        # （核心流程 ①② 只需 edge_tts + ffmpeg，缺了会在运行时给友好提示）
        py = DEFAULTS.get("venv_py", "")
        if not py or not os.path.isfile(py):
            # 尝试找系统 python
            import shutil
            py = shutil.which("python") or shutil.which("python3") or ""
        try:
            import edge_tts
            has_edge = True
        except ImportError:
            has_edge = False

        warnings = []
        if not has_edge:
            warnings.append("• 缺少 edge_tts 库 → 请双击『安装依赖.bat』安装")
        ff = DEFAULTS.get("ffmpeg_bin", "")
        if not ff or not os.path.isfile(os.path.join(ff, "ffmpeg.exe")):
            warnings.append("• 缺少 ffmpeg → 请安装并加入 PATH")

        if warnings:
            messagebox.showwarning(
                "部分依赖缺失",
                "以下依赖暂时缺少，但不影响基本使用（运行时再提示）：\n\n"
                + "\n".join(warnings)
                + "\n\n建议双击『安装依赖.bat』一键安装。")
            # 不退出，让用户仍可使用已有功能

        App(root)
        root.mainloop()
    except Exception as e:
        try:
            messagebox.showerror("启动失败", str(e))
        except Exception:
            pass
        # 写日志便于排查
        try:
            open(os.path.join(tempfile.gettempdir(), "video_voiceover_gui_error.log"),
                 "w", encoding="utf-8").write(repr(e))
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
