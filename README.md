# FocusFlow

Focus timer and study planner. Vue 3 + Vite frontend, Flask + SQLite API.

## Running it locally

Two processes, one API and one dev server.

**1. API** (port 5001 — `backend/app.py` is fixed to 5001):

```sh
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python app.py                 # http://127.0.0.1:5001
```

The SQLite file `backend/focusflow.db` is created on first start and is gitignored,
so a fresh checkout starts with an empty database.

**2. Frontend** (port 5173):

```sh
cd frontend
npm ci                        # install exactly what package-lock.json pins
npm run dev                   # http://localhost:5173
```

The dev server proxies `/api/...` to `http://127.0.0.1:5001` (see `frontend/vite.config.js`),
so the API has to listen on **5001**. Starting it with a bare `flask run` uses port 5000
and every request from the app will fail.

## Tests

```sh
cd backend && python -m unittest discover -s tests
cd frontend && npm test
```

## Troubleshooting

- **Vite overlay: "Failed to parse source for import analysis ... invalid JS syntax"**
  The dev server read a file whose contents it cannot parse as JavaScript, usually a
  half-written or locally modified source file (an editor or AI tool rewriting it), or a
  broken dependency install. Check `git status` for local edits and restore the file
  (`git restore <file>`), then reinstall with `npm ci` from the committed
  `package-lock.json` and restart `npm run dev`. If it persists, the file is still
  modified in the working tree — send the file rather than the error.
- **Everything returns 401 / the app still shows a signed-in shell.**
  The stored access token is stale — most often because `backend/focusflow.db` was
  deleted or replaced, which invalidates every token. Use **Clear Local Storage** in the
  dashboard, then log in again. The browser stores the session in localStorage, not the
  server.
- **Saving an edited task failed with HTTP 500.**
  Older revisions crashed in the API when a task's due date was cleared; the current code
  returns 200. Pull the latest revision before debugging.
