#!/bin/bash
set -euo pipefail

mkdir -p /root/results
python3 /root/solve.py

test -f /root/results/answer.json