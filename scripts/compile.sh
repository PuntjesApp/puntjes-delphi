#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
M=.mormot/src
mkdir -p .mormot/build/example
log=.mormot/build/example/fpc.log
if ! fpc -Mdelphi -FU.mormot/build/example -FE.mormot/build \
  -Fi$M -Fu$M/core -Fu$M/net -Fu$M/lib -Fu$M/crypt -Fusrc -Fl.mormot/static/x86_64-linux \
  examples/QuickStart.dpr > "$log" 2>&1; then
  grep -E 'Error|Fatal' "$log" >&2
  exit 1
fi
if grep -E '^puntjes\.[a-z]+\.pas\([0-9,]+\) (Warning|Note):' "$log" >&2; then
  echo "The generated units must compile with no warning or note." >&2
  exit 1
fi
