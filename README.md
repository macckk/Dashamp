# Dashamp

**Português** · [English](#english)

Dashamp transforma um Linux antigo com tela — um netbook, um Raspberry Pi, um thin client —
em três coisas, nesta ordem:

1. **Player de música** compatível com as skins clássicas do Winamp 2 (`.wsz`), desenhadas pixel a pixel.
2. **Motor de mostradores**: painéis de instrumentos com temas (analógico vintage, digital anos 80,
   moderno) alimentados por qualquer fonte de dados — simulação, replay ou telemetria UDP de jogos de corrida.
3. **Carputer**: o mesmo painel no carro, lendo dados reais via OBD-II (adaptador ELM327), gravando as
   viagens e sincronizando com um servidor.

A máquina de referência é um **ASUS Eee PC 701** (Celeron M 900 MHz, 32 bits, 512 MB–1 GB de RAM,
tela 800×480). Se roda bem nela, roda em praticamente qualquer coisa.

**Status:** em desenvolvimento — veja o andamento em [`PLANO.md`](PLANO.md).

### Pilha

Python 3.11 · pygame-ce (SDL2) · GStreamer · python-OBD · SQLite · FastAPI (servidor) · Debian 12

### Skins

O Dashamp não distribui skins de terceiros. Use as suas ou baixe skins de teste com
`scripts/baixar_skins.sh` (do [Winamp Skin Museum](https://skins.webamp.org/)).
Winamp é marca registrada de seus respectivos donos; este projeto não tem relação com eles.

### Licença

[MIT](LICENSE)

---

## English

Dashamp turns an old Linux box with a screen — a netbook, a Raspberry Pi, a thin client — into:

1. **A music player** that renders classic Winamp 2 skins (`.wsz`) pixel by pixel.
2. **A gauge engine**: themed instrument dashboards (vintage analog, 80s digital, modern) fed by any
   data source — simulation, replay, or UDP telemetry from racing games.
3. **A carputer**: the same dashboard in the car, reading live OBD-II data through an ELM327 adapter,
   logging trips and syncing them to a server.

The reference machine is an **ASUS Eee PC 701** (900 MHz Celeron M, 32-bit, 512 MB–1 GB RAM,
800×480 screen). If it runs well there, it runs almost anywhere.

**Status:** work in progress — see [`PLANO.md`](PLANO.md) (in Portuguese).

Dashamp does not ship third-party skins; fetch test skins with `scripts/baixar_skins.sh`.
Winamp is a trademark of its respective owners; this project is not affiliated with them.

License: [MIT](LICENSE)
