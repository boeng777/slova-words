#!/usr/bin/env bash
# Запуск тренажёра на Linux / macOS одной командой.
# Проверяет Python, создаёт виртуальное окружение, ставит зависимости, поднимает сервер.
set -e
cd "$(dirname "$0")"

# 1) находим Python 3
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "❌ Python 3 не найден. Поставь его с https://www.python.org/downloads/ и запусти снова."
  exit 1
fi

# 2) виртуальное окружение (изолирует зависимости от системного Python)
if [ ! -d .venv ]; then
  echo "📦 Создаю виртуальное окружение..."
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

# 3) зависимости — ставим один раз (маркер .venv/.deps-ok)
if [ ! -f .venv/.deps-ok ]; then
  echo "⬇️  Устанавливаю зависимости..."
  python -m pip install --upgrade pip >/dev/null
  pip install -r requirements.txt
  touch .venv/.deps-ok
fi

# 4) запуск
echo ""
echo "✅ Сервер запущен. Открой в браузере:  http://127.0.0.1:8000"
echo "   Остановить — Ctrl+C."
echo ""
python app.py
