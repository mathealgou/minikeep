# Mini Keep

Mini Keep is a tiny note-taking backend + UI shipped as one Python file (`server.py`). It serves a responsive HTML interface, a JSON API, and handles storage/logging without extra dependencies.

## Highlights

- One-file deploy: `server.py` includes the HTTP server, API, and embedded HTML/JS/CSS UI.
- Zero third-party deps: only Python standard library (tested with Python 3.10+).
- Threaded HTTP server with JSON API for CRUD + search.
- Autosaving browser UI with multilingual labels (EN/ES/PT) and client-side search.
- Persistent storage to plain `.txt` files under `/data`; automatic log rotation (keeps last 24h) under `/log`.

## Quick start

1. Install Python 3.10+.
2. Run:
   ```bash
   python3 server.py -p 8000
   ```
3. Open http://localhost:8000 to use the UI.

`/data` and `/log` are created on startup if missing. Default bind host is `0.0.0.0`; change the port with `-p` or `--port`.

## Configuration

You can keep settings in a JSON config file (and still override them with CLI flags). Supported keys:

```json
{
	"port": 8100,
	"password": "s3cret",
	"log_retention_hours": 48
}
```

- `--config path/to/config.json` loads the file. CLI flags win over the config file.
- `--password` (or the `password` key) enables a simple shared secret; API calls must send header `X-Password: <value>`. The web UI will prompt once and store it locally.
- `--log-retention-hours` (or `log_retention_hours`) controls how long rotated log files are kept (default 24 hours).

## API

All endpoints are JSON. Names are sanitized to `A-Za-z0-9_.-` and forced to end with `.txt`.

- `GET /` – serves the HTML UI.
- `GET /list_files` – list all notes (most recent first). Response: `{ "files": [{ "name", "content", "modified" }] }` where `modified` is epoch seconds.
- `POST /create_file` – body: `{ "name": "foo", "content": "text" }`; creates `foo.txt`. 400 if exists.
- `POST /update_file` – body: `{ "name": "foo.txt", "content": "new" }`; 400 if missing.
- `POST /delete_file` – body: `{ "name": "foo" | "foo.txt" }`; 400 if missing.
- `POST /search_files` – body: `{ "query": "needle" }`; matches on filename or content (case-insensitive). `GET /search_files?q=...` is also supported.

## Web UI

- Responsive grid of note cards; click to edit.
- Autosave on title/content changes; delete from the modal.
- Language selector (EN/ES/PT); selections are remembered in localStorage.
- Search box issues debounced requests to `/search_files`.

## Data & logging

- Notes live as individual `.txt` files in `/data` (relative to `server.py`).
- Logs are written to `/log/<timestamp>.log`; files older than 24h are purged when new log entries are written.

## Development & tests

- Run the built-in tests:
  ```bash
  python -m unittest test_server.py
  ```
- Test suite spins up the threaded server against temporary `/data` and `/log` directories.

## Deploying the single file

Because everything (server, templates, styles, scripts) is inside `server.py`, distribution is just copying that one file to your target host. Keep the `data/` and `log/` directories writable where you run it; they will be created if missing.
