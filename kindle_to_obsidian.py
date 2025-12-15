#!/usr/bin/env python3
"""
Kindle to Obsidian - Extract Kindle highlights and notes to Obsidian markdown files.

A GUI application for syncing your Kindle highlights to your Obsidian vault.

Usage:
    python kindle_to_obsidian.py        # Launch GUI
    python kindle_to_obsidian.py --cli  # Run in CLI mode (for automation)
"""

import os
import subprocess
import sys

# Fix for macOS Tcl/Tk version mismatch
if sys.platform == "darwin":
    os.environ["TK_SILENCE_DEPRECATION"] = "1"


def check_tkinter():
    """Check if tkinter is available and working."""
    try:
        import tkinter as tk
        # Create a test window
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


def print_tkinter_help():
    """Print help for fixing tkinter issues."""
    print("\n" + "=" * 60)
    print("  Tkinter GUI not available")
    print("=" * 60)
    print("""
The GUI requires a working Tkinter installation. On your system,
there's a Tcl/Tk compatibility issue.

OPTIONS:

1. Use CLI mode instead:
   python kindle_to_obsidian.py --cli

2. Fix Tkinter by installing tcl-tk via Homebrew and rebuilding Python:
   
   brew install tcl-tk
   pyenv uninstall 3.10.6
   LDFLAGS="-L$(brew --prefix tcl-tk)/lib" \\
   CPPFLAGS="-I$(brew --prefix tcl-tk)/include" \\
   PKG_CONFIG_PATH="$(brew --prefix tcl-tk)/lib/pkgconfig" \\
   pyenv install 3.10.6

3. Or use the official Python installer from python.org
   (includes a compatible Tcl/Tk)
""")
    print("=" * 60)


def main():
    """Main entry point."""
    # Check for CLI mode flag
    if "--cli" in sys.argv or "-c" in sys.argv:
        from src.cli import cli_main
        return cli_main()
    
    # Check if tkinter works (in subprocess to avoid crash)
    if not check_tkinter():
        print_tkinter_help()
        print("\nFalling back to CLI mode...\n")
        from src.cli import cli_main
        return cli_main()
    
    # Launch GUI
    from src.ui.app import App
    app = App()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
