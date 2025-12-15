"""
Command-line interface for Kindle to Obsidian.

For automation and non-GUI usage.
"""

import argparse
import sys

from .config.settings import Settings
from .core.writer import sync_highlights


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract Kindle highlights and notes to Obsidian markdown files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python kindle_to_obsidian.py --cli                 Run with saved config
  python kindle_to_obsidian.py --cli -i ~/clips.txt  Use custom input file
  python kindle_to_obsidian.py --cli --dry-run       Preview without writing
        """
    )
    parser.add_argument(
        '-c', '--cli',
        action='store_true',
        help='Run in CLI mode (already implied when using this module)'
    )
    parser.add_argument(
        '-i', '--input',
        default=None,
        help='Path to My Clippings.txt (overrides config)'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output directory (overrides config)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )
    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Show current configuration and exit'
    )
    return parser.parse_args()


def cli_main():
    """Main entry point for CLI mode."""
    args = parse_args()
    
    # Load settings
    settings = Settings()
    settings.load()
    
    # Show config if requested
    if args.show_config:
        import yaml
        print("\nCurrent Configuration:")
        print("=" * 40)
        print(yaml.dump(settings.config, default_flow_style=False, sort_keys=False))
        print(f"Config file: {settings.config_path}")
        return 0
    
    # Get paths
    if args.input:
        input_path = args.input
    else:
        input_path = settings.get_expanded_path('paths', 'kindle_clippings')
        # Try auto-detect
        detected = settings.detect_kindle()
        if detected:
            input_path = detected
    
    output_path = args.output or settings.get_expanded_path('paths', 'output_directory')
    
    # Validate input
    import os
    if not os.path.isfile(input_path):
        print(f"Error: Clippings file not found: {input_path}")
        print("Connect your Kindle or specify a file with -i")
        return 1
    
    # Print header
    print("\n" + "=" * 50)
    print("  Kindle to Obsidian")
    print("=" * 50 + "\n")
    
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    if args.dry_run:
        print("Mode:   DRY RUN (no files will be written)")
    print()
    
    # Run sync
    def log(msg):
        print(msg)
    
    result = sync_highlights(
        input_path=input_path,
        output_dir=output_path,
        config=settings.config,
        dry_run=args.dry_run,
        log_callback=log
    )
    
    print("\n" + "=" * 50)
    if args.dry_run:
        print(f"  Would add {result['new_highlights']} new highlights")
    else:
        print(f"  Added {result['new_highlights']} new highlights")
    print("=" * 50 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())

