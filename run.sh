set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ ! -d venv ]; then
    echo "[lopio] Creating virtual enviroment..."
    python3 -m venv venv
fi

source venv/bin/activate

pip install -q -r requirements.txt

echo "[lopio] Starting bot..."
python app.py