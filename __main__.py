#!/usr/bin/env python3

import sys
import os


def main():
    """FileSpacer - Choose between CLI or GUI interface."""
    # Check if running with GUI flag or no arguments
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['--gui', '-g']):
        # Try to launch GUI
        try:
            # Try modern GUI first
            from .filespacer_gui import main as gui_main
            gui_main()
        except ImportError:
            try:
                # Fallback to simple GUI
                from .gui import main as gui_main
                gui_main()
            except ImportError:
                print("Error: GUI dependencies not installed.")
                print("Please install tkinter: sudo apt-get install python3-tk")
                print("\nAlternatively, use the CLI:")
                print("  filespacer-cli --help")
                sys.exit(1)
    else:
        # Use CLI for all other cases
        from .cli import cli
        # Remove the first argument (script name) to let Click handle the rest
        sys.argv[0] = 'filespacer-cli'
        cli()


if __name__ == '__main__':
    main()