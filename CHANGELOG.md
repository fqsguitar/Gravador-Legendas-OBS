# Changelog / Histórico de versões

## [v1.1.0] — 2026-11-03 (release preparation)

**English**
- Redesigned standalone WASAPI capture with continuous disk recording and nonblocking callbacks.
- PC audio, microphone, or both, with mixing after recording.
- Transcription only after stopping; redundant transcription dropdown removed.
- Temporary WAV deleted after successful SRT/TXT generation, preserved on failure.
- OBS video workflow retained.

**Português (Brasil)**
- Captura WASAPI independente reformulada, com gravação contínua em disco e callbacks sem leitura bloqueante.
- Áudio do PC, microfone ou ambos, com mistura após a gravação.
- Transcrição apenas após parar; opção redundante de transcrição removida.
- WAV temporário apagado após gerar SRT/TXT com sucesso, preservado em caso de falha.
- Fluxo de vídeo do OBS preservado.


## [v1.0.0] — 2026-10-30

**English**
- Initial public Windows release.
- OBS Studio WebSocket recording control and system tray integration.
- Transcription directly from the finalized OBS video with faster-whisper.
- SRT timestamps and TXT transcript named after the recording.
- Optional Windows startup minimized to tray.
- English and Brazilian Portuguese documentation.
- Standalone audio-only capture remains **experimental**.

**Português (Brasil)**
- Primeira versão pública para Windows.
- Controle de gravação do OBS via WebSocket e integração com a bandeja.
- Transcrição diretamente do vídeo final do OBS com faster-whisper.
- SRT com minutagem e TXT com o mesmo nome-base da gravação.
- Inicialização opcional com o Windows, minimizado na bandeja.
- Documentação em inglês e português brasileiro.
- Captura independente somente de áudio permanece **experimental**.

[v1.0.0]: https://github.com/fqsguitar/Gravador-Legendas-OBS/releases/tag/v1.0.0
