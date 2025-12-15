#!/usr/bin/env python3
"""
Kindle to Obsidian - Extract Kindle highlights and notes to Obsidian markdown files.

Usage:
    python kindle_to_obsidian.py                    # Auto-detect Kindle, use default output
    python kindle_to_obsidian.py -o /path/to/output # Custom output path
    python kindle_to_obsidian.py -i /path/to/file   # Custom input file
"""

import argparse
import hashlib
import os
import re
import unicodedata
from collections import defaultdict
from datetime import datetime

from dateutil.parser import parse as parse_date

# Default paths
DEFAULT_KINDLE_PATH = "/Volumes/Kindle/documents/My Clippings.txt"
DEFAULT_OUTPUT_PATH = "/Users/noah/Documents/Mapping the future/books"

# Clipping boundary
BOUNDARY = "=========="

# Regex patterns
REGEX_TITLE_AUTHOR = re.compile(r'^(.+)\s*\(([^)]+)\)\s*$')
REGEX_INFO = re.compile(r'^- Your (Highlight|Note|Bookmark).*?(?:on page (\d+))?\s*\|?\s*(?:Location (\d+(?:-\d+)?))?\s*\|\s*Added on (.+)$')
REGEX_LOCATION_RANGE = re.compile(r'(\d+)-(\d+)')
REGEX_LOCATION_SINGLE = re.compile(r'(\d+)')
REGEX_KINDLE_HASH = re.compile(r'<a href="kindle:([a-f0-9]{8})"></a>')


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract Kindle highlights and notes to Obsidian markdown files.'
    )
    parser.add_argument(
        '-i', '--input',
        default=None,
        help=f'Path to My Clippings.txt (default: {DEFAULT_KINDLE_PATH})'
    )
    parser.add_argument(
        '-o', '--output',
        default=DEFAULT_OUTPUT_PATH,
        help=f'Output directory (default: {DEFAULT_OUTPUT_PATH})'
    )
    return parser.parse_args()


def get_input_path(custom_path=None):
    """Determine the input file path, checking Kindle mount if needed."""
    if custom_path:
        if os.path.isfile(custom_path):
            return custom_path
        else:
            print(f"Error: Input file not found: {custom_path}")
            return None
    
    # Check if Kindle is connected
    if os.path.isfile(DEFAULT_KINDLE_PATH):
        return DEFAULT_KINDLE_PATH
    
    # Check if Kindle volume exists but file is missing
    if os.path.isdir("/Volumes/Kindle"):
        print("Error: Kindle connected but My Clippings.txt not found at expected location.")
        return None
    
    print("Error: Kindle not connected. Please connect your Kindle or specify input file with -i")
    return None


def sanitize_filename(filename, max_length=128):
    """Create a safe filename from a book title."""
    # Normalize unicode characters
    clean = unicodedata.normalize('NFKD', filename)
    # Remove or replace invalid characters
    clean = re.sub(r'[<>:"/\\|?*]', '', clean)
    # Remove control characters
    clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean)
    # Strip whitespace and dots from ends
    clean = clean.strip().strip('.')
    # Truncate if too long
    if len(clean) > max_length:
        clean = clean[:max_length].rsplit(' ', 1)[0]
    return clean


def generate_hash(content):
    """Generate an 8-character hash for content."""
    return hashlib.sha256(content.strip().encode('utf-8')).hexdigest()[:8]


def parse_clippings(filepath):
    """
    Parse My Clippings.txt and return structured data.
    
    Returns:
        dict: {book_key: {'title': str, 'author': str, 'clippings': [...]}}
    """
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Remove BOM if present
    content = content.replace('\ufeff', '')
    
    # Split by boundary
    raw_clippings = content.split(BOUNDARY)
    
    books = defaultdict(lambda: {'title': '', 'author': '', 'clippings': []})
    
    for raw in raw_clippings:
        raw = raw.strip()
        if not raw:
            continue
        
        lines = raw.split('\n')
        
        # Find title line (first non-empty line)
        title_line = None
        title_idx = 0
        for i, line in enumerate(lines):
            if line.strip():
                title_line = line.strip()
                title_idx = i
                break
        
        if title_line is None:
            continue
        
        # Find info line (next non-empty line after title)
        info_line = None
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
        loc_start = None
        loc_end = None
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
        try:
            parsed_date = parse_date(date_str)
        except:
            parsed_date = None
        
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
        
        # Use title as key (we group by title only for filename purposes)
        book_key = title
        books[book_key]['title'] = title
        books[book_key]['author'] = author
        books[book_key]['clippings'].append(clipping)
    
    return dict(books)


def deduplicate_partial_notes(notes):
    """
    Remove partial notes that are prefixes of longer notes at the same location.
    
    Kindle sometimes saves incremental versions of notes as you type.
    This keeps only the longest/final version.
    """
    if not notes:
        return notes
    
    # Group notes by location
    by_location = defaultdict(list)
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


def link_notes_to_highlights(clippings):
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
            if highlight['loc_start'] <= note['loc_start'] <= (highlight['loc_end'] or highlight['loc_start']):
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


def scan_existing_hashes(output_dir):
    """
    Scan existing markdown files for kindle hash comments.
    
    Returns:
        dict: {hash: filename} mapping
    """
    existing_hashes = {}
    
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


def write_book_file(book_data, output_dir, existing_hashes):
    """
    Write or append to a book's markdown file.
    
    Returns:
        tuple: (new_count, total_count)
    """
    title = book_data['title']
    author = book_data['author']
    clippings = link_notes_to_highlights(book_data['clippings'])
    
    # Filter to only new clippings
    new_clippings = []
    for c in clippings:
        if c['hash'] not in existing_hashes:
            new_clippings.append(c)
        # Also check nested notes
        if 'notes' in c:
            c['notes'] = [n for n in c['notes'] if n['hash'] not in existing_hashes]
    
    if not new_clippings:
        return 0, len(clippings)
    
    # Create filename
    filename = sanitize_filename(title) + '.md'
    filepath = os.path.join(output_dir, filename)
    
    # Check if file exists
    file_exists = os.path.isfile(filepath)
    
    # Build content to write
    lines = []
    
    if not file_exists:
        # Create new file with frontmatter
        lines.append('---')
        lines.append(f'author: "{author}"')
        lines.append('tags:')
        lines.append('  - books')
        lines.append('---')
        lines.append('')
    
    # Add clippings
    for clipping in new_clippings:
        lines.append('---')
        lines.append(f'<a href="kindle:{clipping["hash"]}"></a>')
        lines.append(clipping['content'])
        
        # Add nested notes
        if 'notes' in clipping and clipping['notes']:
            for note in clipping['notes']:
                lines.append(f'<a href="kindle:{note["hash"]}"></a>')
                lines.append(f'> {note["content"]}')
        
        lines.append('')
    
    lines.append('---')
    
    # Write to file
    mode = 'a' if file_exists else 'w'
    with open(filepath, mode, encoding='utf-8') as f:
        if file_exists:
            f.write('\n')  # Add separator if appending
        f.write('\n'.join(lines))
    
    return len(new_clippings), len(clippings)


def write_short_notes_file(short_books, output_dir, existing_hashes):
    """
    Write or append to short_notes.md for books with fewer than 3 highlights.
    
    Returns:
        tuple: (new_count, books_processed)
    """
    filepath = os.path.join(output_dir, 'AAA Notes.md')
    file_exists = os.path.isfile(filepath)
    
    lines = []
    total_new = 0
    books_with_new = 0
    
    if not file_exists:
        # Create new file with frontmatter
        lines.append('---')
        lines.append('tags:')
        lines.append('  - books')
        lines.append('  - short-notes')
        lines.append('---')
        lines.append('')
    
    for book_data in short_books:
        title = book_data['title']
        author = book_data['author']
        clippings = link_notes_to_highlights(book_data['clippings'])
        
        # Filter to only new clippings
        new_clippings = []
        for c in clippings:
            if c['hash'] not in existing_hashes:
                new_clippings.append(c)
            if 'notes' in c:
                c['notes'] = [n for n in c['notes'] if n['hash'] not in existing_hashes]
        
        if not new_clippings:
            continue
        
        books_with_new += 1
        total_new += len(new_clippings)
        
        # Add book section header
        lines.append(f'## {title}')
        lines.append(f'*{author}*')
        lines.append('')
        
        # Add clippings
        for clipping in new_clippings:
            lines.append('---')
            lines.append(f'<a href="kindle:{clipping["hash"]}"></a>')
            lines.append(clipping['content'])
            
            # Add nested notes
            if 'notes' in clipping and clipping['notes']:
                for note in clipping['notes']:
                    lines.append(f'<a href="kindle:{note["hash"]}"></a>')
                    lines.append(f'> {note["content"]}')
            
            lines.append('')
        
        # Add closing divider for last book section
        lines.append('---')
        lines.append('')
    
    if not lines or (file_exists and len(lines) == 0):
        return 0, 0
    
    # Write to file
    mode = 'a' if file_exists else 'w'
    with open(filepath, mode, encoding='utf-8') as f:
        if file_exists and lines:
            f.write('\n')
        f.write('\n'.join(lines))
    
    return total_new, books_with_new


# Minimum highlights for a book to get its own file
MIN_HIGHLIGHTS_FOR_OWN_FILE = 3


def main():
    args = parse_args()
    
    # Get input path
    input_path = get_input_path(args.input)
    if not input_path:
        return 1
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    print(f"Kindle connected: {'Yes' if input_path == DEFAULT_KINDLE_PATH else 'No (using custom file)'}")
    print(f"Reading: {input_path}")
    print(f"Output: {args.output}")
    print()
    
    # Parse clippings
    books = parse_clippings(input_path)
    print(f"Books found: {len(books)}")
    print()
    
    # Scan existing hashes
    existing_hashes = scan_existing_hashes(args.output)
    print(f"Existing highlights in output: {len(existing_hashes)}")
    print()
    
    # Separate books by highlight count
    regular_books = {}
    short_books = []
    
    for book_key, book_data in books.items():
        highlight_count = len([c for c in book_data['clippings'] if c['type'] == 'highlight'])
        if highlight_count >= MIN_HIGHLIGHTS_FOR_OWN_FILE:
            regular_books[book_key] = book_data
        else:
            short_books.append(book_data)
    
    print(f"Books with {MIN_HIGHLIGHTS_FOR_OWN_FILE}+ highlights: {len(regular_books)}")
    print(f"Books with <{MIN_HIGHLIGHTS_FOR_OWN_FILE} highlights (→ short_notes.md): {len(short_books)}")
    print()
    
    # Process regular books (own files)
    total_new = 0
    for book_key, book_data in sorted(regular_books.items()):
        new_count, total_count = write_book_file(book_data, args.output, existing_hashes)
        
        if new_count > 0:
            print(f"  {book_data['title']}: {total_count} highlights ({new_count} new)")
            total_new += new_count
        else:
            print(f"  {book_data['title']}: {total_count} highlights (0 new, skipped)")
    
    # Process short books (combined into short_notes.md)
    if short_books:
        short_new, short_book_count = write_short_notes_file(short_books, args.output, existing_hashes)
        if short_new > 0:
            print(f"  short_notes.md: {short_book_count} books ({short_new} new highlights)")
            total_new += short_new
        elif short_books:
            print(f"  short_notes.md: {len(short_books)} books (0 new, skipped)")
    
    print()
    print(f"Done! Added {total_new} new highlights.")
    return 0


if __name__ == '__main__':
    exit(main())

