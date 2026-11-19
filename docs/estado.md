# Estado do Dashamp

Última tarefa concluída: **F1.9** (teste de uso do player pelo mantenedor).
Próxima: **F2.1** — interface `Fonte`.

## Teste de uso (F1.9)

- O mantenedor usou o player no Eee PC. Único ajuste: som baixo mesmo no volume máximo do player;
  causa e correção no ALSA (ver Decisões, F1.9).
- Tela cheia foi discutida (playlist larga de 400 px, janela principal a ~2,9×, faixas laterais,
  esticar): decidido **manter o layout atual** (2×, centralizado).
- `deploy/run.sh`: o modo `nada` agora espera o `.app` mudar e sai sozinho (antes era um
  `sleep infinity` que o `pkill` do deploy não encerrava, e o app novo não abria).
- O player passa a ser o app do boot (`.app` = `player`).

## Troca de skin e equalizador (F1.8)

- Tecla **K**: próxima skin de `player/skins_teste/*.wsz` (ordem alfabética), sem reiniciar.
  `Player.aplicar_skin` refaz analisador (mantendo as alturas das barras), playlists, janela do
  equalizador e colorkey da região, e limpa o cache de máscaras de região
  (`janela_principal.limpar_caches`), para nada da skin anterior ficar referenciado.
  A skin base fica na memória como reserva (empréstimo de BMPs ausentes); trocar para ela
  reaproveita esse objeto em vez de ler o `.wsz` de novo (ler e decodificar os BMPs da base
  custava ~230 ms no Eee PC; as trocas para ela caíram de ~430 ms para ~105 ms).
- `--ciclo-skins S` troca sozinho a cada S segundos (só para medir).
- Equalizador: `player/janela_eq.py` desenha o `eqmain.bmp` (fundo, título ativo/inativo, ON,
  AUTO, PRESETS, 28 quadros de slider do verde ao vermelho, cursor normal/selecionado, gráfico
  com a curva interpolada e a linha da pré-amp). Tecla **E** alterna a janela de baixo entre
  playlist e equalizador (os botões EQ/PL da principal acendem conforme). Com foco no equalizador
  (Tab): ←/→ escolhem o slider, ↑/↓ ±1 dB (-12..+12), Enter liga/desliga, Backspace zera.
  AUTO e PRESETS são só desenho.
- Áudio: filtro `audioconvert ! equalizer-10bands ! volume ! audiopanorama ! spectrum`
  (gst-plugins-good, já instalado). As bandas do GStreamer são 29 Hz…15 kHz, próximas mas não
  iguais às do Winamp (60 Hz…16 kHz). Pré-amp pelo `volume` (10^(dB/20)). Desligado = ganhos 0 dB,
  e o elemento fica em passthrough. O analisador mostra o som já equalizado (como no Winamp).
- **Aceite no Eee PC**: 46 trocas seguidas (uma a cada 2 s, tocando): **96–277 ms** por troca
  (winamp5_classified ~180 ms, zelda_amp_3 ~160 ms, base ~105 ms); RSS 68,0 MB depois da 1ª e
  depois **71,1–72,6 MB** oscilando sem tendência até a 46ª. O fps médio com uma troca a cada 2 s
  fica em ~27 (cada troca para o laço uns 3–6 quadros); sem trocas continua 30,0.
- CPU do áudio sozinho (MP3 320 kbps): equalizador desligado 23,9%, ligado **31,0%** (+7 pontos).
  Somado ao player (~55%), fica perto de 62%, dentro do orçamento de 70%.
- Testes: 44 passam no Eee PC (4 novos em `testes/test_troca_skin_eq.py`).

## Playlist (F1.7)

- `player/metadados.py`: `carregar_lista(entradas)` aceita arquivos, pastas (recursivas, ordem
  alfabética) e `.m3u`/`.m3u8` (caminhos relativos à lista; `#EXTINF` usado quando falta ID3).
  MP3 lido em Python puro, só o começo do arquivo: ID3v2.3/2.4 (TIT2/TPE1) e duração pelo
  cabeçalho Xing/Info (VBR) ou pelo bitrate do 1º quadro (CBR). Sem GStreamer na carga.
- `player/janela_playlist.py`: moldura do `pledit.bmp` (cantos, título, laterais, base, puxador da
  rolagem) montada uma vez em 1× e ampliada; altura 116 + 29·k. Cores do `pledit.txt` (normal,
  current, normalbg, selectedbg). O texto é desenhado na escala da tela com a fonte padrão do pygame
  (o `pledit.txt` só nomeia uma fonte do sistema, Arial). Linhas em cache; a janela só é redesenhada
  quando lista, cursor, faixa atual, foco ou rolagem mudam.
- Layout em 800×480: principal 2× em cima + playlist 2× (4 linhas) embaixo = 464 px; tecla **L**
  alterna a playlist sozinha e alta (13 linhas). **Tab** troca o foco (título ativo/inativo como no
  Winamp). Na playlist: ↑/↓, PgUp/PgDn, Home/End, Enter. O cursor acompanha a faixa atual.
- MP3s de teste: `python3 scripts/gerar_mp3_teste.py ~/musica/lista50 --lista 50` (50 faixas de
  6–20 s, 128/192/320 kbps, "Faixa NN"; 18 MB; ~5 min no Eee PC).
- **Aceite no Eee PC**: 50 faixas carregadas em **0,71 s a frio** (cache de disco esvaziado; 0,04 s
  com cache); tocando, as faixas 1→2→3→4 avançaram sozinhas nos tempos esperados (13, 33, 45 s).
  30,0 fps, CPU do processo ~49%, RSS 65 MB. Captura conferida. Testes: 40 passam.
- Observação: no intervalo de 5 s em que há troca de faixa o fps médio cai para ~29,2 (o `abrir`
  do GStreamer bloqueia o laço por alguns quadros). Candidato a otimização (trocar de faixa numa
  thread) se incomodar na F1.9.

## Player funcional (F1.6)

- `player/main.py` (`python -m player.main [arquivos/pastas] --skin X --escala 1|2`; `player` no
  `.app`): janela da skin em 2× no centro da tela, ligada ao `MotorAudio`. Tempo nos dígitos,
  letreiro "N. Artista - Título (m:ss)" rolando 1 caractere a cada 0,2 s em círculo (`  ***  `),
  kbps/kHz, mono/estéreo, cursor de posição, volume, aleatório/repetir.
  Atalhos: Z X C V B, ↑/↓ volume ±5, ←/→ ±5 s, S aleatório, R repetir. Fim da faixa segue a lista;
  no fim para (ou recomeça com repetir).
- `player/analisador.py`: 19 barras de 3 px (+1 de espaço) em 76×16; cores do viscolor (0 fundo,
  1 pontos, 2–17 barras de cima para baixo, 23 pico); sobe na hora, cai 2,2 alturas/s; pico para
  0,4 s e cai. Fundo e coluna de cores pré-renderizados.
- Sem alocação por quadro: `desenhar(..., destino)` reaproveita a superfície 275×116; a máscara de
  região invertida fica em cache; a ampliação 2× usa `transform.scale(..., dest)`.
- **Laço de quadros com prazos absolutos** (`core/app.py`): com `Clock.tick(30)` o player ficava em
  29,4 fps; com um núcleo dividido com o GStreamer, o processo acorda ~1 ms atrasado a cada quadro e
  o atraso se acumulava. Prazos em múltiplos de 1/30 s descontam o atraso no quadro seguinte.
- `player/tipos_audio.py` (Tags, Evento) e `player/audio_falso.py` (`MotorFalso`): testes do player
  no PC, sem GStreamer.
- **Aceite no Eee PC** (tocando o MP3 de teste, 60 s): **30,0 fps** estáveis (28,6 só no intervalo
  em que a captura PNG é gravada), CPU do processo 49% (áudio ~25% + interface ~24%), **CPU do
  sistema 54,8%**, RSS 61 MB. Captura conferida: analisador animado, letreiro rolando, tempo,
  kbps/kHz e estéreo. Testes: 31 passam.

## Áudio (F1.5)

- `player/audio.py` (`MotorAudio`): `playbin` (só áudio + volume por software) com filtro
  `audioconvert ! audiopanorama ! spectrum` e GLib MainLoop numa thread. Volume 0..100 em escala
  cúbica; balanço pelo `audiopanorama`; busca, pausa, posição, duração, tags (título, artista, kbps
  das tags; kHz e canais das caps). Espectro: 512 bandas a cada 50 ms → 19 barras logarítmicas de
  40 Hz a 16 kHz (`player/espectro.py`), num deque curto lido com `espectro()`; fim/erro/aviso na
  fila `eventos`.
- O PyGObject não converte o `GstValueList` da mensagem do `spectrum`: as magnitudes são lidas do
  texto da estrutura (`to_string()` + regex). Funciona sem o pacote `python3-gst-1.0`.
- A saída é uma descrição gst-launch (`autoaudiosink`, `fakesink sync=true` nos testes).
- MP3 de teste sintético (sem direitos autorais): `python3 scripts/gerar_mp3_teste.py` gera
  `~/musica/teste_320kbps.mp3` no Eee PC (5 min, 320 kbps CBR, 11,4 MB, varreduras 40 Hz–16 kHz e
  batidas; leva ~2,5 min). Tags gravadas via `merge_tags` no `id3v2mux` (o `taginject` não aceita
  valores com espaço).
- `deploy/run.sh` aceita `nada` no `.app` (X sem app) para medições sem interferência.
- **Aceite no Eee PC** (X ocioso, saída ALSA real, 5 min): CPU do sistema média **26%** (pico
  34,5%), processo 24,6%, RSS 27 MB; 0 avisos/erros do GStreamer; fim da faixa no tempo certo;
  6000 espectros (20,0/s). Deriva posição×relógio de −0,3 s (atraso de início). O som em si não foi
  ouvido (sinal sintético, verificação remota).
- Atenção para a F3.5: áudio (26%) + dois mostradores (32%) ≈ 58% antes do OBD. Se faltar folga:
  reduzir para 256 bandas ou parar o espectro quando o analisador não estiver na tela.
- Testes: 25 passam no Eee PC (os de áudio usam `fakesink sync=true` e o MP3 de teste).

## Janela principal (F1.4)

- `player/janela_principal.py`: `EstadoJanela` (reprodução, tempo, título, kbps/kHz, mono/estéreo,
  volume, balanço, posição, aleatório/repetir/EQ/PL, título ativo) → `desenhar(skin, estado)` monta
  os 275×116; `ampliar(sup, 2)` dobra os pixels (vizinho mais próximo).
- **Referência**: o screenshot de cada skin no Winamp Skin Museum (renderizado pelo Webamp), baixado
  por `scripts/baixar_skins.sh` para `player/skins_teste/<nome>.png` (ignorado pelo Git).
  `ESTADO_REFERENCIA` reproduz o estado desses screenshots: tocando, 00:03, "1. DJ Mike Llama -
  Llama Whippin' Intro", 128 kbps, 44 kHz, estéreo, volume 75%, balanço 0, posição 60%, e
  **aleatório, repetir, EQ e PL ligados**.
- `player/comparar_referencia.py` compara pixel a pixel, ignorando a área do analisador (24,43,76×16;
  animada) e os pixels fora da região da janela. **Resultado no Eee PC: 0 pixels diferentes nas três
  skins**; a captura da tela real (1× e 2×) também bate pixel a pixel com a referência.
- Ajustes descobertos comparando com a referência (todos conferidos nas três skins):
  - volume: quadro = `floor(v·28/100)`, limitado a 27 (75% → quadro 21, não 20);
  - indicador de 3 px: x=36 do `playpaus.bmp` é o verde (com sinal), x=39 o vermelho; ele é
    desenhado **por cima** do ▶ (os nomes estavam trocados na F1.3);
  - letreiro com **155 px** de largura (31 caracteres), não 154;
  - clutter bar (OAIDV) do `titlebar.bmp` (304,0 8×43) em (10,22).
- **`region.txt`** (seção `[Normal]`): lido em `core/skin.py` (`Skin.regiao`), rasterizado na regra do
  Windows (centro do pixel dentro do polígono) e aplicado como transparência: fora da região a janela
  mostra o fundo, como no Winamp. Winamp5 Classified: 58 pixels fora (cantos arredondados).
- Tela estática no Eee PC: 29,2 fps, 4,5% de CPU, 48 MB. O fps fica um pouco abaixo dos 30,2 da
  tela de teste da F0.7; acompanhar na F1.6, que tem aceite de ≥ 30 fps.
- Testes: 20 passam no Eee PC (inclui a comparação com as referências).

## Mapa de sprites (F1.3)

- `player/sprites.py`: `SPRITES` (nome → BMP + retângulo), `POSICOES` (onde cada elemento fica na
  janela de 275×116), fonte de `text.bmp` (grade 5×6, 31 colunas, com equivalências como `<`→`(`) e
  funções `recortar`, `digito` (prefere `nums_ex`), `caractere`, `volume_fundo`/`balanco_fundo`
  (28 quadros a cada 15 px; balanço a partir de x=9). Coordenadas conferidas com o Webamp (MIT).
- Recortes são `subsurface` (sem cópia) **limitados ao BMP**: retângulo fora vira `None` em vez de
  erro (a Zelda tem `volume.bmp` de 420 px e não tem cursor de volume).
- `player/inspecionar_sprites.py`: grade 2× rotulada, paginada (setas/Espaço), sprite ausente em
  vermelho. Capturas das três skins tiradas no Eee PC e conferidas com os BMPs originais.
- `testes/test_sprites.py`: todo sprite cabe nos BMPs da base-2.91, posições dentro da janela,
  fonte, quadros de volume/balanço e os casos da Zelda. No Eee PC: 14 testes passam (4,8 s).
- Observação para a F1.4: algumas skins (ex.: Winamp5 Classified) já trazem botões desenhados no
  `main.bmp`; o desenho por cima com `cbuttons.bmp` cobre exatamente as mesmas áreas.

## Leitor de skins (F1.2)

- `core/skin.py`: `carregar(caminho, padrao=None) -> Skin`. Índice do zip por nome-base minúsculo
  (raiz tem preferência sobre subpastas); 19 BMPs conhecidos viram superfícies (sem `convert()`,
  para funcionar sem janela; `Skin.converter()` depois de abrir a tela). BMP que o SDL recusa é
  tentado de novo com detecção pelo conteúdo (skins com PNG/GIF renomeado).
- `nums_ex.bmp` e `numbers.bmp` são equivalentes; `imagem("numbers")` prefere `nums_ex`.
- Fallback: BMP ausente vem da skin padrão (`emprestados`); sem padrão, fica em `ausentes`.
  `viscolor.txt`/`pledit.txt` ausentes: os da padrão ou os valores internos (iguais aos da base-2.91,
  conferido em teste). Parsers tolerantes: zeros à esquerda, vírgula sobrando, `//`, cor sem `#`,
  lixo depois do hex, outras seções no `pledit.txt`.
- **Dependência nova: `python3-pytest`** (apt, 2,3 MB) no Eee PC, para rodar `testes/` lá; no PC,
  `pytest` no `.venv` (`deploy/requirements-pc.txt`).
- Aceite no Eee PC: `pytest testes/` → 9 passaram (3,6 s). Carga: base-2.91 293 ms,
  winamp5_classified 81 ms, zelda_amp_3 67 ms (todas < 1 s). A base é mais lenta, apesar de menor;
  provavelmente pelo formato dos BMPs dela. Fica abaixo do limite, então não investiguei.

## Skins de teste (F1.1)

`scripts/baixar_skins.sh` baixa do Winamp Skin Museum (`r2.webampskins.org/skins/<md5>.wsz`) para
`player/skins_teste/` (no `.gitignore`, conferido com `git check-ignore`) e confere o MD5 de cada
uma. Funciona no PC (curl) e no Eee PC; os três arquivos abrem com `unzip -l` nos dois.

| Arquivo local | MD5 | Por que serve de teste |
| --- | --- | --- |
| `base-2.91.wsz` | `5e4f1027…` | padrão do Winamp 2.91; referência e fallback; nomes em MAIÚSCULAS; sem `nums_ex.bmp` |
| `winamp5_classified.wsz` | `b0fb83cc…` | escura e moderna; tem todos os arquivos e vários extras |
| `zelda_amp_3.wsz` | `d770a634…` | temática; nomes com caixa mista (`playPaus.bmp`); **sem `numbers.bmp`** (só `nums_ex.bmp`) |

## Conferência visual (F0.10)

- O mantenedor olhou a tela real com o bench rodando e confirmou que está tudo certo: brilho,
  nitidez, imagem inteira, ponteiros fluidos e a saída pelo teclado (Q/Esc), com o app reabrindo
  pelo laço do `.xinitrc`. Fica verificado no hardware o que o SSH não alcançava na F0.7.

## Boot direto (F0.9)

- Instalação: `deploy/instalar_boot.sh` (roda no PC; repetir é seguro). Modelos em `deploy/sistema/`:
  override do `getty@tty1` com `--autologin` (usuário preenchido na instalação, não fica no
  repositório), `~/.bash_profile` (carrega o `~/.profile` e, só no tty1, `exec startx -- -nocursor`)
  e `~/.xinitrc` (`xset s off`, `s noblank`, `-dpms` e `deploy/run.sh` em laço).
- **O X roda como o usuário comum** (não root): o startx no console do tty1 tem permissão de
  terminal, o que não acontece pelo SSH.
- Cursor escondido pelo próprio X (`-nocursor`): dispensa o pacote `unclutter`.
- `deploy/run.sh` lê `~/dashamp/.app` (nome + argumentos extras; padrão `bench` = cache com dois
  mostradores). Saída do app em `/tmp/dashamp.log` (tmpfs). O Python é chamado por caminho absoluto;
  o `deploy.sh` encerra o app com `pkill -f "[/]dashamp/.venv/bin/python -m"`.
- Verificado após `sudo reboot`: o Eee PC cai no bench sem intervenção (SSH de volta em ~30 s, bench
  rodando ~1 min após ligar); 30 fps, 28% de CPU, 67 MB de RSS; captura conferida. Encerrando o app,
  o laço o reabre em < 6 s.
- Avisos inofensivos no `/tmp/startx.log`: `xf86EnableIO ... Operation not permitted` (normal no X sem
  root com KMS) e `pkexec: not found` (o driver intel tenta o ajudante de brilho via pkexec; se as
  teclas de brilho não funcionarem no X, ver na F0.10).

## Desempenho (F0.8, 2026-11-18)

`core/bench_ponteiro.py`: mostrador 400×400 pré-renderizado + ponteiro (sprite 338×18 com alfa) +
cubo central + texto de fps. Medido por `scripts/medir_bench.sh` no Eee PC, entre 10 s e 25 s de
execução. "parcial" = redesenha só os retângulos que mudam; "total" = tela inteira a cada quadro.
CPU do app é do processo Python; "sistema" inclui o Xorg (que copia os quadros via XShm).

| Ponteiro | Mostradores | Atualização | fps | CPU app | CPU sistema | Xorg | RSS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rotate a cada quadro | 1 | parcial | 30,2 | 44% | 49% | 3% | 48 MB |
| rotate a cada quadro | 1 | total | 30,2 | 52% | 62% | 9% | 48 MB |
| rotate a cada quadro | 2 | parcial | **28,6** | 81% | **86%** | 4% | 49 MB |
| rotate a cada quadro | 2 | total | **27,4** | 83% | **91%** | 8% | 49 MB |
| cache de 360 ângulos | 1 | parcial | 30,2 | 15% | 18% | 1% | 67 MB |
| cache de 360 ângulos | 1 | total | 30,2 | 24% | 35% | 9% | 67 MB |
| **cache de 360 ângulos** | **2** | **parcial** | **30,1** | **29%** | **32%** | 2% | **68 MB** |
| cache de 360 ângulos | 2 | total | 30,2 | 38% | 49% | 9% | 67 MB |

**Aceite atingido**: dois mostradores em tela cheia a 30 fps com 32% de CPU do sistema (parcial)
ou 49% (redesenhando tudo). Conclusões para as fases 1–3:

- **Ponteiros usam cache de ângulos**, nunca `transform.rotate` por quadro: a rotação sozinha custa
  ~20% de CPU por ponteiro e dois deles já estouram o orçamento.
- O cache (gerado com `rotozoom`, antisserrilhado, e recortado ao conteúdo) custa **18 MB e 2,3 s
  de carga por desenho de ponteiro**. Dois mostradores com o mesmo ponteiro dividem o cache. Para
  vários ponteiros diferentes: gerar só os ângulos da varredura (270°), ou guardar o cache em disco.
- **Atualização parcial** economiza 10–17 pontos de CPU (principalmente no Xorg). Vale manter.
- Folga para áudio + espectro + OBD na F3.5: ~65% de CPU e ~50 MB de RAM no orçamento de 120 MB.

## Núcleo (F0.7)

- **pygame-ce trocado pelo `python3-pygame` 2.1.2 do apt** (SDL 2.26.5; 68,5 MB, aprovado pelo
  mantenedor). O wheel i686 do pygame-ce importa, mas morre com *instrução ilegal* em
  `pygame.display.init()` com o driver X11: o kernel aponta o `libSDL2` embutido no wheel
  (`trap invalid opcode ... in libSDL2-2-44947314.0.so`). Com `SDL_VIDEODRIVER=dummy` não falha.
  O Debian compila para a base i686, que o Celeron M (só até SSE2) suporta.
- No PC de desenvolvimento continua o pygame-ce (`deploy/requirements-pc.txt`), porque o pygame 2.1.2
  não tem wheel para Pythons novos. **O código deve usar só a API do pygame 2.1.2.**
- **`SDL_FRAMEBUFFER_ACCELERATION=0`** (definido em `core/app.py`): sem ele o SDL apresenta a janela
  por OpenGL e carrega Mesa `i915_dri` + `libLLVM-15` (~58 MB). Medido na tela de teste:

  | | fps | CPU | RSS |
  | --- | --- | --- | --- |
  | padrão (OpenGL) | 30,2 | 6,5% | 119 MB |
  | `SDL_FRAMEBUFFER_ACCELERATION=0` (XShm) | 30,2 | 2,0% | 49 MB |

- `pygame.display.init()` + `pygame.font.init()` em vez de `pygame.init()`: não abre o mixer, que
  prenderia o ALSA (o áudio é do GStreamer).
- Opções comuns de todo app: `--metricas`, `--captura N`, `--duracao N` (encerra sozinho; para
  medições pelo SSH) e `--janela` (bordas e cursor, no PC).
- Teste pelo SSH: o X sobe como root com
  `sudo xinit /bin/sh -c "xhost +si:localuser:dashamp; exec sleep 900" -- :0 vt1` e o app roda como
  `dashamp` com `DISPLAY=:0`. Captura conferida (800×480 inteiros, animação, 30 fps).
- Ainda não verificado: sair com Esc/Q no teclado físico (pelo SSH não há como apertar a tecla;
  fica para a conferência da F0.10).

## Flash (F0.6)

- `fstab` (backup em `/etc/fstab.antes-f06`, validado com `findmnt --verify`):
  `noatime` no `/`; `/tmp` em tmpfs de 100 MB (`nosuid,nodev,noatime`); **swap comentada**
  (a partição `sda5` continua lá, só não é usada; o `RESUME=` do initramfs aponta para ela e é inofensivo).
- journald: `/etc/systemd/journald.conf.d/10-dashamp.conf` com `Storage=volatile` e
  `RuntimeMaxUse=16M`; journal antigo do flash (`/var/log/journal`, 17 MB) apagado com aprovação.
- Desativados (aprovados pelo mantenedor): `bluetooth` (sem hardware), `wpa_supplicant` (Wi-Fi
  não detectado; religar na F3.7 se aparecer), `apt-daily` e `apt-daily-upgrade` (atualizações agora
  manuais), `man-db`, `anacron`, `dpkg-db-backup`, `e2scrub_all`/`e2scrub_reap` (sem LVM) e
  `fstrim` (o flash não aceita TRIM).
- Mantidos: `ssh`, `networking`, `getty`, `cron`, `logrotate`, `systemd-timesyncd`, `apparmor`,
  `console-setup`, `keyboard-setup`, `systemd-pstore`.
- Após o reboot: SSH de volta em ~45 s; boot de 28,8 s (13,1 s kernel + 15,7 s userspace);
  nenhuma unidade com falha; 435 MB de RAM disponíveis ociosa; 1,6 GB livres.

## Venv e deploy (F0.5)

- ~~pygame-ce 2.5.8 pelo pip~~ (wheel `manylinux2014_i686`): importava, mas não abre janela no
  Eee PC; substituído pelo `python3-pygame` do apt na F0.7.
- **Venv com `--system-site-packages`**: o `gi` (PyGObject) e o GStreamer 1.22 vêm do apt; sem a
  opção, o venv não os enxerga. Venv: 59 MB. `spectrum` e `playbin` disponíveis.
- **`deploy/deploy.sh`**: usa `rsync` se existir no PC; o Git Bash do Windows não tem, então cai
  para `tar` pelo SSH, extraindo em `~/dashamp/.novo` e trocando o conteúdo (espelho: arquivos
  apagados no PC somem no Eee PC). `.venv` e `.app` são preservados; nada é apagado fora de
  `~/dashamp`. `--deps` instala `deploy/requirements.txt`. O host vem de `DASHAMP_HOST_ALVO` no
  `.env` (padrão `eeepc`).
- O reinício usa `pkill -f "[d]ashamp.main"`: sem o colchete, o `pkill` mataria o próprio shell
  remoto, cuja linha de comando contém o padrão.

## Pacotes base (F0.4)

- Kernel antigo `6.1.0-39` removido e cache do apt limpo antes da instalação (1,6 → 1,9 GB livres);
  o GRUB só lista o kernel atual.
- 164 pacotes da lista do plano, sem recomendados: 326 MB. Depois: **1,6 GB livres** em `/`.
- **Extra: `xserver-xorg-input-libinput`** (1,8 MB). Sem ele o X ignora teclado e touchpad
  ("No input driver specified") e o app não receberia Esc/Q.
- X: driver `intel` (915GM), saída `LVDS1` em 800×480; teclado e touchpad via libinput.
- Pelo SSH, o X só sobe como root (usuário comum recebe "Switching VT failed"); no boot (F0.9)
  ele sobe pelo autologin no tty1. O teste de aceite foi feito com `sudo xinit ...`.
- Som: `speaker-test -c2 -l1` toca nos dois canais (confirmado de ouvido pelo mantenedor).
  O mixer só tem `Master` (sem `PCM`), deixado em 80%.

## Máquina alvo (levantamento F0.3, 2026-11-18)

| Item | Valor |
| --- | --- |
| Sistema | Debian 12.15 i386, Python 3.11.2 |
| Kernel | `6.1.0-56-686-pae` (6.1.192-2) — ver nota abaixo |
| CPU | Intel Celeron M 900 MHz, 1 núcleo, 32 bits; flags `sse sse2 pae nx` (sem `ssse3`/`sse4`) |
| **RAM** | **512 MB** (482 MB visíveis ao sistema; ~434 MB disponíveis ociosa) |
| Armazenamento | flash de 3,7 GB: `sda1` 3,2 GB ext4 em `/` + `sda5` 501 MB de swap |
| **Espaço livre em `/`** | **1,6 GB** (1,4 GB usados) |
| Vídeo | Intel 915GM (driver `i915`) |
| Áudio | HDA Intel ICH6 (`snd_hda_intel`), placa 0 |
| Rede | Ethernet Atheros L2 (`atl2`), 100 Mbit |
| Wi-Fi | **não detectado** no barramento PCI (ver nota) |
| USB | webcam integrada (eMPIA), leitor SD (ENE UB6225) |

### Orçamento de memória

Com 512 MB de RAM, o orçamento do app gráfico **cai para RSS ≤ 120 MB** (em vez de 150 MB).

### Notas do levantamento

- **Kernel PAE**: o plano previa o kernel `686` sem PAE, mas esta CPU anuncia `pae` e `nx`, e o
  instalador escolheu `686-pae`, que dá boot normalmente. Com PAE o bit NX (proteção de memória)
  funciona; o custo em 512 MB de RAM é desprezível. Decisão pendente com o mantenedor.
- **Swap**: o instalador criou uma partição de swap de 501 MB (`sda5`), contra o plano.
  Swap no flash gasta a vida útil; a proposta é desligá-la na F0.6 (`swapoff` + linha comentada
  no `fstab`), sem mexer na partição.
- **Kernel antigo**: `6.1.0-39-686-pae` ainda instalado (~186 MB de módulos) e há 76 MB de cache do
  apt. Remover ambos libera ~250 MB antes da F0.4, cujo aceite pede ≥ 1,5 GB livres.
- **Wi-Fi**: nenhuma placa sem fio aparece no `lspci`. Pode estar desativada no BIOS
  (opção de WLAN on-board) ou ausente. Só é necessária na F3.7; investigar antes dela.
- `aplay` ainda não está instalado (vem com `alsa-utils` na F0.4).

## Acesso (F0.2)

- Chave dedicada `~/.ssh/eeepc_ed25519` no PC; `IdentitiesOnly yes` no `Host eeepc`.
- IP e usuário ficam só no `~/.ssh/config` do PC de desenvolvimento e no `.env`.
- `sudo` sem senha em `/etc/sudoers.d/eeepc` (0440, validado com `visudo -c`).
- `sshd`: drop-in `/etc/ssh/sshd_config.d/10-dashamp.conf` com `PasswordAuthentication no`,
  `KbdInteractiveAuthentication no` e `PermitRootLogin no`. Login por senha recusado (testado).
  Para reverter, apague esse arquivo pelo console local e rode `sudo systemctl reload ssh`.

## Decisões

- **F0.0** — `.gitattributes` com `eol=lf` para todo texto: o PC de desenvolvimento é Windows
  (`core.autocrlf=true`) e scripts com CRLF quebram no Linux do Eee PC.
- **F0.0** — a pasta local `Claude outputs/` (rascunhos de trabalho) fica no `.gitignore`.
- **F1.9** — o `Master` do ALSA estava em 44/64 (-20 dB) e o som saía baixo mesmo com o player
  no máximo. Subido para 100% (0 dB) e salvo com `sudo alsactl store` (restaurado no boot pelo
  `alsa-restore`). Headphone, Speaker e PCM já estavam em 100%.
