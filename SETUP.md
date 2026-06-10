# SETUP — pasos exactos para arrancar (modo Mundial)

El repo arranca configurado en **modo Mundial** (`world_cup_enabled=true`,
`world_cup_only_mode=true`, `dry_run=true`). Solo faltan tus claves. Sigue esto
en orden:

## 1. Supabase (~10 min)

1. Crea un proyecto en [supabase.com](https://supabase.com) (plan free vale).
2. SQL Editor → pega y ejecuta el contenido completo de `infra/sql/0001_init.sql`.
3. Authentication → Users → "Add user" → crea tu usuario con email+password
   (el trigger lo da de alta como admin automáticamente).
4. Settings → API → copia estos 3 valores:
   - `Project URL`
   - `anon public` key
   - `service_role` key (⚠️ secreta, solo servidor)

## 2. The Odds API

1. Pide la key gratis en [the-odds-api.com](https://the-odds-api.com).
2. Apúntala — va solo en el worker (`ODDS_API_KEY`).

## 3. Bot de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) → `/newbot` → guarda el **token**.
2. Crea un grupo/canal para las alertas del Mundial y añade el bot.
3. Consigue el **chat id**: añade [@RawDataBot](https://t.me/RawDataBot) al grupo
   un momento, o manda un mensaje y mira
   `https://api.telegram.org/bot<TOKEN>/getUpdates` (los grupos empiezan por `-100`).
4. Guarda el chat id en la base de datos (SQL Editor de Supabase):
   ```sql
   update monitor_segments
   set telegram_chat_id = '-100XXXXXXXXXX'
   where segment_key = 'world_cup';
   ```

## 4. Worker (la pieza que vigila el mercado)

```powershell
cd services/worker
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
# Edita .env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ODDS_API_KEY, TELEGRAM_BOT_TOKEN
python scripts/check_setup.py   # verifica TODO sin gastar créditos de la API
python -m worker.main           # arranca el monitor
```

`check_setup.py` valida: env vars, conexión a Supabase, chat id del Mundial,
key de Odds API (llamada de coste 0), token del bot y que el bot ve el chat.
Si los 6 checks pasan, funciona.

Para producción: despliega `services/worker` en Railway/Fly con el Dockerfile
incluido y las mismas 4 variables de entorno. **Nunca en Vercel.**

## 5. Dashboard web

```powershell
npm install
copy apps\web\.env.example apps\web\.env.local
# Edita .env.local: URL + anon key + service_role de Supabase
npm run dev:web
```

Producción: importa el repo en Vercel, **Root Directory = `apps/web`**, añade
las mismas variables de entorno.

## 6. Salir del modo dry-run

Todo arranca en `dry_run=true`: las alertas se calculan y guardan pero NO se
envían a Telegram. Cuando hayas revisado en el dashboard que las alertas tienen
sentido (1 día de partidos basta), desactívalo desde
**Settings → Football → "Dry run"** (o con el toggle de la API).

## Resumen de claves

| Clave | Dónde va |
|---|---|
| Supabase Project URL | `apps/web/.env.local` + `services/worker/.env` |
| Supabase anon key | solo `apps/web/.env.local` |
| Supabase service_role key | `apps/web/.env.local` (server) + `services/worker/.env` |
| Odds API key | solo `services/worker/.env` |
| Telegram bot token | solo `services/worker/.env` |
| Telegram chat id | tabla `monitor_segments` (SQL del paso 3.4) |
