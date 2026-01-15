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
) -> Tuple[int, int, List[Dict]]:
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
        tuple: (new_count, total_count, new_clippings_list)
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
        return 0, len(clippings), []
    
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
    
    return len(new_clippings), len(clippings), new_clippings


def write_short_notes_file(
    short_books: List[Dict[str, Any]],
    output_dir: str,
    existing_hashes: Dict[str, str],
    config: Dict[str, Any],
    dry_run: bool = False,
    log_callback: Optional[Callable[[str], None]] = None
) -> Tuple[int, int, List[Dict[str, Any]]]:
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
        tuple: (new_count, books_processed, list of {book_title, book_author, clippings})
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
    all_new_items: List[Dict[str, Any]] = []
    
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
        
        # Track for import log
        all_new_items.append({
            'book_title': title,
            'book_author': author,
            'clippings': new_clippings
        })
        
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
        return 0, 0, []
    
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
    
    return total_new, books_with_new, all_new_items


def write_import_log(
    new_items: List[Dict[str, Any]],
    output_dir: str,
    config: Dict[str, Any],
    dry_run: bool = False,
    log_callback: Optional[Callable[[str], None]] = None
) -> str:
    """
    Write an import log file with all newly imported highlights.
    
    Creates a timestamped file in an 'Import Logs' subfolder showing
    all highlights and notes that were imported in this sync session.
    
    Args:
        new_items: List of dicts with 'book_title', 'book_author', 'clippings'
        output_dir: Output directory path
        config: Configuration dictionary
        dry_run: If True, don't write files
        log_callback: Optional callback for logging messages
        
    Returns:
        str: Path to the created import log file (or empty if none created)
    """
    from datetime import datetime
    
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
    # Skip if no new items
    total_new = sum(len(item['clippings']) for item in new_items)
    if total_new == 0:
        return ""
    
    # Create subfolder name from config
    log_folder_name = config.get('output', {}).get('import_log_folder', 'Import Logs')
    log_dir = os.path.join(output_dir, log_folder_name)
    
    # Create timestamped filename
    timestamp = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    filename = f"Import {timestamp}.md"
    filepath = os.path.join(log_dir, filename)
    
    # Build content
    lines = []
    
    # Frontmatter
    lines.append('---')
    lines.append(f'imported: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f'total_new: {total_new}')
    lines.append(f'books: {len(new_items)}')
    if config.get('frontmatter', {}).get('include_tags', True):
        lines.append('tags:')
        lines.append('  - import-log')
    lines.append('---')
    lines.append('')
    lines.append(f'# Import Log - {datetime.now().strftime("%B %d, %Y at %H:%M")}')
    lines.append('')
    lines.append(f'**{total_new} new highlights** from **{len(new_items)} books**')
    lines.append('')
    
    # Add each book's new clippings
    for item in sorted(new_items, key=lambda x: x['book_title']):
        title = item['book_title']
        author = item['book_author']
        clippings = item['clippings']
        
        if not clippings:
            continue
        
        lines.append(f'## {title}')
        lines.append(f'*{author}*')
        lines.append('')
        
        for clipping in clippings:
            lines.append('---')
            lines.append(clipping['content'])
            
            # Add nested notes if present
            if 'notes' in clipping and clipping['notes']:
                for note in clipping['notes']:
                    lines.append(f'> {note["content"]}')
            
            lines.append('')
        
        lines.append('---')
        lines.append('')
    
    if not dry_run:
        # Ensure directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        log(f"Import log: {filename}")
    
    return filepath


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
    
    # Collect all new items for import log
    all_new_items: List[Dict[str, Any]] = []
    
    # Process regular books
    total_new = 0
    if regular_books:
        log("Processing book files:")
        for book_key, book_data in sorted(regular_books.items()):
            new_count, total_count, new_clippings = write_book_file(
                book_data, output_dir, existing_hashes, config, dry_run, log_callback
            )
            total_new += new_count
            if new_clippings:
                all_new_items.append({
                    'book_title': book_data['title'],
                    'book_author': book_data['author'],
                    'clippings': new_clippings
                })
        log("")
    
    # Process short books
    if short_books:
        log("Processing short notes:")
        short_new, short_book_count, short_new_items = write_short_notes_file(
            short_books, output_dir, existing_hashes, config, dry_run, log_callback
        )
        total_new += short_new
        all_new_items.extend(short_new_items)
        log("")
    
    # Write import log if there are new items
    import_log_path = ""
    if all_new_items and config.get('output', {}).get('create_import_log', True):
        log("Creating import log:")
        import_log_path = write_import_log(
            all_new_items, output_dir, config, dry_run, log_callback
        )
        log("")
    
    log(f"Done! Added {total_new} new highlights.")
    
    return {
        'total_books': len(books),
        'new_highlights': total_new,
        'regular_books': len(regular_books),
        'short_books': len(short_books),
        'import_log': import_log_path,
    }

