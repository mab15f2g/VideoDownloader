# YT-DLP Downloader

Kleine Windows-Oberflaeche zum Herunterladen von `MP3` oder `Video` per `yt-dlp`.

## Starten

1. `start.bat` doppelklicken.
2. Falls Python fehlt, versucht der Launcher zuerst eine automatische Installation.
3. Wenn das nicht klappt, wird der offizielle Python-Installer heruntergeladen und gestartet.
4. Danach werden benoetigte Python-Komponenten vorbereitet und die App gestartet.
5. Beim App-Start prueft das Programm `yt-dlp`, `ffmpeg` und `ffprobe`.
6. Fehlende Dateien werden automatisch in diesen Ordner heruntergeladen.
7. `yt-dlp` wird beim Start automatisch auf Updates geprueft.

## Funktionen

- Link einfuegen
- `MP3` oder `Video` waehlen (`MP3` ist vorbelegt)
- `Download` speichert Dateien in `downloads`
- `Abbrechen` stoppt einen laufenden Download, z. B. bei einer versehentlichen Playlist
- Windows-Launcher prueft Python und richtet es wenn noetig ein
- Python-Pakete werden ueber `requirements.txt` vorbereitet
- Automatische Einrichtung von `yt-dlp`, `ffmpeg` und `ffprobe` beim Start
- Automatische Update-Pruefung fuer `yt-dlp` beim Start

## Hinweis

Fuer den automatischen Download wird eine Internetverbindung benoetigt.
