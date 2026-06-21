"""
Тренажёр слов — локальный сервер.

Что делает:
  • отдаёт интерфейс (static/index.html) на http://127.0.0.1:8000
  • хранит прогресс в файле data/state.json
  • фронтенд сам сохраняется после каждого ответа (POST /api/state)

Запуск:
  pip install -r requirements.txt
  python app.py
  (или: uvicorn app:app --reload)
"""

from pathlib import Path
from urllib.parse import quote
import sys
import os
import time
import threading
import json
import urllib.request
import urllib.error

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

# Пути работают и при обычном запуске, и при сборке в .exe через PyInstaller.
#   • статика (read-only) лежит внутри бандла (sys._MEIPASS), когда «заморожено»;
#   • данные (state.json, events.jsonl) пишем рядом с .exe, чтобы прогресс сохранялся.
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys._MEIPASS)              # упакованные ресурсы
    APP_DIR = Path(sys.executable).parent        # папка рядом с .exe — для записи
else:
    BUNDLE_DIR = Path(__file__).parent
    APP_DIR = Path(__file__).parent

STATIC_DIR = BUNDLE_DIR / "static"
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)            # создаём папку для данных, если её нет
STATE_FILE = DATA_DIR / "state.json"
EVENTS_FILE = DATA_DIR / "events.jsonl"  # append-only лог ответов для ML

app = FastAPI(title="Vocab Trainer")

# кэш транскрипций в памяти, чтобы не дёргать словарь повторно
_TR_CACHE: dict[str, str] = {}


@app.get("/api/state")
def get_state():
    """Вернуть сохранённое состояние (или null, если его ещё нет)."""
    if STATE_FILE.exists():
        try:
            return JSONResponse(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except Exception:
            # файл повреждён — начинаем с чистого листа
            return JSONResponse(None)
    return JSONResponse(None)


@app.post("/api/state")
async def set_state(request: Request):
    """Сохранить состояние, присланное фронтендом, в data/state.json."""
    raw = await request.body()
    try:
        json.loads(raw)                  # проверяем, что это валидный JSON
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    STATE_FILE.write_text(raw.decode("utf-8"), encoding="utf-8")
    return {"ok": True}


def _append_events(events):
    """Дописать список событий в data/events.jsonl (по строке на событие)."""
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


@app.post("/api/event")
async def post_event(request: Request):
    """Записать одно событие ответа в лог."""
    try:
        ev = json.loads(await request.body())
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    _append_events([ev])
    return {"ok": True}


@app.post("/api/events")
async def post_events(request: Request):
    """Записать пачку событий (используется для досылки буфера из localStorage)."""
    try:
        events = json.loads(await request.body())
        if not isinstance(events, list):
            raise ValueError
    except Exception:
        return JSONResponse({"ok": False, "error": "expected json array"}, status_code=400)
    _append_events(events)
    return {"ok": True}


@app.get("/api/events.jsonl")
def download_events():
    """Отдать лог ответов файлом (кнопка «Скачать лог»)."""
    if EVENTS_FILE.exists():
        return FileResponse(str(EVENTS_FILE), media_type="application/x-ndjson",
                            filename="events.jsonl")
    # лога ещё нет — отдаём пустой файл, чтобы кнопка не выдавала ошибку
    return PlainTextResponse("", headers={"Content-Disposition": "attachment; filename=events.jsonl"})


@app.post("/api/shutdown")
def shutdown():
    """Корректно завершить локальный сервер (кнопка «Завершить работу»)."""
    def _stop():
        time.sleep(0.4)          # дать ответу дойти до браузера
        os._exit(0)
    threading.Thread(target=_stop, daemon=True).start()
    return {"ok": True}


def _extract_ipa(data):
    """Достать текстовый IPA из ответа dictionaryapi.dev и убрать слэши/скобки."""
    for entry in data:
        cand = entry.get("phonetic")
        if not cand:
            for p in entry.get("phonetics", []):
                if p.get("text"):
                    cand = p["text"]
                    break
        if cand:
            cand = cand.strip()
            if cand and cand[0] in "/[":
                cand = cand[1:]
            if cand and cand[-1] in "/]":
                cand = cand[:-1]
            return cand.strip()
    return ""


@app.get("/api/transcribe")
def transcribe(word: str = ""):
    """Вернуть IPA-транскрипцию слова через бесплатный dictionaryapi.dev.

    Нужен интернет в момент запроса. Результат кэшируется в памяти.
    Если слово не найдено или сети нет — отдаём пустую строку (фронт даст
    вписать руками).
    """
    word = (word or "").strip().lower()
    if not word:
        return {"tr": ""}
    if word in _TR_CACHE:
        return {"tr": _TR_CACHE[word]}
    tr = ""
    try:
        url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + quote(word)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            tr = _extract_ipa(json.load(r))
    except urllib.error.HTTPError:
        tr = ""          # 404 и пр. — слова нет в словаре
    except Exception:
        tr = ""          # нет сети / таймаут — молча отдаём пустое
    _TR_CACHE[word] = tr
    return {"tr": tr}


# Всё остальное (включая "/") отдаём как статику; html=True → "/" вернёт index.html.
# Важно: монтируем ПОСЛЕ объявления /api-маршрутов, иначе они перекроются.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    # порт по умолчанию 8000; можно переопределить переменной окружения PORT
    # (на случай, если 8000 занят другим приложением)
    port = int(os.environ.get("PORT", "8000"))
    # host 127.0.0.1 = только локально. Для доступа из сети поменяй на 0.0.0.0
    uvicorn.run(app, host="127.0.0.1", port=port)
