# Estado do Dashamp

Última tarefa concluída: **F3.2** (consumo e códigos de erro).
Próxima: **F3.3** `[HUMANO]` — primeira leitura no carro.

## Consumo e códigos de erro (F3.2)

- `carputer/consumo.py`: L/h pelo **PID 5E** quando o carro tem; senão **MAF / (AFR × λ)**
  (λ = razão de equivalência comandada, PID 44, 1,0 sem ela); senão **speed-density** pela MAP,
  temperatura do ar, rpm, `--cilindrada` e VE 0,85. Daí `consumo_kml` (0 parado, < 3 km/h) e
  `consumo_medio_kml` (integral por trapézio desde o início; buracos > 2 s não entram).
- Combustíveis (`--combustivel`): `gasolina` (E0, AFR 14,7, 745 g/L), `gasolina_br` (padrão;
  gasolina C E27, AFR ≈ 13,1, 757 g/L) e `etanol` (hidratado, AFR ≈ 8,4, 809 g/L). Aproximações:
  o erro real de um consumo por MAF fica na casa de 5–10% e o corte de injeção em desaceleração não
  é visto quando o carro não informa a λ. Conferir com o tanque cheio na F3.3+.
- Canais novos: `lambda`, `consumo_kml`, `consumo_medio_kml`; agenda ganhou `combustivel_lh`
  (PID 5E, 0,5 s) e `lambda` (1 s).
- **Códigos de erro**: `FonteOBD.ler_erros()` / `apagar_erros()` devolvem um `Future` atendido na
  thread da fonte entre dois ciclos (a porta é uma só); sem conexão, falham na hora; se a conexão
  cai com pedido na fila, ele recebe o erro. Modo 03 (armazenados) e 07 (pendentes); apagar =
  modo 04, sucesso só com a resposta positiva 0x44.
- `carputer/tela_erros.py`: tecla **E** no painel com `--obd`. Lista com o sistema em português
  (P/C/B/U, genérico ou do fabricante) e a descrição do python-OBD (em inglês; traduzir milhares de
  códigos não cabe). **A** apaga com confirmação (**S**/**N**) e avisos; espera máxima 20 s.
  Capturas: `docs/img/f32_codigos.png`, `docs/img/f32_consumo.png`.
- **Emulador**: o cenário `car` vem sem códigos; `scripts/emulador_obd.py --erros P0143,...
  --pendentes ...` os configura. O ELM327-emulator 4.0.0 manda a resposta do modo 03/07 **sem o
  byte de quantidade** que a SAE J1979 exige no CAN; o python-OBD lia "43 01 43 ..." como um
  código só ("C0303"). O lançador troca a função do emulador pela resposta da norma.
- Aceite no Eee PC (emulador com 3 armazenados + 1 pendente, tema digital80, teclas simuladas
  dentro do processo): leu os 4 códigos, confirmou, apagou, leu de novo vazio e voltou ao painel
  com o consumo pelo MAF na tela. 28–30 fps, CPU 13–20%, RSS 57 MB, rpm 14,8 leituras/s.
  Testes: 150 + 5 pulados no PC; 155 no Eee PC (o do emulador lê e apaga os códigos).

## FonteOBD (F3.1)

- `painel/fontes/obd.py`: `FonteOBD(porta, baudrate)` com o python-OBD 0.7.3; `painel.main --obd
  [PORTA] [--obd-baud N]` (sem porta: o python-OBD procura). Caixa de espera com o que falta
  ("adaptador não encontrado", "ligue a ignição", "conectando").
- **Agendador**: `rpm` e `velocidade` em todo ciclo; acelerador 0,25 s; carga, pressão do coletor
  e MAF 0,5 s; temperaturas, tensão, tanque, sonda e trims 1 s. Em cada ciclo vai **um** lento (o
  mais atrasado). Teto de 15 ciclos/s (`CICLOS_MAX_HZ`). Canais sem PID suportado saem da agenda;
  a tensão cai para `ELM_VOLTAGE` (AT RV do adaptador).
- **Decisão: sem `obd.Async`**: ele lê os comandos observados em fila, sem prioridade. A thread
  da `Fonte` faz o papel de laço assíncrono e o agendador fica nela, com `OBD.query`.
- **Reconexão**: sem adaptador, sem ignição ou 5 ciclos seguidos sem rpm/velocidade → publica
  `REPOUSO`, fecha e tenta de novo a cada 3 s.
- Canais novos no catálogo: `maf` (g/s), `trim_curto`, `trim_longo` (%), `sonda_o2` (V).
- **Dependências** (justificativa): `obd` (a biblioteca indicada no plano) exige Pint 0.24.x; o
  Debian 12 tem 0.19, então o Pint vem do pip, com flexcache, flexparser, platformdirs e
  typing_extensions (Python puro). pyserial e PyYAML vêm do apt (python3-serial, python3-yaml).
  ELM327-emulator 4.0.0 (só testes; sdist Python puro). Ao todo poucos MB no venv.
- `import obd` leva **4,1 s** no Eee PC (o Pint monta o registro de unidades): o import fica dentro
  da thread da fonte e o painel abre na hora.
- **Emulador**: no Windows o modo de rede (`elm -n`) não conversa com o python-OBD (só responde
  `` inválido, e o modo lote grava o log sem parar: 150 MB em 3 min). No Eee PC funciona
  pela rede e pela pty. Os testes no PC usam um adaptador falso (`testes/test_obd.py`); o teste com
  o emulador de verdade (parar e subir de novo) roda só no Linux.
- Pela rede (`socket://`) o pyserial faz ~22 leituras com `select` por resposta: **13 ms de CPU por
  pergunta** no Eee PC. Pela pty (o caminho de uma serial USB/Bluetooth de verdade): **1,4 ms**.
  O aceite foi pela pty, com um link fixo `/tmp/elm_porta` (como uma `/dev/rfcomm0`) refeito
  quando o emulador sobe de novo.
- **Aceite no Eee PC** (emulador na mesma máquina, ~25% da CPU dele): valores na tela
  (`docs/img/f31_obd.png`); emulador parado por 10 s → "Device disconnected", 3 tentativas de
  reconexão, ponteiros em repouso; emulador de volta → leitura retomada sozinha
  (`reconexao: 1`). **Taxa efetiva de rpm: 15,0 leituras/s** (o teto; sem teto, 38/s, com
  60% de CPU). Só a fonte: 8% de CPU. Num carro de verdade o ELM327 deve dar menos (≈ 5–10 rpm/s
  com os lentos intercalados); medir na F3.3.
- Painel + OBD (30 s cada): digital80 30 fps, CPU 16%, RSS 56 MB; vintage 28–30 fps, CPU 47–51%,
  62 MB; moderno 29–30 fps, CPU 41%, 55 MB. Os valores do emulador pulam (rpm 0 ↔ 1300, velocidade
  29 ↔ 114) e mexem todos os ponteiros a cada quadro, bem mais do que um carro.
- **Otimização em `Digitos`** (achada aqui): glifo com alfa de 150 px = 4 ms por blit no Eee PC,
  opaco = 0,11 ms. Widget sozinho na área (`Widget.sozinho`, posto pelo Painel) usa imagens
  opacas por (posição, caractere, cor), já combinadas com o fundo: digital80 com OBD caiu de 37%
  para 16% de CPU. No vintage o custo é dos ponteiros (sprite girado com alfa, ~1,3 ms cada).
- Testes: 127 + 5 pulados no PC; 132 no Eee PC (inclui o emulador).

## Corrida de teste (F2.8)

- O mantenedor correu com o **Gran Turismo 7 num PS5** em casa, com o Eee PC na mesma rede (boot
  em `painel --gt7`): o Eee PC achou o console sozinho e o painel acompanhou a corrida. Resultado
  relatado: "ficou excelente". Protocolo da comunidade (Salsa20, heartbeat, offsets) confirmado.
- Problema visto: **ao fim da corrida os mostradores ficavam parados na última medição** (o GT7
  pausa ou para de mandar o carro, e a fonte só publicava pacotes "em pista").
- Correção: `base.REPOUSO` (rpm, velocidade, marcha e acelerador = 0) é publicado uma vez quando
  o GT7 manda pacote pausado (bit 1), carregando (bit 2) ou com o carro fora da pista (bit 0
  apagado), e quando passa `SILENCIO_REPOUSO_S` = 1,5 s sem dado do carro. A `FonteUDPF1` faz o
  mesmo pelo silêncio. Temperatura e tanque ficam no último valor (zerá-los acenderia as luzes de
  motor frio e de reserva). Contador `repouso` em `contagem`.
- **A confirmar na próxima corrida**: o bit 0 ("carro na pista") vem da documentação da
  comunidade; se o painel não reagir durante a corrida, é ele. Também falta conferir a marcha em
  neutro e ré.
- Verificação no Eee PC (PC fingindo ser o PS5 por 22 s, tema digital80): 30 fps, CPU 3–7%,
  RSS 51 MB; captura depois do fim (`docs/img/f28_repouso.png`) com tudo zerado e temperatura e
  tanque mantidos. Testes: 121 + 4 pulados no PC; `test_gt7` e `test_udp_f1` passam no Eee PC.
- Lista pública de jogos de console com telemetria: `docs/jogos.md` (ligada no README).

## FonteGT7 (F2.7b)

- **Correção do mantenedor**: o jogo disponível é o Gran Turismo 7 no PS5, não o F1 24. A fonte do
  F1 fica no projeto (`--udp`); a do GT7 virou a tarefa F2.7b e a F2.8 passa a ser com o GT7.
- Protocolo (sem especificação oficial; o da comunidade): heartbeat b"A" para a porta UDP 33739
  do PS5, repetido a cada 1 s; o PS5 responde na 33740 com pacotes de 296 bytes cifrados com
  Salsa20 (chave = 32 primeiros bytes de "Simulator Interface Packet GT7 ver 0.0"; nonce =
  `iv1 ^ 0xDEADBEAF` + `iv1`, com `iv1` nos bytes 0x40..0x43); assinatura 0x47375330. Campos:
  0x3C rpm, 0x44/0x48 combustível/capacidade, 0x4C velocidade (m/s), 0x58 temperatura da água,
  0x8E flags (pausado = bit 1, pacote ignorado), 0x90 marcha (nibble baixo), 0x91 acelerador
  (0..255). **A corrida da F2.8 confirma**; em especial o que o GT7 manda como marcha na ré/neutro.
- **Descoberta do PS5 sem digitar IP**: enquanto nada chega, o heartbeat vai para o broadcast e
  para os 253 endereços da /24 a cada 3 s; quem responder é o PS5 (e se ele sumir por 10 s, volta a
  procurar). `--ps5 IP` pula a descoberta.
- **Dependência nova**: Salsa20 do `python3-pycryptodome` (apt, 6,8 MB; no Debian o módulo se
  chama `Cryptodome`; no PC, `pycryptodome` do pip, módulo `Crypto` — o código aceita os dois).
  Decifrar em Python puro a 60 Hz custaria boa parte da CPU do Eee PC.
- `painel.main --gt7 [--ps5 IP]`; caixa de espera com o estado ("Procurando o PS5", "PS5
  encontrado: entre na pista", "Sem rede: ligue o cabo"). **F2 agora abre `painel --gt7`.**
  O GT7 não manda consumo nem tensão: no digital80 esses dígitos ficam em "---".
- Simulador de PS5 (`python -m painel.fontes.gt7 --simular-ps5`): responde a heartbeats com
  pacotes cifrados da FonteSimulada, para testar sem o console.
- **Aceite**: 10 testes (cifra, campos, pausado, IV/pacote corrompido, gravação, alvos da
  descoberta, heartbeat + recepção com um PS5 falso). No Eee PC, com o PC fingindo ser o PS5 e
  **sem IP configurado**: o Eee PC achou o "PS5" pela descoberta, recebeu os pacotes e o painel
  ficou a 30 fps com CPU de 5–13% (RSS 60 MB). Captura do digital80 conferida.
- Boot deixado em `painel --gt7`.

## Preparação para a F2.8 em casa (sem SSH)

- Uma primeira resposta "acompanhou bem" não correspondia a um teste com o jogo (não havia jogo
  disponível): os contadores do Eee PC (`/proc/net/snmp` InDatagrams, RX da placa) mostraram que
  nenhum pacote chegou. A F2.8 continua aberta.
- **Teclas no Eee PC** (para usar sem SSH): F1 = player, F2 = painel recebendo o F1 24
  (`painel --udp`), F3 = painel com a simulação. O `run.sh` exporta `DASHAMP_ARQUIVO_APP`; o
  `core.app` grava a escolha no `.app` e encerra, e o laço do `.xinitrc` abre o app novo (o tema
  escolhido é mantido). No PC de desenvolvimento (sem a variável) as teclas não fazem nada.
- O tema escolhido com **T** fica gravado no `.app` (`--tema`), valendo para o próximo boot.
- `painel --udp` mostra, enquanto não chega telemetria, uma caixa com o **IP do Eee PC** e a porta
  (consulta o IP a cada 5 s, para o caso de a rede subir depois do app); some no primeiro pacote.
- Rede: `enp3s0` por DHCP (`allow-hotplug`), então funciona em outra rede; o Wi-Fi não funciona
  (F0.3), por isso em casa é preciso o **cabo de rede ligado antes de ligar o Eee PC**.
- Boot deixado em `painel --udp`.

## FonteUDPF1 (F2.7)

- Edição do jogo do mantenedor: **F1 24**. O fórum da EA com a especificação oficial recusou
  acesso automático (HTTP 403); o layout foi conferido com um cliente de terceiros para o F1 24
  e bate com os tamanhos de pacote da especificação: cabeçalho de 29 bytes, Car Telemetry (id 6)
  1352 bytes = 29 + 22 × 60 + 3, Car Status (id 7) 1239 bytes = 29 + 22 × 55; little-endian,
  sem preenchimento; porta 20777. **A confirmação final é a corrida da F2.8** (o decodificador
  conta pacotes ignorados por formato/tamanho; se o layout estiver errado, aparece ali).
- `painel/fontes/udp_f1.py`: `decodificar(pacote)` só aceita `m_packetFormat == 2024` e o tamanho
  exato; usa o carro `m_playerCarIndex`. Canais: velocidade, acelerador (×100), marcha (-1 = R,
  0 = N, até 8), rpm, temp_motor (telemetria) e combustivel_nivel (tanque ÷ capacidade, do
  status). `FonteUDPF1(porta, gravar_em=)` publica uma leitura por pacote de telemetria e conta
  os pacotes por tipo (`contagem`); SO_RCVBUF pedido de 1 MB (o kernel limita a 180 kB).
- Gravador de pacotes brutos (`GravadorPacotes`, `ler_pacotes`; arquivo `DASHUDP1` + registros
  `<d t><H tam><bytes>`), `--gravar` e `--enviar ARQ --destino IP` (reproduz pela rede no ritmo
  gravado). `painel.main --udp [--gravar-udp ARQ]`.
- O catálogo de canais passou `marcha` para -1..8 (ré e as 8 marchas do F1).
- **Aceite**: os testes montam pacotes no layout do F1 24 (com valores diferentes nos outros 21
  carros, para pegar deslocamento errado), gravam, releem e decodificam os valores certos; um
  teste recebe pela rede local. No Eee PC, corrida sintética de 30 s a 60 Hz enviada pelo PC:
  **1800/1800 pacotes de telemetria e 60/60 de status**, painel a 30,0 fps, CPU 30–48% (tema
  moderno). Uma primeira tentativa "perdeu" 136 pacotes porque o app encerrou (--duracao) antes
  do fim do envio; o gravador sozinho e o kernel (`RcvbufErrors` 0) não perderam nada.
- Observação para a F2.8: os temas têm escala de carro de rua (8000 rpm, 220–260 km/h); no F1
  (até ~13000 rpm, > 300 km/h) os mostradores ficam no máximo. Ajustar se o mantenedor quiser
  (variantes de tema com outra faixa).

## Três temas (F2.6)

- Geradores em `painel/temas/gerar_{vintage,digital80,moderno}.py` (`python -m
  painel.temas.gerar_vintage`), com ferramentas comuns em `painel/temas/desenho.py`: fundo
  desenhado em 2× e reduzido com smoothscale (antisserrilhado), escalas analógicas com o mesmo
  mapeamento de ângulo dos widgets, aro metálico, degradês, granulado, sprite de agulha. Os PNGs e
  o `tema.json` gerados são commitados.
- **Fontes**: só DejaVu (licença livre), lida de `/usr/share/fonts/truetype/dejavu` ou de
  `tmp/fontes/` (fora do Git; copiada do Eee PC). A fonte não vai para o repositório, só os PNGs
  com os números já desenhados. No laço o painel usa a fonte padrão do pygame.
- Widgets novos: `Arco` (anel segmentado; cada segmento aceso é um sprite pequeno pré-renderizado,
  sem desenho de polígono no laço) e `Numero` (número com fonte, dígitos tabulares para não
  "dançar"). Ambos no formato de tema (`"tipo": "arco"`, `"numero"`).
- Temas:
  - `vintage`: dois mostradores creme com aro cromado, números em DejaVu Serif, ponteiros
    vermelhos (sprite gerado), combustível e temperatura em submostradores, fundo de couro;
  - `digital80`: rpm em bargraph de 40 segmentos verde/âmbar/vermelho, velocidade e marcha em
    LED de 7 segmentos, barras verticais de temperatura e combustível, consumo e tensão;
  - `moderno`: arco de rpm com 64 segmentos e a velocidade em número grande no centro, arcos
    pequenos de temperatura e combustível.
- `painel.main`: tema padrão `vintage`; tecla **T** passa para o próximo tema sem reiniciar
  (`--ciclo-temas S` para medir).
- **Aceite no Eee PC** (30 s cada, FonteSimulada, sem captura): vintage 30,0 fps, CPU 8–34%
  (picos enquanto o cache dos ponteiros enche), RSS 56 MB; digital80 30,0 fps, CPU 4–10%,
  49 MB; moderno 30,0 fps, CPU 5–17%, 49 MB. Carga: 185 / 231 / 300–352 ms. Trocando a cada 3 s
  o fps médio do intervalo cai para 27–29 (cada carga para o laço). Com captura, o intervalo do
  PNG cai para 27,7–29,1 (a gravação do PNG). Capturas em `docs/img/f26_*.png`. 98 testes no PC.

## Formato de tema (F2.5)

- `painel/tema.py`: `carregar(nome_ou_pasta) -> Tema(nome, pasta, painel, segundos_carga)` lê
  `painel/temas/<nome>/tema.json` (versão 1) + PNGs da pasta. Formato documentado no docstring do
  módulo: `fundo` (cor, imagem), `imagens` (enfeites), `textos` (rótulos com tamanho, cor e
  alinhamento) e `widgets` (tipo `ponteiro`, `barra`, `digitos`, `luz` ou `historico`; cada campo
  vira o parâmetro de mesmo nome do widget; `faixa` [mín, máx]; `zonas` [[de, até, cor]]; cores
  "#rrggbb" ou [r, g, b]). O fundo (cor + imagens + textos + partes estáticas dos widgets) é
  composto uma vez na carga.
- `Ponteiro` ganhou `sprite` (PNG do tema, pivô no centro apontando para a direita), `escala`
  (false = a face vem da imagem do tema) e `cubo`.
- Validação: **todos** os erros do arquivo numa `ErroTema` só, cada um com o caminho do campo e
  o que se esperava, ex.: `widgets[1] (barra 'temp_motor').segmentos: esperado um número inteiro,
  veio texto "vinte"`; também JSON malformado (linha e coluna), versão, campos desconhecidos
  (lista os válidos), canal fora do catálogo (lista os canais), faixa invertida, PNG ausente,
  widget saindo da tela de 800×480 e tema inexistente (lista os temas).
- `python -m painel.main [--tema exemplo] [--replay viagem.db]` (e `painel` no `.app`); tema
  inválido sai com código 2 e a lista de erros. `painel/temas/exemplo/` = layout da tela de teste.
- **Aceite no Eee PC**: tema `exemplo` (10 widgets) carregado em **174–235 ms** com o cache de
  disco esvaziado; 30,0 fps, CPU 8–15%, RSS 54 MB. Um tema com 9 erros mostra os 9 de uma vez e
  sai com código 2. 19 testes novos em `testes/test_tema.py`.

## Widgets (F2.4)

- `painel/widgets/`: base `Widget` (canal, faixa, `tau` da suavização exponencial, `Zona(de, ate,
  cor)` de alerta) com o ciclo `pintar_fundo` (parte estática no fundo, uma vez) → `atualizar`
  (aproxima o valor mostrado do lido: `v += (alvo - v)(1 - e^(-dt/tau))`) → `desenhar` (só se a
  `_chave()` quantizada mudou; restaura o fundo e devolve os retângulos sujos).
  - `Ponteiro`: escala (traços, números, arco das zonas, rótulo) desenhada em 2× e reduzida com
    smoothscale. **Cache de ângulos sob demanda** (passo de 1°, só dentro da varredura): a F0.8
    pré-gerava 360 ângulos em 2,9 s e 18 MB, o que não cabe nos < 1 s de carga de tema da F2.5;
    agora cada ângulo é girado na primeira vez que aparece (no máximo um por quadro).
  - `Barra`: segmentos apagados no fundo, acesos (cor da zona do meio de cada segmento)
    pré-renderizados; horizontal ou vertical (enche de baixo para cima). Dois blits por mudança.
  - `Digitos`: 7 segmentos desenhados por código (hexágonos, itálico leve) em 3× com
    smoothscale; "8" fantasma no fundo; glifos em cache por cor; ponto decimal; "---" sem dado
    ou se não couber.
  - `LuzEspia`: acende na cor da zona em que o valor está, com halo; pode piscar.
  - `Historico`: deque de N s × taxa (4/s), redesenha a linha só a cada amostra nova; grade a
    cada 10 s e linhas das zonas no fundo.
  - `Painel`: fundo pré-renderizado + widgets + fonte. Widgets sobrepostos formam um grupo
    (componentes conexos): se um muda, o grupo inteiro é restaurado e redesenhado na ordem.
- `python -m painel.teste_widgets [--replay viagem.db --velocidade 2]`: conta-giros com a marcha
  dentro, velocidade em LED, barras de temperatura e acelerador, 4 luzes e histórico de 60 s.
- **Aceite no Eee PC** (60 s com a FonteSimulada): **30,0 fps** (29,7 num intervalo com o cache
  do ponteiro enchendo; 29,1 no da captura), CPU do processo 7–13% (picos de 22–32% enquanto
  ângulos novos são girados), RSS 50–55 MB. Captura em `docs/img/f24_widgets.png`. 8 testes novos.

## Gravação de viagens e FonteReplay (F2.3)

- Formato (`painel/gravacao.py`, versão 1): um SQLite por viagem com `metadados(chave, valor)`
  (versao, criado_em em UTC, fonte, hz e o que vier; no fechamento duracao_s e leituras),
  `canais(id, nome, unidade)` e `leituras(t, canal, valor)` com `canal` inteiro (economiza ~30%
  do tamanho). Sem índice: as linhas ficam em ordem de gravação e a leitura é sequencial.
  Canais fora do catálogo são registrados assim mesmo.
- `Gravador(caminho, metadados, intervalo_s=10)`: acumula em memória e grava em **lote**, uma
  transação a cada 10 s (`synchronous=NORMAL`); queda de energia perde no máximo o último lote e o
  arquivo continua íntegro. `acompanhar(fonte)` assina a fonte (`Fonte.assinar`, novo na F2.3:
  callback em cada publicação, na thread da fonte), para não perder leituras como aconteceria
  lendo `ultima()` pelo laço de quadros.
- `ler_viagem(caminho)`: gerador de `(t, valores)`, lendo aos poucos (não carrega o arquivo todo
  na RAM do Eee PC); recusa versão de formato desconhecida.
- `FonteReplay(caminho, velocidade=1, repetir=False)`: publica cada leitura no instante gravado
  ÷ velocidade, com o `t` original; a velocidade muda durante a reprodução sem saltos (re-ancora o
  relógio); valores acumulados (canal ausente mantém o último valor, útil para PIDs do OBD com
  ritmos diferentes); `terminou` sinaliza o fim.
- **Aceite no Eee PC** (`python -m painel.fontes.replay --verificar 60 --velocidade 4`): 60 s da
  FonteSimulada em tempo real → 481 leituras em 6 lotes, **152 kB** (≈ 9 MB/h; os 200 MB de
  rodízio da F3.4 guardam ~22 h); replay a 4× em **15,01 s** (esperado 15,00), **481 de 481
  iguais** em `t` e em todos os valores. A 1×: 20 s em 20,01 s, iguais. 66 testes passam.
- Nos testes, gravar com uma transação por leitura levava 10 s no Windows (um fsync por commit):
  os testes gravam num lote só, como o uso real.

## FonteSimulada (F2.2)

- `painel/fontes/simulada.py`: `Carro` (estado + `passo(dt)` + `valores()`), `simular(segundos)`
  determinística (para testes e gráficos) e `FonteSimulada(hz=8, semente=1, temp_inicial=25)`, que
  avança o carro pelo dt real entre amostras (se a máquina atrasar, o carro não anda mais devagar
  que o relógio).
- Modelo: motorista em fases (parado 3–8 s → acelera com pedal 45–95% até 40–120 km/h → mantém
  com controle proporcional → desacelera até parar ou até um alvo ≥ 15 km/h menor); câmbio de
  5 marchas (8/14/21/28/35 km/h a 1000 rpm), sobe em 2500–4500 rpm conforme o pedal, reduz abaixo
  de 1300, corte de 0,4 s em cada troca; embreagem patinando até 10 km/h; marcha lenta
  1150 rpm fria → 820 quente; motor aquece com a potência até a válvula (~90 °C em ~8 min
  partindo de 25 °C); ar de admissão esquenta parado; consumo ∝ rpm × carga; tanque de 50 L.
  Todos os 11 canais do catálogo, limitados às faixas dele.
- `python -m painel.fontes.simulada --segundos 60 --csv /tmp/simulada.csv` grava em tempo real
  pela thread. `scripts/grafico_csv.py` desenha o CSV num PNG com o pygame (sem matplotlib).
- **Aceite no Eee PC**: 60 s → **480 leituras = 8,00 Hz**, CPU do processo **1,8%**. Gráfico
  conferido (`docs/img/f22_simulada_60s.png`): duas arrancadas até ~55 e ~83 km/h com 1ª→4ª/5ª,
  quedas de rotação nas trocas, reduções até parar, aquecimento contínuo, consumo de 1,3 L/h
  parado a ~13 L/h acelerando forte. 7 testes novos (58 no total no Eee PC).

## Interface Fonte (F2.1)

- `painel/fontes/base.py`: `Leitura(t, valores)` imutável (valores num `MappingProxyType`, para o
  app poder guardar a leitura sem cópia); `Fonte` abstrata com `iniciar()`, `parar()`, `ultima()`,
  `ativa`, `leituras` (contador), `erro` (exceção da thread, que não morre calada) e uso com `with`.
  `ultima()` só troca uma referência sob um lock curto: o laço de quadros nunca espera a fonte.
- Duas formas de fonte: `FontePeriodica(hz)` com `amostrar(t)` chamado em instantes absolutos
  (sem deriva; se atrasar mais de um período, recomeça do agora), para simulação e replay; e
  `Fonte._rodar()` livre, publicando com `_publicar()` quando chega dado (UDP, OBD).
- Catálogo `CANAIS` (só leitura), com unidade, faixa e descrição: `rpm`, `velocidade`, `marcha`,
  `temp_motor`, `temp_ar`, `acelerador`, `carga`, `pressao_coletor`, `tensao`, `combustivel_lh`,
  `combustivel_nivel`. As descrições citam o PID do OBD-II de cada um (fase 3).
  `Canal.limitar()` e `canais_desconhecidos()` para validar.
- **Aceite**: 7 testes em `testes/test_fonte_base.py` passam no PC e no Eee PC (51 no total no
  Eee PC). No Windows o `Event.wait` tem resolução de ~15 ms; o teste de ritmo usa 20 Hz.

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
