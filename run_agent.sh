#!/bin/bash

curl -s -X POST http://127.0.0.1:8766/task \
  -H "Content-Type: application/json" \
  -d '{"goal":"'$1'","input":"auto"}' > /dev/null

sleep 1

python auto_patch.py
