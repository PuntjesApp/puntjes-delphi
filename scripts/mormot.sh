#!/bin/sh
set -eu
TAG=2.4-stable
COMMIT=6dbdf7453e7656c62a2a555c8ff838feabc9c565
STATIC_SHA256=ae2d8da212c5b4f2778370de7aee965f7fd82eef911da27eeb797d6db06db449
cd "$(dirname "$0")/.."
if [ ! -d .mormot/.git ]; then
  git clone --quiet --depth 1 --branch "$TAG" https://github.com/synopse/mORMot2.git .mormot
fi
actual=$(git -C .mormot rev-parse HEAD)
if [ "$actual" != "$COMMIT" ]; then
  echo "mORMot $TAG is at $actual, not the pinned $COMMIT. Someone moved the tag; check it before you change the pin." >&2
  exit 1
fi
if [ ! -d .mormot/static/x86_64-linux ]; then
  curl -fsSL --retry 5 --retry-all-errors -o .mormot/static.tgz \
    "https://github.com/synopse/mORMot2/releases/download/$TAG/mormot2static.tgz"
  echo "$STATIC_SHA256  .mormot/static.tgz" | sha256sum -c --quiet
  mkdir -p .mormot/static
  tar -xzf .mormot/static.tgz -C .mormot/static
  rm .mormot/static.tgz
fi
