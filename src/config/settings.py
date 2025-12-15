"""
Settings management for Kindle to Obsidian.

Handles loading, saving, and providing defaults for all configuration options.
"""

import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def get_config_path() -> Path:
    """Get the path to the config file (next to the main script)."""
    # Go up from src/config to the project root
    return Path(__file__).parent.parent.parent / "config.yaml"


def get_platform_kindle_path() -> str:
    """Get the default Kindle clippings path for the current platform."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return "/Volumes/Kindle/documents/My Clippings.txt"
    elif system == "Windows":
        # Check common drive letters
        for drive in ["D", "E", "F", "G", "H"]:
            path = f"{drive}:\\documents\\My Clippings.txt"
            if os.path.exists(path):
                return path
        # Default to E: if none found
        return "E:\\documents\\My Clippings.txt"
    else:  # Linux
        user = os.environ.get("USER", "user")
        return f"/media/{user}/Kindle/documents/My Clippings.txt"


def get_platform_output_path() -> str:
    """Get a sensible default output path for the current platform."""
    system = platform.system()
    home = Path.home()
    
    if system == "Darwin":  # macOS
        return str(home / "Documents" / "Obsidian" / "Books")
    elif system == "Windows":
        return str(home / "Documents" / "Obsidian" / "Books")
    else:  # Linux
        return str(home / "Documents" / "Obsidian" / "Books")


def get_default_config() -> Dict[str, Any]:
    """Get the default configuration with platform-aware paths."""
    return {
        'paths': {
            'kindle_clippings': get_platform_kindle_path(),
            'output_directory': get_platform_output_path(),
        },
        'output': {
            'min_highlights_for_own_file': 3,
            'short_notes_filename': 'Short Notes.md',
            'default_tag': 'books',
            'short_notes_tag': 'short-notes',
        },
        'frontmatter': {
            'include_author': True,
            'include_tags': True,
        },
    }


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries. Override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def expand_path(path: str) -> str:
    """Expand ~ and environment variables in path."""
    return os.path.expandvars(os.path.expanduser(path))


class Settings:
    """
    Manages application settings with automatic persistence.
    
    Usage:
        settings = Settings()
        settings.load()
        
        # Access settings
        kindle_path = settings.get('paths', 'kindle_clippings')
        
        # Modify settings
        settings.set('paths', 'output_directory', '/new/path')
        settings.save()
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or get_config_path()
        self._config: Dict[str, Any] = get_default_config()
    
    def load(self) -> 'Settings':
        """Load settings from YAML file, merging with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f) or {}
                self._config = deep_merge(get_default_config(), user_config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
                self._config = get_default_config()
        return self
    
    def save(self) -> None:
        """Save current settings to YAML file."""
        # Ensure parent directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a nested config value.
        
        Example:
            settings.get('paths', 'kindle_clippings')
            settings.get('output', 'min_highlights_for_own_file')
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, *args) -> None:
        """
        Set a nested config value.
        
        Example:
            settings.set('paths', 'kindle_clippings', '/new/path')
        """
        if len(args) < 2:
            raise ValueError("Need at least a key and value")
        
        *keys, value = args
        
        # Navigate to parent
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set value
        current[keys[-1]] = value
    
    def get_expanded_path(self, *keys: str) -> str:
        """Get a path value with ~ and env vars expanded."""
        path = self.get(*keys, default='')
        return expand_path(path)
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full config dictionary."""
        return self._config
    
    def detect_kindle(self) -> Optional[str]:
        """
        Try to detect if a Kindle is connected.
        Returns the path if found, None otherwise.
        """
        # Check configured path first
        configured = self.get_expanded_path('paths', 'kindle_clippings')
        if os.path.isfile(configured):
            return configured
        
        # Try platform-specific detection
        system = platform.system()
        
        if system == "Darwin":  # macOS
            path = "/Volumes/Kindle/documents/My Clippings.txt"
            if os.path.isfile(path):
                return path
        elif system == "Windows":
            for drive in ["D", "E", "F", "G", "H"]:
                path = f"{drive}:\\documents\\My Clippings.txt"
                if os.path.isfile(path):
                    return path
        else:  # Linux
            # Try common mount points
            for base in ["/media", "/mnt", "/run/media"]:
                if os.path.isdir(base):
                    for user_dir in os.listdir(base):
                        path = os.path.join(base, user_dir, "Kindle", "documents", "My Clippings.txt")
                        if os.path.isfile(path):
                            return path
        
        return None
    
    def get_output_preview(self) -> Dict[str, int]:
        """
        Get a preview of what's in the output directory.
        Returns dict with 'book_files' and 'total_highlights' counts.
        """
        import re
        
        output_dir = self.get_expanded_path('paths', 'output_directory')
        result = {'book_files': 0, 'total_highlights': 0}
        
        if not os.path.isdir(output_dir):
            return result
        
        hash_pattern = re.compile(r'<a href="kindle:([a-f0-9]{8})"></a>')
        
        for filename in os.listdir(output_dir):
            if filename.endswith('.md'):
                result['book_files'] += 1
                try:
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    result['total_highlights'] += len(hash_pattern.findall(content))
                except:
                    pass
        
        return result
    
    def get_clippings_preview(self) -> Dict[str, int]:
        """
        Get a preview of what's in the clippings file.
        Returns dict with 'books' and 'highlights' counts.
        """
        result = {'books': 0, 'highlights': 0}
        
        path = self.get_expanded_path('paths', 'kindle_clippings')
        if not os.path.isfile(path):
            return result
        
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            # Quick count without full parsing
            boundary = "=========="
            clippings = content.split(boundary)
            
            books = set()
            for clip in clippings:
                clip = clip.strip()
                if not clip:
                    continue
                
                lines = clip.split('\n')
                for line in lines:
                    if line.strip():
                        # First non-empty line is the title
                        books.add(line.strip())
                        break
                
                # Check if it's a highlight or note (not bookmark)
                if '- Your Highlight' in clip or '- Your Note' in clip:
                    result['highlights'] += 1
            
            result['books'] = len(books)
        except:
            pass
        
        return result

