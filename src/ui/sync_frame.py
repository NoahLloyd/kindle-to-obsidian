"""
Sync frame for Kindle to Obsidian GUI.

Provides sync button and log output display.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from ..config.settings import Settings
from ..core.writer import sync_highlights


class SyncFrame(ttk.Frame):
    """Frame for sync button and output log."""
    
    def __init__(
        self,
        parent: tk.Widget,
        settings: Settings,
        get_clippings_path: Callable[[], str],
        get_output_path: Callable[[], str],
        on_sync_complete: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, padding=10)
        
        self.settings = settings
        self.get_clippings_path = get_clippings_path
        self.get_output_path = get_output_path
        self.on_sync_complete = on_sync_complete
        
        self._is_syncing = False
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the UI widgets."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        button_frame.columnconfigure(0, weight=1)
        
        self.sync_button = ttk.Button(
            button_frame,
            text="Sync Highlights",
            command=self._on_sync_click,
            style="Accent.TButton"
        )
        self.sync_button.grid(row=0, column=0, pady=5)
        
        # Progress bar (hidden by default)
        self.progress = ttk.Progressbar(
            button_frame,
            mode='indeterminate',
            length=200
        )
        
        # Log frame
        log_frame = ttk.LabelFrame(self, text="Output Log", padding=5)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text with scrollbar
        self.log_text = tk.Text(
            log_frame,
            height=10,
            width=60,
            wrap="word",
            state="disabled",
            font=("Menlo", 11) if os.name != "nt" else ("Consolas", 10)
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Clear button
        clear_button = ttk.Button(
            log_frame,
            text="Clear Log",
            command=self._clear_log
        )
        clear_button.grid(row=1, column=0, columnspan=2, pady=(5, 0))
    
    def _on_sync_click(self):
        """Handle sync button click."""
        if self._is_syncing:
            return
        
        # Validate paths
        clippings_path = self.get_clippings_path()
        output_path = self.get_output_path()
        
        if not clippings_path:
            messagebox.showerror(
                "Error",
                "Please select a clippings file first."
            )
            return
        
        if not os.path.isfile(clippings_path):
            messagebox.showerror(
                "Error",
                f"Clippings file not found:\n{clippings_path}"
            )
            return
        
        if not output_path:
            messagebox.showerror(
                "Error",
                "Please select an output folder first."
            )
            return
        
        # Start sync in background thread
        self._start_sync(clippings_path, output_path)
    
    def _start_sync(self, clippings_path: str, output_path: str):
        """Start the sync process in a background thread."""
        self._is_syncing = True
        self._set_ui_syncing(True)
        self._clear_log()
        self._log("Starting sync...")
        self._log(f"Input: {clippings_path}")
        self._log(f"Output: {output_path}")
        self._log("")
        
        def run_sync():
            try:
                result = sync_highlights(
                    input_path=clippings_path,
                    output_dir=output_path,
                    config=self.settings.config,
                    dry_run=False,
                    log_callback=self._log_threadsafe
                )
                
                # Notify completion on main thread
                self.after(0, lambda: self._on_sync_finished(result, None))
                
            except Exception as e:
                self.after(0, lambda: self._on_sync_finished(None, str(e)))
        
        thread = threading.Thread(target=run_sync, daemon=True)
        thread.start()
    
    def _on_sync_finished(self, result: Optional[dict], error: Optional[str]):
        """Handle sync completion."""
        self._is_syncing = False
        self._set_ui_syncing(False)
        
        if error:
            self._log("")
            self._log(f"Error: {error}")
            messagebox.showerror("Sync Error", f"An error occurred:\n{error}")
        else:
            self._log("")
            self._log("=" * 40)
            self._log("Sync complete!")
            if result:
                self._log(f"  Books processed: {result['total_books']}")
                self._log(f"  New highlights: {result['new_highlights']}")
        
        # Notify callback
        if self.on_sync_complete:
            self.on_sync_complete()
    
    def _set_ui_syncing(self, syncing: bool):
        """Update UI state for syncing."""
        if syncing:
            self.sync_button.configure(state="disabled", text="Syncing...")
            self.progress.grid(row=1, column=0, pady=5)
            self.progress.start(10)
        else:
            self.sync_button.configure(state="normal", text="Sync Highlights")
            self.progress.stop()
            self.progress.grid_forget()
    
    def _log(self, message: str):
        """Add a message to the log (must be called from main thread)."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
    def _log_threadsafe(self, message: str):
        """Add a message to the log from any thread."""
        self.after(0, lambda: self._log(message))
    
    def _clear_log(self):
        """Clear the log text."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

