#!/bin/zsh
read "msg?> "
payload=$(printf '%s' "$msg" | python3 -c "import json,sys; print(json.dumps({'message': sys.stdin.read()}))")
curl -s -X POST http://127.0.0.1:8766/chat \
  -H "Content-Type: application/json" \
  -d "$payload"
echo
