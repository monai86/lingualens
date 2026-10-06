#!/bin/bash
# PasaScope Desktop GUI Launcher shortcut
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
ROOT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
cd "$ROOT_DIR"

if [ -f "$ROOT_DIR/.venv312/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/.venv312/bin/python"
elif [ -f "$ROOT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
"$PYTHON_BIN" scripts/pasascope_gui.py "$@" 2> >(grep -v -E 'libmpg123|id3\.c' >&2)

