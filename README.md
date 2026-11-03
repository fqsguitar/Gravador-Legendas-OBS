# OBS Subtitle Recorder / Gravador de Legendas OBS

**[Download Windows v1.0.0](https://github.com/fqsguitar/Gravador-Legendas-OBS/releases/tag/v1.0.0)** · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

**English** | [Português (Brasil)](README.pt-BR.md)

Windows desktop application that controls OBS Studio recording and automatically generates timestamped **SRT subtitles** and **TXT transcripts** from the finished OBS video using local **faster-whisper**.

> **OBS Studio is NOT included. For video mode, install and configure OBS separately from https://obsproject.com/ and keep it running. Standalone audio mode does not require OBS.** This project is not affiliated with OBS Studio.

## Features
- Start/stop OBS recording from the application or Windows system tray via OBS WebSocket.
- Transcribe the finished OBS MP4/MKV directly: no parallel WASAPI recording in OBS mode.
- Save `video-name.srt` and `video-name.txt` next to `video-name.mp4`.
- System tray status: **green** idle, **red** recording, **blinking yellow** transcribing.
- Remain resident after transcription, reset timer and support repeated recordings.
- Optional auto-start minimized to tray on Windows sign-in.
- Remember preferences; protect the OBS WebSocket password using Windows DPAPI.
- Standalone PC audio, microphone, or PC + microphone capture to temporary disk files.
- Transcription always runs after recording ends; temporary WAV is deleted only after SRT/TXT are generated successfully, and retained on failure.

## Requirements
- Windows 10/11.
- **OBS Studio 28+** for video mode only; WebSocket support is built in.
- Python and the `py` launcher for building the EXE.
- Internet access for initial Python dependencies and Whisper model download; transcription runs locally afterward.
- Permission to record the content and participants concerned.

## 1. Install OBS Studio (for video mode only)
1. Download and install **OBS Studio** from https://obsproject.com/. The build script **does not** install OBS.
2. Open OBS and create a scene with the desired screen/window capture.
3. Under **Settings → Audio**, set up **Desktop Audio** and **Mic/Auxiliary Audio** as needed. Check that the OBS audio mixer meters move for both the PC and microphone.
4. Under **Settings → Output → Recording**, choose a recording folder and MP4 or MKV format.
5. Open **Tools → WebSocket Server Settings**.
6. Enable the WebSocket server, set port **4455** (default), enable authentication, generate or choose a password, and apply.
7. **Keep OBS running.** You do not have to click Start Recording inside OBS; the application will send the command over WebSocket.

**Security:** use host `localhost` on the same computer; do not expose the WebSocket port to the public internet.

## 2. Build and launch
1. Install Python for Windows and check `py --version` in PowerShell.
2. Download the repository via **Code → Download ZIP**, extract it, and run `compilar_obs.bat`.
3. The batch file installs Python packages and builds `dist\GravadorLegendasOBS.exe` with PyInstaller.
4. Move the EXE to its final folder (for example, `%LOCALAPPDATA%\Programs\GravadorLegendasOBS\`) **before** enabling startup.
5. Launch the EXE.

The batch file **does not install OBS**, create an installer, or enable Windows startup. Corporate security policies may restrict installations.

## 3. Connect and record
In the app, enable **Gravar vídeo no OBS**, set **Host** to `localhost`, **Port** to `4455`, and enter the same WebSocket password as in OBS. Start with Whisper model **small** and the desired language.

Click **Iniciar gravação** (Start recording), or use the system tray menu. OBS records the video and all audio configured in its mixer. Click **Parar e salvar** (Stop and save) to finish. The application transcribes the saved OBS video after recording ends.

Example output:
```text
2026-10-28 16-40-53.mp4
2026-10-28 16-40-53.srt
2026-10-28 16-40-53.txt
```
The subtitle timestamps follow the video timeline.

## 4. System tray
Close the window with **X** to keep the app running in the tray. Right-click the icon to start/stop recording, open the window or output folder, or exit. Emergency force exit can interrupt ongoing processing.

## 5. Start automatically with Windows — configure BOTH apps
**A. Subtitle Recorder:** place the EXE in its permanent location, then tick **Iniciar com o Windows (minimizado na bandeja)**. This registers startup for the current Windows user and launches the app minimized. Untick to disable; if you move the EXE, untick and tick again to update the path.

**B. OBS Studio:** configure OBS separately to launch at Windows sign-in. You can create a shortcut in the current user's Startup folder: press **Win+R**, enter `shell:startup`, and add an OBS shortcut. Where supported, use `--minimize-to-tray` to keep OBS minimized. Verify OBS is running and WebSocket is ready before starting a recording.

**Important:** ticking the box in the Subtitle Recorder **does not start or install OBS**. Both applications must be running for video recording.

## 6. Standalone audio mode — without OBS
Untick **Gravar vídeo no OBS**, select **Áudio do PC**, **Microfone**, or **PC + Microfone**, and start recording. The application captures continuously to temporary files, mixes the audio sources after stopping, and then generates SRT/TXT. Once both files are generated, the WAV is deleted. If transcription fails, the WAV is preserved. The mode was manually tested; verify your Windows default input/output devices before important recordings.

## 7. Troubleshooting
- **Connection failed:** verify OBS is open, WebSocket enabled, `localhost`, port and password.
- **Silent video:** inspect Desktop Audio and Mic/Aux meters in OBS before recording.
- **No SRT:** confirm OBS finished writing the video; check application logs.
- **Slow transcription:** use Whisper `small` instead of `medium`; first run may download/load a model.
- **Windows startup fails:** verify the EXE has not moved and that OBS startup was configured independently.

## Privacy and status
Speech recognition runs locally after model download. OBS WebSocket credentials are protected with Windows DPAPI in the current user's settings; **never commit** local `config.json`, meeting recordings, transcripts or logs.

**OBS mode:** tested with consecutive recordings, successful SRT/TXT output and return to idle tray state. **Standalone audio mode:** manually tested after capture redesign; behavior may vary with Windows audio devices.

License: MIT.