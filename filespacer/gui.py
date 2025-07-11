#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from datetime import datetime
from filespacer import FileSpacer, FileSpacerError, CompressionStats


class FileSpacerGUI:
    """Lightweight GUI for FileSpacer using standard tkinter."""

    def __init__(self, root):
        self.root = root
        self.root.title("FileSpacer")
        self.root.geometry("600x500")

        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs
        self.extract_tab = ttk.Frame(self.notebook)
        self.compress_tab = ttk.Frame(self.notebook)
        self.decompress_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.extract_tab, text="Extract ZIP")
        self.notebook.add(self.compress_tab, text="Compress")
        self.notebook.add(self.decompress_tab, text="Decompress ZST")

        # Initialize tabs
        self._create_extract_tab()
        self._create_compress_tab()
        self._create_decompress_tab()

        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill="x", side="bottom")

        self.filespacer = FileSpacer(progress_callback=self._update_status)

    def _update_status(self, message):
        """Update status bar with progress messages."""
        self.status_var.set(message.strip())
        self.root.update_idletasks()

    def _create_extract_tab(self):
        """Create the ZIP extraction tab."""
        frame = ttk.Frame(self.extract_tab, padding="10")
        frame.pack(fill="both", expand=True)

        # Input file selection
        ttk.Label(frame, text="ZIP File:").grid(row=0, column=0, sticky="w", pady=5)
        self.extract_input_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.extract_input_var, width=40).grid(row=0, column=1, pady=5)
        ttk.Button(frame, text="Browse", command=self._select_zip_file).grid(row=0, column=2, padx=5)

        # Output directory
        ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky="w", pady=5)
        self.extract_output_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.extract_output_var, width=40).grid(row=1, column=1, pady=5)
        ttk.Button(frame, text="Browse", command=self._select_output_dir).grid(row=1, column=2, padx=5)

        # Exclude file
        ttk.Label(frame, text="Exclude File:").grid(row=2, column=0, sticky="w", pady=5)
        self.exclude_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.exclude_var, width=40).grid(row=2, column=1, pady=5)

        # Password
        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky="w", pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, show="*", width=40).grid(row=3, column=1, pady=5)

        # Extract button
        ttk.Button(frame, text="Extract", command=self._extract_zip).grid(row=4, column=1, pady=20)

    def _create_compress_tab(self):
        """Create the compression tab."""
        frame = ttk.Frame(self.compress_tab, padding="10")
        frame.pack(fill="both", expand=True)

        # Input selection
        ttk.Label(frame, text="Input (File/Folder):").grid(row=0, column=0, sticky="w", pady=5)
        self.compress_input_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.compress_input_var, width=40).grid(row=0, column=1, pady=5)
        ttk.Button(frame, text="File", command=self._select_compress_file).grid(row=0, column=2, padx=2)
        ttk.Button(frame, text="Folder", command=self._select_compress_folder).grid(row=0, column=3, padx=2)

        # Output file
        ttk.Label(frame, text="Output File:").grid(row=1, column=0, sticky="w", pady=5)
        self.compress_output_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.compress_output_var, width=40).grid(row=1, column=1, pady=5)

        # Compression level
        ttk.Label(frame, text="Compression Level:").grid(row=2, column=0, sticky="w", pady=5)
        self.level_var = tk.IntVar(value=3)
        level_frame = ttk.Frame(frame)
        level_frame.grid(row=2, column=1, sticky="w")
        ttk.Scale(level_frame, from_=1, to=22, variable=self.level_var, orient="horizontal", length=200).pack(side="left")
        ttk.Label(level_frame, textvariable=self.level_var, width=3).pack(side="left", padx=5)

        # Compress button
        ttk.Button(frame, text="Compress", command=self._compress).grid(row=3, column=1, pady=20)

    def _create_decompress_tab(self):
        """Create the decompression tab."""
        frame = ttk.Frame(self.decompress_tab, padding="10")
        frame.pack(fill="both", expand=True)

        # Input file
        ttk.Label(frame, text="ZST File:").grid(row=0, column=0, sticky="w", pady=5)
        self.decompress_input_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.decompress_input_var, width=40).grid(row=0, column=1, pady=5)
        ttk.Button(frame, text="Browse", command=self._select_zst_file).grid(row=0, column=2, padx=5)

        # Output
        ttk.Label(frame, text="Output:").grid(row=1, column=0, sticky="w", pady=5)
        self.decompress_output_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.decompress_output_var, width=40).grid(row=1, column=1, pady=5)
        ttk.Button(frame, text="Browse", command=self._select_decompress_output).grid(row=1, column=2, padx=5)

        # Decompress button
        ttk.Button(frame, text="Decompress", command=self._decompress).grid(row=2, column=1, pady=20)

    def _select_zip_file(self):
        filename = filedialog.askopenfilename(title="Select ZIP file", filetypes=[("ZIP files", "*.zip")])
        if filename:
            self.extract_input_var.set(filename)

    def _select_output_dir(self):
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.extract_output_var.set(directory)

    def _select_compress_file(self):
        filename = filedialog.askopenfilename(title="Select file to compress")
        if filename:
            self.compress_input_var.set(filename)
            # Suggest output filename
            output = str(Path(filename).with_suffix(".zst"))
            self.compress_output_var.set(output)

    def _select_compress_folder(self):
        directory = filedialog.askdirectory(title="Select folder to compress")
        if directory:
            self.compress_input_var.set(directory)
            # Suggest output filename
            output = str(Path(directory).parent / f"{Path(directory).name}.zst")
            self.compress_output_var.set(output)

    def _select_zst_file(self):
        filename = filedialog.askopenfilename(
            title="Select ZST file", filetypes=[("ZST files", "*.zst"), ("All files", "*.*")]
        )
        if filename:
            self.decompress_input_var.set(filename)
            # Suggest output
            if filename.endswith(".zst"):
                output = filename[:-4]
            else:
                output = filename + ".out"
            self.decompress_output_var.set(output)

    def _select_decompress_output(self):
        # Check if input looks like a folder archive
        input_file = self.decompress_input_var.get()
        if "folder" in input_file.lower() or "dir" in input_file.lower():
            directory = filedialog.askdirectory(title="Select output directory")
            if directory:
                self.decompress_output_var.set(directory)
        else:
            filename = filedialog.asksaveasfilename(title="Save decompressed file as")
            if filename:
                self.decompress_output_var.set(filename)

    def _run_threaded(self, func, *args, **kwargs):
        """Run function in a separate thread to keep GUI responsive."""
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()

    def _extract_zip(self):
        input_file = self.extract_input_var.get()
        output_dir = self.extract_output_var.get()

        if not input_file or not output_dir:
            messagebox.showerror("Error", "Please select input file and output directory")
            return

        exclude = self.exclude_var.get() or None
        password = self.password_var.get() or None

        def extract():
            start_time = datetime.now()
            success = self.filespacer.extract_zip(input_file, output_dir, exclude, password)
            duration = datetime.now() - start_time

            if success:
                messagebox.showinfo("Success", f"Extraction completed in {duration}")
            else:
                messagebox.showerror("Error", "Extraction failed")

        self._run_threaded(extract)

    def _compress(self):
        input_path = self.compress_input_var.get()
        output_path = self.compress_output_var.get()

        if not input_path or not output_path:
            messagebox.showerror("Error", "Please select input and output paths")
            return

        level = self.level_var.get()

        def compress():
            start_time = datetime.now()
            input_p = Path(input_path)

            if input_p.is_file():
                success = self.filespacer.compress_file(input_path, output_path, level)
            else:
                success = self.filespacer.compress_folder(input_path, output_path, level)

            duration = datetime.now() - start_time

            if success:
                messagebox.showinfo("Success", f"Compression completed in {duration}")
            else:
                messagebox.showerror("Error", "Compression failed")

        self._run_threaded(compress)

    def _decompress(self):
        input_file = self.decompress_input_var.get()
        output_path = self.decompress_output_var.get()

        if not input_file or not output_path:
            messagebox.showerror("Error", "Please select input file and output path")
            return

        def decompress():
            start_time = datetime.now()
            success = self.filespacer.extract_zst(input_file, output_path)
            duration = datetime.now() - start_time

            if success:
                messagebox.showinfo("Success", f"Decompression completed in {duration}")
            else:
                messagebox.showerror("Error", "Decompression failed")

        self._run_threaded(decompress)


def main():
    root = tk.Tk()
    app = FileSpacerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
