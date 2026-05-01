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
from tkinter import scrolledtext, messagebox, filedialog, ttk
import shlex

try:
    from PIL import Image, ImageTk, ImageOps
except ImportError:
    Image = None
    ImageTk = None
    ImageOps = None

try:
    import vlc
except ImportError:
    vlc = None

HISTORY_FILE = Path.home() / ".shell_terminal_history.json"

INTERNAL_COMMANDS = [
    "help", "?", "clear", "cls", "cd", "pwd", "ls",
    "alias", "view", "exit", "pushd", "popd"
]

IMAGE_EXTS = {".png", ".gif", ".ppm", ".pgm", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
TEXT_EXTS = {
    ".txt", ".log", ".md", ".rst", ".py", ".json", ".xml", ".html", ".htm",
    ".css", ".js", ".csv", ".ini", ".cfg", ".conf", ".yml", ".yaml", ".toml",
    ".bat", ".cmd", ".ps1", ".sh", ".c", ".cpp", ".h", ".java", ".go", ".rs",
}
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a", ".opus", ".wma", ".aiff", ".aif"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".m4v", ".mpeg", ".mpg", ".3gp", ".3g2", ".ts", ".m2ts", ".mts", ".f4v"}

APP_NAME = "ShellTerminal"
ALIASES_FILE = Path.home() / ".shell_terminal_aliases.json"

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

THEME_FILE = Path.home() / ".shell_terminal_theme.json"

def load_theme():
    """Carrega o tema do arquivo JSON, criando o padrão se necessário."""
    default = {
        "tag_styles": {
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
        },
        "output_tags": {
            "prompt": {"foreground": "#38bdf8"},
            "cmd": {"foreground": "#facc15"},
            "ok": {"foreground": "#86efac"},
            "err": {"foreground": "#fca5a5"},
            "warn": {"foreground": "#fbbf24"},
            "info": {"foreground": "#93c5fd"},
            "dim": {"foreground": "#9ca3af"},
            "path": {"foreground": "#c084fc"},
            "dir": {"foreground": "#67e8f9"},
            "file": {"foreground": "#e5e7eb"},
            "banner": {"foreground": "#22c55e"},
        },
        "highlight_tags": {
            "hl_ip": {"foreground": "#60a5fa"},
            "hl_number": {"foreground": "#fb923c"},
            "hl_path": {"foreground": "#a78bfa"},
            "hl_url": {"foreground": "#6ee7b7", "underline": True},
            "hl_email": {"foreground": "#c4b5fd"},
            "hl_date": {"foreground": "#fbbf24"},
            "hl_time": {"foreground": "#38bdf8"},
            "hl_mac": {"foreground": "#2dd4bf"},
            "hl_keyword": {"foreground": "#f472b6"},
            "hl_success": {"foreground": "#34d399"},
            "hl_error": {"foreground": "#f87171"},
            "hl_warning": {"foreground": "#fbbf24"},
            "hl_info": {"foreground": "#60a5fa"},
            "hl_permissions": {"foreground": "#fbbf24"},
            "hl_process": {"foreground": "#a78bfa"},
            "hl_file_size": {"foreground": "#fb923c"},
            "hl_log_level": {"foreground": "#f472b6"},
            "hl_interface": {"foreground": "#38bdf8"},
            "hl_subnet": {"foreground": "#2dd4bf"},
            "hl_gateway": {"foreground": "#34d399"},
            "hl_dns": {"foreground": "#f472b6"},
            "hl_status_active": {"foreground": "#34d399"},
            "hl_status_inactive": {"foreground": "#9ca3af"},
            "hl_status_dead": {"foreground": "#f87171"},
        },
        "highlight_rules": [
            # --- Redes (Windows/Linux) ---
            {"pattern": "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b", "tag": "hl_ip"},
            {"pattern": "\\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\\b", "tag": "hl_mac"},
            {"pattern": "\\b(?:[0-9a-fA-F]{4}\\.){2}[0-9a-fA-F]{4}\\b", "tag": "hl_mac"},
            {"pattern": "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}/\\d{1,2}\\b", "tag": "hl_subnet"},
            {"pattern": "(?i)\\b(default gateway|gateway|router)\\b[:\\s]*[\\d\\.]+", "tag": "hl_gateway"},
            {"pattern": "(?i)\\b(dns server|nameserver)\\b[:\\s]*[\\d\\.]+", "tag": "hl_dns"},
            {"pattern": "(?i)\\b(ethernet adapter|wireless adapter|network interface)\\b", "tag": "hl_interface"},
            {"pattern": "(?i)\\b(interface|eth[0-9]+|wlan[0-9]+|lo)\\b", "tag": "hl_interface"},
            {"pattern": "(?i)\\b(up|down|unknown)\\b", "tag": "hl_status_active"},
            {"pattern": "(?i)\\bconnected\\b", "tag": "hl_success"},

            # --- Datas e horas ---
            {"pattern": "\\b\\d{4}-\\d{2}-\\d{2}\\b", "tag": "hl_date"},
            {"pattern": "\\b\\d{2}/\\d{2}/\\d{4}\\b", "tag": "hl_date"},
            {"pattern": "\\b\\d{2}:\\d{2}:\\d{2}\\b", "tag": "hl_time"},
            {"pattern": "\\b\\d{2}:\\d{2}\\b", "tag": "hl_time"},
            {"pattern": "\\b(AM|PM)\\b", "tag": "hl_time"},

            # --- URLs e e-mails ---
            {"pattern": "https?://[\\w./?=&%#~-]+", "tag": "hl_url"},
            {"pattern": "ftp://[\\w./?=&%#~-]+", "tag": "hl_url"},
            {"pattern": "\\b[\\w.+-]+@[\\w-]+\\.[\\w.]+\\b", "tag": "hl_email"},

            # --- Caminhos de arquivo (Windows e Unix) ---
            {"pattern": "[a-zA-Z]:[\\\\/][^\\s]*", "tag": "hl_path"},
            {"pattern": "(?:~|/)[^\\s]*", "tag": "hl_path"},

            # --- Permissões Unix (ex: -rw-r--r--) ---
            {"pattern": "\\b[-dclps](?:[-r][-w][-xsStT]){3}\\b", "tag": "hl_permissions"},

            # --- Tamanhos de arquivo ---
            {"pattern": "\\b\\d+(\\.\\d+)?\\s*[KMGTP]B?\\b", "tag": "hl_file_size"},

            # --- Status de serviços (systemd) ---
            {"pattern": "(?i)\\bactive\\b", "tag": "hl_status_active"},
            {"pattern": "(?i)\\binactive\\b", "tag": "hl_status_inactive"},
            {"pattern": "(?i)\\bdead\\b", "tag": "hl_status_dead"},
            {"pattern": "(?i)\\brunning\\b", "tag": "hl_status_active"},
            {"pattern": "(?i)\\bstopped\\b", "tag": "hl_status_inactive"},

            # --- Níveis de log genéricos ---
            {"pattern": "(?i)\\b(error|fail|critical|alert)\\b", "tag": "hl_error"},
            {"pattern": "(?i)\\b(warning|warn)\\b", "tag": "hl_warning"},
            {"pattern": "(?i)\\b(success|ok|done|completed)\\b", "tag": "hl_success"},
            {"pattern": "(?i)\\b(info|information|notice|debug|trace)\\b", "tag": "hl_info"},
            {"pattern": "(?i)\\b(denied|forbidden|refused|timeout|unreachable)\\b", "tag": "hl_error"},

            # --- Processos entre colchetes [ ] ---
            {"pattern": "\\[[\\w.]+\\]", "tag": "hl_process"},

            # --- Palavras-chave de comandos comuns ---
            {"pattern": "(?i)\\blisten(ing)?\\b", "tag": "hl_info"},
            {"pattern": "(?i)\\bestablished\\b", "tag": "hl_success"},
            {"pattern": "(?i)\\btime out\\b", "tag": "hl_error"},
            {"pattern": "(?i)\\bpacket\\b", "tag": "hl_info"},

            # --- Números isolados (fraca prioridade, colocada por último) ---
            {"pattern": "\\b\\d+\\b", "tag": "hl_number"},
        ],
    }

    try:
        if THEME_FILE.exists():
            with open(THEME_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = default.copy()
            if "tag_styles" in data:
                merged["tag_styles"].update(data["tag_styles"])
            if "output_tags" in data:
                merged["output_tags"].update(data["output_tags"])
            if "highlight_tags" in data:
                merged["highlight_tags"].update(data["highlight_tags"])
            if "highlight_rules" in data:
                merged["highlight_rules"] = data["highlight_rules"]  # substitui lista inteira
            return merged
        else:
            _save_theme(default)
            return default
    except Exception:
        return default

def _save_theme(theme):
    """Salva o tema no arquivo JSON."""
    try:
        with open(THEME_FILE, "w", encoding="utf-8") as f:
            json.dump(theme, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

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
        self.player = None
        self._is_playing = False
        self.dragging = False
        self.length_known = False
        self.player_length = 0
        self._update_progress_id = None
        self._vlc_instance = None
        self._is_media = False
        self._media_kind = None

        self.title(f"View - {path.name}")
        self.geometry("920x680")
        self.minsize(640, 420)
        self.configure(bg="#111827")
        self.transient(master)
        self.grab_set()
        self.app = master.winfo_toplevel()
        self.theme = getattr(self.app, 'theme', {})
        
        self._max_time_seen = 0
        self._duration_finalized = False
        self._event_manager = None
        
        self._original_img = None 
        self._img_tk = None 
        self._zoom_factor = 1.0  
        self._canvas_img_id = None   
        self._pan_start = None  

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
            size = self.path.stat().st_size
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
            self._media_kind = "audio" if ext in AUDIO_EXTS else "video"
            if vlc is not None:
                self._show_media()
            else:
                self._show_binary_preview(
                    f"Arquivo de {self._media_kind} (instale python-vlc + VLC para reproduzir)"
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
        # Se o Pillow não estiver disponível, mantém o fallback original
        if Image is None or ImageTk is None:
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
                if Image is not None and ImageTk is not None:
                    img = Image.open(self.path)
                    if ImageOps is not None:
                        img = ImageOps.exif_transpose(img)
                    img.thumbnail((1800, 1200))
                    self._photo = ImageTk.PhotoImage(img)
                elif ext in {".png", ".gif", ".ppm", ".pgm"}:
                    self._photo = tk.PhotoImage(file=str(self.path))
                else:
                    self._show_message(
                        "Esse formato de imagem precisa do Pillow para abrir internamente.\n\n"
                        "Instale com: pip install pillow"
                    )
                    return

                canvas.create_image(0, 0, anchor="nw", image=self._photo)
                canvas.config(scrollregion=canvas.bbox("all"))

            except Exception as exc:
                self._show_message(
                    "Não foi possível abrir a imagem internamente.\n\n"
                    f"Detalhe: {exc}"
                )
            self._show_message("Pillow é necessário para visualização avançada de imagens.")
            return

        # Frame superior (controles)
        ctrl_frame = tk.Frame(self.body, bg="#1f2937")
        ctrl_frame.pack(fill="x", pady=(0, 4))

        tk.Label(ctrl_frame, text="Zoom:", bg="#1f2937", fg="#e5e7eb",
                font=("Segoe UI", 9)).pack(side="left", padx=(6, 2))

        self.zoom_var = tk.IntVar(value=100)
        self.zoom_slider = tk.Scale(
            ctrl_frame, from_=10, to=500, orient=tk.HORIZONTAL,
            variable=self.zoom_var, command=self._on_zoom_slider,
            bg="#1f2937", fg="#e5e7eb", troughcolor="#374151",
            highlightthickness=0, length=200
        )
        self.zoom_slider.pack(side="left", padx=2)

        self.zoom_label = tk.Label(ctrl_frame, text="100%", bg="#1f2937", fg="#e5e7eb",
                                font=("Segoe UI", 9), width=5, anchor="w")
        self.zoom_label.pack(side="left", padx=2)

        fit_btn = tk.Button(ctrl_frame, text="↔️ Ajustar", command=self._fit_image,
                            bg="#374151", fg="#e5e7eb", relief="flat",
                            font=("Segoe UI", 9))
        fit_btn.pack(side="left", padx=8)

        reset_btn = tk.Button(ctrl_frame, text="100%", command=lambda: self._set_zoom(100),
                            bg="#374151", fg="#e5e7eb", relief="flat",
                            font=("Segoe UI", 9))
        reset_btn.pack(side="left", padx=2)

        # Canvas principal com scrollbars
        canvas_frame = tk.Frame(self.body, bg="#0b1220")
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="#0b1220", highlightthickness=0,
                                cursor="hand2")
        vbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        hbar = tk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        # Abrir a imagem original
        try:
            img = Image.open(self.path)
            if ImageOps is not None:
                img = ImageOps.exif_transpose(img)
            self._original_img = img.copy()
            self._zoom_factor = 1.0
            self._canvas_img_id = None
        except Exception as exc:
            self._show_message(f"Não foi possível abrir a imagem.\n\n{exc}")
            return

        # Vincular eventos de mouse
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Zoom com a roda do mouse
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)        # Windows
        self.canvas.bind("<Button-4>", self._on_mouse_wheel_linux)    # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mouse_wheel_linux)    # Linux scroll down

        # Ajustar tamanho da imagem ao canvas (fit inicial)
        self.after(100, self._fit_image)

    def _update_image_display(self):
        """Redesenha a imagem no canvas com o fator de zoom atual, mantendo a posição relativa."""
        if self._original_img is None:
            return

        # Redimensionar a original para o zoom atual
        w, h = self._original_img.size
        new_w = max(1, int(w * self._zoom_factor))
        new_h = max(1, int(h * self._zoom_factor))

        try:
            resized = self._original_img.resize((new_w, new_h), Image.LANCZOS)
        except AttributeError:
            resized = self._original_img.resize((new_w, new_h), Image.ANTIALIAS)

        self._img_tk = ImageTk.PhotoImage(resized)

        # Guardar a posição central antiga (para manter o ponto de vista)
        if self._canvas_img_id is not None:
            old_bbox = self.canvas.bbox(self._canvas_img_id)
            if old_bbox:
                old_center_x = (old_bbox[0] + old_bbox[2]) / 2
                old_center_y = (old_bbox[1] + old_bbox[3]) / 2
            else:
                old_center_x, old_center_y = 0, 0
            self.canvas.delete(self._canvas_img_id)
        else:
            old_center_x, old_center_y = 0, 0

        # Desenhar nova imagem centralizada
        self._canvas_img_id = self.canvas.create_image(
            new_w // 2, new_h // 2, anchor="center", image=self._img_tk
        )

        # Ajustar região de rolagem
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))

        # Reposicionar o viewport para tentar manter a área central anterior
        if old_center_x > 0 or old_center_y > 0:
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            new_xview = (old_center_x - canvas_w / 2) / new_w
            new_yview = (old_center_y - canvas_h / 2) / new_h
            new_xview = max(0, min(1, new_xview))
            new_yview = max(0, min(1, new_yview))
            self.canvas.xview_moveto(new_xview)
            self.canvas.yview_moveto(new_yview)
        else:
            # Centralizar a imagem na primeira exibição
            self.canvas.xview_moveto(0.0)
            self.canvas.yview_moveto(0.0)
            self.after(10, self._center_image_in_view)

    def _center_image_in_view(self):
        """Centraliza a imagem no canvas usando as scrollbars."""
        if self._canvas_img_id is None:
            return
        bbox = self.canvas.bbox(self._canvas_img_id)
        if not bbox:
            return
        img_w = bbox[2] - bbox[0]
        img_h = bbox[3] - bbox[1]
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if img_w > canvas_w:
            self.canvas.xview_moveto(0.0)  # Não centraliza horizontal, mas mostra o início
        else:
            offset_x = (img_w - canvas_w) / 2
            if offset_x > 0:
                self.canvas.xview_moveto(offset_x / img_w)

        if img_h > canvas_h:
            self.canvas.yview_moveto(0.0)
        else:
            offset_y = (img_h - canvas_h) / 2
            if offset_y > 0:
                self.canvas.yview_moveto(offset_y / img_h)

    def _set_zoom(self, percent):
        """Define o zoom percentual (10-500) e atualiza o slider e a imagem."""
        percent = max(10, min(500, percent))
        self._zoom_factor = percent / 100.0
        self.zoom_var.set(percent)
        self.zoom_label.config(text=f"{percent}%")
        self._update_image_display()

    def _on_zoom_slider(self, val):
        """Callback do slider de zoom."""
        self._set_zoom(int(float(val)))

    def _on_mouse_wheel(self, event):
        """Zoom com a roda do mouse (Windows)."""
        if event.delta > 0:
            self._set_zoom(self.zoom_var.get() + 10)
        else:
            self._set_zoom(self.zoom_var.get() - 10)

    def _on_mouse_wheel_linux(self, event):
        """Zoom com a roda do mouse (Linux)."""
        if event.num == 4:
            self._set_zoom(self.zoom_var.get() + 10)
        elif event.num == 5:
            self._set_zoom(self.zoom_var.get() - 10)

    def _fit_image(self):
        """Ajusta a imagem para que caiba inteira no canvas visível."""
        if self._original_img is None or not self.canvas.winfo_exists():
            return

        # Aguarda breve para obter as dimensões reais do canvas
        self.update_idletasks()
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 2 or canvas_h < 2:
            # Tenta novamente após 50ms
            self.after(50, self._fit_image)
            return

        img_w, img_h = self._original_img.size
        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        fit_scale = min(scale_w, scale_h) * 0.95   # margem de 5%

        fit_percent = max(10, min(500, int(fit_scale * 100)))
        self._set_zoom(fit_percent)

    # Métodos para pan (arrastar com o mouse)
    def _on_canvas_press(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self._pan_start = (event.x, event.y)

    def _on_canvas_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_canvas_release(self, event):
        self._pan_start = None

    def _show_text(self):
        # Barra de ferramentas
        toolbar = tk.Frame(self.body, bg="#1f2937")
        toolbar.pack(fill="x", pady=(0, 4))

        self.edit_status = tk.Label(toolbar, text=" 📝 Modo edição", bg="#1f2937", fg="#e5e7eb",
                                    font=("Segoe UI", 9))
        self.edit_status.pack(side="left", padx=8)

        save_btn = tk.Button(toolbar, text="💾 Salvar", command=self._save_text,
                            bg="#2563eb", fg="#ffffff", relief="flat",
                            font=("Segoe UI", 9), padx=6)
        save_btn.pack(side="right", padx=4)

        reload_btn = tk.Button(toolbar, text="🔄 Recarregar", command=self._reload_text,
                            bg="#374151", fg="#e5e7eb", relief="flat",
                            font=("Segoe UI", 9), padx=6)
        reload_btn.pack(side="right", padx=4)

        # Área de texto com scroll
        self.text_box = scrolledtext.ScrolledText(
            self.body,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            wrap="none",
            font=("Consolas", 11),
            undo=True,
            tabs=("4c",)  # tab = 4 espaços
        )
        self.text_box.pack(fill="both", expand=True)

        # Configurar tags de syntax highlighting
        self._setup_syntax_tags()

        # Carregar conteúdo
        self._load_text_content()

        # Vincular eventos
        self.text_box.bind("<Tab>", self._handle_tab)
        self.text_box.bind("<Shift-Tab>", self._handle_shift_tab)
        self.text_box.bind("<Control-s>", lambda e: self._save_text())
        self.text_box.bind("<KeyRelease>", self._on_text_change)
        self.text_box.bind("<<Modified>>", self._on_modified)

        # Foco
        self.text_box.focus_set()

        # Atualizar info
        self.info.config(text=self._info_text() + "   |   Modo Edição")

    def _setup_syntax_tags(self):
        """Configura tags de cor para sintaxe baseada na extensão."""
        ext = self.path.suffix.lower()

        # Cores de base do tema ou fallback
        colors = {
            "keyword": self.theme.get("highlight_tags", {}).get("hl_keyword", {"foreground": "#f472b6"}),
            "string": self.theme.get("highlight_tags", {}).get("hl_success", {"foreground": "#34d399"}),
            "comment": self.theme.get("highlight_tags", {}).get("hl_dim", {"foreground": "#9ca3af"}),
            "number": self.theme.get("highlight_tags", {}).get("hl_number", {"foreground": "#fb923c"}),
            "function": self.theme.get("highlight_tags", {}).get("hl_info", {"foreground": "#60a5fa"}),
            "builtin": self.theme.get("highlight_tags", {}).get("hl_warning", {"foreground": "#fbbf24"}),
            "decorator": self.theme.get("highlight_tags", {}).get("hl_magenta", {"foreground": "#c678dd"}),
            "class": self.theme.get("highlight_tags", {}).get("hl_path", {"foreground": "#a78bfa"}),
        }

        for tag, cfg in colors.items():
            self.text_box.tag_configure(tag, **cfg)

        # Estilos específicos por linguagem
        if ext in (".py", ".pyw"):
            self._highlighter = self._highlight_python
        elif ext in (".json",):
            self._highlighter = self._highlight_json
        elif ext in (".html", ".htm"):
            self._highlighter = self._highlight_html
        elif ext in (".css",):
            self._highlighter = self._highlight_css
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            self._highlighter = self._highlight_javascript
        elif ext in (".xml", ".yaml", ".yml"):
            self._highlighter = self._highlight_xml_yaml
        elif ext in (".c", ".cpp", ".h", ".java", ".go", ".rs"):
            self._highlighter = self._highlight_c_like
        else:
            self._highlighter = self._highlight_generic

    def _load_text_content(self):
        try:
            try:
                text = self.path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = self.path.read_text(encoding=locale.getpreferredencoding(False), errors="replace")
        except Exception as exc:
            self._show_message(f"Não foi possível ler o arquivo como texto.\n\n{exc}")
            return

        self._original_content = text
        self._current_content = text
        self.text_box.insert("1.0", text)
        self._apply_highlighting()
        self.text_box.edit_reset()  # limpa flag de modificação

    def _apply_highlighting(self, event=None):
        """Aplica coloração sintática a todo o texto."""
        if not hasattr(self, '_highlighter'):
            return

        content = self.text_box.get("1.0", "end-1c")

        # Limpar tags anteriores
        for tag in self.text_box.tag_names():
            if tag not in ("sel",):
                self.text_box.tag_remove(tag, "1.0", "end")

        # Aplicar regras
        self._highlighter(content)

    def _highlight_python(self, text):
        """Destaque para Python."""
        import keyword
        # Palavras-chave
        for kw in keyword.kwlist + ["self", "True", "False", "None"]:
            for match in re.finditer(r'\b' + re.escape(kw) + r'\b', text):
                self._add_tag("keyword", match)

        # Números
        for match in re.finditer(r'\b\d+\b', text):
            self._add_tag("number", match)

        # Strings (simples e duplas)
        for match in re.finditer(r'(\'\'\'.*?\'\'\'|\"\"\".*?\"\"\"|\'.*?\'|\".*?\")', text, re.DOTALL):
            self._add_tag("string", match)

        # Comentários
        for match in re.finditer(r'#.*$', text, re.MULTILINE):
            self._add_tag("comment", match)

        # Decorators
        for match in re.finditer(r'@\w+', text):
            self._add_tag("decorator", match)

        # Nomes de função/classes
        for match in re.finditer(r'(?<=def )\w+|(?<=class )\w+', text):
            self._add_tag("function", match)

    def _highlight_json(self, text):
        for match in re.finditer(r'\"[^\"]*\"', text):
            self._add_tag("string", match)
        for match in re.finditer(r'\b\d+\b', text):
            self._add_tag("number", match)
        for match in re.finditer(r'\b(true|false|null)\b', text):
            self._add_tag("keyword", match)

    def _highlight_html(self, text):
        for match in re.finditer(r'<!--.*?-->', text, re.DOTALL):
            self._add_tag("comment", match)
        for match in re.finditer(r'<[^>]+>', text):
            self._add_tag("keyword", match)
        for match in re.finditer(r'".*?"', text):
            self._add_tag("string", match)

    def _highlight_css(self, text):
        for match in re.finditer(r'/\*.*?\*/', text, re.DOTALL):
            self._add_tag("comment", match)
        for match in re.finditer(r'[.#]?[a-zA-Z-]+(?=\s*\{)', text):
            self._add_tag("function", match)
        for match in re.finditer(r':\s*[^;{]+', text):
            self._add_tag("string", match)

    def _highlight_javascript(self, text):
        keywords = ["function", "var", "let", "const", "return", "if", "else", "for", "while", "class", "import", "export", "default", "new", "this", "async", "await", "try", "catch", "throw", "true", "false", "null", "undefined"]
        for kw in keywords:
            for match in re.finditer(r'\b' + re.escape(kw) + r'\b', text):
                self._add_tag("keyword", match)
        for match in re.finditer(r'\b\d+\b', text):
            self._add_tag("number", match)
        for match in re.finditer(r'(\".*?\"|\'.*?\')', text):
            self._add_tag("string", match)
        for match in re.finditer(r'//.*$', text, re.MULTILINE):
            self._add_tag("comment", match)

    def _highlight_xml_yaml(self, text):
        # Simples: strings e números
        for match in re.finditer(r'\".*?\"|\'.*?\'', text):
            self._add_tag("string", match)
        for match in re.finditer(r'\b\d+\b', text):
            self._add_tag("number", match)

    def _highlight_c_like(self, text):
        keywords = ["if", "else", "for", "while", "return", "int", "float", "char", "void", "struct", "class", "public", "private", "protected", "static", "const", "namespace", "using", "new", "delete", "try", "catch", "throw"]
        for kw in keywords:
            for match in re.finditer(r'\b' + re.escape(kw) + r'\b', text):
                self._add_tag("keyword", match)
        for match in re.finditer(r'\b\d+\b', text):
            self._add_tag("number", match)
        for match in re.finditer(r'\"[^\"]*\"', text):
            self._add_tag("string", match)
        for match in re.finditer(r'//.*$', text, re.MULTILINE):
            self._add_tag("comment", match)

    def _highlight_generic(self, text):
        # Fallback: números e strings
        for match in re.finditer(r'\b\d+\b', text):
            self._add_tag("number", match)
        for match in re.finditer(r'\"[^\"]*\"|\'[^\']*\'', text):
            self._add_tag("string", match)

    def _add_tag(self, tag, match):
        start = f"1.0+{match.start()}c"
        end = f"1.0+{match.end()}c"
        self.text_box.tag_add(tag, start, end)
    
    def _handle_tab(self, event):
        """Insere 4 espaços ou indenta seleção."""
        try:
            if self.text_box.tag_ranges("sel"):
                # Indentar linhas selecionadas
                sel_start = self.text_box.index("sel.first")
                sel_end = self.text_box.index("sel.last")
                self.text_box.tag_remove("sel", "1.0", "end")
                line_start = int(sel_start.split('.')[0])
                line_end = int(sel_end.split('.')[0])
                for line in range(line_start, line_end + 1):
                    self.text_box.insert(f"{line}.0", "    ")
                self.text_box.tag_add("sel", sel_start, f"{line_end}.end")
                return "break"

            # Tab normal: 4 espaços
            self.text_box.insert("insert", "    ")
            return "break"
        except Exception:
            return "break"

    def _handle_shift_tab(self, event):
        """Remove indentação de linhas selecionadas."""
        try:
            if self.text_box.tag_ranges("sel"):
                sel_start = self.text_box.index("sel.first")
                sel_end = self.text_box.index("sel.last")
                line_start = int(sel_start.split('.')[0])
                line_end = int(sel_end.split('.')[0])
                for line in range(line_start, line_end + 1):
                    line_content = self.text_box.get(f"{line}.0", f"{line}.end")
                    if line_content.startswith("    "):
                        self.text_box.delete(f"{line}.0", f"{line}.0+4c")
                return "break"
            # Se nada selecionado, remove 4 espaços no cursor, se possível
            cursor = self.text_box.index("insert")
            line, col = cursor.split('.')
            line_start = f"{line}.0"
            if self.text_box.get(line_start, cursor).endswith("    "):
                self.text_box.delete(f"insert-4c", "insert")
            return "break"
        except Exception:
            return "break"
    
    def _save_text(self):
        new_content = self.text_box.get("1.0", "end-1c")
        try:
            self.path.write_text(new_content, encoding="utf-8")
            self._original_content = new_content
            self._current_content = new_content
            self.text_box.edit_reset()
            self.edit_status.config(text=" ✅ Salvo", fg="#34d399")
            self.after(2000, lambda: self.edit_status.config(text=" 📝 Modo edição", fg="#e5e7eb"))
        except Exception as e:
            self.edit_status.config(text=f" ❌ Erro ao salvar: {e}", fg="#f87171")

    def _reload_text(self):
        if self._text_modified():
            if not messagebox.askyesno("Recarregar", "Descartar alterações e recarregar?"):
                return
        self._load_text_content()

    def _text_modified(self):
        return self.text_box.edit_modified()

    def _on_modified(self, event=None):
        if self._text_modified():
            self.edit_status.config(text=" 🔴 Modificado", fg="#fbbf24")

    def _on_text_change(self, event=None):
        self._apply_highlighting()
        if self._text_modified():
            self.edit_status.config(text=" 🔴 Modificado", fg="#fbbf24")
    
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
            text="Este visualizador não usa aplicativos externos. Abaixo está uma prévia simples do conteúdo bruto.",
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

    def _show_media(self):
        for widget in self.body.winfo_children():
            widget.destroy()

        self._is_media = True
        is_audio = self._media_kind == "audio"

        if is_audio:
            self.media_frame = tk.Frame(self.body, bg="#0b1220", height=110)
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
            from_=0,
            to=1000,
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

        ctrl = tk.Frame(self.body, bg="#1f2937")
        ctrl.pack(fill="x", pady=(10, 0))

        self.play_pause_btn = tk.Button(ctrl, text="▶️ Play", command=self._toggle_play)
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

        self.status = tk.Label(
            ctrl,
            text="Carregando VLC...",
            bg="#1f2937",
            fg="#9ca3af",
            anchor="e",
        )
        self.status.pack(side="right", padx=8)

        self._vlc_instance = vlc.Instance()
        self.player = self._vlc_instance.media_player_new()
        media = self._vlc_instance.media_new(str(self.path))
        self.player.set_media(media)

        try:
            self._event_manager = self.player.event_manager()
            self._event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end)
            self._event_manager.event_attach(vlc.EventType.MediaPlayerLengthChanged, self._on_length_changed)
        except Exception:
            self._event_manager = None

        self.after(100, self._attach_vlc_player)
    
    def _probe_duration_ms(self):
        if self.player is None:
            return 0

        try:
            media = self.player.get_media()
            if media is not None:
                try:
                    media.parse()
                except Exception:
                    pass

                try:
                    duration = int(media.get_duration())
                    if duration > 0:
                        return duration
                except Exception:
                    pass
        except Exception:
            pass

        try:
            length = int(self.player.get_length())
            return length if length > 0 else 0
        except Exception:
            return 0
    
    def _attach_vlc_player(self):
        if self.player is None:
            return

        self.update_idletasks()
        try:
            win_id = int(self.media_frame.winfo_id())
            if sys.platform == "win32":
                self.player.set_hwnd(win_id)
            elif sys.platform.startswith("linux"):
                self.player.set_xwindow(win_id)
            else:
                self.player.set_nsobject(win_id)
        except Exception:
            pass

        self.player.play()
        self._is_playing = True
        self._update_play_button()
        self.status.config(text="VLC ativo")

        self._update_progress()

    def _on_media_end(self, event):
        try:
            self.after(0, self._finalize_duration_from_observed)
        except Exception:
            pass

    def _on_length_changed(self, event):
        try:
            new_length = event.u.new_length
        except AttributeError:
            return
        if new_length > 0:
            self.player_length = new_length
            self.progress_scale.config(to=new_length)
            self.time_total.config(text=self._format_time(new_length))
            self.length_known = True

    def _finalize_duration_from_observed(self):
        if self.player is None or self._duration_finalized:
            return

        observed = 0
        try:
            observed = int(self._max_time_seen)
        except Exception:
            observed = 0

        try:
            current = int(self.player.get_time())
            if current > observed:
                observed = current
        except Exception:
            pass

        if observed <= 0:
            return

        # Corrige apenas se a duração exibida estiver claramente maior do que a real
        if self.player_length <= 0 or observed < int(self.player_length * 0.9):
            self.player_length = observed
            self.progress_scale.config(to=observed)
            self.time_total.config(text=self._format_time(observed))
            if self.scale_var.get() > observed:
                self.scale_var.set(observed)

        self._duration_finalized = True
        self.length_known = True
    
    def _format_time(self, ms):
        if ms < 0:
            ms = 0
        total_sec = int(ms // 1000)
        mins = total_sec // 60
        secs = total_sec % 60
        return f"{mins:02d}:{secs:02d}"

    def _on_scale_press(self, event):
        self.dragging = True

    def _on_scale_release(self, event):
        self.dragging = False
        if self.player is not None:
            seek_time = int(self.scale_var.get())
            self.player.set_time(seek_time)

    def _on_scale_move(self, value):
        if self.dragging:
            try:
                val_ms = int(float(value))
                self.time_current.config(text=self._format_time(val_ms))
            except ValueError:
                pass

    def _update_progress(self):
        if self.player is None:
            return

        if not self.length_known:
            duration = self._probe_duration_ms()
            if duration > 0:
                self.player_length = duration
                self.progress_scale.config(to=duration)
                self.time_total.config(text=self._format_time(duration))
                self.length_known = True

        try:
            state = self.player.get_state()
        except Exception:
            state = None

        current = -1
        try:
            current = int(self.player.get_time())
        except Exception:
            current = -1

        if current >= 0:
            if current > self._max_time_seen:
                self._max_time_seen = current

            # Heurística: corrige duração se a estimativa pela posição for muito menor
            if self.player_length > 0 and current > 5000:   # só após 5 segundos de reprodução
                try:
                    position = self.player.get_position()
                except Exception:
                    position = 0.0
                if position > 0.12:                         # posição confiável (>12%)
                    estimated = current / position
                    if estimated < self.player_length * 0.8:   # diferença > 20%
                        self._apply_duration_correction(int(estimated))
            
            if not self.dragging:
                self.scale_var.set(current)
                self.time_current.config(text=self._format_time(current))

        # Corrige no fim natural da reprodução
        if state == getattr(vlc.State, "Ended", None):
            self._finalize_duration_from_observed()

        if self.winfo_exists():
            self._update_progress_id = self.after(200, self._update_progress)

    def _apply_duration_correction(self, corrected_ms):
        corrected_ms = int(corrected_ms)
        if corrected_ms <= 0:
            return

        self.player_length = corrected_ms
        self.progress_scale.config(to=corrected_ms)
        self.time_total.config(text=self._format_time(corrected_ms))
        if self.scale_var.get() > corrected_ms:
            self.scale_var.set(corrected_ms)

    def _toggle_play(self):
        if self.player is None:
            return
        if self.player.is_playing():
            self.player.pause()
            self._is_playing = False
            self.status.config(text="Pausado")
        else:
            self.player.play()
            self._is_playing = True
            self.status.config(text="Reproduzindo")
        self._update_play_button()

    def _stop_media(self):
        if self.player is not None:
            self.player.stop()
            self._is_playing = False
            self.status.config(text="Parado")
            self._update_play_button()

    def _set_volume(self, val):
        if self.player is not None:
            self.player.audio_set_volume(int(val))

    def _update_play_button(self):
        if self.player is None:
            return
        self.play_pause_btn.config(text="Pause" if self._is_playing else "Play")

    def _on_close(self):
        if hasattr(self, 'text_box') and self._text_modified():
            if not messagebox.askyesno("Fechar", "Há alterações não salvas. Descartar?"):
                return
        
        if self._update_progress_id is not None:
            try:
                self.after_cancel(self._update_progress_id)
            except Exception:
                pass

        if self.player is not None:
            try:
                self.player.stop()
                self.player.release()
            except Exception:
                pass
            self.player = None

        if self._vlc_instance is not None:
            try:
                self._vlc_instance.release()
            except Exception:
                pass
            self._vlc_instance = None

        self.destroy()

class TerminalSessionTab(tk.Frame):
    def __init__(self, master, app, tab_title="Terminal"):
        super().__init__(master, bg="#0f172a")
        self.app = app
        self.tab_title = tab_title

        self.shell_buffer = ""
        self.last_blank = False
        self.cwd = Path.cwd()
        self.history_index = len(self.app.history)

        self._ac_prefix = None
        self._ac_matches = []
        self._ac_index = -1
        self._path_command_cache = None

        self.bridge = ShellBridge()
        self.bridge.start()

        self._build_ui()
        self._install_tags()
        self._banner()

        self.after(30, self._poll_shell)
        self.after(50, self._prompt)

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

        # Duas colunas: a primeira terá 20% da largura, a segunda 80%
        bottom.grid_columnconfigure(0, weight=20, uniform='bottom_cols')
        bottom.grid_columnconfigure(1, weight=80, uniform='bottom_cols')

        # --- Coluna 0: "botão" de diretório (20%) ---
        self.cwd_click_after_id = None
        self.cwd_editing = False

        self.cwd_container = tk.Frame(
            bottom,
            bg="#111827",
            bd=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#374151",
        )
        self.cwd_container.grid(row=0, column=0, sticky='ew', padx=(0, 8))

        self.cwd_label = tk.Label(
            self.cwd_container,
            text=self._short_cwd(),
            bg="#111827",
            fg="#e5e7eb",
            font=("Consolas", 9, "bold"),
            padx=8,
            pady=2,
            cursor="hand2",
        )
        self.cwd_label.pack(fill="both", expand=True)

        self.cwd_entry_var = tk.StringVar()
        self.cwd_entry = tk.Entry(
            self.cwd_container,
            textvariable=self.cwd_entry_var,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            font=("Consolas", 9, "bold"),
        )

        for widget in (self.cwd_container, self.cwd_label):
            widget.bind("<Button-1>", self._on_cwd_single_click)
            widget.bind("<Double-Button-1>", self._on_cwd_double_click)

        # --- Coluna 1: sub-frame para prompt + entrada (80%) ---
        input_frame = tk.Frame(bottom, bg="#0f172a")
        input_frame.grid(row=0, column=1, sticky='ew')

        self.prompt_label = tk.Label(
            input_frame,
            text=">",
            bg="#0f172a",
            fg="#38bdf8",
            font=("Consolas", 11, "bold"),
        )
        self.prompt_label.pack(side="left")

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_frame,
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
        self.entry.bind("<Tab>", self._autocomplete)

        self.bind("<Control-l>", lambda e: self._clear())
        self.bind("<Control-k>", lambda e: self.entry_var.set(""))
        self.entry.bind("<Control-l>", lambda e: self._clear())
        self.entry.bind("<Control-k>", lambda e: self.entry_var.set(""))

    def _install_tags(self):
        # Tags de saída (prompt, cmd, ok, etc.)
        for tag_name, cfg in self.app.theme.get("output_tags", {}).items():
            self.output.tag_configure(tag_name, **cfg)
        # Tags de estilo ANSI (cores que vêm dos comandos)
        for tag_name, cfg in self.app.theme.get("tag_styles", {}).items():
            self.output.tag_configure(tag_name, **cfg)
        # Tags de destaque (highlighting configurável)
        for tag_name, cfg in self.app.theme.get("highlight_tags", {}).items():
            self.output.tag_configure(tag_name, **cfg)

    def _insert_rich_text(self, text):
        """Insere texto no output aplicando cores ANSI e regras de destaque."""
        self.output.configure(state="normal")
        
        # Compilar regras de highlight se ainda não estiverem prontas
        if not hasattr(self, '_compiled_highlights'):
            self._compiled_highlights = []
            for rule in self.app.theme.get("highlight_rules", []):
                try:
                    regex = re.compile(rule["pattern"], re.IGNORECASE if rule.get("ignore_case", False) else 0)
                    self._compiled_highlights.append((regex, rule["tag"]))
                except Exception:
                    pass  # ignora regra mal formada

        # Processar ANSI e escrever trecho por trecho
        pos = 0
        active_tags = []
        
        for match in ANSI_RE.finditer(text):
            # Texto antes do código ANSI
            chunk = text[pos:match.start()]
            if chunk:
                self._write_highlighted_chunk(chunk, active_tags)
            pos = match.end()
            codes = match.group(1) or "0"
            
            # Atualizar tags ANSI ativas
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

        # Último pedaço após último código ANSI
        tail = text[pos:]
        if tail:
            self._write_highlighted_chunk(tail, active_tags)

        self.output.see("end")
        self.output.configure(state="disabled")

    def _write_highlighted_chunk(self, chunk, ansi_tags):
        """Escreve um trecho de texto aplicando tags ANSI e depois regras de destaque."""
        if not chunk:
            return

        start_idx = self.output.index("end-1c")  # início do texto que será inserido
        if ansi_tags:
            self.output.insert("end", chunk, tuple(ansi_tags))
        else:
            self.output.insert("end", chunk)
        end_idx = self.output.index("end-1c")

        # Aplicar regras de destaque DENTRO do chunk recém-inserido
        if hasattr(self, '_compiled_highlights'):
            for regex, tag in self._compiled_highlights:
                # Buscar todas as correspondências dentro do chunk
                for m in regex.finditer(chunk):
                    offset_start = m.start()
                    offset_end = m.end()
                    # Converter para índices do Text widget
                    tag_start = f"{start_idx}+{offset_start}c"
                    tag_end = f"{start_idx}+{offset_end}c"
                    self.output.tag_add(tag, tag_start, tag_end)

        # Garantir que as tags ANSI tenham prioridade visual sobre as de destaque
        if ansi_tags:
            for tag in ansi_tags:
                self.output.tag_raise(tag)
    
    def _short_cwd(self, max_len=34):
        s = str(self.cwd)
        if len(s) <= max_len:
            return s
        return "..." + s[-(max_len - 3):]

    def _set_cwd(self, new_path):
        try:
            p = Path(new_path).expanduser().resolve()
            if p.exists() and p.is_dir():
                self.cwd = p
                self.cwd_label.config(text=self._short_cwd())
                self._prompt()
                return True
        except Exception:
            pass
        return False

    def _choose_cwd_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Escolher diretório")
        dlg.configure(bg="#111827")
        dlg.geometry("640x160")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        tk.Label(
            dlg,
            text="Digite um caminho ou use a navegação visual:",
            bg="#111827",
            fg="#e5e7eb",
            anchor="w",
            justify="left",
            font=("Segoe UI", 10, "bold"),
        ).pack(fill="x", padx=12, pady=(12, 6))

        entry_var = tk.StringVar(value=str(self.cwd))
        row = tk.Frame(dlg, bg="#111827")
        row.pack(fill="x", padx=12)

        entry = tk.Entry(
            row,
            textvariable=entry_var,
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            relief="flat",
            font=("Consolas", 10),
        )
        entry.pack(side="left", fill="x", expand=True, ipady=6)

        def browse():
            selected = filedialog.askdirectory(
                parent=dlg,
                initialdir=str(self.cwd),
                title="Selecionar diretório",
            )
            if selected:
                entry_var.set(selected)

        tk.Button(
            row,
            text="Procurar...",
            command=browse,
            bg="#374151",
            fg="#e5e7eb",
            relief="flat",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(8, 0))

        btns = tk.Frame(dlg, bg="#111827")
        btns.pack(fill="x", padx=12, pady=12)

        def ok():
            raw = entry_var.get().strip()
            if self._set_cwd(raw):
                dlg.destroy()
            else:
                messagebox.showerror("Diretório inválido", "O caminho informado não existe ou não é uma pasta.")

        tk.Button(
            btns,
            text="OK",
            command=ok,
            bg="#2563eb",
            fg="#ffffff",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            width=10,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            btns,
            text="Cancelar",
            command=dlg.destroy,
            bg="#374151",
            fg="#e5e7eb",
            relief="flat",
            font=("Segoe UI", 9),
            width=10,
        ).pack(side="right")

        entry.focus_set()
        entry.icursor("end")

    def _on_cwd_single_click(self, event=None):
        if self.cwd_editing:
            return "break"

        if self.cwd_click_after_id is not None:
            try:
                self.after_cancel(self.cwd_click_after_id)
            except Exception:
                pass

        self.cwd_click_after_id = self.after(220, self._open_cwd_picker)
        return "break"

    def _on_cwd_double_click(self, event=None):
        if self.cwd_click_after_id is not None:
            try:
                self.after_cancel(self.cwd_click_after_id)
            except Exception:
                pass
            self.cwd_click_after_id = None

        self._begin_cwd_edit()
        return "break"

    def _open_cwd_picker(self):
        self.cwd_click_after_id = None
        if self.cwd_editing:
            return

        selected = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            initialdir=str(self.cwd),
            title="Selecionar diretório",
        )
        if selected:
            self._set_cwd(selected)

    def _begin_cwd_edit(self):
        if self.cwd_editing:
            return

        self.cwd_editing = True
        self.cwd_entry_var.set(str(self.cwd))

        self.cwd_label.pack_forget()
        self.cwd_entry.pack(fill="both", expand=True, padx=1, pady=1)
        self.cwd_entry.focus_set()
        self.cwd_entry.icursor("end")
        self.cwd_entry.selection_range(0, "end")

        self.cwd_entry.bind("<Return>", self._finish_cwd_edit)
        self.cwd_entry.bind("<Escape>", self._cancel_cwd_edit)
        self.cwd_entry.bind("<FocusOut>", self._finish_cwd_edit)

    def _finish_cwd_edit(self, event=None):
        if not self.cwd_editing:
            return "break"

        raw = self.cwd_entry_var.get().strip()
        if raw and self._set_cwd(raw):
            self._end_cwd_edit()
        else:
            messagebox.showerror(
                "Diretório inválido",
                "O caminho informado não existe ou não é uma pasta.",
            )
            self.cwd_entry.focus_set()
            self.cwd_entry.selection_range(0, "end")
        return "break"

    def _cancel_cwd_edit(self, event=None):
        if self.cwd_editing:
            self._end_cwd_edit()
        return "break"

    def _end_cwd_edit(self):
        self.cwd_editing = False
        try:
            self.cwd_entry.pack_forget()
        except Exception:
            pass
        self.cwd_label.config(text=self._short_cwd())
        self.cwd_label.pack(fill="both", expand=True)

    def _set_cwd(self, new_path):
        try:
            p = Path(new_path).expanduser().resolve()
            if p.exists() and p.is_dir():
                self.cwd = p
                self.cwd_label.config(text=self._short_cwd())
                self._prompt()
                return True
        except Exception:
            pass
        return False
    
    def _banner(self):
        self._write_line(f"{APP_NAME} — terminal em Python puro conectado ao shell", "banner")
        self._write_line(f"Shell: {self.bridge.shell_name}", "dim")
        self._write_line("Comandos internos: help, clear, cd, pwd, ls, alias, view, exit", "dim")
        self._write_line("", None)

    def _prompt(self):
        self.cwd_label.config(text=self._short_cwd())
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
        if not self.app.history:
            return "break"
        self.history_index = max(0, self.history_index - 1)
        self.entry_var.set(self.app.history[self.history_index])
        self.entry.icursor("end")
        return "break"

    def _history_down(self, event=None):
        if not self.app.history:
            return "break"
        self.history_index = min(len(self.app.history), self.history_index + 1)
        if self.history_index >= len(self.app.history):
            self.entry_var.set("")
        else:
            self.entry_var.set(self.app.history[self.history_index])
        self.entry.icursor("end")
        return "break"

    def _record_history(self, cmd):
        self.app.record_history(cmd)
        self.history_index = len(self.app.history)

    def _autocomplete(self, event=None):
        text = self.entry_var.get()
        cursor = self.entry.index(tk.INSERT)

        before = text[:cursor]
        after = text[cursor:]

        leading_ws_len = len(before) - len(before.lstrip())
        leading_ws = before[:leading_ws_len]
        chunk = before[leading_ws_len:]

        if " " in chunk:
            return "break"

        prefix = chunk
        candidates = self._get_completion_candidates(prefix)
        if not candidates:
            return "break"

        if prefix != self._ac_prefix:
            self._ac_prefix = prefix
            self._ac_matches = candidates
            self._ac_index = 0
        else:
            if not self._ac_matches:
                self._ac_matches = candidates
                self._ac_index = 0
            else:
                self._ac_index = (self._ac_index + 1) % len(self._ac_matches)

        chosen = self._ac_matches[self._ac_index]

        rest = ""
        if after and not after.startswith(" "):
            rest = " " + after
        else:
            rest = after

        new_text = f"{leading_ws}{chosen}{rest}"
        self.entry_var.set(new_text)
        self.entry.icursor(len(leading_ws + chosen))
        return "break"

    def _get_completion_candidates(self, prefix):
        if self._path_command_cache is None:
            self._path_command_cache = self._collect_path_commands()

        candidates = set(INTERNAL_COMMANDS)
        candidates.update(self.app.aliases.keys())
        candidates.update(self._path_command_cache)

        if not prefix:
            return sorted(candidates, key=str.lower)

        return sorted([c for c in candidates if c.startswith(prefix)], key=str.lower)

    def _collect_path_commands(self):
        found = set()
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        if os.name == "nt":
            exts = [e.lower() for e in os.environ.get("PATHEXT", ".EXE;.BAT;.CMD;.COM").split(";")]
            for d in path_dirs:
                try:
                    p = Path(d)
                    if not p.exists():
                        continue
                    for child in p.iterdir():
                        if child.is_file() and child.suffix.lower() in exts:
                            name = child.stem if child.suffix else child.name
                            found.add(name)
                except Exception:
                    pass
        else:
            for d in path_dirs:
                try:
                    p = Path(d)
                    if not p.exists():
                        continue
                    for child in p.iterdir():
                        if child.is_file() and os.access(str(child), os.X_OK):
                            found.add(child.name)
                except Exception:
                    pass

        return found

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
            parts = shlex.split(cmd, posix=(os.name != "nt"))
        except Exception:
            return cmd

        if not parts:
            return cmd

        name = parts[0]
        if name not in self.app.aliases:
            return cmd

        template = self.app.aliases[name]
        rest = " ".join(parts[1:])
        expanded = template.replace("%*", rest)
        if "%*" not in template and rest:
            expanded = f"{template} {rest}"
        return expanded

    def _enter(self, event=None):
        raw = self.entry_var.get().strip()
        self.entry_var.set("")
        self._ac_prefix = None
        self._ac_matches = []
        self._ac_index = -1

        if not raw:
            self._prompt()
            return "break"

        self._record_history(raw)
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
        self._insert_rich_text(line + "\n")

    def _update_local_cwd_if_needed(self, command):
        try:
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
                self.cwd_label.config(text=self._short_cwd())

        elif cmd == "pushd" and len(parts) >= 2:
            target = self._resolve(parts[1])
            if target.exists() and target.is_dir():
                self.cwd = target.resolve()
                self.cwd_label.config(text=self._short_cwd())

        elif cmd == "popd":
            pass

    def _internal(self, command):
        try:
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
                "  exit              fecha esta aba",
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
                self.cwd_label.config(text=self._short_cwd())
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
                if not self.app.aliases:
                    self._write_line("Nenhum alias salvo.", "dim")
                else:
                    for k, v in sorted(self.app.aliases.items()):
                        self._write_line(f"{k} -> {v}", "warn")
                return True

            sub = args[0].lower()
            if sub == "add":
                if len(args) < 3:
                    self._write_line("Uso: alias add NOME COMANDO", "warn")
                    return True
                name = args[1]
                value = " ".join(args[2:])
                self.app.aliases[name] = value
                self.app.save_aliases()
                self._write_line(f"Alias salvo: {name} -> {value}", "ok")
                return True

            if sub in {"del", "rm", "remove"}:
                if len(args) < 2:
                    self._write_line("Uso: alias del NOME", "warn")
                    return True
                name = args[1]
                if name in self.app.aliases:
                    del self.app.aliases[name]
                    self.app.save_aliases()
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

            MediaViewer(self.winfo_toplevel(), path)
            self._write_line(f"Visualização aberta: {path.name}", "info")
            return True

        if c == "exit":
            self.close_tab()
            return True

        return False

    def close_tab(self):
        try:
            self.bridge.terminate()
        finally:
            self.app.close_tab(self)

    def _on_close(self):
        self.close_tab()

class BrowserTab:
    def __init__(self, app, title):
        self.app = app
        self.title = title

        self.session = TerminalSessionTab(app.body, app, tab_title=title)
        self.session.pack_forget()

        self.header = tk.Frame(
            app.tab_strip_inner,
            bg="#111827",
            bd=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#1f2937",
            cursor="hand2",
        )

        self.label = tk.Label(
            self.header,
            text=title,
            bg="#111827",
            fg="#e5e7eb",
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.label.pack(side="left")

        self.close_btn = tk.Label(
            self.header,
            text="×",
            bg="#111827",
            fg="#9ca3af",
            font=("Segoe UI", 10, "bold"),
            padx=8,
            pady=4,
            cursor="hand2",
        )
        self.close_btn.pack(side="left")

        for widget in (self.header, self.label):
            widget.bind("<Button-1>", self._select)
            widget.bind("<Button-2>", self._close)
            widget.bind("<Button-3>", lambda e: None)

        self.close_btn.bind("<Button-1>", self._close)
        self.close_btn.bind("<Button-2>", self._close)

    def _select(self, event=None):
        self.app.select_tab(self)
        return "break"

    def _close(self, event=None):
        self.app.close_tab(self)
        return "break"

    def set_active(self, active: bool):
        bg = "#0b1220" if active else "#111827"
        fg = "#ffffff" if active else "#e5e7eb"
        close_fg = "#fca5a5" if active else "#9ca3af"
        border = "#2563eb" if active else "#1f2937"

        self.header.config(bg=bg, highlightbackground=border)
        self.label.config(bg=bg, fg=fg)
        self.close_btn.config(bg=bg, fg=close_fg)


class TabbedTerminalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1100x760")
        self.minsize(900, 560)
        self.configure(bg="#0f172a")
        self.theme = load_theme()

        self.aliases = self._load_aliases()
        self.history = self._load_history()
        self.tabs = []
        self.active_tab = None
        self.tab_count = 0
        self.session_to_tab = {}

        self._build_ui()
        self._add_tab()

        self.protocol("WM_DELETE_WINDOW", self._close_all)
        self.bind("<Control-t>", lambda e: self._add_tab())
        self.bind("<Control-w>", lambda e: self._close_current_tab())
        self.bind("<Control-Tab>", lambda e: self._next_tab())
        self.bind("<Control-Shift-Tab>", lambda e: self._prev_tab())

    def _build_ui(self):
        top = tk.Frame(self, bg="#0f172a")
        top.pack(fill="x", padx=12, pady=(12, 6))

        self.tab_strip = tk.Frame(top, bg="#0f172a")
        self.tab_strip.pack(side="left", fill="x", expand=True)

        self.tab_strip_inner = tk.Frame(self.tab_strip, bg="#0f172a")
        self.tab_strip_inner.pack(side="left", fill="x", expand=True)

        self.new_btn = tk.Button(
            top,
            text="+",
            command=self._add_tab,
            bg="#2563eb",
            fg="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        )
        self.new_btn.pack(side="right")

        self.body = tk.Frame(self, bg="#0f172a")
        self.body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _load_aliases(self):
        if ALIASES_FILE.exists():
            try:
                data = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {}

    def save_aliases(self):
        ALIASES_FILE.write_text(
            json.dumps(self.aliases, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_history(self):
        if HISTORY_FILE.exists():
            try:
                data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [str(x) for x in data][-20:]
            except Exception:
                pass
        return []

    def _save_history(self):
        HISTORY_FILE.write_text(
            json.dumps(self.history[-20:], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def record_history(self, cmd):
        cmd = cmd.strip()
        if not cmd:
            return
        self.history.append(cmd)
        self.history = self.history[-20:]
        self._save_history()

    def _add_tab(self):
        self.tab_count += 1
        title = f"Aba {self.tab_count}"

        tab = BrowserTab(self, title)
        self.tabs.append(tab)
        self.session_to_tab[tab.session] = tab

        self._render_tabs()
        self.select_tab(tab)

    def _render_tabs(self):
        for child in self.tab_strip_inner.winfo_children():
            child.pack_forget()

        for tab in self.tabs:
            tab.header.pack(side="left", padx=(0, 4))
            tab.set_active(tab is self.active_tab)

        self.tab_strip_inner.update_idletasks()

    def select_tab(self, tab):
        if tab not in self.tabs:
            return

        if self.active_tab is tab:
            tab.session._prompt()
            return

        if self.active_tab is not None:
            try:
                self.active_tab.session.pack_forget()
            except Exception:
                pass

        self.active_tab = tab
        tab.session.pack(fill="both", expand=True)
        tab.session._prompt()
        self._render_tabs()

    def _current_tab(self):
        return self.active_tab

    def _close_current_tab(self):
        if self.active_tab is not None:
            self.close_tab(self.active_tab)

    def close_tab(self, tab):
        if tab not in self.tabs:
            return

        was_active = (tab is self.active_tab)

        try:
            if hasattr(tab.session, "bridge") and tab.session.bridge is not None:
                tab.session.bridge.terminate()
        except Exception:
            pass

        try:
            tab.session.pack_forget()
        except Exception:
            pass

        try:
            tab.session.destroy()
        except Exception:
            pass

        try:
            tab.header.destroy()
        except Exception:
            pass

        self.session_to_tab.pop(tab.session, None)
        index = self.tabs.index(tab)
        self.tabs.remove(tab)

        if not self.tabs:
            self._save_history()
            self.destroy()
            return

        if was_active:
            new_index = min(index, len(self.tabs) - 1)
            self.active_tab = None
            self.select_tab(self.tabs[new_index])
        else:
            self._render_tabs()
    
    def _next_tab(self):
        if not self.tabs:
            return "break"
        idx = self.tabs.index(self.active_tab)
        self.select_tab(self.tabs[(idx + 1) % len(self.tabs)])
        return "break"

    def _prev_tab(self):
        if not self.tabs:
            return "break"
        idx = self.tabs.index(self.active_tab)
        self.select_tab(self.tabs[(idx - 1) % len(self.tabs)])
        return "break"

    def _close_all(self):
        for tab in list(self.tabs):
            try:
                if hasattr(tab.session, "bridge") and tab.session.bridge is not None:
                    tab.session.bridge.terminate()
            except Exception:
                pass
        self._save_history()
        self.destroy()


if __name__ == "__main__":
    app = TabbedTerminalApp()
    app.mainloop()