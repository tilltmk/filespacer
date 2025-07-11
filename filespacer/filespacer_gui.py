#!/usr/bin/env python3

import sys
import os
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Try to import GUI libraries
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    HAS_GUI = True
except ImportError:
    HAS_GUI = False

# Try modern themed tkinter
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *

    HAS_THEME = True
except ImportError:
    HAS_THEME = False

from filespacer import FileSpacer, FileSpacerError, CompressionStats


class ModernFileSpacerGUI:
    """Modern, lightweight GUI for FileSpacer."""

    def __init__(self, root):
        self.root = root
        self.root.title("FileSpacer")
        self.root.geometry("800x600")

        # Set modern theme if available
        if HAS_THEME:
            self.style = ttk.Style("darkly")
        else:
            self.style = ttk.Style()
            self._setup_basic_theme()

        # Variables
        self.current_operation = None
        self.operation_thread = None

        # Setup UI
        self._create_menu()
        self._create_main_ui()
        self._create_status_bar()

        # Initialize FileSpacer
        self.filespacer = FileSpacer(progress_callback=self._progress_callback, logger=self._setup_logger())

        # Bind keyboard shortcuts
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<F1>", lambda e: self._show_help())

    def _setup_logger(self) -> logging.Logger:
        """Setup GUI logger."""
        logger = logging.getLogger("filespacer-gui")
        logger.setLevel(logging.INFO)
        return logger

    def _setup_basic_theme(self):
        """Setup basic modern theme for standard tkinter."""
        self.style.configure("Title.TLabel", font=("Helvetica", 16, "bold"))
        self.style.configure("Heading.TLabel", font=("Helvetica", 12, "bold"))

    def _create_menu(self):
        """Create application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Help", command=self._show_help, accelerator="F1")
        help_menu.add_command(label="About", command=self._show_about)

    def _create_main_ui(self):
        """Create main user interface."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ttk.Label(main_frame, text="FileSpacer", style="Title.TLabel")
        title_label.pack(pady=(0, 20))

        # Operation buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(0, 20))

        self._create_operation_button(
            button_frame, "Extract ZIP", self._show_extract_dialog, "Extract files from ZIP archives", 0
        )

        self._create_operation_button(button_frame, "Compress", self._show_compress_dialog, "Compress files or folders", 1)

        self._create_operation_button(button_frame, "Decompress", self._show_decompress_dialog, "Decompress ZST files", 2)

        # Progress area
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding=10)
        progress_frame.pack(fill="both", expand=True)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=400, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # Output text
        output_frame = ttk.Frame(progress_frame)
        output_frame.pack(fill="both", expand=True)

        self.output_text = tk.Text(
            output_frame,
            height=10,
            wrap="word",
            bg="#2b2b2b" if HAS_THEME else "white",
            fg="#ffffff" if HAS_THEME else "black",
        )
        self.output_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(output_frame, command=self.output_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.output_text.config(yscrollcommand=scrollbar.set)

    def _create_operation_button(self, parent, text, command, tooltip, column):
        """Create an operation button."""
        btn = ttk.Button(parent, text=text, command=command, width=20)
        btn.grid(row=0, column=column, padx=5)

        # Tooltip
        self._create_tooltip(btn, tooltip)

    def _create_tooltip(self, widget, text):
        """Create tooltip for widget."""

        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, "tooltip"):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _create_status_bar(self):
        """Create status bar."""
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")

    def _progress_callback(self, message: str):
        """Handle progress updates from FileSpacer."""
        self.root.after(0, self._update_output, message)

    def _update_output(self, message: str):
        """Update output text widget."""
        self.output_text.insert("end", message)
        self.output_text.see("end")

    def _show_extract_dialog(self):
        """Show extraction dialog."""
        dialog = ExtractDialog(self.root, self.filespacer)
        self.root.wait_window(dialog.dialog)

    def _show_compress_dialog(self):
        """Show compression dialog."""
        dialog = CompressDialog(self.root, self.filespacer)
        self.root.wait_window(dialog.dialog)

    def _show_decompress_dialog(self):
        """Show decompression dialog."""
        dialog = DecompressDialog(self.root, self.filespacer)
        self.root.wait_window(dialog.dialog)

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.root, self.filespacer)
        self.root.wait_window(dialog.dialog)

    def _show_help(self):
        """Show help dialog."""
        help_text = """FileSpacer - File Compression Tool

Operations:
• Extract ZIP: Extract files from ZIP archives with optional password
• Compress: Compress files or folders using Zstandard
• Decompress: Decompress Zstandard (.zst) files

Features:
• High compression ratios with Zstandard
• Progress tracking for all operations
• File integrity verification
• Multi-threaded compression
• Password-protected ZIP support

Keyboard Shortcuts:
• Ctrl+Q: Exit application
• F1: Show this help"""

        messagebox.showinfo("Help", help_text)

    def _show_about(self):
        """Show about dialog."""
        about_text = """FileSpacer v1.0.0

A powerful and modern file compression tool.

© 2024 FileSpacer
https://github.com/tilltmk/filespacer"""

        messagebox.showinfo("About FileSpacer", about_text)


class BaseDialog:
    """Base class for operation dialogs."""

    def __init__(self, parent, filespacer, title):
        self.parent = parent
        self.filespacer = filespacer
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Create UI
        self._create_ui()

        # Bind escape key
        self.dialog.bind("<Escape>", lambda e: self.cancel())

    def _create_ui(self):
        """Override in subclasses."""
        raise NotImplementedError

    def _create_file_selector(self, parent, label, var, is_dir=False, save=False):
        """Create file/directory selector."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)

        ttk.Label(frame, text=label, width=15).pack(side="left")
        ttk.Entry(frame, textvariable=var, width=40).pack(side="left", padx=5)

        def browse():
            if is_dir:
                path = filedialog.askdirectory()
            elif save:
                path = filedialog.asksaveasfilename(defaultextension=".zst")
            else:
                path = filedialog.askopenfilename()

            if path:
                var.set(path)

        ttk.Button(frame, text="Browse", command=browse, width=10).pack(side="left")

    def run_operation(self, operation, *args, **kwargs):
        """Run operation in thread."""

        def worker():
            try:
                self.dialog.after(0, lambda: self.start_button.config(state="disabled"))
                result = operation(*args, **kwargs)
                self.dialog.after(0, lambda: self._operation_complete(True, result))
            except Exception as e:
                self.dialog.after(0, lambda: self._operation_complete(False, str(e)))

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

    def _operation_complete(self, success, result):
        """Handle operation completion."""
        self.start_button.config(state="normal")

        if success:
            messagebox.showinfo("Success", "Operation completed successfully!", parent=self.dialog)
            self.result = result
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", f"Operation failed: {result}", parent=self.dialog)

    def cancel(self):
        """Cancel dialog."""
        self.dialog.destroy()


class ExtractDialog(BaseDialog):
    """ZIP extraction dialog."""

    def __init__(self, parent, filespacer):
        super().__init__(parent, filespacer, "Extract ZIP Archive")

    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # File selectors
        self.zip_var = tk.StringVar()
        self._create_file_selector(main_frame, "ZIP File:", self.zip_var)

        self.output_var = tk.StringVar()
        self._create_file_selector(main_frame, "Output Directory:", self.output_var, is_dir=True)

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
        options_frame.pack(fill="x", pady=10)

        # Password
        pwd_frame = ttk.Frame(options_frame)
        pwd_frame.pack(fill="x", pady=5)
        ttk.Label(pwd_frame, text="Password:", width=15).pack(side="left")
        self.password_var = tk.StringVar()
        ttk.Entry(pwd_frame, textvariable=self.password_var, show="*", width=30).pack(side="left")

        # Exclude patterns
        exclude_frame = ttk.Frame(options_frame)
        exclude_frame.pack(fill="x", pady=5)
        ttk.Label(exclude_frame, text="Exclude:", width=15).pack(side="left")
        self.exclude_var = tk.StringVar()
        ttk.Entry(exclude_frame, textvariable=self.exclude_var, width=30).pack(side="left")
        ttk.Label(exclude_frame, text="(comma-separated)", font=("", 8)).pack(side="left", padx=5)

        # Verify integrity
        self.verify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Verify file integrity", variable=self.verify_var).pack(anchor="w")

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        self.start_button = ttk.Button(button_frame, text="Extract", command=self.extract)
        self.start_button.pack(side="right", padx=5)

        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right")

    def extract(self):
        """Start extraction."""
        if not self.zip_var.get() or not self.output_var.get():
            messagebox.showerror("Error", "Please select input and output paths", parent=self.dialog)
            return

        exclude_list = [e.strip() for e in self.exclude_var.get().split(",") if e.strip()]

        self.run_operation(
            self.filespacer.extract_zip,
            self.zip_var.get(),
            self.output_var.get(),
            exclude_files=exclude_list or None,
            password=self.password_var.get() or None,
            verify_integrity=self.verify_var.get(),
        )


class CompressDialog(BaseDialog):
    """Compression dialog."""

    def __init__(self, parent, filespacer):
        super().__init__(parent, filespacer, "Compress Files")

    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Input selection
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill="x", pady=5)

        ttk.Label(input_frame, text="Input:", width=15).pack(side="left")
        self.input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.input_var, width=40).pack(side="left", padx=5)

        ttk.Button(input_frame, text="File", command=self._select_file, width=8).pack(side="left", padx=2)
        ttk.Button(input_frame, text="Folder", command=self._select_folder, width=8).pack(side="left")

        # Output
        self.output_var = tk.StringVar()
        self._create_file_selector(main_frame, "Output File:", self.output_var, save=True)

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
        options_frame.pack(fill="x", pady=10)

        # Compression level
        level_frame = ttk.Frame(options_frame)
        level_frame.pack(fill="x", pady=5)
        ttk.Label(level_frame, text="Compression Level:", width=20).pack(side="left")

        self.level_var = tk.IntVar(value=3)
        level_scale = ttk.Scale(level_frame, from_=1, to=22, variable=self.level_var, orient="horizontal", length=200)
        level_scale.pack(side="left", padx=5)

        self.level_label = ttk.Label(level_frame, text="3")
        self.level_label.pack(side="left", padx=5)

        def update_level(value):
            self.level_label.config(text=str(int(float(value))))

        level_scale.config(command=update_level)

        # Other options
        self.hash_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Calculate file hash", variable=self.hash_var).pack(anchor="w")

        self.parallel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Use parallel compression", variable=self.parallel_var).pack(anchor="w")

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        self.start_button = ttk.Button(button_frame, text="Compress", command=self.compress)
        self.start_button.pack(side="right", padx=5)

        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right")

    def _select_file(self):
        """Select file for compression."""
        path = filedialog.askopenfilename()
        if path:
            self.input_var.set(path)
            # Suggest output name
            output = str(Path(path).with_suffix(".zst"))
            self.output_var.set(output)

    def _select_folder(self):
        """Select folder for compression."""
        path = filedialog.askdirectory()
        if path:
            self.input_var.set(path)
            # Suggest output name
            folder_name = Path(path).name
            output = str(Path(path).parent / f"{folder_name}.zst")
            self.output_var.set(output)

    def compress(self):
        """Start compression."""
        if not self.input_var.get() or not self.output_var.get():
            messagebox.showerror("Error", "Please select input and output paths", parent=self.dialog)
            return

        input_path = Path(self.input_var.get())

        if input_path.is_file():
            self.run_operation(
                self.filespacer.compress_file,
                input_path,
                self.output_var.get(),
                compression_level=self.level_var.get(),
                calculate_hash=self.hash_var.get(),
            )
        else:
            self.run_operation(
                self.filespacer.compress_folder,
                input_path,
                self.output_var.get(),
                compression_level=self.level_var.get(),
                parallel=self.parallel_var.get(),
            )


class DecompressDialog(BaseDialog):
    """Decompression dialog."""

    def __init__(self, parent, filespacer):
        super().__init__(parent, filespacer, "Decompress ZST File")

    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # File selectors
        self.input_var = tk.StringVar()
        self._create_file_selector(main_frame, "ZST File:", self.input_var)

        self.output_var = tk.StringVar()
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill="x", pady=5)

        ttk.Label(output_frame, text="Output:", width=15).pack(side="left")
        ttk.Entry(output_frame, textvariable=self.output_var, width=40).pack(side="left", padx=5)

        ttk.Button(output_frame, text="File", command=self._select_output_file, width=8).pack(side="left", padx=2)
        ttk.Button(output_frame, text="Folder", command=self._select_output_folder, width=8).pack(side="left")

        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
        options_frame.pack(fill="x", pady=10)

        self.verify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Verify file hash", variable=self.verify_var).pack(anchor="w")

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        self.start_button = ttk.Button(button_frame, text="Decompress", command=self.decompress)
        self.start_button.pack(side="right", padx=5)

        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right")

    def _select_output_file(self):
        """Select output file."""
        path = filedialog.asksaveasfilename()
        if path:
            self.output_var.set(path)

    def _select_output_folder(self):
        """Select output folder."""
        path = filedialog.askdirectory()
        if path:
            self.output_var.set(path)

    def decompress(self):
        """Start decompression."""
        if not self.input_var.get() or not self.output_var.get():
            messagebox.showerror("Error", "Please select input and output paths", parent=self.dialog)
            return

        self.run_operation(
            self.filespacer.extract_zst, self.input_var.get(), self.output_var.get(), verify_hash=self.verify_var.get()
        )


class SettingsDialog(BaseDialog):
    """Settings dialog."""

    def __init__(self, parent, filespacer):
        super().__init__(parent, filespacer, "Settings")

    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Settings
        settings_frame = ttk.LabelFrame(main_frame, text="Configuration", padding=10)
        settings_frame.pack(fill="both", expand=True)

        # Chunk size
        chunk_frame = ttk.Frame(settings_frame)
        chunk_frame.pack(fill="x", pady=5)
        ttk.Label(chunk_frame, text="Chunk Size (KB):", width=20).pack(side="left")
        self.chunk_var = tk.IntVar(value=self.filespacer.chunk_size // 1024)
        ttk.Spinbox(chunk_frame, from_=64, to=16384, textvariable=self.chunk_var, width=10).pack(side="left")

        # Default compression
        comp_frame = ttk.Frame(settings_frame)
        comp_frame.pack(fill="x", pady=5)
        ttk.Label(comp_frame, text="Default Compression:", width=20).pack(side="left")
        self.comp_var = tk.IntVar(value=self.filespacer.config.get("compression_level", 3))
        ttk.Spinbox(comp_frame, from_=1, to=22, textvariable=self.comp_var, width=10).pack(side="left")

        # Threads
        thread_frame = ttk.Frame(settings_frame)
        thread_frame.pack(fill="x", pady=5)
        ttk.Label(thread_frame, text="Parallel Threads:", width=20).pack(side="left")
        self.thread_var = tk.IntVar(value=self.filespacer.config.get("parallel_threads", 4))
        ttk.Spinbox(thread_frame, from_=1, to=32, textvariable=self.thread_var, width=10).pack(side="left")

        # Verify by default
        self.verify_var = tk.BooleanVar(value=self.filespacer.config.get("verify_integrity", True))
        ttk.Checkbutton(settings_frame, text="Verify integrity by default", variable=self.verify_var).pack(anchor="w", pady=5)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right")

    def save_settings(self):
        """Save settings."""
        # Update config
        self.filespacer.config["chunk_size"] = self.chunk_var.get() * 1024
        self.filespacer.config["compression_level"] = self.comp_var.get()
        self.filespacer.config["parallel_threads"] = self.thread_var.get()
        self.filespacer.config["verify_integrity"] = self.verify_var.get()

        # Save to file
        config_dir = Path.home() / ".filespacer"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"

        import json

        with open(config_file, "w") as f:
            json.dump(self.filespacer.config, f, indent=2)

        messagebox.showinfo("Success", "Settings saved successfully!", parent=self.dialog)
        self.dialog.destroy()


def main():
    """Main entry point for GUI."""
    if not HAS_GUI:
        print("Error: tkinter is not available. Please install python3-tk package.")
        print("On Ubuntu/Debian: sudo apt-get install python3-tk")
        print("On Fedora: sudo dnf install python3-tkinter")
        sys.exit(1)

    root = tk.Tk() if not HAS_THEME else ttk.Window(themename="darkly")
    app = ModernFileSpacerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
