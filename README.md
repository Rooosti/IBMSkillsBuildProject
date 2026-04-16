# IBMSkillsBuildProject

Steam recommender project built with a Next.js frontend and a FastAPI backend.

## Prerequisites

Make sure you have these installed:

- Node.js and npm
- Python 3.13
- Docker Desktop (or Docker Engine + Docker Compose)

## Project Structure

- `./` — Next.js frontend
- `./backend` — FastAPI backend
- `./backend/scripts` — database setup and ingestion scripts

## 1. Clone the repository

```bash
git clone https://github.com/Rooosti/IBMSkillsBuildProject.git
cd IBMSkillsBuildProject
```

## 2. Set up the frontend

From the project root:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

The frontend will run at:

```text
http://localhost:3000
```

## 3. Set up the backend

Open a second terminal and move into the backend folder:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

## 4. Create the backend environment file

Create a file named `.env` inside `backend/` and add:

```env
FRONTEND_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
STEAM_OPENID_REALM=http://localhost:8000
STEAM_OPENID_RETURN_TO=http://localhost:8000/api/v1/auth/steam/callback
STEAM_WEB_API_KEY=your_steam_web_api_key
SESSION_SECRET=your_session_secret
COOKIE_SECURE=false

POSTGRES_DB=steamrecommender
POSTGRES_USER=steamapp
POSTGRES_PASSWORD=steamapp_dev_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_API_KEY=your_watsonx_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_MODEL_ID=meta-llama/llama-3-3-70b-instruct
WATSONX_VERIFY_SSL=true
```

## 5. Start PostgreSQL

From `backend/`, run:

```bash
docker compose up -d
```

## 6. Start the FastAPI backend

From `backend/`, with the virtual environment activated, run:

```bash
fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

The backend will run at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/v1/health
```

## 7. Seed the Steam tag taxonomy and query map

Once the database is running and your backend `.env` file is set up, run these commands from `backend/` with the virtual environment activated:

```bash
python -m scripts.ingest_steam_tag_taxonomy
python -m scripts.seed_steam_query_tag_map
```

These commands populate:

- the Steam tag taxonomy
- the Steam query-to-tag mapping used by the app

## 8. If the tag tables do not exist yet

If you run into missing table errors, create the Steam tag tables first:

```bash
python -m scripts.create_steam_tag_tables
```

Then run the seed commands again:

```bash
python -m scripts.ingest_steam_tag_taxonomy
python -m scripts.seed_steam_query_tag_map
```

## Running the full project

You will usually have these running in separate terminals.

### Terminal 1 — frontend

From the repo root:

```bash
npm run dev
```

### Terminal 2 — backend

From `backend/`:

```bash
source .venv/bin/activate
fastapi dev app/main.py --host 0.0.0.0 --port 8000
```

### Terminal 3 — one-time data setup

From `backend/`:

```bash
source .venv/bin/activate
python -m scripts.ingest_steam_tag_taxonomy
python -m scripts.seed_steam_query_tag_map
```

## Notes

- Make sure Docker/Postgres is running before starting the backend.
- Make sure your `.env` file is present in `backend/`.
- Replace placeholder values for `STEAM_WEB_API_KEY`, `SESSION_SECRET`, and Watsonx credentials with real values.
- The backend builds its database URL from the Postgres environment variables, so you do not need to set `DATABASE_URL` separately.
