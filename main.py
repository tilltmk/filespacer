import customtkinter as ctk
import os
import zipfile
import zlib
import zstandard as zstd
from tkinter import filedialog, messagebox, Tk, END
from tqdm.auto import tqdm
from datetime import datetime
import threading
import io

# Functions for extraction and compression
def extract_zip_excluding(input_zip, output_dir, exclude_file, password=None, output_func=None):
    try:
        with zipfile.ZipFile(input_zip, 'r') as zip_ref:
            if password:
                zip_ref.setpassword(password.encode())
            members = zip_ref.namelist()
            total_members = len(members)
            
            with tqdm(total=total_members, unit='file', desc="Extracting", ncols=70, file=output_func) as progress_bar:
                for member in members:
                    if member != exclude_file:
                        try:
                            zip_ref.extract(member, output_dir)
                        except (zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error) as e:
                            output_func.write(f"Failed to extract {member}: {e}\n")
                    progress_bar.update(1)
        return True
    except FileNotFoundError:
        output_func.write(f"The file {input_zip} does not exist.\n")
        return False
    except zipfile.BadZipFile:
        output_func.write(f"The file {input_zip} is not a zip file.\n")
        return False
    except Exception as e:
        output_func.write(f"An error occurred: {e}\n")
        return False

def compress_file(input_path, output_path, compression_level=3, output_func=None):
    file_size = os.path.getsize(input_path)
    cctx = zstd.ZstdCompressor(level=compression_level)
    
    with open(input_path, 'rb') as input_file, open(output_path, 'wb') as output_file:
        with tqdm(total=file_size, unit='B', unit_scale=True, desc='Compressing', ncols=70, file=output_func) as pbar:
            def update_progress(chunk):
                pbar.update(len(chunk))

            reader = cctx.stream_reader(input_file)
            buffer = bytearray(16384)

            while True:
                read_bytes = reader.readinto(buffer)
                if not read_bytes:
                    break
                output_file.write(buffer[:read_bytes])
                update_progress(read_bytes)

def compress_folder(input_folder, output_path, compression_level=3, output_func=None):
    total_files = sum([len(files) for _, _, files in os.walk(input_folder)])
    
    with open(output_path, 'wb') as output_file:
        cctx = zstd.ZstdCompressor(level=compression_level)
        with cctx.stream_writer(output_file) as compressor:
            with tqdm(total=total_files, unit='file', desc='Compressing', ncols=70, file=output_func) as pbar:
                files_processed = 0

                for root, _, files in os.walk(input_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        with open(file_path, 'rb') as f:
                            compressor.write(f.read())
                        
                        files_processed += 1
                        pbar.update(1)

def extract_zst(input_path, output_folder, output_func=None):
    dctx = zstd.ZstdDecompressor()
    with open(input_path, 'rb') as ifh, open(output_folder, 'wb') as ofh:
        dctx.copy_stream(ifh, ofh)

class TextRedirector(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.last_line = ""

    def write(self, s):
        if '\r' in s:
            self.text_widget.delete("end-1c linestart", "end")
            self.last_line = s.split('\r')[-1]
        else:
            self.last_line += s
        
        if '\n' in s:
            self.text_widget.insert(END, self.last_line)
            self.last_line = ""
        
        self.text_widget.see(END)

    def flush(self):
        if self.last_line:
            self.text_widget.insert(END, self.last_line)
            self.last_line = ""
        self.text_widget.see(END)

# GUI classes and functions
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FileSpacer")
        self.geometry("800x600")

        self.create_widgets()

    def create_widgets(self):
        self.label = ctk.CTkLabel(self, text="FileSpacer", font=("Arial", 24))
        self.label.pack(pady=20)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.extract_tab = self.tabview.add("Extract")
        self.compress_tab = self.tabview.add("Compress")
        self.decode_zst_tab = self.tabview.add("Decode Zstd")

        self.create_extract_tab()
        self.create_compress_tab()
        self.create_decode_zst_tab()

        # Quit Button
        self.quit_button = ctk.CTkButton(self, text="Exit", command=self.quit_program)
        self.quit_button.pack(pady=10)

    def create_extract_tab(self):
        self.extract_frame = ctk.CTkFrame(self.extract_tab)
        self.extract_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.extract_zip_button = ctk.CTkButton(self.extract_frame, text="Retrieve Zip-File", command=self.select_zip_file)
        self.extract_zip_button.pack(pady=10)

        self.exclude_file_entry = ctk.CTkEntry(self.extract_frame, placeholder_text="Exclude File")
        self.exclude_file_entry.pack(pady=10)
        
        self.password_entry = ctk.CTkEntry(self.extract_frame, placeholder_text="Password", show="*")
        self.password_entry.pack(pady=10)

        self.extract_start_button = ctk.CTkButton(self.extract_frame, text="Start Extraction", command=self.start_extraction)
        self.extract_start_button.pack(pady=10)

        self.create_terminal(self.extract_frame)

    def create_compress_tab(self):
        self.compress_frame = ctk.CTkFrame(self.compress_tab)
        self.compress_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.compress_file_button = ctk.CTkButton(self.compress_frame, text="Retrieve File to Compress", command=self.select_compress_file)
        self.compress_file_button.pack(pady=10)

        self.compress_folder_button = ctk.CTkButton(self.compress_frame, text="Retrieve Folder to Compress", command=self.select_compress_folder)
        self.compress_folder_button.pack(pady=10)

        self.compression_level_entry = ctk.CTkSlider(self.compress_frame, from_=1, to=22, number_of_steps=21)
        self.compression_level_entry.set(3)
        self.compression_level_entry.pack(pady=10)

        self.output_path_entry = ctk.CTkEntry(self.compress_frame, placeholder_text="Output Path")
        self.output_path_entry.pack(pady=10)

        self.compress_start_button = ctk.CTkButton(self.compress_frame, text="Start Compression", command=self.start_compression)
        self.compress_start_button.pack(pady=10)

        self.create_terminal(self.compress_frame)

    def create_decode_zst_tab(self):
        self.decode_zst_frame = ctk.CTkFrame(self.decode_zst_tab)
        self.decode_zst_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.decode_zst_button = ctk.CTkButton(self.decode_zst_frame, text="Retrieve Zstandard File", command=self.select_zst_file)
        self.decode_zst_button.pack(pady=10)

        self.decode_output_path_entry = ctk.CTkEntry(self.decode_zst_frame, placeholder_text="Output Path")
        self.decode_output_path_entry.pack(pady=10)

        self.decode_start_button = ctk.CTkButton(self.decode_zst_frame, text="Start Decoding", command=self.start_decoding)
        self.decode_start_button.pack(pady=10)

        self.create_terminal(self.decode_zst_frame)

    def create_terminal(self, parent):
        terminal_frame = ctk.CTkFrame(parent)
        terminal_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.terminal_output = ctk.CTkTextbox(terminal_frame, font=("Courier", 12))
        self.terminal_output.pack(fill="both", expand=True)

    def clear_terminal(self):
        self.terminal_output.delete("1.0", END)

    def select_zip_file(self):
        self.input_zip = filedialog.askopenfilename(title="Select Zip File", filetypes=[("Zip files", "*.zip")])
        if self.input_zip:
            self.output_dir = filedialog.askdirectory(title="Select Output Directory")

    def start_extraction(self):
        if not hasattr(self, 'input_zip') or not hasattr(self, 'output_dir'):
            messagebox.showerror("Error", "Please select a zip file and output directory first.")
            return

        exclude_file = self.exclude_file_entry.get()
        password = self.password_entry.get() or None
        
        start_time = datetime.now()

        thread = threading.Thread(target=lambda: self.run_extract_zip(self.input_zip, self.output_dir, exclude_file, password, start_time))
        thread.start()

    def select_compress_file(self):
        self.input_path = filedialog.askopenfilename(title="Select File to Compress", filetypes=[("All files", "*.*")])
        if self.input_path:
            self.output_path = filedialog.asksaveasfilename(title="Save Compressed File As", defaultextension=".zst", filetypes=[("Zstandard compressed files", "*.zst")])

    def select_compress_folder(self):
        self.input_path = filedialog.askdirectory(title="Select Folder to Compress")
        if self.input_path:
            self.output_path = filedialog.asksaveasfilename(title="Save Compressed File As", defaultextension=".zst", filetypes=[("Zstandard compressed files", "*.zst")])

    def start_compression(self):
        if not hasattr(self, 'input_path') or not hasattr(self, 'output_path'):
            messagebox.showerror("Error", "Please select an input file/folder and output path first.")
            return

        compression_level = int(self.compression_level_entry.get())
        
        start_time = datetime.now()

        if os.path.isfile(self.input_path):
            thread = threading.Thread(target=lambda: self.run_compress_file(self.input_path, self.output_path, compression_level, start_time))
        else:
            thread = threading.Thread(target=lambda: self.run_compress_folder(self.input_path, self.output_path, compression_level, start_time))
        thread.start()

    def select_zst_file(self):
        self.input_path = filedialog.askopenfilename(title="Select Zstandard File", filetypes=[("Zstandard files", "*.zst")])
        if self.input_path:
            self.output_path = filedialog.asksaveasfilename(title="Select Output File", defaultextension="", filetypes=[("All files", "*.*")])

    def start_decoding(self):
        if not hasattr(self, 'input_path') or not hasattr(self, 'output_path'):
            messagebox.showerror("Error", "Please select an input file and output path first.")
            return

        start_time = datetime.now()

        thread = threading.Thread(target=lambda: self.run_extract_zst(self.input_path, self.output_path, start_time))
        thread.start()
        
    def run_compress_folder(self, input_folder, output_path, compression_level, start_time):
        self.clear_terminal()
        compress_folder(input_folder, output_path, compression_level, output_func=TextRedirector(self.terminal_output))
        duration = datetime.now() - start_time
        messagebox.showinfo("Success", f"Compression completed successfully in {duration}!")

    def run_extract_zst(self, input_path, output_path, start_time):
        self.clear_terminal()
        extract_zst(input_path, output_path, output_func=TextRedirector(self.terminal_output))
        duration = datetime.now() - start_time
        messagebox.showinfo("Success", f"Extraction completed successfully in {duration}!")

    def run_compress_file(self, input_path, output_path, compression_level, start_time):
        self.clear_terminal()
        compress_file(input_path, output_path, compression_level, output_func=TextRedirector(self.terminal_output))
        duration = datetime.now() - start_time
        messagebox.showinfo("Success", f"Compression completed successfully in {duration}!")

    def run_extract_zip(self, input_zip, output_dir, exclude_file, password, start_time):
        self.clear_terminal()
        success = extract_zip_excluding(input_zip, output_dir, exclude_file, password, output_func=TextRedirector(self.terminal_output))
        duration = datetime.now() - start_time
        if success:
            messagebox.showinfo("Success", f"Extraction completed successfully in {duration}!")
        else:
            messagebox.showerror("Error", "Extraction failed.")

    def quit_program(self):
        self.quit()
        self.destroy()

if __name__ == "__main__":
    # Must be set before using filedialogs in CustomTkinter
    root = Tk()
    root.withdraw()
    
    ctk.set_appearance_mode("dark")  # Options: "light", "dark", "system" (system default)
    ctk.set_default_color_theme("green")  # Color options: "blue", "green", "dark-blue"
    
    app = App()
    app.mainloop()
