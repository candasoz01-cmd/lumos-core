#!/bin/zsh
cd "$(dirname "$0")/.."

source .venv_lumos/bin/activate

export OPENAI_MODEL=gpt-4.1-mini

python -m kando_bridge.run --port 8766
