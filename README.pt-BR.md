# Gravador de Legendas + OBS Studio

**[Baixar versão Windows v1.0.0](https://github.com/fqsguitar/Gravador-Legendas-OBS/releases/tag/v1.0.0)** · [Histórico](CHANGELOG.md) · [Como contribuir](CONTRIBUTING.md) · [Segurança](SECURITY.md)

[English](README.md) | **Português (Brasil)**

Aplicativo para Windows que controla gravações do **OBS Studio** e gera automaticamente legendas **SRT com minutagem** e transcrições **TXT** a partir do vídeo final, usando **faster-whisper localmente**.

> **O OBS Studio NÃO acompanha este projeto. É obrigatório instalar e configurar o OBS separadamente em https://obsproject.com/. O OBS precisa estar aberto para gravar vídeo.**

## Recursos
- Inicia e para o OBS via WebSocket, pela janela ou bandeja do Windows.
- Transcreve diretamente o MP4/MKV final do OBS, sem segunda captura WASAPI.
- Salva SRT/TXT com o mesmo nome-base do vídeo e na mesma pasta.
- Bandeja: **verde** pronto, **vermelho** gravando, **amarelo piscando** transcrevendo.
- Permanece aberto após a transcrição, zera o cronômetro e permite novas gravações.
- Configurações persistentes e senha WebSocket protegida com DPAPI do Windows.
- Inicialização automática opcional com o Windows.
- Modo somente áudio independente **experimental**.

## Requisitos
Windows 10/11, OBS Studio 28 ou superior instalado à parte, Python com comando `py` para compilar e internet inicialmente para baixar dependências/modelo Whisper. Respeite as autorizações e políticas de gravação.

## 1. Instalação e configuração do OBS
1. Baixe o OBS em **https://obsproject.com/** e instale. O `compilar_obs.bat` **não instala o OBS**.
2. Abra o OBS, crie uma cena e configure a captura da tela ou janela.
3. Em **Configurações → Áudio**, configure **Áudio do desktop** e **Microfone/áudio auxiliar** conforme necessário. Confira os medidores no mixer.
4. Em **Configurações → Saída → Gravação**, escolha pasta e formato (MP4 ou MKV).
5. Em **Ferramentas → Configurações do servidor WebSocket** (em inglês, **Tools → WebSocket Server Settings**), habilite o servidor.
6. Use a porta **4455**, ative a autenticação e configure uma senha. Clique em Aplicar/OK.
7. **Deixe o OBS aberto.** Não precisa iniciar a gravação manualmente nele: o Python controla via WebSocket.

Não exponha a porta WebSocket à internet; para programas no mesmo PC, use `localhost`.

## 2. Compilar e abrir
1. Instale Python e confira `py --version` no PowerShell.
2. Baixe o repositório em **Code → Download ZIP** e extraia.
3. Execute `compilar_obs.bat`. Ele instala dependências Python e compila com PyInstaller.
4. Abra `dist\GravadorLegendasOBS.exe`. Antes de ativar a inicialização automática, mova o EXE para uma pasta definitiva, como `%LOCALAPPDATA%\Programs\GravadorLegendasOBS\`.

**O BAT não instala o OBS nem habilita a inicialização automática.** Em computadores corporativos, respeite as políticas de TI.

## 3. Gravar e gerar legendas
Marque **Gravar vídeo no OBS**, configure **Host** `localhost`, **Porta** `4455` e a senha do WebSocket. Selecione modelo Whisper **small** e idioma desejado.

Clique em **Iniciar gravação** na janela ou na bandeja. O OBS grava o vídeo e as fontes de áudio configuradas nele. Clique em **Parar e salvar** e aguarde a transcrição. No modo OBS, a transcrição é **após a gravação**, mesmo que a interface indique Ao vivo.

```text
2026-10-28 16-40-53.mp4
2026-10-28 16-40-53.srt
2026-10-28 16-40-53.txt
```
A minutagem do SRT acompanha o próprio vídeo.

## 4. Bandeja do Windows
Ao clicar no X, a janela é ocultada, mas o aplicativo continua na bandeja. Clique com o botão direito no ícone para iniciar/parar, abrir a janela, abrir a pasta ou sair. O encerramento forçado é somente para emergências.

## 5. Iniciar com o Windows — configurar OS DOIS programas
**A. Gravador:** coloque o EXE na pasta definitiva e marque **Iniciar com o Windows (minimizado na bandeja)**. A opção registra a inicialização para o usuário atual. Para desativar, desmarque. Se mover o EXE, desmarque e marque novamente.

**B. OBS Studio:** configure separadamente o OBS para iniciar com o Windows. Uma forma é pressionar **Win+R**, executar `shell:startup` e colocar um atalho do OBS nessa pasta. Se sua versão suportar, use `--minimize-to-tray` para iniciar minimizado. Teste se o OBS abre e se o WebSocket fica disponível após o logon.

**Marcar a caixa do gravador NÃO inicia o OBS automaticamente.** O OBS precisa estar aberto quando você solicitar uma gravação de vídeo.

## 6. Somente áudio — experimental
Desmarcando **Gravar vídeo no OBS**, o programa usa captura local PyAudioWPatch/WASAPI e tenta gerar WAV/SRT/TXT. Esse modo apresentou travamentos na finalização e falhas de captura nos testes. **Não use em reuniões importantes até ser corrigido.**

## 7. Problemas comuns
- **OBS não conecta:** confira se está aberto, WebSocket habilitado, host, porta e senha.
- **Vídeo sem áudio:** confira Áudio do desktop, microfone e medidores no OBS.
- **SRT não aparece:** confirme se o OBS finalizou o vídeo e consulte os logs.
- **Transcrição lenta:** prefira modelo `small`; o primeiro uso pode baixar o modelo.
- **Não inicia com Windows:** confira o caminho do EXE e a inicialização independente do OBS.

## Privacidade e estado
A transcrição roda localmente após baixar o modelo. A senha WebSocket é protegida por DPAPI. Não publique `config.json`, logs, gravações ou transcrições privadas.

**Modo OBS:** validado com gravações consecutivas e retorno à bandeja. **Modo somente áudio:** experimental. Projeto independente, sem afiliação ao OBS Studio. Licença MIT.