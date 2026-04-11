# Media Player (wx + VLC)

Protótipo inicial de um tocador de mídia em **Python**, com interface em **wxPython** e engine de reprodução do **VLC** via `python-vlc`.

## Requisitos

- Python 3.10+
- VLC Media Player instalado no sistema (fornece `libvlc`)

## Dependências Python

As dependências do projeto estão em `requirements.txt`:

- `wxPython`
- `python-vlc`
- `accessible-output2` (anúncios por leitores de tela quando disponíveis)

## Executar

1. Crie e ative um ambiente virtual.
2. Instale as dependências de `requirements.txt`.
3. Execute o arquivo `src/main.py`.

## Funcionalidades já implementadas

- Inicializa sem mídia tocando
- Layout limpo: painel de vídeo em abas com barra de tempo discreta abaixo (sem botões e sem slider interativo)
- Barra de tempo visual com tempo atual/total abaixo da área de vídeo
- Menu `Arquivo` (acessível com `ALT`) com:
	- Nova playlist
	- Abrir arquivo
	- Abrir pasta em modo navegador
	- Abrir playlist `.m3u` / `.m3u8`
	- Salvar playlist atual
	- Recentes (arquivos, pastas e playlists)
	- Sair
- Menu `Reprodução` com:
	- Faixa anterior
	- Play/Pause
	- Stop
	- Próxima faixa
	- Embaralhar
	- Modo de repetição
	- Anunciar tempo atual/total
	- Anunciar volume atual
	- Anunciar status completo
	- Fechar mídia atual ou aba vazia
- Menu `Exibir` com alternância de foco entre o painel lateral de itens e o player
- Menu `Abas` com navegação entre playlists abertas
- Menu `Configurações` com tela de preferências persistentes
- Abrir arquivo de áudio/vídeo
- Abrir vários arquivos de uma vez na mesma playlist
- Abrir pasta em uma aba com painel lateral fixo, subpastas e mídias suportadas
- Navegar em pastas com `Enter` para entrar e `Backspace` para voltar
- Pré-escutar automaticamente arquivos de mídia ao mudar a seleção no navegador da aba, com resposta mais rápida e sem anúncio completo a cada item
- No modo explorador de pastas, o arquivo selecionado não avança automaticamente para os demais itens da pasta ao terminar
- Abrir múltiplas playlists/seleções em abas diferentes
- Salvar e reabrir playlists em `.m3u` / `.m3u8`
- Histórico de arquivos, pastas e playlists recentes no menu `Arquivo`
- Restaurar abas, item atual, posição e volume ao abrir o app novamente
- Salvar preferências do usuário em arquivo separado (`settings.json`)
- Shuffle e repetição configuráveis por aba/playlist
- Controle por teclado:
	- `Espaço` para play/pause
	- `Ctrl+T` para criar uma nova playlist vazia
	- `E` para ativar/desativar embaralhamento na playlist atual
	- `R` para alternar repetição: desligado / faixa / playlist
	- `T` para anunciar tempo atual e duração total
	- `V` para anunciar o volume atual
	- `S` para anunciar status completo do player
	- `Alt+↑` para mover o item atual uma posição para cima na playlist
	- `Alt+↓` para mover o item atual uma posição para baixo na playlist
	- `Alt+←` para faixa anterior
	- `Alt+→` para próxima faixa
	- `Alt+Home` para ir ao primeiro item da playlist
	- `Alt+End` para ir ao último item da playlist
	- `Ctrl+PageUp` para faixa anterior
	- `Ctrl+PageDown` para próxima faixa
	- `Ctrl+W` para fechar a mídia atual ou, se a aba estiver vazia, fechar a aba
	- `F6` para alternar o foco entre o painel lateral de itens e o controle do player
	- `Enter` no painel lateral da aba para entrar em pastas ou tocar o arquivo selecionado
	- `Backspace` no painel lateral da aba para voltar à pasta anterior
	- `Ctrl+Shift+P` para abrir uma playlist
	- `Ctrl+Shift+S` para salvar a playlist atual
	- `Ctrl+Tab` para ir para a próxima aba
	- `Ctrl+Shift+Tab` para voltar para a aba anterior
	- `Ctrl+,` para abrir preferências
	- `Esc` para fechar preferências ou sair do painel lateral e voltar ao player
	- `Home` para ir ao início da mídia
	- `End` para ir ao fim da mídia
	- `←` / `→` para retroceder/avançar
	- `↑` / `↓` para volume
	- `Tab` não muda foco para o output nativo do VLC (evita anúncio "VLC (Direct3D11 output)" em leitores de tela)
- Renderização de vídeo embutida na janela wx
- Atualização visual contínua do progresso da mídia com porcentagem quando a duração está disponível
- Anúncios de acessibilidade por fala:
	- Ao abrir o app: "Nenhuma mídia tocando agora."
	- Ao restaurar a sessão anterior
	- Ao trocar de aba: nome da aba e item atual
	- Ao mudar shuffle/repetição
	- Ao anunciar tempo atual/total sob demanda
	- Ao anunciar o volume atual sob demanda
	- Ao anunciar status completo sob demanda
	- Ao tocar/pausar/parar mídia
	- Ao finalizar uma mídia ou playlist
	- Ao alternar entre o painel lateral de itens e o controle do player

> Observação: os anúncios priorizam saída de leitor de tela (ex.: NVDA/JAWS) e evitam fallback de voz de sistema quando não há leitor ativo.

## Estrutura atual do código

- `src/main.py` — entrypoint enxuto do app
- `src/player/app.py` — bootstrap da aplicação wx
- `src/player/frame.py` — janela principal + integração com VLC + atalhos
- `src/player/media.py` — descoberta de arquivos de mídia e entradas do navegador de pastas
- `src/player/playlist_io.py` — leitura e escrita de playlists `.m3u` / `.m3u8`
- `src/player/playlist_browser.py` — painel lateral acessível da aba atual (playlist ou pasta)
- `src/player/playlists.py` — estado das playlists e títulos de abas
- `src/player/preferences_dialog.py` — janela de preferências
- `src/player/session.py` — persistência de abas, posição e volume
- `src/player/settings.py` — persistência de preferências do usuário
- `src/player/constants.py` — constantes e configurações do player

## Próximos passos sugeridos

- Seleção múltipla e reordenação em lote na lista acessível
