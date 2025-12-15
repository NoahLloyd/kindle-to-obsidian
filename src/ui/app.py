"""
Main application window for Kindle to Obsidian GUI.

Assembles all UI frames into the main window with scrollable content.
"""

import tkinter as tk
from tkinter import ttk

from ..config.settings import Settings
from .paths_frame import PathsFrame
from .formatting_frame import FormattingFrame
from .sync_frame import SyncFrame


class ScrollableFrame(ttk.Frame):
    """A scrollable frame container."""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind canvas resize to update frame width
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Layout
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel scrolling
        self.bind_mousewheel()
    
    def _on_canvas_configure(self, event):
        """Update the inner frame width when canvas is resized."""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def bind_mousewheel(self):
        """Bind mousewheel events for scrolling."""
        def _on_mousewheel(event):
            # macOS uses event.delta differently
            if event.delta:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                # Linux
                if event.num == 4:
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(1, "units")
        
        # Bind to canvas and all children
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", _on_mousewheel)
        self.canvas.bind_all("<Button-5>", _on_mousewheel)


class App(tk.Tk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Kindle to Obsidian")
        self.minsize(600, 400)
        
        # Center window on screen
        self.geometry("720x650")
        self._center_window()
        
        # Load settings
        self.settings = Settings()
        self.settings.load()
        
        # Configure styles
        self._configure_styles()
        
        # Create UI
        self._create_widgets()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _configure_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        
        # Try to use a modern theme
        available_themes = style.theme_names()
        if "aqua" in available_themes:
            style.theme_use("aqua")
        elif "clam" in available_themes:
            style.theme_use("clam")
        
        # Configure accent button style
        style.configure(
            "Accent.TButton",
            font=("TkDefaultFont", 12, "bold")
        )
    
    def _create_widgets(self):
        """Create the main UI layout with scrolling."""
        # Configure main grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Create scrollable container
        self.scroll_container = ScrollableFrame(self)
        self.scroll_container.pack(fill="both", expand=True)
        
        # Main content frame (inside scrollable area)
        main_frame = ttk.Frame(self.scroll_container.scrollable_frame, padding=15)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Kindle to Obsidian",
            font=("TkDefaultFont", 18, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # Paths frame
        self.paths_frame = PathsFrame(
            main_frame,
            self.settings,
            on_change=self._on_settings_change
        )
        self.paths_frame.pack(fill="x", pady=(0, 10))
        
        # Formatting frame
        self.formatting_frame = FormattingFrame(
            main_frame,
            self.settings,
            on_change=self._on_settings_change
        )
        self.formatting_frame.pack(fill="x", pady=(0, 10))
        
        # Sync frame
        self.sync_frame = SyncFrame(
            main_frame,
            self.settings,
            get_clippings_path=self.paths_frame.get_clippings_path,
            get_output_path=self.paths_frame.get_output_path,
            on_sync_complete=self._on_sync_complete
        )
        self.sync_frame.pack(fill="both", expand=True, pady=(0, 10))
    
    def _on_settings_change(self):
        """Handle settings change."""
        # Settings are auto-saved by the frames
        pass
    
    def _on_sync_complete(self):
        """Handle sync completion."""
        # Refresh previews to show updated counts
        self.paths_frame.refresh_previews()
    
    def _on_close(self):
        """Handle window close."""
        # Save settings before closing
        self.settings.save()
        self.destroy()
    
    def run(self):
        """Run the application main loop."""
        self.mainloop()


def main():
    """Entry point for the GUI application."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
