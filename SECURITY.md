# Security / Segurança

## English

This app communicates with OBS Studio over WebSocket and transcribes recordings locally.

- Install OBS Studio from https://obsproject.com/ separately.
- Keep OBS WebSocket bound to your local machine when possible; use `localhost`, authentication, and a strong password. Never expose port 4455 to the public internet.
- The app stores the OBS password encrypted with Windows DPAPI for the current user. This does **not** protect an already compromised Windows account.
- Do not upload recordings, subtitles, transcripts, local configuration files, or unredacted logs to public issues.
- Only record meetings when permitted by participants, workplace rules, and applicable law.
- Download binaries from the repository's official Releases page; avoid untrusted repackaged installers.
- To report a security vulnerability, contact the repository owner privately rather than posting credentials or exploit details in a public issue.

## Português (Brasil)

O aplicativo controla o OBS Studio via WebSocket e realiza a transcrição localmente.

- Instale o OBS separadamente pelo site https://obsproject.com/.
- Prefira WebSocket acessível apenas localmente, com host `localhost`, autenticação e senha forte. Não exponha a porta 4455 à internet.
- A senha é criptografada usando DPAPI do Windows para o usuário atual. Isso **não** protege uma conta Windows já comprometida.
- Não publique vídeos, áudios, legendas, transcrições, configurações ou logs sem remover informações sensíveis.
- Grave reuniões apenas quando permitido pelos participantes, políticas da organização e legislação aplicável.
- Baixe executáveis apenas da página oficial de Releases.
- Para vulnerabilidades, contate o mantenedor de forma privada, sem publicar senhas ou detalhes exploráveis em issues públicas.
