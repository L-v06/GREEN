# Green Bot

Green é um bot do Discord para gestão e análise de estatísticas de um grupo de amigos que joga Avalon online. Faz parte de um ecossistema de bots junto com o Pink Bot, responsável pelo registro das partidas.

> **Projeto colaborativo.** A planilha de dados e a coleta de informações foram desenvolvidas por Blue e Sue. O código foi desenvolvido a partir das ideias e necessidades levantadas pelo grupo.

---

## Funcionalidades

- Estatísticas individuais de jogadores com gráficos e embeds paginados
- Estatísticas por papel — cobertura de 34 papéis (17 bons, 17 maus) com autocomplete e busca fuzzy
- Leaderboards gerais com rankings por diferentes métricas
- Rastreamento de sequências de GM
- Sincronização com Google Sheets via API, com cache local em JSON
- Parsing automático dos logs do Pink Bot para atualização da planilha
- Página de ajuda com documentação dos comandos dentro do Discord

---

## Tecnologias

- Python 3
- discord.py
- gspread (Google Sheets API)
- matplotlib
- Arquitetura modular com Cogs

---

## Estrutura

```
GREEN/
├── main.py                  # Inicialização do bot
├── utils_sheets.py          # Leitura da planilha
├── utils_sheet_update.py    # Escrita e atualização da planilha
├── utils_graphs.py          # Geração de gráficos
├── utils_roles.py           # Mapeamento dos 34 papéis
├── utils_config.py          # Configurações gerais
├── Cogs/
│   ├── stats.py             # Estatísticas individuais
│   ├── general_stats.py     # Leaderboards
│   ├── roles_stats.py       # Estatísticas por papel
│   ├── gm_streaks.py        # Sequências de GM
│   ├── gm_track_roles.py    # Rastreamento de papéis por GM
│   ├── update_sheet.py      # Sincronização com Sheets
│   ├── admin_stats.py       # Comandos administrativos
│   ├── help_page.py         # Página de ajuda
│   ├── add_players_ids.py   # Cadastro de jogadores
│   └── error_handler.py     # Tratamento de erros
└── requirements.txt
```

---

## Configuração

1. Clone o repositório
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Crie um arquivo `.env` com as variáveis abaixo:
   ```dotenv
   TOKEN=

   BOT_MODE=prod  # prod ou dev

   # Servidor principal
   PROD_SERVER_ID=
   PROD_STATS_CHANNEL_ID=
   PROD_QUEST_CHAT_ID=
   PROD_ROUND_TABLE_ID=
   PROD_GM_ROLE_ID=
   PROD_EVIL_ROLE_ID=
   PROD_KNIGHTS_OF_THE_ROUND_TABLE_ID=
   PROD_SHEET_NAME=

   # Servidor de teste
   DEV_SERVER_ID=
   DEV_STATS_CHANNEL_ID=
   DEV_QUEST_CHAT_ID=
   DEV_ROUND_TABLE_ID=
   DEV_GM_ROLE_ID=
   DEV_EVIL_ROLE_ID=
   DEV_KNIGHTS_OF_THE_ROUND_TABLE_ID=
   DEV_SHEET_NAME=
   ```
4. Adicione o arquivo `green_credentials.json` com as credenciais da Google Service Account
5. Rode o bot:
   ```bash
   python main.py
   ```

> Para mais detalhes, veja `how_to_start_this_thing_tutorial.md`

---

## Status

Projeto em desenvolvimento ativo — novas funcionalidades são adicionadas conforme o grupo encontra novas formas de explorar os dados.

---

## Créditos

- **Blue** — coleta de dados
- **Sue** — organização dos dados e colaboradora do projeto
- **Lu** — desenvolvimento do código
