"""
Formatting options frame for Kindle to Obsidian GUI.

Provides controls for customizing output format.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ..config.settings import Settings


class FormattingFrame(ttk.LabelFrame):
    """Frame for formatting and output options."""
    
    def __init__(
        self,
        parent: tk.Widget,
        settings: Settings,
        on_change: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent, text="Formatting Options", padding=10)
        
        self.settings = settings
        self.on_change = on_change
        
        # Variables
        self.min_highlights_var = tk.IntVar()
        self.short_notes_filename_var = tk.StringVar()
        self.default_tag_var = tk.StringVar()
        self.short_notes_tag_var = tk.StringVar()
        self.include_author_var = tk.BooleanVar()
        self.include_tags_var = tk.BooleanVar()
        
        self._create_widgets()
        self._load_from_settings()
    
    def _create_widgets(self):
        """Create the UI widgets."""
        # Configure grid
        self.columnconfigure(1, weight=1)
        
        row = 0
        
        # Min highlights for own file
        ttk.Label(self, text="Min highlights for own file:").grid(
            row=row, column=0, sticky="w", pady=3
        )
        
        min_frame = ttk.Frame(self)
        min_frame.grid(row=row, column=1, sticky="w", pady=3)
        
        self.min_highlights_spinbox = ttk.Spinbox(
            min_frame,
            from_=1,
            to=100,
            width=5,
            textvariable=self.min_highlights_var,
            command=self._on_min_highlights_change
        )
        self.min_highlights_spinbox.grid(row=0, column=0)
        self.min_highlights_spinbox.bind('<FocusOut>', lambda e: self._on_min_highlights_change())
        
        ttk.Label(
            min_frame,
            text="(books with fewer go to short notes file)",
            foreground="gray"
        ).grid(row=0, column=1, padx=(10, 0))
        
        row += 1
        
        # Short notes filename
        ttk.Label(self, text="Short notes filename:").grid(
            row=row, column=0, sticky="w", pady=3
        )
        
        short_frame = ttk.Frame(self)
        short_frame.grid(row=row, column=1, sticky="w", pady=3)
        
        self.short_notes_entry = ttk.Entry(
            short_frame,
            textvariable=self.short_notes_filename_var,
            width=25
        )
        self.short_notes_entry.grid(row=0, column=0)
        self.short_notes_entry.bind('<FocusOut>', lambda e: self._on_short_notes_filename_change())
        self.short_notes_entry.bind('<Return>', lambda e: self._on_short_notes_filename_change())
        
        row += 1
        
        # Separator
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        row += 1
        
        # Default tag
        ttk.Label(self, text="Default tag:").grid(
            row=row, column=0, sticky="w", pady=3
        )
        
        tag_frame = ttk.Frame(self)
        tag_frame.grid(row=row, column=1, sticky="w", pady=3)
        
        self.default_tag_entry = ttk.Entry(
            tag_frame,
            textvariable=self.default_tag_var,
            width=20
        )
        self.default_tag_entry.grid(row=0, column=0)
        self.default_tag_entry.bind('<FocusOut>', lambda e: self._on_default_tag_change())
        self.default_tag_entry.bind('<Return>', lambda e: self._on_default_tag_change())
        
        ttk.Label(
            tag_frame,
            text="(applied to all book files)",
            foreground="gray"
        ).grid(row=0, column=1, padx=(10, 0))
        
        row += 1
        
        # Short notes tag
        ttk.Label(self, text="Short notes tag:").grid(
            row=row, column=0, sticky="w", pady=3
        )
        
        short_tag_frame = ttk.Frame(self)
        short_tag_frame.grid(row=row, column=1, sticky="w", pady=3)
        
        self.short_notes_tag_entry = ttk.Entry(
            short_tag_frame,
            textvariable=self.short_notes_tag_var,
            width=20
        )
        self.short_notes_tag_entry.grid(row=0, column=0)
        self.short_notes_tag_entry.bind('<FocusOut>', lambda e: self._on_short_notes_tag_change())
        self.short_notes_tag_entry.bind('<Return>', lambda e: self._on_short_notes_tag_change())
        
        ttk.Label(
            short_tag_frame,
            text="(additional tag for short notes)",
            foreground="gray"
        ).grid(row=0, column=1, padx=(10, 0))
        
        row += 1
        
        # Separator
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        row += 1
        
        # Frontmatter options
        ttk.Label(self, text="Frontmatter:").grid(
            row=row, column=0, sticky="nw", pady=3
        )
        
        frontmatter_frame = ttk.Frame(self)
        frontmatter_frame.grid(row=row, column=1, sticky="w", pady=3)
        
        self.include_author_check = ttk.Checkbutton(
            frontmatter_frame,
            text="Include author",
            variable=self.include_author_var,
            command=self._on_include_author_change
        )
        self.include_author_check.grid(row=0, column=0, sticky="w")
        
        self.include_tags_check = ttk.Checkbutton(
            frontmatter_frame,
            text="Include tags",
            variable=self.include_tags_var,
            command=self._on_include_tags_change
        )
        self.include_tags_check.grid(row=1, column=0, sticky="w")
    
    def _load_from_settings(self):
        """Load values from settings."""
        self.min_highlights_var.set(
            self.settings.get('output', 'min_highlights_for_own_file', default=3)
        )
        self.short_notes_filename_var.set(
            self.settings.get('output', 'short_notes_filename', default='Short Notes.md')
        )
        self.default_tag_var.set(
            self.settings.get('output', 'default_tag', default='books')
        )
        self.short_notes_tag_var.set(
            self.settings.get('output', 'short_notes_tag', default='short-notes')
        )
        self.include_author_var.set(
            self.settings.get('frontmatter', 'include_author', default=True)
        )
        self.include_tags_var.set(
            self.settings.get('frontmatter', 'include_tags', default=True)
        )
    
    def _save_and_notify(self):
        """Save settings and notify of change."""
        self.settings.save()
        if self.on_change:
            self.on_change()
    
    def _on_min_highlights_change(self):
        """Handle min highlights change."""
        try:
            value = self.min_highlights_var.get()
            if value >= 1:
                self.settings.set('output', 'min_highlights_for_own_file', value)
                self._save_and_notify()
        except tk.TclError:
            pass  # Invalid value, ignore
    
    def _on_short_notes_filename_change(self):
        """Handle short notes filename change."""
        value = self.short_notes_filename_var.get().strip()
        if value:
            if not value.endswith('.md'):
                value += '.md'
                self.short_notes_filename_var.set(value)
            self.settings.set('output', 'short_notes_filename', value)
            self._save_and_notify()
    
    def _on_default_tag_change(self):
        """Handle default tag change."""
        value = self.default_tag_var.get().strip()
        if value:
            self.settings.set('output', 'default_tag', value)
            self._save_and_notify()
    
    def _on_short_notes_tag_change(self):
        """Handle short notes tag change."""
        value = self.short_notes_tag_var.get().strip()
        if value:
            self.settings.set('output', 'short_notes_tag', value)
            self._save_and_notify()
    
    def _on_include_author_change(self):
        """Handle include author checkbox change."""
        self.settings.set('frontmatter', 'include_author', self.include_author_var.get())
        self._save_and_notify()
    
    def _on_include_tags_change(self):
        """Handle include tags checkbox change."""
        self.settings.set('frontmatter', 'include_tags', self.include_tags_var.get())
        self._save_and_notify()

