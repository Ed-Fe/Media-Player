# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Novo diálogo **Abrir mídia, playlist ou pasta** para abrir arquivos de mídia, playlists `.m3u/.m3u8`, links de playlist e pastas a partir de um único fluxo.
- Suporte a abrir playlists remotas `.m3u/.m3u8` por URL, preservando entradas remotas e resolvendo caminhos relativos a partir da origem da playlist.
- Configuração de **crossfade** nas Preferências, com suporte a sobrepor automaticamente faixas de áudio e opção `0` para desativar o recurso.
- Suporte inicial ao **YouTube Music** com autenticação por navegador, importação de `browser.json`/JSON de cookies/`cookies.txt`, abertura de playlists e mixes da conta e resolução de streams com `yt-dlp`.
- Botão **Aplicar em todas as abas** no Equalizador para copiar o preset e o estado atual para todas as abas de mídia abertas.
- Preferência **Desativar saída de vídeo (tocar só o áudio)**, ativada por padrão, para evitar janelas externas do VLC quando o usuário quer reproduzir vídeos só com áudio.

### Changed
- O menu **Arquivo** passou a concentrar a abertura geral em uma única ação, mantendo atalhos específicos para abrir arquivos locais e pastas no navegador.
- O atalho `Ctrl+O` agora aceita tanto arquivos de mídia quanto uma playlist local `.m3u/.m3u8`, usando o mesmo conjunto de tipos do seletor **Arquivo...** do diálogo unificado.
- Pastas locais agora podem ser abertas tanto no navegador quanto como playlists estáticas carregadas de forma assíncrona.
- A reprodução passou a usar players VLC dedicados por faixa no crossfade, com tratamento específico para o backend de áudio do Windows e melhor folga de inicialização entre músicas.
- O submenu **YouTube Music** passou a atualizar o estado da conexão, permitir desconectar a conta salva e carregar playlists/mixes sem bloquear a interface.
- O código do player foi reorganizado por responsabilidades em pacotes como `frames/`, `library/`, `playlists/`, `preferences/`, `equalizer/`, `update/` e `youtube_music/`, com divisão adicional dos fluxos de biblioteca em mixins menores.
- A área do player agora mostra uma mensagem clara quando a saída de vídeo está desativada e a mídia está tocando em modo áudio apenas.
- Abas restauradas do YouTube Music agora tentam recuperar novamente os rótulos corretos das faixas após reconectar a conta.

### Fixed
- Transições de áudio com menos cortes e sem retorno repentino de volume no fim do crossfade ao avançar entre faixas compatíveis.
- Próxima/anterior e crossfade do YouTube Music ficaram mais estáveis com cache/prefetch de streams e fallback automático para reprodução normal quando a próxima faixa demora a resolver.
- Operações em segundo plano do YouTube Music agora têm timeout defensivo para evitar deixar o app preso em estado ocupado.

### Notes
- Esta versão inclui uma refatoração estrutural grande. Apesar da validação rápida e das verificações feitas durante o desenvolvimento, ainda podem aparecer problemas ou regressões em fluxos menos exercitados.
- Se você encontrar qualquer comportamento estranho, travamento, atalho quebrado, regressão de acessibilidade ou falha ao abrir mídia/playlist/pasta, por favor reporte um bug com o máximo de detalhes possível.

## [0.3.0] - 2026-04-12

### Added
- Atalho `Ctrl+Shift+W` para fechar a aba ou playlist atual diretamente.
- Navegação por digitação de letras e números no navegador de itens para localizar arquivos e faixas mais rápido.
- Carregamento assíncrono de playlists e do explorador de pastas, com mensagens de carregamento enquanto a biblioteca é preparada.

### Changed
- O navegador de itens passou a usar uma lista virtual compartilhada por playlists e pastas para lidar melhor com bibliotecas grandes.
- A leitura inicial de pastas agora reaproveita uma única varredura para montar entradas do navegador e a lista de mídias da aba.
- O explorador de pastas não mostra mais um marcador visual de reprodução ao lado do arquivo em prévia.
- O aplicativo passou a se chamar **KeyTune** na interface e na documentação principal, sem o sufixo técnico.
- Inclusão de mnemônicos com `&` em botões e opções de Preferências, Equalizador, Ajuda rápida de atalhos e diálogos de atualização para melhorar a navegação por teclado.

### Fixed
- Redução das travadas ao abrir pastas muito grandes, transferindo a carga pesada para um worker e aliviando a primeira pintura do navegador.
- Redução do custo de atualização de playlists grandes com cache de índices, reaproveitamento de rótulos e refresh incremental da lista.
- Restauração do volume salvo ao abrir o app com sessão recuperada, aplicando corretamente o nível anterior já no início da reprodução.
- Preservação da posição atual do áudio ao entrar e sair da aba do equalizador, sem voltar para o tempo em que a aba foi aberta.
- Retorno ao modo de foco correto ao fechar o equalizador e eliminação do corte no áudio causado pelo recarregamento desnecessário da mesma mídia.

## [0.2.0] - 2026-04-11

### Added
- Verificação automática de atualizações ao iniciar a versão empacotada do Windows.
- Visualização das notas da release antes de confirmar o download da atualização.
- Diálogo de download com barra de progresso para baixar novas releases antes de instalar.
- Atualizador externo para aplicar o ZIP da release sem sobrescrever arquivos em uso.
- Geração e publicação do arquivo `MediaPlayer-windows.zip.sha256` nas releases.
- Script local para gerar a release Windows e roteiro documentado para testar o atualizador ponta a ponta.

### Changed
- Workflow de release do Windows para incluir `MediaPlayerUpdater.exe` no pacote publicado.

### Fixed
- 

## [0.1.0] - 2026-04-11

### Added
- Windows release workflow (`.github/workflows/release-windows.yml`) to build and publish a ZIP package.
- Bundled VLC runtime in release artifacts (`dist/MediaPlayer/vlc`) so users can run without preinstalled VLC.
- Runtime bootstrap (`src/player/vlc_runtime.py`) to detect local VLC folder and configure DLL/plugin paths on Windows.

### Changed
- Startup flow in `src/main.py` to initialize bundled VLC runtime before loading the app.
- `README.md` with release packaging instructions for GitHub Actions.
- `.gitignore` to ignore local packaging outputs (`build/`, `dist/`, `*.zip`).
