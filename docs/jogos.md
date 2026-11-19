# Jogos de console que podem alimentar o painel

**Português** · [English](#english)

O painel do Dashamp recebe a telemetria que alguns jogos de corrida mandam pela rede local (UDP).
O console e o aparelho com o Dashamp só precisam estar **na mesma rede**, com o aparelho no cabo
ou no Wi-Fi. Não há PC no meio.

Situação de cada jogo (levantamento de novembro de 2026):

| Jogo | Consoles | Situação no Dashamp | Como liga |
| --- | --- | --- | --- |
| **Gran Turismo 7** | PS4, PS5 | ✅ **Suportado e testado** num PS5 de verdade (F2.8) | Nada para configurar no jogo: o Dashamp acha o console sozinho (tecla F2 no Eee PC) |
| **F1 24** (EA/Codemasters) | PS4, PS5, Xbox One, Xbox Series | ✅ **Suportado**, testado com pacotes gerados (sem o jogo) | No jogo: Telemetria UDP ligada, IP do aparelho, porta 20777, formato **2024** |
| **F1 25** | PS5, Xbox Series | ⚠️ Deve funcionar com o formato **2024** escolhido no jogo; o formato 2025 ainda não é lido | Igual ao F1 24 |
| F1 2018 a F1 23 | PS4, PS5, Xbox | 🔶 Possível: mesmo tipo de protocolo, mas cada ano muda o pacote | Telemetria UDP no menu do jogo |
| Gran Turismo Sport | PS4 | 🔶 Possível: protocolo parecido com o do GT7 (versão mais antiga) | Igual ao GT7 |
| Forza Motorsport 7, Forza Horizon 4 e 5, Forza Motorsport (2023) | Xbox One, Xbox Series | 🔶 Possível: o recurso "Data Out" manda UDP para um IP e porta escolhidos | Menu HUD/Jogabilidade → Data Out |
| Forza Horizon 5 | PS5 | ❓ Não confirmado se o "Data Out" existe na versão de PlayStation | — |
| Project CARS 2 | PS4, Xbox One | 🔶 Possível: UDP no formato "Project CARS 2", porta 5606 | Opções → Sistema → UDP |
| Project CARS 3 | PS4, Xbox One | ❓ Há relatos de que o UDP não foi liberado nos consoles | — |
| EA Sports WRC | PS5, Xbox Series | ❌ Telemetria UDP só no PC | — |
| DiRT Rally 2.0 | PS4, Xbox One | ❌ Telemetria só no PC (arquivo de configuração) | — |
| Assetto Corsa Competizione | PS4, PS5, Xbox | ❌ Sem telemetria para fora do console | — |

Legenda: ✅ funciona hoje · ⚠️ funciona com ressalva · 🔶 o jogo manda telemetria, falta escrever
a fonte no Dashamp · ❓ não confirmado · ❌ o jogo não manda telemetria no console.

### O que cada jogo mostra no painel

| Canal | GT7 | F1 24 |
| --- | --- | --- |
| rpm, velocidade, marcha, acelerador | sim | sim |
| temperatura do motor | água | motor |
| nível do tanque | sim | sim |
| consumo (L/h), tensão da bateria | não (o mostrador fica em `---`) | não |

Quando a corrida acaba (ou o jogo pausa, carrega ou para de mandar dados por 1,5 s), rpm,
velocidade, marcha e acelerador voltam ao zero; temperatura e tanque ficam no último valor.

### Quer ajudar com outro jogo?

Uma fonte nova é um arquivo em `painel/fontes/` (veja `gt7.py` e `udp_f1.py`). O mais útil para
começar é uma **gravação dos pacotes** do jogo: rode o painel com `--udp --gravar-udp arquivo.udp`
(ou `--gt7 --gravar-udp`) e abra uma *issue* com o arquivo e o nome do jogo e do console.

Os nomes dos jogos são marcas de seus donos; o Dashamp não tem relação com eles e só lê a
telemetria que os próprios jogos oferecem.

---

## English

# Console games that can feed the dashboard

Dashamp's dashboard reads the telemetry some racing games broadcast on the local network (UDP).
The console and the Dashamp box only need to be on the **same network**; no PC in between.

Status as of November 2026:

| Game | Consoles | Dashamp status | Setup |
| --- | --- | --- | --- |
| **Gran Turismo 7** | PS4, PS5 | ✅ **Supported, tested** on a real PS5 | Nothing to set in the game: Dashamp finds the console (F2 key on the Eee PC) |
| **F1 24** | PS4, PS5, Xbox One/Series | ✅ **Supported**, tested with generated packets | UDP Telemetry on, device IP, port 20777, format **2024** |
| **F1 25** | PS5, Xbox Series | ⚠️ Should work with UDP format **2024** selected; format 2025 not parsed yet | Same as F1 24 |
| F1 2018 – F1 23 | PS4, PS5, Xbox | 🔶 Possible: same kind of protocol, packet layout changes each year | In-game UDP Telemetry menu |
| Gran Turismo Sport | PS4 | 🔶 Possible: older version of the GT7 protocol | Same as GT7 |
| Forza Motorsport 7, Forza Horizon 4 & 5, Forza Motorsport (2023) | Xbox One/Series | 🔶 Possible: "Data Out" sends UDP to a chosen IP and port | HUD/Gameplay → Data Out |
| Forza Horizon 5 | PS5 | ❓ Unconfirmed whether Data Out exists on PlayStation | — |
| Project CARS 2 | PS4, Xbox One | 🔶 Possible: "Project CARS 2" UDP format, port 5606 | Options → System → UDP |
| Project CARS 3 | PS4, Xbox One | ❓ Reports say UDP is not enabled on consoles | — |
| EA Sports WRC | PS5, Xbox Series | ❌ UDP telemetry is PC-only | — |
| DiRT Rally 2.0 | PS4, Xbox One | ❌ PC-only (config file) | — |
| Assetto Corsa Competizione | PS4, PS5, Xbox | ❌ No external telemetry on consoles | — |

Legend: ✅ works today · ⚠️ works with a caveat · 🔶 the game sends telemetry, Dashamp source not
written yet · ❓ unconfirmed · ❌ no console telemetry.

When a race ends (or the game pauses, loads, or stops sending for 1.5 s), rpm, speed, gear and
throttle drop to zero; temperature and fuel keep their last value.

To help with another game, record its packets (`--udp --gravar-udp file.udp`) and open an issue
with the file plus the game and console names. Game names are trademarks of their owners; Dashamp
is not affiliated with them.
