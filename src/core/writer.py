"""
Markdown file writer for Kindle to Obsidian.

Writes highlights and notes to Obsidian-compatible markdown files.
"""

import os
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple

from .parser import link_notes_to_highlights


def sanitize_filename(filename: str, max_length: int = 128) -> str:
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


def write_book_file(
    book_data: Dict[str, Any],
    output_dir: str,
    existing_hashes: Dict[str, str],
    config: Dict[str, Any],
    dry_run: bool = False,
    log_callback: Optional[Callable[[str], None]] = None
) -> Tuple[int, int]:
    """
    Write or append to a book's markdown file.
    
    Args:
        book_data: Book data with title, author, and clippings
        output_dir: Output directory path
        existing_hashes: Dict of already-exported hashes
        config: Configuration dictionary
        dry_run: If True, don't write files
        log_callback: Optional callback for logging messages
        
    Returns:
        tuple: (new_count, total_count)
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
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
        if config.get('frontmatter', {}).get('include_author', True):
            lines.append(f'author: "{author}"')
        if config.get('frontmatter', {}).get('include_tags', True):
            lines.append('tags:')
            default_tag = config.get('output', {}).get('default_tag', 'books')
            lines.append(f'  - {default_tag}')
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
    
    if not dry_run:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Write to file
        mode = 'a' if file_exists else 'w'
        with open(filepath, mode, encoding='utf-8') as f:
            if file_exists:
                f.write('\n')  # Add separator if appending
            f.write('\n'.join(lines))
        
        log(f"  {title}: {len(new_clippings)} new")
    
    return len(new_clippings), len(clippings)


def write_short_notes_file(
    short_books: List[Dict[str, Any]],
    output_dir: str,
    existing_hashes: Dict[str, str],
    config: Dict[str, Any],
    dry_run: bool = False,
    log_callback: Optional[Callable[[str], None]] = None
) -> Tuple[int, int]:
    """
    Write or append to short_notes.md for books with fewer highlights.
    
    Args:
        short_books: List of book data dicts
        output_dir: Output directory path
        existing_hashes: Dict of already-exported hashes
        config: Configuration dictionary
        dry_run: If True, don't write files
        log_callback: Optional callback for logging messages
        
    Returns:
        tuple: (new_count, books_processed)
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
    filename = config.get('output', {}).get('short_notes_filename', 'Short Notes.md')
    filepath = os.path.join(output_dir, filename)
    file_exists = os.path.isfile(filepath)
    
    lines: List[str] = []
    total_new = 0
    books_with_new = 0
    
    if not file_exists:
        # Create new file with frontmatter
        lines.append('---')
        if config.get('frontmatter', {}).get('include_tags', True):
            lines.append('tags:')
            default_tag = config.get('output', {}).get('default_tag', 'books')
            short_tag = config.get('output', {}).get('short_notes_tag', 'short-notes')
            lines.append(f'  - {default_tag}')
            lines.append(f'  - {short_tag}')
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
    
    if not dry_run:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Write to file
        mode = 'a' if file_exists else 'w'
        with open(filepath, mode, encoding='utf-8') as f:
            if file_exists and lines:
                f.write('\n')
            f.write('\n'.join(lines))
        
        log(f"  {filename}: {total_new} new from {books_with_new} books")
    
    return total_new, books_with_new


def sync_highlights(
    input_path: str,
    output_dir: str,
    config: Dict[str, Any],
    dry_run: bool = False,
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, int]:
    """
    Main sync function - parses clippings and writes markdown files.
    
    Args:
        input_path: Path to My Clippings.txt
        output_dir: Output directory for markdown files
        config: Configuration dictionary
        dry_run: If True, don't write files
        log_callback: Optional callback for logging messages
        
    Returns:
        dict with 'total_books', 'new_highlights', 'regular_books', 'short_books'
    """
    from .parser import parse_clippings, scan_existing_hashes
    
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
    # Parse clippings
    log("Parsing clippings file...")
    books = parse_clippings(input_path)
    log(f"Found {len(books)} books")
    
    # Scan existing hashes
    log("Scanning existing files...")
    existing_hashes = scan_existing_hashes(output_dir)
    log(f"Found {len(existing_hashes)} existing highlights")
    
    # Separate books by highlight count
    min_highlights = config.get('output', {}).get('min_highlights_for_own_file', 3)
    regular_books = {}
    short_books = []
    
    for book_key, book_data in books.items():
        highlight_count = len([c for c in book_data['clippings'] if c['type'] == 'highlight'])
        if highlight_count >= min_highlights:
            regular_books[book_key] = book_data
        else:
            short_books.append(book_data)
    
    log(f"Books with {min_highlights}+ highlights: {len(regular_books)}")
    log(f"Books with <{min_highlights} highlights: {len(short_books)}")
    log("")
    
    # Process regular books
    total_new = 0
    if regular_books:
        log("Processing book files:")
        for book_key, book_data in sorted(regular_books.items()):
            new_count, total_count = write_book_file(
                book_data, output_dir, existing_hashes, config, dry_run, log_callback
            )
            total_new += new_count
        log("")
    
    # Process short books
    if short_books:
        log("Processing short notes:")
        short_new, short_book_count = write_short_notes_file(
            short_books, output_dir, existing_hashes, config, dry_run, log_callback
        )
        total_new += short_new
        log("")
    
    log(f"Done! Added {total_new} new highlights.")
    
    return {
        'total_books': len(books),
        'new_highlights': total_new,
        'regular_books': len(regular_books),
        'short_books': len(short_books),
    }

