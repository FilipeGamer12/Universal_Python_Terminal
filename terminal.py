import os
import re
import sys
import json
import queue
import signal
import threading
import locale
import codecs
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, messagebox

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

try:
    import vlc
except ImportError:
    vlc = None


APP_NAME = "ShellTerminal"
ALIASES_FILE = Path.home() / ".shell_terminal_aliases.json"

IMAGE_EXTS = {".png", ".gif", ".ppm", ".pgm", ".jpg", ".jpeg"}
TEXT_EXTS = {
    ".txt", ".log", ".md", ".rst", ".py", ".json", ".xml", ".html", ".htm",
    ".css", ".js", ".csv", ".ini", ".cfg", ".conf", ".yml", ".yaml", ".toml",
    ".bat", ".cmd", ".ps1", ".sh", ".c", ".cpp", ".h", ".java", ".go", ".rs",
}
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".m4v"}

ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")

FG_COLORS = {
    30: "ansi_black",
    31: "ansi_red",
    32: "ansi_green",
    33: "ansi_yellow",
    34: "ansi_blue",
    35: "ansi_magenta",
    36: "ansi_cyan",
    37: "ansi_white",
    90: "ansi_bright_black",
    91: "ansi_bright_red",
    92: "ansi_bright_green",
    93: "ansi_bright_yellow",
    94: "ansi_bright_blue",
    95: "ansi_bright_magenta",
    96: "ansi_bright_cyan",
    97: "ansi_bright_white",
}

BG_COLORS = {
    40: "bg_black",
    41: "bg_red",
    42: "bg_green",
    43: "bg_yellow",
    44: "bg_blue",
    45: "bg_magenta",
    46: "bg_cyan",
    47: "bg_white",
    100: "bg_bright_black",
    101: "bg_bright_red",
    102: "bg_bright_green",
    103: "bg_bright_yellow",
    104: "bg_bright_blue",
    105: "bg_bright_magenta",
    106: "bg_bright_cyan",
    107: "bg_bright_white",
}

STYLE_TAGS = {
    "ansi_black": {"foreground": "#000000"},
    "ansi_red": {"foreground": "#ff5f56"},
    "ansi_green": {"foreground": "#00c853"},
    "ansi_yellow": {"foreground": "#ffbd2e"},
    "ansi_blue": {"foreground": "#2d8cff"},
    "ansi_magenta": {"foreground": "#c678dd"},
    "ansi_cyan": {"foreground": "#00d8d8"},
    "ansi_white": {"foreground": "#e6e6e6"},
    "ansi_bright_black": {"foreground": "#808080"},
    "ansi_bright_red": {"foreground": "#ff6b6b"},
    "ansi_bright_green": {"foreground": "#7CFC00"},
    "ansi_bright_yellow": {"foreground": "#ffe066"},
    "ansi_bright_blue": {"foreground": "#6ea8fe"},
    "ansi_bright_magenta": {"foreground": "#f783ac"},
    "ansi_bright_cyan": {"foreground": "#66d9e8"},
    "ansi_bright_white": {"foreground": "#ffffff"},
    "bg_black": {"background": "#000000"},
    "bg_red": {"background": "#3a0000"},
    "bg_green": {"background": "#003a00"},
    "bg_yellow": {"background": "#3a2a00"},
    "bg_blue": {"background": "#001a3a"},
    "bg_magenta": {"background": "#3a0030"},
    "bg_cyan": {"background": "#00343a"},
    "bg_white": {"background": "#3a3a3a"},
    "bg_bright_black": {"background": "#1f1f1f"},
    "bg_bright_red": {"background": "#4d0000"},
    "bg_bright_green": {"background": "#004d00"},
    "bg_bright_yellow": {"background": "#4d3900"},
    "bg_bright_blue": {"background": "#002a4d"},
    "bg_bright_magenta": {"background": "#4d0040"},
    "bg_bright_cyan": {"background": "#00484d"},
    "bg_bright_white": {"background": "#4d4d4d"},
    "bold": {"font": ("Consolas", 11, "bold")},
}


class ShellBridge:
    def __init__(self):
        self.proc = None
        self.master_fd = None
        self.reader_thread = None
        self.alive = False
        self.queue = queue.Queue()
        self.shell_name = None
        self.encoding = "utf-8"
        self.decoder = None
        self.prompt_token = "__PYTERM__"

    def _windows_console_encoding(self):
        try:
            import ctypes
            cp = ctypes.windll.kernel32.GetConsoleOutputCP()
            if cp and cp > 0:
                return f"cp{cp}"
        except Exception:
            pass
        return locale.getpreferredencoding(False) or "utf-8"

    def _make_decoder(self):
        self.decoder = codecs.getincrementaldecoder(self.encoding)(errors="replace")

    def start(self):
        if os.name == "nt":
            shell = os.environ.get("COMSPEC", "cmd.exe")
            self.encoding = self._windows_console_encoding()
            self._make_decoder()

            startup = f"prompt {self.prompt_token}$G"
            self.proc = subprocess.Popen(
                [shell, "/Q", "/D", "/K", startup],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
            self.shell_name = shell
            self.alive = True
            self.reader_thread = threading.Thread(target=self._read_windows, daemon=True)
            self.reader_thread.start()
        else:
            import pty
            shell = os.environ.get("SHELL", "/bin/bash")
            self.encoding = locale.getpreferredencoding(False) or "utf-8"
            self._make_decoder()

            env = os.environ.copy()
            env["PS1"] = self.prompt_token + " "
            env["PROMPT_COMMAND"] = ""

            pid, master_fd = pty.fork()
            if pid == 0:
                os.execvpe(shell, [shell], env)

            self.proc = pid
            self.master_fd = master_fd
            self.shell_name = shell
            self.alive = True
            self.reader_thread = threading.Thread(target=self._read_posix, daemon=True)
            self.reader_thread.start()

    def _push_decoded(self, data: bytes):
        if not data:
            return
        if self.decoder is None:
            self._make_decoder()
        text = self.decoder.decode(data)
        if text:
            self.queue.put(text)

    def _flush_decoder(self):
        if self.decoder is None:
            return
        tail = self.decoder.decode(b"", final=True)
        if tail:
            self.queue.put(tail)

    def _read_windows(self):
        assert self.proc is not None and self.proc.stdout is not None
        while self.alive:
            try:
                data = self.proc.stdout.read(4096)
            except Exception:
                break
            if not data:
                break
            self._push_decoded(data)

        self._flush_decoder()
        self.alive = False

    def _read_posix(self):
        import select
        assert self.master_fd is not None
        while self.alive:
            r, _, _ = select.select([self.master_fd], [], [], 0.05)
            if self.master_fd in r:
                try:
                    data = os.read(self.master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                self._push_decoded(data)

        self._flush_decoder()
        self.alive = False

    def send(self, text):
        if not self.alive:
            return
        payload = text if text.endswith("\n") else text + "\n"
        if os.name == "nt":
            assert self.proc is not None and self.proc.stdin is not None
            self.proc.stdin.write(payload.encode(self.encoding, errors="replace"))
            self.proc.stdin.flush()
        else:
            assert self.master_fd is not None
            os.write(self.master_fd, payload.encode(self.encoding, errors="replace"))

    def terminate(self):
        self.alive = False
        try:
            if os.name == "nt":
                if self.proc and self.proc.poll() is None:
                    self.proc.terminate()
            else:
                if self.proc is not None:
                    os.kill(self.proc, signal.SIGHUP)
        except Exception:
            pass


class MediaViewer(tk.Toplevel):
    def __init__(self, master, path: Path):
        super().__init__(master)
        self.path = path
        self._photo = None
        self.player = None          # instância vlc.MediaPlayer
        self._is_playing = False
        self.dragging = False       # flag para evitar conflitos na barra de progresso
        self.length_known = False
        self.player_length = 0
        self._update_progress_id = None

        self.title(f"View - {path.name}")
        self.geometry("920x680")
        self.minsize(640, 420)
        self.configure(bg="#111827")
        self.transient(master)
        self.grab_set()

        head = tk.Frame(self, bg="#111827")
        head.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(
            head,
            text=path.name,
            bg="#111827",
            fg="#e5e7eb",
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x")

        self.info = tk.Label(
            head,
            text=self._info_text(),
            bg="#111827",
            fg="#9ca3af",
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        self.info.pack(fill="x", pady=(4, 0))

        self.body = tk.Frame(self, bg="#111827")
        self.body.pack(fill="both", expand=True, padx=12, pady=12)

        self._show()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _info_text(self):
        try:
            stat = self.path.stat()
            size = stat.st_size
        except Exception:
            size = "?"

        return f"Tipo: {self.path.suffix.lower() or 'sem extensão'}   |   Tamanho: {size} bytes"

    def _show(self):
        ext = self.path.suffix.lower()

        if ext in IMAGE_EXTS:
            self._show_image()
            return

        if ext in TEXT_EXTS or self._looks_text():
            self._show_text()
            return

        if ext in AUDIO_EXTS or ext in VIDEO_EXTS:
            if vlc is not None:
                self._show_media()
            else:
                kind = "Arquivo de áudio" if ext in AUDIO_EXTS else "Arquivo de vídeo"
                self._show_binary_preview(
                    f"{kind} (instale python-vlc para reprodução)"
                )
            return

        self._show_binary_preview("Arquivo binário")

    def _looks_text(self):
        try:
            data = self.path.read_bytes()[:4096]
            if b"\x00" in data:
                return False
            data.decode("utf-8")
            return True
        except Exception:
            try:
                data.decode(locale.getpreferredencoding(False) or "utf-8")
                return True
            except Exception:
                return False

    def _show_image(self):
        canvas = tk.Canvas(self.body, bg="#0b1220", highlightthickness=0)
        vbar = tk.Scrollbar(self.body, orient="vertical", command=canvas.yview)
        hbar = tk.Scrollbar(self.body, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        self.body.rowconfigure(0, weight=1)
        self.body.columnconfigure(0, weight=1)

        ext = self.path.suffix.lower()

        try:
            if ext in {".jpg", ".jpeg"}:
                if Image is None or ImageTk is None:
                    self._show_message(
                        "Para abrir JPG/JPEG internamente, a biblioteca Pillow precisa estar instalada.\n\n"
                        "Execute: pip install pillow"
                    )
                    return

                img = Image.open(self.path)
                img.thumbnail((1800, 1200))
                self._photo = ImageTk.PhotoImage(img)
            else:
                self._photo = tk.PhotoImage(file=str(self.path))

            canvas.create_image(0, 0, anchor="nw", image=self._photo)
            canvas.config(scrollregion=canvas.bbox("all"))

        except Exception as exc:
            self._show_message(
                "Não foi possível abrir a imagem internamente.\n\n"
                f"Detalhe: {exc}"
            )

    def _show_text(self):
        box = scrolledtext.ScrolledText(
            self.body,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            wrap="word",
            font=("Consolas", 11),
        )
        box.pack(fill="both", expand=True)

        try:
            try:
                text = self.path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = self.path.read_text(encoding=locale.getpreferredencoding(False), errors="replace")
        except Exception as exc:
            self._show_message(f"Não foi possível ler o arquivo como texto.\n\n{exc}")
            return

        box.insert("1.0", text)
        box.configure(state="disabled")

    def _show_binary_preview(self, kind_label):
        top = tk.Frame(self.body, bg="#111827")
        top.pack(fill="x", pady=(0, 8))

        tk.Label(
            top,
            text=f"{kind_label} aberto internamente.",
            bg="#111827",
            fg="#e5e7eb",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            top,
            text=(
                "Este visualizador não usa aplicativos externos. "
                "Abaixo está uma prévia simples do conteúdo bruto."
            ),
            bg="#111827",
            fg="#9ca3af",
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        box = scrolledtext.ScrolledText(
            self.body,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            wrap="none",
            font=("Consolas", 10),
        )
        box.pack(fill="both", expand=True)

        try:
            data = self.path.read_bytes()[:8192]
            preview = self._hexdump(data)
            box.insert("1.0", preview)
        except Exception as exc:
            box.insert("1.0", f"Não foi possível ler o arquivo.\n\n{exc}")

        box.configure(state="disabled")

    def _hexdump(self, data: bytes, width: int = 16):
        lines = []
        for offset in range(0, len(data), width):
            chunk = data[offset:offset + width]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{offset:08x}  {hex_part:<{width * 3}}  |{ascii_part}|")
        if not lines:
            lines.append("(arquivo vazio)")
        return "\n".join(lines)

    def _show_message(self, text):
        label = tk.Label(
            self.body,
            text=text,
            bg="#111827",
            fg="#fca5a5",
            justify="left",
            anchor="nw",
            wraplength=820,
            font=("Segoe UI", 10),
        )
        label.pack(fill="both", expand=True, anchor="nw")

    # ==================================================================
    #  NOVO: reprodução de áudio/vídeo com VLC + barra de progresso
    # ==================================================================
    def _show_media(self):
        """Configura player VLC para áudio ou vídeo com controle de progresso."""
        for widget in self.body.winfo_children():
            widget.destroy()

        is_audio = self.path.suffix.lower() in AUDIO_EXTS

        # Frame do player (preto, onde o vídeo será renderizado)
        if is_audio:
            self.media_frame = tk.Frame(self.body, bg="#0b1220", height=100)
            self.media_frame.pack(fill="x", expand=False)
            self.media_frame.pack_propagate(False)
            tk.Label(
                self.media_frame,
                text=f"🔊 {self.path.name}",
                bg="#0b1220",
                fg="#e5e7eb",
                font=("Segoe UI", 12),
            ).pack(expand=True)
        else:
            self.media_frame = tk.Frame(self.body, bg="black")
            self.media_frame.pack(fill="both", expand=True)

        # --- Barra de progresso ---
        progress_frame = tk.Frame(self.body, bg="#1f2937")
        progress_frame.pack(fill="x", pady=(6, 0))

        self.time_current = tk.Label(
            progress_frame, text="00:00", bg="#1f2937", fg="#e5e7eb", width=6, anchor="e"
        )
        self.time_current.pack(side="left", padx=(4, 0))

        self.scale_var = tk.DoubleVar(value=0)
        self.progress_scale = tk.Scale(
            progress_frame,
            variable=self.scale_var,
            from_=0, to=1000,               # máximo temporário
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=self._on_scale_move,
            bg="#1f2937",
            fg="#e5e7eb",
            troughcolor="#374151",
            highlightthickness=0,
        )
        self.progress_scale.pack(side="left", fill="x", expand=True, padx=6)
        self.progress_scale.bind("<ButtonPress-1>", self._on_scale_press)
        self.progress_scale.bind("<ButtonRelease-1>", self._on_scale_release)

        self.time_total = tk.Label(
            progress_frame, text="--:--", bg="#1f2937", fg="#e5e7eb", width=6, anchor="w"
        )
        self.time_total.pack(side="left", padx=(0, 4))

        # --- Controles (play/pause, stop, volume) ---
        ctrl = tk.Frame(self.body, bg="#1f2937")
        ctrl.pack(fill="x", pady=(10, 0))

        self.play_pause_btn = tk.Button(
            ctrl, text="▶️ Play", command=self._toggle_play
        )
        self.play_pause_btn.pack(side="left", padx=4)

        stop_btn = tk.Button(ctrl, text="⏹️ Stop", command=self._stop_media)
        stop_btn.pack(side="left", padx=4)

        tk.Label(ctrl, text=" Vol:", bg="#1f2937", fg="#e5e7eb").pack(side="left", padx=(10, 0))
        self.vol_scale = tk.Scale(
            ctrl,
            from_=0, to=100,
            orient="horizontal",
            command=self._set_volume,
            bg="#1f2937",
            fg="#e5e7eb",
            highlightthickness=0,
        )
        self.vol_scale.set(70)
        self.vol_scale.pack(side="left", padx=4)

        # Inicializa VLC
        instance = vlc.Instance()
        self.player = instance.media_player_new()
        media = instance.media_new(str(self.path))
        self.player.set_media(media)

        # Associa o player ao frame correspondente
        win_id = self.media_frame.winfo_id()
        if sys.platform == "win32":
            self.player.set_hwnd(win_id)
        elif sys.platform.startswith("linux"):
            self.player.set_xwindow(win_id)
        else:   # macOS
            self.player.set_nsobject(win_id)

        self.player.play()
        self._is_playing = True
        self._update_play_button()

        # Inicia a atualização periódica da barra de progresso
        self._update_progress()

    # ------------------- Métodos auxiliares da barra de progresso -------------------
    def _format_time(self, ms):
        """Converte milissegundos para string MM:SS."""
        if ms < 0:
            ms = 0
        total_sec = int(ms // 1000)
        mins = total_sec // 60
        secs = total_sec % 60
        return f"{mins:02d}:{secs:02d}"

    def _on_scale_press(self, event):
        """Marca que o usuário está arrastando a barra."""
        self.dragging = True

    def _on_scale_release(self, event):
        """Ao soltar a barra, busca a posição selecionada."""
        self.dragging = False
        if self.player is not None:
            seek_time = int(self.scale_var.get())
            self.player.set_time(seek_time)

    def _on_scale_move(self, value):
        """Atualiza o rótulo de tempo enquanto o usuário arrasta."""
        if self.dragging:
            try:
                val_ms = int(float(value))
                self.time_current.config(text=self._format_time(val_ms))
            except ValueError:
                pass

    def _update_progress(self):
        """Loop que mantém a barra de progresso sincronizada com o player."""
        if self.player is None:
            return

        # Obtém a duração total quando disponível
        if not self.length_known:
            length = self.player.get_length()
            if length > 0:
                self.player_length = length
                self.progress_scale.config(to=length)
                self.time_total.config(text=self._format_time(length))
                self.length_known = True

        # Atualiza a posição atual, exceto se o usuário estiver arrastando
        if not self.dragging:
            current = self.player.get_time()
            if current >= 0:
                self.scale_var.set(current)
                self.time_current.config(text=self._format_time(current))

        # Agenda a próxima atualização (se a janela ainda existir)
        if self.winfo_exists():
            self._update_progress_id = self.after(200, self._update_progress)

    # ------------------- Controles de reprodução -------------------
    def _toggle_play(self):
        if self.player is None:
            return
        if self.player.is_playing():
            self.player.pause()
            self._is_playing = False
        else:
            self.player.play()
            self._is_playing = True
        self._update_play_button()

    def _stop_media(self):
        if self.player is not None:
            self.player.stop()
            self._is_playing = False
            self._update_play_button()

    def _set_volume(self, val):
        if self.player is not None:
            self.player.audio_set_volume(int(val))

    def _update_play_button(self):
        if self.player is None:
            return
        self.play_pause_btn.config(
            text="⏸️ Pause" if self._is_playing else "▶️ Play"
        )

    def _on_close(self):
        """Para a reprodução, cancela o loop de atualização e libera recursos."""
        if self._update_progress_id is not None:
            self.after_cancel(self._update_progress_id)
        if self.player is not None:
            self.player.stop()
            self.player.release()
            self.player = None
        self.destroy()


class TerminalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.shell_buffer = ""
        self.last_blank = False
        self.title(APP_NAME)
        self.geometry("1024x720")
        self.minsize(800, 520)
        self.configure(bg="#0f172a")

        self.cwd = Path.cwd()
        self.aliases = self._load_aliases()
        self.history = []
        self.history_index = 0
        self.bridge = ShellBridge()
        self.bridge.start()

        self._build_ui()
        self._install_tags()
        self._banner()
        self.after(30, self._poll_shell)
        self.after(50, self._prompt)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self):
        self.output = scrolledtext.ScrolledText(
            self,
            bg="#020617",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            padx=10,
            pady=10,
            wrap="word",
            font=("Consolas", 11),
        )
        self.output.pack(fill="both", expand=True, padx=12, pady=(12, 8))
        self.output.configure(state="disabled")

        bottom = tk.Frame(self, bg="#0f172a")
        bottom.pack(fill="x", padx=12, pady=(0, 12))

        self.prompt_label = tk.Label(bottom, text="", bg="#0f172a", fg="#38bdf8", font=("Consolas", 11, "bold"))
        self.prompt_label.pack(side="left")

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            bottom,
            textvariable=self.entry_var,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            font=("Consolas", 11),
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=8)
        self.entry.bind("<Return>", self._enter)
        self.entry.bind("<Up>", self._history_up)
        self.entry.bind("<Down>", self._history_down)

        self.bind("<Control-l>", lambda e: self._clear())
        self.bind("<Control-k>", lambda e: self.entry_var.set(""))

    def _install_tags(self):
        self.output.tag_configure("prompt", foreground="#38bdf8")
        self.output.tag_configure("cmd", foreground="#facc15")
        self.output.tag_configure("ok", foreground="#86efac")
        self.output.tag_configure("err", foreground="#fca5a5")
        self.output.tag_configure("info", foreground="#93c5fd")
        self.output.tag_configure("dim", foreground="#9ca3af")
        self.output.tag_configure("path", foreground="#c084fc")
        self.output.tag_configure("dir", foreground="#67e8f9")
        self.output.tag_configure("file", foreground="#e5e7eb")
        self.output.tag_configure("banner", foreground="#22c55e")
        for name, cfg in STYLE_TAGS.items():
            self.output.tag_configure(name, **cfg)

    def _load_aliases(self):
        if ALIASES_FILE.exists():
            try:
                return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_aliases(self):
        ALIASES_FILE.write_text(json.dumps(self.aliases, indent=2, ensure_ascii=False), encoding="utf-8")

    def _banner(self):
        self._write_line(f"{APP_NAME} — terminal em Python puro conectado ao shell", "banner")
        self._write_line(f"Shell: {self.bridge.shell_name}", "dim")
        self._write_line("Comandos internos: help, clear, cd, pwd, ls, alias, view, exit", "dim")
        self._write_line("", None)

    def _prompt(self):
        self.prompt_label.config(text=f"{self.cwd}>  ")
        self.entry.focus_set()

    def _clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self._banner()
        self._prompt()

    def _write(self, text, tag=None):
        self.output.configure(state="normal")
        if tag:
            self.output.insert("end", text, tag)
        else:
            self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _write_line(self, text="", tag=None):
        self._write(text + "\n", tag)

    def _write_ansi(self, text):
        pos = 0
        active_tags = []

        for match in ANSI_RE.finditer(text):
            chunk = text[pos:match.start()]
            if chunk:
                self._write(chunk, tuple(active_tags) if active_tags else None)
            pos = match.end()
            codes = match.group(1) or "0"

            for code_s in codes.split(";"):
                try:
                    code = int(code_s)
                except ValueError:
                    continue

                if code == 0:
                    active_tags = []
                elif code == 1:
                    if "bold" not in active_tags:
                        active_tags.append("bold")
                elif code == 22:
                    active_tags = [t for t in active_tags if t != "bold"]
                elif code in FG_COLORS:
                    active_tags = [t for t in active_tags if t not in FG_COLORS.values()]
                    active_tags.append(FG_COLORS[code])
                elif code in BG_COLORS:
                    active_tags = [t for t in active_tags if t not in BG_COLORS.values()]
                    active_tags.append(BG_COLORS[code])

        tail = text[pos:]
        if tail:
            self._write(tail, tuple(active_tags) if active_tags else None)

    def _poll_shell(self):
        drained = False
        while True:
            try:
                chunk = self.bridge.queue.get_nowait()
            except queue.Empty:
                break
            drained = True
            self.shell_buffer += chunk
            self.shell_buffer = self.shell_buffer.replace("\r\n", "\n").replace("\r", "\n")

            while "\n" in self.shell_buffer:
                line, self.shell_buffer = self.shell_buffer.split("\n", 1)
                self._handle_shell_line(line)

        if drained:
            self.output.see("end")

        if self.bridge.alive:
            self.after(30, self._poll_shell)
        else:
            self._write_line("\n[Shell encerrado]", "err")

    def _history_up(self, event=None):
        if not self.history:
            return "break"
        self.history_index = max(0, self.history_index - 1)
        self.entry_var.set(self.history[self.history_index])
        self.entry.icursor("end")
        return "break"

    def _history_down(self, event=None):
        if not self.history:
            return "break"
        self.history_index = min(len(self.history), self.history_index + 1)
        if self.history_index >= len(self.history):
            self.entry_var.set("")
        else:
            self.entry_var.set(self.history[self.history_index])
        self.entry.icursor("end")
        return "break"

    def _clean_path_arg(self, raw):
        raw = raw.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
            raw = raw[1:-1]
        return raw

    def _resolve(self, raw):
        raw = self._clean_path_arg(raw)
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (self.cwd / p).resolve()
        return p

    def _apply_alias(self, cmd):
        try:
            import shlex
            parts = shlex.split(cmd, posix=(os.name != "nt"))
        except Exception:
            return cmd

        if not parts:
            return cmd

        name = parts[0]
        if name not in self.aliases:
            return cmd

        template = self.aliases[name]
        rest = " ".join(parts[1:])
        expanded = template.replace("%*", rest)
        if "%*" not in template and rest:
            expanded = f"{template} {rest}"
        return expanded

    def _enter(self, event=None):
        raw = self.entry_var.get().strip()
        self.entry_var.set("")
        if not raw:
            self._prompt()
            return "break"

        self.history.append(raw)
        self.history_index = len(self.history)

        expanded = self._apply_alias(raw)

        self._write_line(f"-$ {raw}", "cmd")

        if self._internal(expanded):
            self._prompt()
            return "break"

        self._update_local_cwd_if_needed(expanded)
        self.bridge.send(expanded)
        self._prompt()
        return "break"

    def _handle_shell_line(self, line):
        if self.bridge.prompt_token in line:
            line = line.replace(self.bridge.prompt_token, "")

        stripped = line.strip()

        if os.name == "nt":
            low = stripped.lower()
            if low.startswith("microsoft windows ["):
                return
            if low.startswith("(c) microsoft corporation"):
                return
            if stripped == ">":
                return

        if stripped == "":
            if self.last_blank:
                return
            self.last_blank = True
            self._write_line("")
            return

        self.last_blank = False
        self._write_ansi(line + "\n")

    def _update_local_cwd_if_needed(self, command):
        try:
            import shlex
            parts = shlex.split(command, posix=(os.name != "nt"))
        except Exception:
            return

        if not parts:
            return

        cmd = parts[0].lower()

        if cmd == "cd":
            target = None

            if len(parts) == 1:
                target = Path.home()
            else:
                args = parts[1:]
                if os.name == "nt" and args and args[0].lower() == "/d" and len(args) > 1:
                    target = self._resolve(args[1])
                else:
                    target = self._resolve(args[0])

            if target and target.exists() and target.is_dir():
                self.cwd = target.resolve()

        elif cmd == "pushd" and len(parts) >= 2:
            target = self._resolve(parts[1])
            if target.exists() and target.is_dir():
                self.cwd = target.resolve()

        elif cmd == "popd":
            pass

    def _internal(self, command):
        try:
            import shlex
            parts = shlex.split(command, posix=(os.name != "nt"))
        except Exception as exc:
            self._write_line(f"Erro de sintaxe: {exc}", "err")
            return True

        if not parts:
            return True

        cmd, *args = parts
        c = cmd.lower()

        if c in {"help", "?"}:
            self._write_line("Comandos internos:", "info")
            for line in [
                "  help / ?          ajuda",
                "  clear / cls       limpa a tela",
                "  cd <pasta>        muda diretório local do emulador",
                "  pwd               mostra diretório local do emulador",
                "  ls [pasta]        lista arquivos localmente",
                "  alias list        lista aliases",
                "  alias add N C     cria comando personalizado",
                "  alias del N       remove alias",
                "  view <arquivo>    abre arquivo/mídia internamente",
                "  exit              fecha o emulador",
            ]:
                self._write_line(line, "dim")
            return True

        if c in {"clear", "cls"}:
            self._clear()
            return True

        if c == "pwd":
            self._write_line(str(self.cwd), "path")
            return True

        if c == "cd":
            dest = Path.home() if not args else self._resolve(args[0])
            if dest.exists() and dest.is_dir():
                self.cwd = dest.resolve()
                self._write_line("Diretório alterado.", "ok")
            else:
                self._write_line("Diretório inválido.", "err")
            return True

        if c == "ls":
            target = self.cwd if not args else self._resolve(args[0])
            if not target.exists():
                self._write_line("Caminho não encontrado.", "err")
                return True
            if target.is_file():
                self._write_line(target.name, "file")
                return True

            for p in sorted(target.iterdir(), key=lambda x: x.name.lower()):
                if p.is_dir():
                    continue
                size = ""
                try:
                    size = f"  {p.stat().st_size} bytes"
                except Exception:
                    pass
                self._write_line(f"       {p.name}{size}", "file")
            return True

        if c == "alias":
            if not args or args[0].lower() == "list":
                if not self.aliases:
                    self._write_line("Nenhum alias salvo.", "dim")
                else:
                    for k, v in sorted(self.aliases.items()):
                        self._write_line(f"{k} -> {v}", "warn")
                return True

            sub = args[0].lower()
            if sub == "add":
                if len(args) < 3:
                    self._write_line("Uso: alias add NOME COMANDO", "warn")
                    return True
                name = args[1]
                value = " ".join(args[2:])
                self.aliases[name] = value
                self._save_aliases()
                self._write_line(f"Alias salvo: {name} -> {value}", "ok")
                return True

            if sub in {"del", "rm", "remove"}:
                if len(args) < 2:
                    self._write_line("Uso: alias del NOME", "warn")
                    return True
                name = args[1]
                if name in self.aliases:
                    del self.aliases[name]
                    self._save_aliases()
                    self._write_line(f"Alias removido: {name}", "ok")
                else:
                    self._write_line("Alias não encontrado.", "err")
                return True

            self._write_line("Use: alias list | alias add | alias del", "warn")
            return True

        if c == "view":
            if not args:
                self._write_line("Uso: view <arquivo>", "warn")
                return True

            path = self._resolve(args[0])
            if not path.exists():
                self._write_line("Arquivo não encontrado.", "err")
                return True

            MediaViewer(self, path)
            self._write_line(f"Visualização aberta: {path.name}", "info")
            return True

        if c == "exit":
            self._close()
            return True

        return False

    def _close(self):
        try:
            self.bridge.terminate()
        finally:
            self.destroy()


if __name__ == "__main__":
    app = TerminalApp()
    app.mainloop()