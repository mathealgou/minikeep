import argparse
import json
import os
import re
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR = Path(__file__).parent / "log"
LOG_DIR.mkdir(exist_ok=True)
DEFAULT_PORT = 8000
DEFAULT_LOG_RETENTION_HOURS = 24
PASSWORD = ""
LOG_RETENTION_HOURS = DEFAULT_LOG_RETENTION_HOURS

HTML_PAGE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Mini Keep</title>
  <style>
    :root {
      --bg: #2d2a2e;
      --panel: #221f22;
      --accent: #ffd866;
      --muted: #9d9ca1;
      --text: #fcfcfa;
      --border: #403e41;
      --ink: #ab9df2;
      --glow: rgba(255,216,102,0.12);
    }
    * { box-sizing: border-box; }
    html { background: var(--bg); }
    body {
      margin: 0;
      font-family: "Inter", system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      position: relative;
      overflow-x: hidden;
    }
    header {
      padding: 24px 20px 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      position: sticky;
      top: 0;
      background: var(--panel);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--border);
      z-index: 2;
    }
    h1 { margin: 0; font-size: 22px; letter-spacing: 0.4px; }
    .actions { display: flex; gap: 8px; }
    main { padding: 16px 20px 40px; max-width: 1100px; margin: 0 auto; position: relative; z-index: 1; }
    .list { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: border-color 0.15s ease, transform 0.15s ease, background 0.15s ease;
      cursor: pointer;
    }
    .card:hover { border-color: var(--accent); transform: translateY(-2px); background: #2f2c30; box-shadow: 0 8px 24px rgba(0,0,0,0.35); }
    .meta { color: var(--muted); font-size: 12px; }
    .card h3 { margin: 0; font-size: 16px; color: var(--accent); }
    .card pre {
      margin: 0;
      background: #1e1b1e;
      border-radius: 8px;
      padding: 10px;
      border: 1px solid var(--border);
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 13px;
      line-height: 1.4;
      color: #f8f8f2;
      max-height: 180px;
      overflow: hidden;
    }
    .status { font-size: 13px; color: var(--muted); margin: 12px 0; }
    button, input, textarea {
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #1e1b1e;
      color: var(--text);
      padding: 10px 12px;
      font-size: 14px;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    }
    .field input, .field textarea { width: 100%; display: block; }
    textarea { resize: vertical; min-height: 160px; }
    input:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px var(--glow); }
    button.primary {
      cursor: pointer;
      background: var(--accent);
      border: none;
      color: #0b1220;
      font-weight: 700;
      letter-spacing: 0.2px;
    }
    button.secondary { background: #1e1b1e; color: var(--text); border: 1px solid var(--border); cursor: pointer; }
    .pill { padding: 6px 10px; border-radius: 999px; border: 1px solid var(--border); color: var(--muted); font-size: 13px; }
    .topline { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.55);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
      z-index: 5;
    }
    .modal {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      width: min(600px, 100%);
      box-shadow: 0 18px 60px rgba(0,0,0,0.35);
      display: grid;
      gap: 12px;
    }
    .modal header { display: flex; justify-content: space-between; align-items: center; padding: 0; background: none; border: 0; position: static; }
    .modal header h2 { margin: 0; font-size: 17px; }
    .field { display: grid; gap: 6px; }
    .modal footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
    .hint { color: var(--muted); font-size: 12px; }
    @media (max-width: 640px) {
      header { flex-direction: column; align-items: flex-start; }
      h1 { font-size: 18px; }
    }
  </style>
</head>
<body>
  <header>
    <h1 id="appTitle">Mini Keep</h1>
    <div class="actions">
      <input id="searchBox" aria-label="Search notes" />
      <button type="button" class="pill" id="reloadBtn" onclick="refreshNotes()">Reload</button>
      <button type="button" class="primary" id="newBtn" onclick="openModal('create')">New note</button>
      <select id="langSelect" class="pill" aria-label="Language">
        <option value="en">EN</option>
        <option value="es">ES</option>
        <option value="pt">PT</option>
      </select>
    </div>
  </header>
  <main>
    <div class="topline">
      <div class="status" id="count"></div>
      <div class="status" id="status"></div>
    </div>
    <div class="list" id="notes"></div>
  </main>

  <div class="modal-backdrop" id="modalWrap">
    <div class="modal">
      <header>
        <h2 id="modalTitle">New note</h2>
        <button class="secondary" id="closeBtn" onclick="closeModal()">Close</button>
      </header>
      <form id="noteForm">
        <div class="field">
          <label for="noteName" id="labelTitle">Title</label>
          <input id="noteName" required />
          <div class="hint" id="hintStorage">Stored as .txt in /data</div>
        </div>
        <div class="field">
          <label for="noteContent" id="labelContent">Content</label>
          <textarea id="noteContent" rows="8"></textarea>
        </div>
        <footer>
          <button type="button" class="secondary" id="deleteBtn" onclick="handleDelete()" style="display:none">Delete</button>
        </footer>
      </form>
    </div>
  </div>

  <script>
    const notesGrid = document.getElementById('notes');
    const statusEl = document.getElementById('status');
    const countEl = document.getElementById('count');
    const modalWrap = document.getElementById('modalWrap');
    const langSelect = document.getElementById('langSelect');
    const searchBox = document.getElementById('searchBox');
    const noteName = document.getElementById('noteName');
    const noteContent = document.getElementById('noteContent');
    const noteForm = document.getElementById('noteForm');
    const deleteBtn = document.getElementById('deleteBtn');
    const modalTitle = document.getElementById('modalTitle');
    const closeBtn = document.getElementById('closeBtn');
    const labelTitle = document.getElementById('labelTitle');
    const labelContent = document.getElementById('labelContent');
    const hintStorage = document.getElementById('hintStorage');
    const appTitle = document.getElementById('appTitle');
    const reloadBtn = document.getElementById('reloadBtn');
    const newBtn = document.getElementById('newBtn');

    let currentMode = 'create';
    let currentNote = null;
    let searchTimer = null;
    let currentLang = (localStorage.getItem('miniKeepLang') || 'en');
    let authToken = localStorage.getItem('miniKeepPassword') || '';

    const i18n = {
      en: {
        appTitle: 'Mini Keep',
        searchPlaceholder: 'Search notes',
        reload: 'Reload',
        newNote: 'New note',
        modalNew: 'New note',
        modalEdit: 'Edit note',
        close: 'Close',
        title: 'Title',
        content: 'Content',
        storedHint: 'Stored as .txt in /data',
        required: 'is required',
        delete: 'Delete',
        created: 'Created',
        updated: 'Updated',
        deleted: 'Deleted',
        count: '{n} note{p} (most recent first)',
      },
      es: {
        appTitle: 'Mini Keep',
        searchPlaceholder: 'Buscar notas',
        reload: 'Recargar',
        newNote: 'Nueva nota',
        modalNew: 'Nueva nota',
        modalEdit: 'Editar nota',
        close: 'Cerrar',
        title: 'Título',
        content: 'Contenido',
        storedHint: 'Guardado como .txt en /data',
        required: 'es obligatorio',
        delete: 'Eliminar',
        created: 'Creada',
        updated: 'Actualizada',
        deleted: 'Eliminada',
        count: '{n} nota{p} (más recientes primero)',
      },
      pt: {
        appTitle: 'Mini Keep',
        searchPlaceholder: 'Buscar notas',
        reload: 'Recarregar',
        newNote: 'Nova nota',
        modalNew: 'Nova nota',
        modalEdit: 'Editar nota',
        close: 'Fechar',
        title: 'Título',
        content: 'Conteúdo',
        storedHint: 'Salvo como .txt em /data',
        required: 'é obrigatório',
        delete: 'Excluir',
        created: 'Criada',
        updated: 'Atualizada',
        deleted: 'Excluída',
        count: '{n} nota{p} (mais recentes primeiro)',
      },
    };

    function t(key, vars = {}) {
      const catalog = i18n[currentLang] || i18n.en;
        const template = catalog[key] || i18n.en[key] || key; // No functional change; keeping formatting consistent
      return template.replace(/\\{(\\w+)\\}/g, (_, k) => (vars[k] !== undefined ? vars[k] : ''));
    }

    function applyTranslations() {
      document.documentElement.lang = currentLang;
      appTitle.textContent = t('appTitle');
      searchBox.placeholder = t('searchPlaceholder');
      reloadBtn.textContent = t('reload');
      newBtn.textContent = t('newNote');
      modalTitle.textContent = currentMode === 'create' ? t('modalNew') : t('modalEdit');
      closeBtn.textContent = t('close');
      labelTitle.textContent = t('title');
      labelContent.textContent = t('content');
      hintStorage.textContent = t('storedHint');
      deleteBtn.textContent = t('delete');
      langSelect.value = currentLang;
    }

    function setStatus(msg, isError = false) {
      statusEl.textContent = msg || '';
      statusEl.style.color = isError ? '#f87171' : '#9ca3af';
    }

    async function promptForPassword() {
      const input = window.prompt('Enter password');
      authToken = input ? input.trim() : '';
      localStorage.setItem('miniKeepPassword', authToken);
      return authToken;
    }

    async function api(path, body, attempt = 0) {
      const headers = {};
      if (body) headers['Content-Type'] = 'application/json';
      if (authToken) headers['X-Password'] = authToken;
      const opts = body ? { method: 'POST', headers, body: JSON.stringify(body) } : { headers };
      const res = await fetch(path, opts);
      let data = {};
      try {
        data = await res.json();
      } catch (err) {
        data = {};
      }
      if (res.status === 401 && attempt < 1) {
        await promptForPassword();
        return api(path, body, attempt + 1);
      }
      if (!res.ok) throw new Error(data.error || 'Request failed');
      return data;
    }

    function openModal(mode, note = null) {
      currentMode = mode;
      currentNote = note;
      modalTitle.textContent = mode === 'create' ? t('modalNew') : t('modalEdit');
      deleteBtn.style.display = mode === 'edit' ? 'inline-flex' : 'none';
      noteName.disabled = false;
      if (note) {
        noteName.value = note.name.replace(/\\.txt$/, '');
        noteContent.value = note.content;
      } else {
        noteName.value = '';
        noteContent.value = '';
      }
      modalWrap.style.display = 'flex';
      noteName.focus();
    }

    function closeModal() {
      modalWrap.style.display = 'none';
    }

    function formatTime(ts) {
      const d = new Date(ts * 1000);
      return d.toLocaleString();
    }

    function escapeHtml(str) {
      return str.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
    }

    function renderNotes(list) {
      notesGrid.innerHTML = '';
      list.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
          <div class="meta">${formatTime(item.modified)}</div>
          <h3>${item.name.replace(/\\.txt$/, '')}</h3>
          <pre>${escapeHtml(item.content)}</pre>
        `;
        card.addEventListener('click', () => openModal('edit', item));
        notesGrid.appendChild(card);
      });
      const plural = list.length === 1 ? '' : 's';
      countEl.textContent = t('count', { n: list.length, p: plural });
    }

    async function refreshNotes(query = '') {
      try {
        const path = query.trim() ? '/search_files' : '/list_files';
        const data = await api(path, query.trim() ? { query } : undefined);
        renderNotes(data.files);
        setStatus('');
      } catch (err) {
        setStatus(err.message, true);
      }
    }

    let autosaveTimer = null;

    function scheduleSave() {
      if (autosaveTimer) clearTimeout(autosaveTimer);
      autosaveTimer = setTimeout(autoSave, 400);
    }

    async function autoSave() {
      const rawName = noteName.value.trim();
      const content = noteContent.value;
      if (!rawName) {
        setStatus(t('title') + ' ' + t('required') || 'Title required', true);
        return;
      }
      const nameWithExt = rawName.endsWith('.txt') ? rawName : `${rawName}.txt`;
      try {
        if (currentMode === 'create') {
          await api('/create_file', { name: rawName, content });
          currentMode = 'edit';
          currentNote = { name: nameWithExt, content };
          noteName.disabled = false;
          deleteBtn.style.display = 'inline-flex';
          setStatus(t('created'));
        } else if (currentNote) {
          if (nameWithExt !== currentNote.name) {
            await api('/create_file', { name: rawName, content });
            await api('/delete_file', { name: currentNote.name });
            currentNote = { name: nameWithExt, content };
            setStatus(t('updated'));
          } else {
            await api('/update_file', { name: currentNote.name, content });
            currentNote.content = content;
            setStatus(t('updated'));
          }
        }
        await refreshNotes(searchBox.value);
      } catch (err) {
        setStatus(err.message, true);
      }
    }

    noteForm.addEventListener('submit', (e) => {
      e.preventDefault();
      scheduleSave();
    });

    noteName.addEventListener('input', scheduleSave);
    noteContent.addEventListener('input', scheduleSave);

    async function handleDelete() {
      if (!currentNote) return;
      if (!confirm(`${t('delete')} ${currentNote.name}?`)) return;
      try {
        await api('/delete_file', { name: currentNote.name });
        setStatus(t('deleted'));
        closeModal();
        await refreshNotes(searchBox.value);
      } catch (err) {
        setStatus(err.message, true);
      }
    }

    searchBox.addEventListener('input', (e) => {
      const val = e.target.value;
      if (searchTimer) clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        refreshNotes(val);
      }, 180);
    });

    langSelect.addEventListener('change', (e) => {
      currentLang = e.target.value || 'en';
      localStorage.setItem('miniKeepLang', currentLang);
      applyTranslations();
      refreshNotes(searchBox.value);
    });

    modalWrap.addEventListener('click', (e) => {
      if (e.target === modalWrap) closeModal();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
    });

    applyTranslations();
    refreshNotes();
  </script>
</body>
</html>
"""


def sanitize_name(name: str) -> str:
    base = os.path.basename(name).strip()
    if not base:
        raise ValueError("name is required")
    if not base.endswith(".txt"):
        base += ".txt"
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", base)
    return safe


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid json") from exc


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def load_config(path: str | None) -> dict:
    if not path:
        return {}
    cfg_path = Path(path)
    if not cfg_path.is_file():
        raise FileNotFoundError(f"config file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("config file must contain a JSON object")
    return data


class Handler(BaseHTTPRequestHandler):
  def _is_authorized(self) -> bool:
    if not PASSWORD:
      return True
    provided = self.headers.get("X-Password", "")
    return provided == PASSWORD

  def _require_auth(self) -> bool:
    if self._is_authorized():
      return True
    send_json(self, 401, {"error": "unauthorized"})
    return False

  def log_message(self, format: str, *args) -> None:
    try:
      LOG_DIR.mkdir(exist_ok=True)
      now = datetime.utcnow()
      cutoff = now - timedelta(hours=LOG_RETENTION_HOURS)
      for path in LOG_DIR.glob("*.log"):
        try:
          ts = datetime.fromisoformat(path.stem)
          if ts < cutoff:
            path.unlink(missing_ok=True)
        except Exception:
          continue

      fname = now.isoformat(timespec="seconds").replace(":", "-") + ".log"
      msg = (format % args) if args else format
      msg = msg[:2000]
      (LOG_DIR / fname).write_text(msg + "\n", encoding="utf-8")
    except Exception:
      return

  def do_GET(self) -> None:  # noqa: N802
    parsed = urlparse(self.path)
    if parsed.path == "/":
      self.serve_index()
    elif parsed.path == "/list_files":
      self.list_files()
    elif parsed.path == "/search_files":
      self.search_files()
    else:
      send_json(self, 404, {"error": "not found"})

  def do_POST(self) -> None:  # noqa: N802
    parsed = urlparse(self.path)
    try:
      if parsed.path == "/create_file":
        self.create_file()
      elif parsed.path == "/update_file":
        self.update_file()
      elif parsed.path == "/delete_file":
        self.delete_file()
      elif parsed.path == "/search_files":
        self.search_files()
      else:
        send_json(self, 404, {"error": "not found"})
    except ValueError as exc:
      send_json(self, 400, {"error": str(exc)})

  def serve_index(self) -> None:
    body = HTML_PAGE.encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def list_files(self) -> None:
    if not self._require_auth():
      return
    files = []
    paths = sorted(DATA_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths:
      content = path.read_text(encoding="utf-8")
      files.append({"name": path.name, "content": content, "modified": int(path.stat().st_mtime)})
    send_json(self, 200, {"files": files})

  def search_files(self) -> None:
    if not self._require_auth():
      return
    if self.command == "GET":
      query = urlparse(self.path).query or ""
      q = query.replace("q=", "")
    else:
      payload = read_json_body(self)
      q = payload.get("query", "")
    q = str(q).strip().lower()
    if not q:
      self.list_files()
      return
    files = []
    paths = sorted(DATA_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths:
      content = path.read_text(encoding="utf-8")
      if q in path.name.lower() or q in content.lower():
        files.append({"name": path.name, "content": content, "modified": int(path.stat().st_mtime)})
    send_json(self, 200, {"files": files})

  def create_file(self) -> None:
    if not self._require_auth():
      return
    payload = read_json_body(self)
    name = sanitize_name(payload.get("name", ""))
    content = payload.get("content", "")
    target = DATA_DIR / name
    if target.exists():
      raise ValueError("file already exists")
    target.write_text(str(content), encoding="utf-8")
    send_json(self, 201, {"status": "created", "name": name})

  def update_file(self) -> None:
    if not self._require_auth():
      return
    payload = read_json_body(self)
    name = sanitize_name(payload.get("name", ""))
    content = payload.get("content", "")
    target = DATA_DIR / name
    if not target.exists():
      raise ValueError("file not found")
    target.write_text(str(content), encoding="utf-8")
    send_json(self, 200, {"status": "updated", "name": name})

  def delete_file(self) -> None:
    if not self._require_auth():
      return
    payload = read_json_body(self)
    name = sanitize_name(payload.get("name", ""))
    target = DATA_DIR / name
    if not target.exists():
      raise ValueError("file not found")
    target.unlink()
    send_json(self, 200, {"status": "deleted", "name": name})


def main() -> None:
  parser = argparse.ArgumentParser(description="Minimal notes server")
  parser.add_argument("--config", "-c", type=str, default=None, help="Path to JSON config file")
  parser.add_argument("--port", "-p", type=int, default=None, help="Port to bind (default: 8000)")
  parser.add_argument("--password", "-w", type=str, default=None, help="Password required via X-Password header")
  parser.add_argument(
    "--log-retention-hours",
    type=int,
    default=None,
    help=f"Hours to keep rotated logs (default: {DEFAULT_LOG_RETENTION_HOURS})",
  )
  args = parser.parse_args()

  config = load_config(args.config)

  port = config.get("port") if isinstance(config.get("port"), int) else None
  if args.port is not None:
    port = args.port
  if port is None:
    port = DEFAULT_PORT

  password = config.get("password", "") if isinstance(config, dict) else ""
  if args.password is not None:
    password = args.password

  log_hours = config.get("log_retention_hours") if isinstance(config, dict) else None
  if args.log_retention_hours is not None:
    log_hours = args.log_retention_hours
  if not isinstance(log_hours, int) or log_hours <= 0:
    log_hours = DEFAULT_LOG_RETENTION_HOURS

  global PASSWORD, LOG_RETENTION_HOURS
  PASSWORD = password or ""
  LOG_RETENTION_HOURS = log_hours

  host = "0.0.0.0"
  with ThreadingHTTPServer((host, port), Handler) as httpd:
    print(f"Serving on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
