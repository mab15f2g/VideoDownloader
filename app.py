from __future__ import annotations

import shutil
import ssl
import subprocess
import sys
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import messagebox, scrolledtext


BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/"
    "ffmpeg-master-latest-win64-gpl.zip"
)


def find_command(*names: str) -> Optional[str]:
    for name in names:
        local_path = BASE_DIR / name
        if local_path.exists():
            return str(local_path)
        found = shutil.which(name)
        if found:
            return found
    return None


class YtDlpGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("YT-DLP Downloader")
        self.root.geometry("720x500")
        self.root.minsize(640, 440)

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="mp3")
        self.busy = False
        self.current_process: Optional[subprocess.Popen] = None
        self.cancel_requested = False

        self.ytdlp_cmd: Optional[str] = None
        self.ffmpeg_cmd: Optional[str] = None
        self.ffprobe_cmd: Optional[str] = None

        self.build_ui()
        self.refresh_dependency_status()
        self.startup_dependency_check()

    def build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=16, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Link einfuegen",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        tk.Entry(
            frame,
            textvariable=self.url_var,
            font=("Segoe UI", 11),
        ).pack(fill="x", pady=(6, 14))

        options_frame = tk.Frame(frame)
        options_frame.pack(fill="x")

        tk.Label(
            options_frame,
            text="Format:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(0, 10))

        tk.Radiobutton(
            options_frame,
            text="MP3",
            variable=self.mode_var,
            value="mp3",
            font=("Segoe UI", 10),
        ).pack(side="left")

        tk.Radiobutton(
            options_frame,
            text="Video",
            variable=self.mode_var,
            value="video",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(12, 0))

        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(fill="x", pady=(16, 12))

        self.download_button = tk.Button(
            buttons_frame,
            text="Download",
            font=("Segoe UI", 10, "bold"),
            width=14,
            command=self.start_download,
        )
        self.download_button.pack(side="left")

        self.cancel_button = tk.Button(
            buttons_frame,
            text="Abbrechen",
            font=("Segoe UI", 10),
            width=14,
            state="disabled",
            command=self.cancel_download,
        )
        self.cancel_button.pack(side="left", padx=(10, 0))

        self.status_label = tk.Label(
            frame,
            text="",
            justify="left",
            anchor="w",
            fg="#333333",
            font=("Segoe UI", 9),
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        self.log_box = scrolledtext.ScrolledText(
            frame,
            wrap="word",
            font=("Consolas", 10),
            height=16,
            state="disabled",
        )
        self.log_box.pack(fill="both", expand=True)

        self.log(
            "Downloads werden gespeichert unter:\n"
            f"{DOWNLOAD_DIR}\n"
        )

    def refresh_dependency_status(self) -> None:
        self.ytdlp_cmd = find_command("yt-dlp.exe", "yt-dlp")
        self.ffmpeg_cmd = find_command("ffmpeg.exe", "ffmpeg")
        self.ffprobe_cmd = find_command("ffprobe.exe", "ffprobe")
        lines = [
            f"yt-dlp: {'gefunden' if self.ytdlp_cmd else 'nicht gefunden'}",
            f"ffmpeg: {'gefunden' if self.ffmpeg_cmd else 'nicht gefunden'}",
            f"ffprobe: {'gefunden' if self.ffprobe_cmd else 'nicht gefunden'}",
            f"Download-Ordner: {DOWNLOAD_DIR}",
        ]
        self.status_label.config(text="\n".join(lines))

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        download_state = "disabled" if busy else "normal"
        cancel_state = "normal" if busy and self.current_process else "disabled"
        self.download_button.config(state=download_state)
        self.cancel_button.config(state=cancel_state)

    def update_cancel_button(self) -> None:
        cancel_state = "normal" if self.busy and self.current_process else "disabled"
        self.cancel_button.config(state=cancel_state)

    def log(self, text: str) -> None:
        self.log_box.config(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def run_on_ui(self, func, *args) -> None:
        self.root.after(0, lambda: func(*args))

    def startup_dependency_check(self) -> None:
        self.set_busy(True)
        self.log("Pruefe beim Start auf yt-dlp, ffmpeg und ffprobe ...")
        threading.Thread(target=self.startup_dependency_worker, daemon=True).start()

    def startup_dependency_worker(self) -> None:
        try:
            if not self.ytdlp_cmd:
                self.run_on_ui(self.log, "yt-dlp fehlt. Starte automatischen Download ...")
                self.download_file(YT_DLP_URL, BASE_DIR / "yt-dlp.exe")
                self.run_on_ui(self.log, "yt-dlp wurde heruntergeladen.")

            self.run_on_ui(self.refresh_dependency_status)

            if not self.ffmpeg_cmd or not self.ffprobe_cmd:
                self.run_on_ui(
                    self.log,
                    "ffmpeg oder ffprobe fehlen. Lade FFmpeg-Paket herunter ...",
                )
                self.install_ffmpeg_bundle()
                self.run_on_ui(self.log, "ffmpeg und ffprobe wurden bereitgestellt.")

            self.run_on_ui(self.refresh_dependency_status)
            if self.ytdlp_cmd:
                self.run_on_ui(self.log, "Pruefe yt-dlp auf Updates ...")
                update_code = self.run_command_and_log([self.ytdlp_cmd, "-U"])
                if update_code == 0:
                    self.run_on_ui(self.log, "yt-dlp ist aktuell.")
                else:
                    self.run_on_ui(
                        self.log,
                        f"yt-dlp-Updatepruefung fehlgeschlagen. Rueckgabecode: {update_code}",
                    )

            self.run_on_ui(self.refresh_dependency_status)
            if self.ytdlp_cmd and self.ffmpeg_cmd and self.ffprobe_cmd:
                self.run_on_ui(self.log, "Alle benoetigten Programme sind verfuegbar.")
        except Exception as exc:
            self.run_on_ui(self.refresh_dependency_status)
            self.run_on_ui(self.log, f"Automatische Einrichtung fehlgeschlagen: {exc}")
            self.run_on_ui(
                messagebox.showerror,
                "Automatischer Download fehlgeschlagen",
                "Die benoetigten Programme konnten nicht automatisch geladen werden.\n"
                f"Details: {exc}",
            )
        finally:
            self.run_on_ui(self.refresh_dependency_status)
            self.run_on_ui(self.set_busy, False)

    def download_file(self, url: str, target: Path) -> None:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        contexts = []
        default_context = ssl.create_default_context()
        contexts.append(("Standard-SSL-Pruefung", default_context))

        try:
            import certifi  # type: ignore

            certifi_context = ssl.create_default_context(cafile=certifi.where())
            contexts.append(("Certifi-Zertifikate", certifi_context))
        except Exception:
            pass

        insecure_context = ssl._create_unverified_context()
        contexts.append(("SSL-Fallback ohne Zertifikatspruefung", insecure_context))

        last_error = None
        for label, context in contexts:
            try:
                self.run_on_ui(self.log, f"Downloadversuch ueber: {label}")
                with urllib.request.urlopen(request, context=context) as response, target.open("wb") as output:
                    shutil.copyfileobj(response, output)

                if label == "SSL-Fallback ohne Zertifikatspruefung":
                    self.run_on_ui(
                        self.log,
                        "Warnung: Download lief ohne SSL-Zertifikatspruefung.",
                    )
                return
            except Exception as exc:
                last_error = exc
                self.run_on_ui(self.log, f"{label} fehlgeschlagen: {exc}")

        raise RuntimeError(f"Download fehlgeschlagen: {last_error}")

    def install_ffmpeg_bundle(self) -> None:
        archive_path = BASE_DIR / "ffmpeg_download.zip"
        self.download_file(FFMPEG_URL, archive_path)

        extracted_root: Optional[Path] = None
        with zipfile.ZipFile(archive_path, "r") as archive:
            for member in archive.namelist():
                path = Path(member)
                if path.name.lower() == "ffmpeg.exe":
                    extracted_root = path.parents[1]
                    break

            archive.extractall(BASE_DIR)

        if archive_path.exists():
            archive_path.unlink()

        if extracted_root is None:
            raise RuntimeError("ffmpeg.exe wurde im Paket nicht gefunden.")

        bin_dir = BASE_DIR / extracted_root / "bin"
        for exe_name in ("ffmpeg.exe", "ffprobe.exe"):
            source = bin_dir / exe_name
            target = BASE_DIR / exe_name
            if not source.exists():
                raise RuntimeError(f"{exe_name} wurde im Paket nicht gefunden.")
            shutil.copy2(source, target)

        extracted_dir = BASE_DIR / extracted_root
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir, ignore_errors=True)

    def ensure_dependencies(self, needs_ffmpeg: bool) -> bool:
        self.refresh_dependency_status()

        if not self.ytdlp_cmd:
            messagebox.showerror(
                "Fehlendes yt-dlp",
                "yt-dlp steht nicht zur Verfuegung. Bitte App neu starten.",
            )
            return False

        if needs_ffmpeg and (not self.ffmpeg_cmd or not self.ffprobe_cmd):
            messagebox.showerror(
                "Fehlendes ffmpeg/ffprobe",
                "ffmpeg oder ffprobe stehen nicht zur Verfuegung. Bitte App neu starten.",
            )
            return False

        return True

    def start_download(self) -> None:
        url = self.url_var.get().strip()
        mode = self.mode_var.get()

        if not url:
            messagebox.showwarning("Kein Link", "Bitte zuerst einen Link einfuegen.")
            return

        needs_ffmpeg = mode == "mp3"
        if not self.ensure_dependencies(needs_ffmpeg=needs_ffmpeg):
            return

        self.set_busy(True)
        self.cancel_requested = False
        self.log(f"Starte Download ({mode.upper()}): {url}")
        threading.Thread(
            target=self.download_worker,
            args=(url, mode),
            daemon=True,
        ).start()

    def cancel_download(self) -> None:
        process = self.current_process
        if not process:
            return

        self.cancel_requested = True
        self.log("Abbruch angefordert ...")
        try:
            process.terminate()
        except Exception as exc:
            self.log(f"Abbruch konnte nicht gesendet werden: {exc}")

    def download_worker(self, url: str, mode: str) -> None:
        output_template = str(DOWNLOAD_DIR / "%(title)s.%(ext)s")
        command = [self.ytdlp_cmd]

        if mode == "mp3":
            command += [
                "-x",
                "--audio-format",
                "mp3",
            ]
        else:
            command += [
                "-f",
                "bestvideo+bestaudio/best",
                "--merge-output-format",
                "mp4",
            ]

        if self.ffmpeg_cmd:
            command += ["--ffmpeg-location", self.ffmpeg_cmd]

        command += ["-o", output_template, url]
        self.execute_command(command, success_text="Download abgeschlossen.")

    def run_command_and_log(self, command: list[str]) -> int:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=BASE_DIR,
        )
        self.current_process = process
        self.run_on_ui(self.update_cancel_button)

        assert process.stdout is not None
        for line in process.stdout:
            self.run_on_ui(self.log, line.rstrip())

        return_code = process.wait()
        self.current_process = None
        self.run_on_ui(self.update_cancel_button)
        return return_code

    def execute_command(self, command: list[str], success_text: str) -> None:
        try:
            return_code = self.run_command_and_log(command)
            if return_code == 0:
                self.run_on_ui(self.log, success_text)
            elif self.cancel_requested:
                self.run_on_ui(self.log, "Download wurde abgebrochen.")
            else:
                self.run_on_ui(
                    self.log,
                    f"Vorgang fehlgeschlagen. Rueckgabecode: {return_code}",
                )
                self.run_on_ui(
                    messagebox.showerror,
                    "Fehler",
                    "Der Vorgang ist fehlgeschlagen. Details stehen im Log.",
                )
        except Exception as exc:
            self.run_on_ui(self.log, f"Unerwarteter Fehler: {exc}")
            self.run_on_ui(
                messagebox.showerror,
                "Fehler",
                f"Unerwarteter Fehler: {exc}",
            )
        finally:
            self.current_process = None
            self.run_on_ui(self.set_busy, False)
            self.run_on_ui(self.refresh_dependency_status)


def main() -> None:
    root = tk.Tk()
    app = YtDlpGui(root)
    root.mainloop()


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        raise SystemExit("Bitte Python 3.9 oder neuer verwenden.")
    main()
