#!/bin/bash
# Launcher script for Kindle to Obsidian
cd "$(dirname "$0")"

# Prefer Python 3.12 from pyenv if available (has working Tkinter)
PYTHON_CMD="python3"
if [ -f "$HOME/.pyenv/versions/3.12.4/bin/python" ]; then
    PYTHON_CMD="$HOME/.pyenv/versions/3.12.4/bin/python"
fi

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the app
python kindle_to_obsidian.py "$@"

