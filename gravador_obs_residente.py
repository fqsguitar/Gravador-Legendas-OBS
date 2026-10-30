import os
import json
import base64
import ctypes
from ctypes import wintypes
import sys
import time
import wave
import queue
import threading
import traceback
import logging
import faulthandler
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import subprocess
import winreg
from PIL import Image, ImageDraw
import pystray
import atexit
import faulthandler

RATE = 16000
CHUNK = 1024


# Windows DPAPI: senha criptografada para o usuario atual do Windows.
class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]


def _blob(data):
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf


def dpapi_encrypt(value):
    raw, keepalive = _blob(value.encode('utf-8'))
    result = DATA_BLOB()
    crypt = ctypes.windll.crypt32
    if not crypt.CryptProtectData(ctypes.byref(raw), None, None, None, None, 0x1, ctypes.byref(result)):
        raise ctypes.WinError()
    try:
        return base64.b64encode(ctypes.string_at(result.pbData, result.cbData)).decode('ascii')
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)


def dpapi_decrypt(value):
    raw, keepalive = _blob(base64.b64decode(value, validate=True))
    result = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(raw), None, None, None, None, 0x1, ctypes.byref(result)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(result.pbData, result.cbData).decode('utf-8')
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)


class App:
    def __init__(self, root):
        self.root = root
        root.title('Gravador e Legendas - OBS opcional')
        root.geometry('740x610')
        self.running = False
        self.worker = None
        self.phase = "ready"
        self.tray = None
        self._tray_failures = 0
        self._tray_last_phase = None
        self.blink = False
        self.exiting = False
        self.auto_start = tk.BooleanVar(value=False)
        self._ui_queue = queue.Queue()
        self.obs_client = None
        self.obs_started = False
        self.obs_video_mode = False
        self.obs_video_path = None
        self.obs_start_time = None
        self.audio_start_time = None
        self.srt_offset = 0.0
        self.source = tk.StringVar(value='PC + Microfone')
        self.mode = tk.StringVar(value='Após gravação')
        self.model = tk.StringVar(value='small')
        self.language = tk.StringVar(value='pt')
        self.output = tk.StringVar(value=str(Path.home() / 'Documents' / 'Legendas'))
        self.use_obs = tk.BooleanVar(value=True)
        self.obs_host = tk.StringVar(value='localhost')
        self.obs_port = tk.StringVar(value='4455')
        self.obs_password = tk.StringVar(value='')
        self.status = tk.StringVar(value='Pronto')
        self.elapsed = tk.StringVar(value='00:00:00')
        self.partial_busy = threading.Event()
        self.frames_lock = threading.Lock()
        self.frames = []
        p = ttk.Frame(root, padding=18)
        p.pack(fill='both', expand=True)
        ttk.Label(p, text='Gravador de áudio e legendas', font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        for label, var, options in [
            ('Fonte de áudio', self.source, ['Áudio do PC', 'Microfone', 'PC + Microfone']),
            ('Transcrição', self.mode, ['Após gravação', 'Ao vivo']),
            ('Modelo Whisper', self.model, ['tiny', 'base', 'small', 'medium', 'large-v3']),
            ('Idioma', self.language, ['pt', 'en', 'auto'])
        ]:
            line = ttk.Frame(p)
            line.pack(fill='x', pady=5)
            ttk.Label(line, text=label, width=20).pack(side='left')
            ttk.Combobox(line, textvariable=var, values=options, state='readonly', width=30).pack(side='left')
        line = ttk.Frame(p)
        line.pack(fill='x', pady=7)
        ttk.Label(line, text='Pasta de saída', width=20).pack(side='left')
        ttk.Entry(line, textvariable=self.output, width=42).pack(side='left', fill='x', expand=True)
        ttk.Button(line, text='...', command=self.choose).pack(side='left')
        ttk.Label(p, textvariable=self.elapsed, font=('Consolas', 24)).pack(pady=9)
        buttons = ttk.Frame(p)
        buttons.pack()
        self.start_btn = ttk.Button(buttons, text='Iniciar gravação', command=self.start)
        self.start_btn.pack(side='left', padx=5)
        self.stop_btn = ttk.Button(buttons, text='Parar e salvar', command=self.stop, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        self.import_btn = ttk.Button(buttons, text='Importar áudio/vídeo', command=self.import_file)
        self.import_btn.pack(side='left', padx=5)
        ttk.Label(p, textvariable=self.status, wraplength=680).pack(anchor='w', pady=14)
        obs = ttk.LabelFrame(p, text='OBS Studio (opcional)', padding=8)
        obs.pack(fill='x', pady=8)
        ttk.Checkbutton(obs, text='Gravar vídeo no OBS (desmarque para somente áudio + legendas)', variable=self.use_obs).pack(anchor='w')
        settings = ttk.Frame(obs)
        settings.pack(fill='x', pady=4)
        ttk.Label(settings, text='Host').pack(side='left')
        ttk.Entry(settings, textvariable=self.obs_host, width=14).pack(side='left', padx=4)
        ttk.Label(settings, text='Porta').pack(side='left')
        ttk.Entry(settings, textvariable=self.obs_port, width=7).pack(side='left', padx=4)
        ttk.Label(settings, text='Senha').pack(side='left')
        ttk.Entry(settings, textvariable=self.obs_password, width=18, show='*').pack(side='left', padx=4)
        ttk.Checkbutton(p, text='Iniciar com o Windows (minimizado na bandeja)', variable=self.auto_start, command=self.toggle_autostart).pack(anchor='w', pady=6)
        ttk.Label(p, text='Com OBS: transcrição após parar, diretamente do vídeo (sem captura extra).\nSem OBS: captura WAV local; transcrição ao vivo ou após gravação.', foreground='#555').pack(anchor='w')
        self.load_settings()
        self.auto_start.set(self.is_autostart_enabled())
        root.report_callback_exception = self._tk_exception
        root.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.root.after(100, self._drain_ui)
        self.root.after(500, self._tray_tick)
        self._start_tray()
        self.log_event("Aplicativo iniciado")
        if '--minimized' in sys.argv:
            root.withdraw()

    def settings_path(self):
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
        return base / 'GravadorLegendasOBS' / 'config.json'

    def load_settings(self):
        path = self.settings_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            fields = {'source': self.source, 'mode': self.mode, 'model': self.model,
                      'language': self.language, 'output': self.output, 'use_obs': self.use_obs,
                      'obs_host': self.obs_host, 'obs_port': self.obs_port}
            for key, var in fields.items():
                if key in data:
                    var.set(data[key])
            if data.get('obs_password_dpapi'):
                try:
                    self.obs_password.set(dpapi_decrypt(data['obs_password_dpapi']))
                except Exception:
                    self.obs_password.set('')
                    self.status.set('Configurações carregadas; informe novamente a senha do OBS.')
        except Exception as exc:
            self.status.set(f'Não foi possível carregar configurações: {exc}')

    def save_settings(self):
        try:
            data = {'source': self.source.get(), 'mode': self.mode.get(),
                    'model': self.model.get(), 'language': self.language.get(),
                    'output': self.output.get(), 'use_obs': self.use_obs.get(),
                    'obs_host': self.obs_host.get(), 'obs_port': self.obs_port.get(),
                    'obs_password_dpapi': dpapi_encrypt(self.obs_password.get()) if self.obs_password.get() else ''}
            path = self.settings_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(path)
            return True
        except Exception as exc:
            messagebox.showwarning('Configurações', f'Não foi possível salvar as configurações:\n{exc}')
            return False

    @staticmethod
    def startup_command():
        if getattr(sys, 'frozen', False):
            return '"' + sys.executable + '" --minimized'
        return '"' + sys.executable + '" "' + str(Path(__file__).resolve()) + '" --minimized'

    def is_autostart_enabled(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                value, _ = winreg.QueryValueEx(key, 'GravadorLegendasOBS')
                return value == self.startup_command()
        except OSError:
            return False

    def toggle_autostart(self):
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as key:
                if self.auto_start.get():
                    winreg.SetValueEx(key, 'GravadorLegendasOBS', 0, winreg.REG_SZ, self.startup_command())
                else:
                    try:
                        winreg.DeleteValue(key, 'GravadorLegendasOBS')
                    except FileNotFoundError:
                        pass
        except OSError as exc:
            self.auto_start.set(self.is_autostart_enabled())
            messagebox.showerror('Inicialização automática', str(exc))

    @staticmethod
    def tray_image(color):
        im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((5, 5, 59, 59), fill=color, outline='#333333', width=3)
        return im

    def _start_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('Abrir janela', lambda icon, item: self.ui(self.show_window), default=True),
            pystray.MenuItem('Iniciar gravação', lambda icon, item: self.ui(self.start), enabled=lambda item: self.phase == 'ready'),
            pystray.MenuItem('Parar gravação', lambda icon, item: self.ui(self.stop), enabled=lambda item: self.phase == 'recording'),
            pystray.MenuItem('Abrir pasta de legendas', lambda icon, item: self.ui(self.open_output)),
            pystray.MenuItem('Sair', lambda icon, item: self.ui(self.exit_program)),
            pystray.MenuItem('Forçar encerramento (emergência)', lambda icon, item: self.ui(self.force_exit))
        )
        self.tray = pystray.Icon('GravadorLegendasOBS', self.tray_image('#16a34a'), 'Gravador de legendas - Pronto', menu)
        try:
            # No Windows, manter o loop da bandeja numa thread dedicada.
            # Evita depender do ciclo de vida da janela Tk escondida.
            self._tray_thread = threading.Thread(target=self._run_tray, name='SystemTray', daemon=True)
            self._tray_thread.start()
        except Exception:
            self.log_runtime_error('Falha ao iniciar bandeja')
            self.tray = None

    def _run_tray(self):
        self.log_event('Bandeja iniciada')
        try:
            self.tray.run()
        except BaseException:
            self.log_runtime_error('Falha no loop da bandeja')
        finally:
            self.log_event('Loop da bandeja encerrado; exiting=' + str(self.exiting))

    def log_event(self, msg):
        try:
            path = self.settings_path().parent / 'gravador_runtime.log'
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a', encoding='utf-8') as f:
                f.write(f'[{datetime.now().isoformat()}] {msg}\n')
        except Exception:
            pass

    def _drain_ui(self):
        if self.exiting:
            return
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        except Exception:
            self.log_runtime_error('Falha no processamento de eventos da interface')
        finally:
            if not self.exiting:
                self.root.after(100, self._drain_ui)

    def _tray_tick(self):
        """Atualiza a bandeja sem deixar uma falha de pystray derrubar o Tk."""
        if self.exiting:
            return
        try:
            self.blink = not self.blink
            color = ('#16a34a' if self.phase == 'ready' else
                     '#dc2626' if self.phase == 'recording' else
                     '#eab308' if self.blink else '#666666')
            if self.tray is not None:
                self.tray.icon = self.tray_image(color)
                self.tray.title = {'ready': 'Pronto', 'recording': 'Gravando',
                                   'processing': 'Gerando legendas'}.get(self.phase, 'Pronto')
                # Atualiza o estado dos itens apenas quando muda a fase.
                if self.phase != self._tray_last_phase:
                    self.tray.update_menu()
                    self._tray_last_phase = self.phase
            self._tray_failures = 0
        except Exception:
            self._tray_failures += 1
            self.log_runtime_error('Falha ao atualizar bandeja')
        finally:
            if not self.exiting:
                self.root.after(500, self._tray_tick)

    def log_runtime_error(self, context):
        try:
            path = self.settings_path().parent / 'gravador_runtime.log'
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a', encoding='utf-8') as f:
                f.write(f'\n[{datetime.now().isoformat()}] {context}\n{traceback.format_exc()}\n')
        except Exception:
            pass

    def _tk_exception(self, exc_type, exc_value, exc_tb):
        try:
            path = self.settings_path().parent / 'gravador_runtime.log'
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a', encoding='utf-8') as f:
                f.write(f'\n[{datetime.now().isoformat()}] Excecao Tkinter\n')
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        except Exception:
            pass

    def set_phase(self, phase):
        old = self.phase
        self.phase = phase
        if old != phase:
            self.log_event(f'Estado: {old} -> {phase}')
        # Menu deve refletir a fase imediatamente, sem esperar abrir a janela.
        if self.tray is not None:
            try:
                self.tray.update_menu()
                self._tray_last_phase = phase
            except Exception:
                self.log_runtime_error('Falha ao atualizar menu por fase')
        if phase == 'ready':
            self.elapsed.set('00:00:00')
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.import_btn.config(state='normal')
        elif phase == 'processing':
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='disabled')
            self.import_btn.config(state='disabled')

    def hide_window(self):
        self.save_settings()
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def open_output(self):
        folder = Path(self.output.get())
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))

    def exit_program(self):
        if self.phase != 'ready' or self.partial_busy.is_set():
            messagebox.showwarning('Processamento ativo', 'Pare a gravação e aguarde a transcrição antes de sair.')
            return
        self.save_settings()
        self.log_event('Saida normal solicitada')
        self.exiting = True
        if self.tray:
            self.tray.stop()
        self.root.destroy()

    def force_exit(self):
        """Saída emergencial: interrompe também threads presas no Whisper."""
        if not messagebox.askyesno(
            'Forçar encerramento',
            'Encerrar o gravador imediatamente?\n\n'
            'A transcrição em andamento será perdida. Arquivos já salvos permanecem.\n'
            'Se o OBS estiver gravando, pare a gravação diretamente nele.\n\n'
            'Deseja continuar?', icon='warning'):
            return
        try:
            self.save_settings()
        except Exception:
            pass
        # os._exit termina inclusive threads bloqueadas em bibliotecas nativas.
        # Não aciona o OBS, para evitar encerramento acidental da gravação de vídeo.
        self.log_event('Encerramento forcado solicitado')
        os._exit(2)

    def choose(self):
        path = filedialog.askdirectory(initialdir=self.output.get())
        if path:
            self.output.set(path)

    def ui(self, fn):
        if not self.exiting:
            self._ui_queue.put(fn)

    def set_status(self, value):
        self.ui(lambda: self.status.set(value))

    def log_error(self):
        try:
            folder = Path(self.capture_output)
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / 'gravador_erros.log').open('a', encoding='utf-8') as f:
                f.write(f'\n[{datetime.now().isoformat()}]\n{traceback.format_exc()}\n')
        except Exception:
            pass

    def start(self):
        if self.phase != 'ready':
            return
        if self.worker is not None and self.worker.is_alive():
            messagebox.showinfo('Aguarde', 'A tarefa anterior ainda está em andamento.')
            return
        if self.partial_busy.is_set():
            messagebox.showinfo('Aguarde', 'A transcrição parcial anterior ainda está em andamento.')
            return
        self.save_settings()
        self.capture_source = self.source.get()
        self.capture_mode = self.mode.get()
        self.capture_model = self.model.get()
        self.capture_language = self.language.get()
        self.capture_output = self.output.get()
        self.obs_client = None
        self.obs_started = False
        self.obs_video_mode = False
        self.obs_video_path = None
        self.obs_start_time = None
        self.audio_start_time = None
        self.srt_offset = 0.0
        if self.use_obs.get():
            try:
                import obsws_python as obsws
                client = obsws.ReqClient(host=self.obs_host.get().strip() or 'localhost',
                                         port=int(self.obs_port.get()), password=self.obs_password.get(), timeout=5)
                if client.get_record_status().output_active:
                    messagebox.showwarning('OBS já gravando', 'Pare a gravação existente no OBS antes de iniciar.')
                    return
                client.start_record()
                self.obs_start_time = time.monotonic()
                self.obs_client = client
                self.obs_started = True
                self.obs_video_mode = True
                self.log_event('OBS iniciado; captura WASAPI paralela DESATIVADA')
            except Exception as exc:
                if not messagebox.askyesno('OBS indisponível',
                        f'Não foi possível iniciar o OBS:\n{exc}\n\nGravar somente áudio + legendas?'):
                    return
        self.running = True
        self.set_phase('recording')
        self.started = time.monotonic()
        self.name = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        self.start_btn.config(state='disabled')
        self.import_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        if self.obs_video_mode:
            self.worker = None  # OBS é a única fonte; transcrição começa ao parar.
            self.status.set('OBS gravando vídeo e áudio. A legenda será gerada ao parar.')
        else:
            with self.frames_lock:
                self.frames = []
            self.worker = threading.Thread(target=self.capture, name='AudioCapture', daemon=True)
            self.worker.start()
        self.tick()

    def tick(self):
        if self.running:
            n = int(time.monotonic() - self.started)
            self.elapsed.set(f'{n//3600:02}:{n//60%60:02}:{n%60:02}')
            self.root.after(500, self.tick)

    def stop_obs(self):
        """Retorna caminho real informado pelo OBS (sem adivinhar o nome)."""
        if not (self.obs_started and self.obs_client):
            return None
        try:
            response = self.obs_client.stop_record()
            video_path = getattr(response, 'output_path', None)
            if not video_path:
                raise RuntimeError('OBS não retornou output_path ao parar a gravação.')
            self.obs_video_path = str(Path(video_path))
            self.name = Path(video_path).stem
            self.log_event(f'OBS finalizado: {self.obs_video_path}')
            return self.obs_video_path
        finally:
            self.obs_started = False
            self.obs_client = None

    def stop(self):
        if self.phase != 'recording':
            return
        self.set_phase('processing')
        self.stop_btn.config(state='disabled')
        self.running = False
        if self.obs_video_mode:
            self.status.set('Finalizando vídeo no OBS...')
            try:
                video_path = self.stop_obs()
            except Exception as exc:
                self.log_error()
                self.status.set(f'Falha ao finalizar OBS: {exc}. Confira o vídeo no OBS.')
                self._finish_capture()
                return
            self.worker = threading.Thread(target=self.transcribe_obs_video,
                                           args=(video_path, self.capture_model, self.capture_language),
                                           name='OBSWhisper', daemon=True)
            self.worker.start()
        else:
            self.status.set('Finalizando captura de áudio local...')

    def transcribe_obs_video(self, video_path, model_name, language):
        try:
            path = Path(video_path)
            if not path.is_file():
                raise FileNotFoundError(f'Vídeo do OBS não encontrado: {path}')
            if path.stat().st_size == 0:
                raise RuntimeError('O vídeo do OBS está vazio.')
            self.log_event(f'Iniciando transcrição do vídeo: {path.name}')
            self.transcribe(str(path), False, model_name, language, 0)
        except Exception as exc:
            self.log_error()
            self.set_status(f'Erro ao processar vídeo OBS: {exc}')
        finally:
            self.ui(self._finish_capture)

    @staticmethod
    def find_devices(pa, source):
        """PyAudioWPatch: o loopback corresponde ao dispositivo de saída padrão."""
        loopback = None
        mic = None
        if source != 'Microfone':
            default_out = pa.get_default_wasapi_loopback()
            loopback = default_out
            if loopback is None:
                raise RuntimeError('Não foi encontrado dispositivo WASAPI Loopback padrão.')
        if source != 'Áudio do PC':
            mic = pa.get_default_input_device_info()
        return loopback, mic

    def capture(self):
        pa = None
        streams = []
        try:
            import pyaudiowpatch as pyaudio
            pa = pyaudio.PyAudio()
            loopback, mic = self.find_devices(pa, self.capture_source)
            devices = [('pc', loopback), ('mic', mic)]
            chunks = {'pc': [], 'mic': []}
            starts = {}
            lock = threading.Lock()
            errors = queue.Queue()
            threads = []
            active = [(name, device) for name, device in devices if device is not None]
            for name, device in active:
                channels = int(device['maxInputChannels'])
                if channels < 1:
                    raise RuntimeError(f'Dispositivo {name} sem canais de entrada.')
                # Usamos a taxa nativa do dispositivo para evitar falhas WASAPI.
                rate = int(device['defaultSampleRate'])
                stream = pa.open(format=pyaudio.paInt16, channels=channels, rate=rate,
                                 input=True, input_device_index=int(device['index']),
                                 frames_per_buffer=CHUNK, start=False)
                streams.append((name, stream, channels, rate))

            def reader(name, stream, channels, rate):
                try:
                    with lock:
                        starts[name] = time.monotonic()
                    stream.start_stream()
                    while self.running:
                        raw = stream.read(CHUNK, exception_on_overflow=False)
                        samples = np.frombuffer(raw, dtype='<i2').reshape(-1, channels).astype(np.float32).mean(axis=1) / 32768.0
                        with lock:
                            chunks[name].append(samples)
                except Exception:
                    errors.put((name, traceback.format_exc()))
                    self.running = False

            for name, stream, channels, rate in streams:
                t = threading.Thread(target=reader, args=(name, stream, channels, rate), daemon=True)
                t.start()
                threads.append(t)
            self.audio_start_time = min(starts.values()) if starts else time.monotonic()
            if self.obs_start_time is not None:
                self.srt_offset = max(0.0, self.audio_start_time - self.obs_start_time)
            last_partial = time.monotonic()
            while self.running:
                if not errors.empty():
                    break
                time.sleep(0.15)
                if self.capture_mode == 'Ao vivo' and time.monotonic() - last_partial >= 15 and not self.partial_busy.is_set():
                    last_partial = time.monotonic()
                    audio = self.mix_snapshot(chunks, starts, streams, lock)
                    if audio.size:
                        path = self.write_wav(audio, partial=True)
                        self.partial_busy.set()
                        threading.Thread(target=self.partial_transcribe, args=(path,), daemon=True).start()
            # Nunca fechar PortAudio enquanto uma thread ainda executa stream.read().
            # O timeout antigo permitia fechar streams ativos e causava access violation.
            for t in threads:
                t.join(timeout=2)
                if t.is_alive():
                    self.log_event(f'Aguardando finalizacao segura da thread {t.name}')
                    t.join()  # Bloqueia ate o reader sair; nao libera stream prematuramente.
            # Guardar os metadados de cada fonte antes de liberar os streams.
            # mix_snapshot precisa dos nomes e taxas para montar o WAV.
            stream_metadata = [(name, None, channels, rate) for name, _, channels, rate in streams]
            # A captura terminou: liberar o dispositivo ANTES de iniciar o Whisper.
            for _, stream, _, _ in streams:
                if stream.is_active():
                    stream.stop_stream()
                stream.close()
            streams.clear()
            pa.terminate()
            pa = None
            self.log_event('Threads de audio encerradas e PortAudio liberado')
            if not errors.empty():
                name, detail = errors.get()
                raise RuntimeError(f'Falha ao ler {name}:\n{detail}')
            audio = self.mix_snapshot(chunks, starts, stream_metadata, lock)
            if not audio.size:
                raise RuntimeError('Nenhum áudio capturado. Verifique os dispositivos de entrada/saída.')
            path = self.write_wav(audio)
            self.set_status('Áudio salvo. Gerando SRT e TXT...')
            self.transcribe(path, False, self.capture_model, self.capture_language, self.srt_offset)
        except Exception as e:
            self.log_error()
            self.set_status(f'Erro: {e}. Consulte gravador_erros.log na pasta de saída.')
        finally:
            self.running = False
            # Protecao: em erro, nunca liberar stream se algum reader ainda o utiliza.
            if streams:
                alive = [t for t in locals().get('threads', []) if t.is_alive()]
                if alive:
                    self.log_event('ERRO: reader ainda ativo; recursos mantidos para evitar crash nativo')
                else:
                    for _, stream, _, _ in streams:
                        try:
                            if stream.is_active():
                                stream.stop_stream()
                            stream.close()
                        except Exception:
                            pass
                    if pa is not None:
                        pa.terminate()
            elif pa is not None:
                pa.terminate()
            if self.obs_started:
                self.stop_obs()
            self.ui(self._finish_capture)

    def _finish_capture(self):
        if self.exiting:
            return
        if self.partial_busy.is_set():
            self.root.after(250, self._finish_capture)
        else:
            self.running = False
            self.set_phase('ready')
            self.log_event('Transcricao concluida; aplicativo permanece residente')
            # Apenas volta ao estado de espera. NUNCA chama stop() do tray,
            # destroy() do Tk ou os._exit() no fim da transcricao.

    @staticmethod
    def mix_snapshot(chunks, starts, streams, lock):
        with lock:
            data = {k: np.concatenate(v) if v else np.empty(0, dtype=np.float32) for k, v in chunks.items()}
            origins = dict(starts)
        if not origins:
            return np.empty(0, dtype=np.float32)
        t0 = min(origins.values())
        tracks = []
        for name, _, _, rate in streams:
            x = data[name]
            if not x.size or name not in origins:
                continue
            length = int(round(len(x) * RATE / rate))
            if length < 1:
                continue
            # Reamostragem linear; suficiente para fala e legendagem.
            x = np.interp(np.arange(length) * rate / RATE, np.arange(len(x)), x).astype(np.float32)
            offset = max(0, round((origins[name] - t0) * RATE))
            tracks.append((offset, x))
        if not tracks:
            return np.empty(0, dtype=np.float32)
        result = np.zeros(max(offset + len(x) for offset, x in tracks), dtype=np.float32)
        gain = 0.7 if len(tracks) > 1 else 1.0
        for offset, x in tracks:
            result[offset:offset + len(x)] += gain * x
        return np.clip(result, -1, 1)

    def write_wav(self, audio, partial=False):
        folder = Path(self.capture_output)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (self.name + ('_parcial' if partial else '') + '.wav')
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes((audio * 32767).astype('<i2').tobytes())
        return str(path)

    def partial_transcribe(self, path):
        try:
            self.transcribe(path, True, self.capture_model, self.capture_language, 0)
        finally:
            self.partial_busy.clear()

    @staticmethod
    def stamp(seconds):
        ms = max(0, round(seconds * 1000))
        return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

    def transcribe(self, path, partial=False, model_name='small', language='pt', offset=0):
        try:
            from faster_whisper import WhisperModel
            self.set_status(f'Carregando modelo Whisper {model_name}...') if not partial else None
            model = WhisperModel(model_name, device='cpu', compute_type='int8', cpu_threads=6, num_workers=1)
            self.set_status('Transcrevendo áudio...') if not partial else None
            # WAV PCM gerado pelo gravador: entregar amostras diretamente ao Whisper,
            # evitando a incompatibilidade entre PyAV e faster-whisper.
            audio_input = path
            if Path(path).suffix.lower() != '.wav':
                # Compatibilidade com PyAV que não aceita metadata_errors.
                # A versão anterior já precisava deste ajuste para importar MP4.
                import av
                if not getattr(av.open, '_gravador_compat', False):
                    original_av_open = av.open
                    def compatible_av_open(*args, **kwargs):
                        kwargs.pop('metadata_errors', None)
                        return original_av_open(*args, **kwargs)
                    compatible_av_open._gravador_compat = True
                    av.open = compatible_av_open
            if Path(path).suffix.lower() == '.wav':
                with wave.open(str(path), 'rb') as wav_file:
                    if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2 or wav_file.getframerate() != RATE or wav_file.getcomptype() != 'NONE':
                        raise ValueError('WAV deve ser PCM mono, 16 bits, 16000 Hz. Para outros formatos, importe áudio/vídeo com decodificação PyAV corrigida.')
                    audio_input = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype='<i2').astype(np.float32) / 32768.0
            segments, _ = model.transcribe(audio_input, language=None if language == 'auto' else language, vad_filter=True, beam_size=5, word_timestamps=False, condition_on_previous_text=True)
            base = Path(path).with_suffix('')
            srt, txt = [], []
            for i, seg in enumerate(segments, 1):
                content = seg.text.strip()
                srt.append(f'{i}\n{self.stamp(seg.start + offset)} --> {self.stamp(seg.end + offset)}\n{content}\n')
                txt.append(content)
            self.set_status('Salvando SRT e TXT...') if not partial else None
            base.with_suffix('.srt').write_text('\n'.join(srt), encoding='utf-8-sig')
            base.with_suffix('.txt').write_text('\n'.join(txt), encoding='utf-8-sig')
            if not partial:
                self.set_status(f'Concluído! SRT e TXT em: {base.parent}')
            else:
                self.set_status('Legenda parcial atualizada (a gravação continua).')
        except Exception:
            self.log_error()
            self.set_status('Erro na transcrição. Consulte gravador_erros.log.')

    def import_file(self):
        if self.worker is not None and self.worker.is_alive():
            messagebox.showinfo('Aguarde', 'A gravação anterior ainda está em andamento.')
            return
        path = filedialog.askopenfilename(filetypes=[('Áudio e vídeo', '*.wav *.mp3 *.m4a *.mp4 *.mkv *.flac'), ('Todos', '*.*')])
        if path:
            self.set_phase('processing')
            self.capture_output = self.output.get()
            self.start_btn.config(state='disabled')
            self.import_btn.config(state='disabled')
            self.set_status('Transcrevendo arquivo importado...')
            def job():
                try:
                    self.transcribe(path, False, self.model.get(), self.language.get(), 0)
                finally:
                    self.ui(lambda: self.set_phase('ready'))
            self.worker = threading.Thread(target=job, daemon=True)
            self.worker.start()

    def close(self):
        self.hide_window()


if __name__ == '__main__':
    runtime_dir = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local')) / 'GravadorLegendasOBS'
    runtime_dir.mkdir(parents=True, exist_ok=True)
    fault_file = (runtime_dir / 'gravador_fatal.log').open('a', encoding='utf-8')
    faulthandler.enable(file=fault_file, all_threads=True)
    def _uncaught_thread(args):
        with (runtime_dir / 'gravador_runtime.log').open('a', encoding='utf-8') as f:
            f.write(f'[{datetime.now().isoformat()}] Falha thread {args.thread.name}\n')
            traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=f)
    threading.excepthook = _uncaught_thread
    atexit.register(lambda: (runtime_dir / 'gravador_runtime.log').open('a', encoding='utf-8').write(f'[{datetime.now().isoformat()}] Processo Python encerrado\n'))
    root = tk.Tk()
    app = App(root)
    root.mainloop()
    app.log_event('Tk mainloop terminou')
