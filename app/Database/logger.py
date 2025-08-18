# app/Database/logger.py
import os
from datetime import datetime
from threading import Lock

# /app/app  (um nível acima de app/Database)
APP_DIR  = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR  = os.path.join(APP_DIR, "logs")             # -> /app/app/logs
LOG_FILE = os.path.join(LOG_DIR, "frontend.log")     # -> /app/app/logs/frontend.log

# prints de verificação (1x na importação)
print(f"[logger-init] APP_DIR={APP_DIR}", flush=True)
print(f"[logger-init] LOG_DIR={LOG_DIR}", flush=True)
print(f"[logger-init] LOG_FILE={LOG_FILE}", flush=True)

LOGS = []
_MAX_IN_MEMORY = 2000
_lock = Lock()

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)

    with _lock:
        LOGS.append(line)
        if len(LOGS) > _MAX_IN_MEMORY:
            del LOGS[: len(LOGS) - _MAX_IN_MEMORY]

        try:
            # cria a pasta app/logs se ainda não existir (remove se não quiseres criar automaticamente)
            if not os.path.isdir(LOG_DIR):
                print(f"[logger] Pasta de logs não existe: {LOG_DIR}", flush=True)
            return

            # cria só o ficheiro se necessário e escreve
            if not os.path.exists(LOG_FILE):
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("=== Novo ficheiro de logs criado ===\n")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[logger] Erro a escrever no ficheiro de logs: {e}", flush=True)

def get_logs(limit: int = 500):
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                return [ln.rstrip("\n") for ln in f.readlines()[-limit:]]
    except Exception:
        pass
    return LOGS[-limit:]
