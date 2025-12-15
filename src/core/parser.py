"""
Clippings file parser for Kindle to Obsidian.

Parses My Clippings.txt and returns structured data.
"""

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.parser import parse as parse_date

# Clipping boundary marker
BOUNDARY = "=========="

# Regex patterns
REGEX_TITLE_AUTHOR = re.compile(r'^(.+)\s*\(([^)]+)\)\s*$')
REGEX_INFO = re.compile(
    r'^- Your (Highlight|Note|Bookmark).*?(?:on page (\d+))?\s*\|?\s*'
    r'(?:Location (\d+(?:-\d+)?))?\s*\|\s*Added on (.+)$'
)
REGEX_LOCATION_RANGE = re.compile(r'(\d+)-(\d+)')
REGEX_LOCATION_SINGLE = re.compile(r'(\d+)')
REGEX_KINDLE_HASH = re.compile(r'<a href="kindle:([a-f0-9]{8})"></a>')


def generate_hash(content: str) -> str:
    """Generate an 8-character hash for content."""
    return hashlib.sha256(content.strip().encode('utf-8')).hexdigest()[:8]


def parse_clippings(filepath: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse My Clippings.txt and return structured data.
    
    Args:
        filepath: Path to My Clippings.txt
        
    Returns:
        dict: {book_key: {'title': str, 'author': str, 'clippings': [...]}}
    """
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Remove BOM if present
    content = content.replace('\ufeff', '')
    
    # Split by boundary
    raw_clippings = content.split(BOUNDARY)
    
    books: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {'title': '', 'author': '', 'clippings': []}
    )
    
    for raw in raw_clippings:
        raw = raw.strip()
        if not raw:
            continue
        
        lines = raw.split('\n')
        
        # Find title line (first non-empty line)
        title_line: Optional[str] = None
        title_idx = 0
        for i, line in enumerate(lines):
            if line.strip():
                title_line = line.strip()
                title_idx = i
                break
        
        if title_line is None:
            continue
        
        # Find info line (next non-empty line after title)
        info_line: Optional[str] = None
        info_idx = 0
        for i, line in enumerate(lines[title_idx + 1:], start=title_idx + 1):
            if line.strip():
                info_line = line.strip()
                info_idx = i
                break
        
        if info_line is None:
            continue
        
        # Parse title and author
        title_match = REGEX_TITLE_AUTHOR.match(title_line)
        
        if title_match:
            title = title_match.group(1).strip()
            author = title_match.group(2).strip()
        else:
            title = title_line.strip()
            author = "Unknown"
        
        # Parse info line (type, location, page, date)
        info_match = REGEX_INFO.match(info_line)
        
        if not info_match:
            continue
        
        clip_type = info_match.group(1).lower()  # highlight, note, bookmark
        page = info_match.group(2)
        location = info_match.group(3)
        date_str = info_match.group(4)
        
        # Skip bookmarks
        if clip_type == 'bookmark':
            continue
        
        # Parse location
        loc_start: Optional[int] = None
        loc_end: Optional[int] = None
        if location:
            range_match = REGEX_LOCATION_RANGE.match(location)
            if range_match:
                loc_start = int(range_match.group(1))
                loc_end = int(range_match.group(2))
            else:
                single_match = REGEX_LOCATION_SINGLE.match(location)
                if single_match:
                    loc_start = int(single_match.group(1))
                    loc_end = loc_start
        
        # Parse date
        parsed_date: Optional[datetime] = None
        try:
            parsed_date = parse_date(date_str)
        except:
            pass
        
        # Get content (everything after info line, preserving newlines)
        content_lines = lines[info_idx + 1:]
        # Strip leading/trailing empty lines but preserve internal newlines
        while content_lines and not content_lines[0].strip():
            content_lines.pop(0)
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        content_text = '\n'.join(content_lines)
        
        if not content_text:
            continue
        
        # Skip Kindle DRM limit messages
        if 'You have reached the clipping limit for this item' in content_text:
            continue
        
        # Generate hash
        content_hash = generate_hash(content_text)
        
        # Create clipping object
        clipping = {
            'type': clip_type,
            'content': content_text,
            'hash': content_hash,
            'page': int(page) if page else None,
            'loc_start': loc_start,
            'loc_end': loc_end,
            'date': parsed_date,
        }
        
        # Use title as key
        book_key = title
        books[book_key]['title'] = title
        books[book_key]['author'] = author
        books[book_key]['clippings'].append(clipping)
    
    return dict(books)


def deduplicate_partial_notes(notes: List[Dict]) -> List[Dict]:
    """
    Remove partial notes that are prefixes of longer notes at the same location.
    
    Kindle sometimes saves incremental versions of notes as you type.
    This keeps only the longest/final version.
    """
    if not notes:
        return notes
    
    # Group notes by location
    by_location: Dict[tuple, List[Dict]] = defaultdict(list)
    for note in notes:
        loc_key = (note['loc_start'], note['loc_end'])
        by_location[loc_key].append(note)
    
    result = []
    for loc_key, loc_notes in by_location.items():
        if len(loc_notes) == 1:
            result.extend(loc_notes)
            continue
        
        # Sort by content length (longest first)
        loc_notes.sort(key=lambda x: len(x['content']), reverse=True)
        
        # Keep only notes that aren't prefixes of longer notes
        kept = []
        for note in loc_notes:
            is_prefix = False
            for longer_note in kept:
                if longer_note['content'].startswith(note['content']):
                    is_prefix = True
                    break
            if not is_prefix:
                kept.append(note)
        
        result.extend(kept)
    
    return result


def link_notes_to_highlights(clippings: List[Dict]) -> List[Dict]:
    """
    Link notes to their corresponding highlights based on location.
    
    Returns clippings sorted by location with notes nested under highlights.
    """
    highlights = [c for c in clippings if c['type'] == 'highlight']
    notes = [c for c in clippings if c['type'] == 'note']
    
    # Deduplicate partial notes first
    notes = deduplicate_partial_notes(notes)
    
    # Sort highlights by location
    highlights.sort(key=lambda x: (x['loc_start'] or 0, x['date'] or datetime.min))
    
    # Link notes to highlights
    for highlight in highlights:
        highlight['notes'] = []
        
        if highlight['loc_start'] is None:
            continue
        
        for note in notes:
            if note['loc_start'] is None:
                continue
            
            # Check if note location falls within highlight range
            loc_end = highlight['loc_end'] or highlight['loc_start']
            if highlight['loc_start'] <= note['loc_start'] <= loc_end:
                highlight['notes'].append(note)
    
    # Find unlinked notes (notes that didn't match any highlight)
    linked_note_hashes = set()
    for h in highlights:
        for n in h['notes']:
            linked_note_hashes.add(n['hash'])
    
    unlinked_notes = [n for n in notes if n['hash'] not in linked_note_hashes]
    
    # Add unlinked notes as standalone items
    result = highlights + unlinked_notes
    result.sort(key=lambda x: (x['loc_start'] or 0, x['date'] or datetime.min))
    
    return result


def scan_existing_hashes(output_dir: str) -> Dict[str, str]:
    """
    Scan existing markdown files for kindle hash comments.
    
    Args:
        output_dir: Path to the output directory
        
    Returns:
        dict: {hash: filename} mapping
    """
    import os
    
    existing_hashes: Dict[str, str] = {}
    
    if not os.path.isdir(output_dir):
        return existing_hashes
    
    for filename in os.listdir(output_dir):
        if not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            hashes = REGEX_KINDLE_HASH.findall(content)
            for h in hashes:
                existing_hashes[h] = filename
        except Exception as e:
            print(f"Warning: Could not read {filename}: {e}")
    
    return existing_hashes

