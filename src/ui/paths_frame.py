"""
Paths selection frame for Kindle to Obsidian GUI.

Provides file/folder selection with preview information.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional

from ..config.settings import Settings


class PathsFrame(ttk.LabelFrame):
    """Frame for selecting input clippings file and output directory."""
    
    def __init__(
        self,
        parent: tk.Widget,
        settings: Settings,
        on_change: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, text="Paths", padding=10)
        
        self.settings = settings
        self.on_change = on_change
        
        # Variables
        self.clippings_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.clippings_preview_var = tk.StringVar(value="No file selected")
        self.output_preview_var = tk.StringVar(value="No folder selected")
        
        self._create_widgets()
        self._load_from_settings()
    
    def _create_widgets(self):
        """Create the UI widgets."""
        # Configure grid
        self.columnconfigure(1, weight=1)
        
        # Clippings file row
        ttk.Label(self, text="Clippings File:").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        
        clippings_frame = ttk.Frame(self)
        clippings_frame.grid(row=0, column=1, sticky="ew", pady=(0, 2))
        clippings_frame.columnconfigure(0, weight=1)
        
        self.clippings_entry = ttk.Entry(
            clippings_frame,
            textvariable=self.clippings_var,
            width=50
        )
        self.clippings_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.clippings_entry.bind('<FocusOut>', lambda e: self._on_clippings_change())
        self.clippings_entry.bind('<Return>', lambda e: self._on_clippings_change())
        
        ttk.Button(
            clippings_frame,
            text="Browse...",
            command=self._browse_clippings,
            width=10
        ).grid(row=0, column=1)
        
        # Clippings preview
        self.clippings_preview = ttk.Label(
            self,
            textvariable=self.clippings_preview_var,
            foreground="gray"
        )
        self.clippings_preview.grid(row=1, column=1, sticky="w", pady=(0, 10))
        
        # Auto-detect button
        detect_frame = ttk.Frame(self)
        detect_frame.grid(row=2, column=1, sticky="w", pady=(0, 10))
        
        ttk.Button(
            detect_frame,
            text="Auto-detect Kindle",
            command=self._auto_detect_kindle
        ).pack(side="left")
        
        self.detect_status = ttk.Label(detect_frame, text="", foreground="gray")
        self.detect_status.pack(side="left", padx=(10, 0))
        
        # Output folder row
        ttk.Label(self, text="Output Folder:").grid(
            row=3, column=0, sticky="w", pady=(0, 2)
        )
        
        output_frame = ttk.Frame(self)
        output_frame.grid(row=3, column=1, sticky="ew", pady=(0, 2))
        output_frame.columnconfigure(0, weight=1)
        
        self.output_entry = ttk.Entry(
            output_frame,
            textvariable=self.output_var,
            width=50
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.output_entry.bind('<FocusOut>', lambda e: self._on_output_change())
        self.output_entry.bind('<Return>', lambda e: self._on_output_change())
        
        ttk.Button(
            output_frame,
            text="Browse...",
            command=self._browse_output,
            width=10
        ).grid(row=0, column=1)
        
        # Output preview
        self.output_preview = ttk.Label(
            self,
            textvariable=self.output_preview_var,
            foreground="gray"
        )
        self.output_preview.grid(row=4, column=1, sticky="w", pady=(0, 5))
    
    def _load_from_settings(self):
        """Load paths from settings."""
        clippings = self.settings.get('paths', 'kindle_clippings', default='')
        output = self.settings.get('paths', 'output_directory', default='')
        
        self.clippings_var.set(clippings)
        self.output_var.set(output)
        
        self._update_clippings_preview()
        self._update_output_preview()
    
    def _browse_clippings(self):
        """Open file dialog for clippings file."""
        initial_dir = os.path.dirname(self.clippings_var.get()) or os.path.expanduser("~")
        
        filepath = filedialog.askopenfilename(
            title="Select My Clippings.txt",
            initialdir=initial_dir,
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            self.clippings_var.set(filepath)
            self._on_clippings_change()
    
    def _browse_output(self):
        """Open folder dialog for output directory."""
        initial_dir = self.output_var.get() or os.path.expanduser("~")
        
        folderpath = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=initial_dir
        )
        
        if folderpath:
            self.output_var.set(folderpath)
            self._on_output_change()
    
    def _auto_detect_kindle(self):
        """Try to auto-detect connected Kindle."""
        detected = self.settings.detect_kindle()
        
        if detected:
            self.clippings_var.set(detected)
            self._on_clippings_change()
            self.detect_status.config(text="Found!", foreground="green")
        else:
            self.detect_status.config(text="Not found", foreground="red")
        
        # Clear status after 3 seconds
        self.after(3000, lambda: self.detect_status.config(text=""))
    
    def _on_clippings_change(self):
        """Handle clippings path change."""
        path = self.clippings_var.get()
        self.settings.set('paths', 'kindle_clippings', path)
        self.settings.save()
        self._update_clippings_preview()
        
        if self.on_change:
            self.on_change()
    
    def _on_output_change(self):
        """Handle output path change."""
        path = self.output_var.get()
        self.settings.set('paths', 'output_directory', path)
        self.settings.save()
        self._update_output_preview()
        
        if self.on_change:
            self.on_change()
    
    def _update_clippings_preview(self):
        """Update the clippings file preview text."""
        path = self.settings.get_expanded_path('paths', 'kindle_clippings')
        
        if not path:
            self.clippings_preview_var.set("No file selected")
            return
        
        if not os.path.isfile(path):
            self.clippings_preview_var.set("File not found")
            return
        
        preview = self.settings.get_clippings_preview()
        self.clippings_preview_var.set(
            f"Found {preview['books']} books, {preview['highlights']} highlights"
        )
    
    def _update_output_preview(self):
        """Update the output folder preview text."""
        path = self.settings.get_expanded_path('paths', 'output_directory')
        
        if not path:
            self.output_preview_var.set("No folder selected")
            return
        
        if not os.path.isdir(path):
            self.output_preview_var.set("Folder will be created")
            return
        
        preview = self.settings.get_output_preview()
        self.output_preview_var.set(
            f"{preview['book_files']} book files, {preview['total_highlights']} highlights"
        )
    
    def get_clippings_path(self) -> str:
        """Get the expanded clippings file path."""
        return self.settings.get_expanded_path('paths', 'kindle_clippings')
    
    def get_output_path(self) -> str:
        """Get the expanded output directory path."""
        return self.settings.get_expanded_path('paths', 'output_directory')
    
    def refresh_previews(self):
        """Refresh both preview texts."""
        self._update_clippings_preview()
        self._update_output_preview()

