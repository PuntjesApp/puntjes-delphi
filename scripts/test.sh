#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
M=.mormot/src
mkdir -p .mormot/build/test
log=.mormot/build/test/fpc.log
if ! fpc -Mdelphi -gl -FU.mormot/build/test -FE.mormot/build/test \
  -Fi$M -Fu$M/core -Fu$M/net -Fu$M/lib -Fu$M/crypt -Fusrc -Fl.mormot/static/x86_64-linux \
  tests/OptionalBody.dpr > "$log" 2>&1; then
  grep -E 'Error|Fatal' "$log" >&2
  exit 1
fi
.mormot/build/test/OptionalBody
