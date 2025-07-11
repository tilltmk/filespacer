![FileSpacer Icon](screenshots/FileSpacer-icon.png)

# FileSpacer

**FileSpacer** is a powerful, modern file compression tool with both CLI and GUI interfaces. It features high-performance Zstandard compression, file integrity verification, and robust error handling.

## 🚀 Features

### Core Features
- **High-Performance Compression**: Uses Zstandard for excellent compression ratios and speed
- **Multiple Interfaces**: Clean CLI with Click and optional lightweight GUI
- **File Integrity**: SHA-256 hash verification for compressed files
- **Parallel Processing**: Multi-threaded compression for faster performance
- **Progress Tracking**: Real-time progress bars for all operations
- **Smart Error Handling**: Comprehensive error messages and recovery options

### Compression Features
- Compress single files or entire folders
- Adjustable compression levels (1-22)
- Exclude patterns for selective compression
- Streaming compression for large files
- Automatic hash calculation and verification

### Extraction Features
- Extract ZIP files with password protection
- Decompress Zstandard (.zst) files
- Extract corrupted ZIP files (best effort)
- Path traversal protection
- Selective file exclusion

## Installation

### From Source
```bash
git clone https://github.com/tilltmk/filespacer.git
cd filespacer
pip install -e .
```

### Requirements
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

FileSpacer provides a powerful CLI with comprehensive options:

#### Extract ZIP Files
```bash
# Basic extraction
filespacer-cli extract archive.zip output_dir/

# With password and exclusions
filespacer-cli extract archive.zip output_dir/ \
  --password mypassword \
  --exclude "*.tmp" \
  --exclude "cache/*"

# Skip integrity verification for speed
filespacer-cli extract archive.zip output_dir/ --no-verify
```

#### Compress Files/Folders
```bash
# Compress a single file
filespacer-cli compress document.pdf document.zst

# Compress with specific level (1-22)
filespacer-cli compress large_file.dat compressed.zst --level 10

# Compress folder with exclusions
filespacer-cli compress my_folder/ backup.zst \
  --exclude "*.log" \
  --exclude "node_modules"

# Show detailed statistics
filespacer-cli compress data/ data.zst --stats
```

#### Decompress ZST Files
```bash
# Decompress single file
filespacer-cli decompress file.zst output.txt

# Decompress folder archive
filespacer-cli decompress folder.zst output_dir/

# Skip hash verification
filespacer-cli decompress file.zst output.txt --no-verify
```

#### Configuration
```bash
# Create user configuration
filespacer-cli config --user

# Show current configuration
filespacer-cli config --show

# Use custom config file
filespacer-cli --config ~/myconfig.json compress file.txt file.zst
```

#### File Information
```bash
# Show information about compressed file
filespacer-cli info compressed.zst
```

### Graphical User Interface

Launch the GUI with:
```bash
# Launch GUI
filespacer --gui

# Or simply
filespacer
```

The GUI provides:
- Intuitive file selection dialogs
- Real-time progress tracking
- Visual compression level adjustment
- Settings management
- Comprehensive error reporting

### Python API

```python
from filespacer import FileSpacer

# Initialize
fs = FileSpacer()

# Compress a file
stats = fs.compress_file('input.txt', 'output.zst', compression_level=5)
print(f"Compression ratio: {stats.compression_ratio:.2f}:1")

# Compress a folder
stats = fs.compress_folder('my_folder/', 'backup.zst', 
                          exclude_patterns=['*.tmp', '*.log'])

# Extract ZIP
fs.extract_zip('archive.zip', 'output_dir/', 
               exclude_files=['thumbs.db'],
               password='secret')

# Decompress ZST
fs.extract_zst('compressed.zst', 'output_file')
```

## Configuration

FileSpacer supports configuration files for persistent settings:

```json
{
  "chunk_size": 1048576,
  "compression_level": 3,
  "verify_integrity": true,
  "parallel_threads": 4
}
```

Save to `~/.filespacer/config.json` for automatic loading.

## Performance Tips

1. **Compression Levels**:
   - 1-3: Fast compression, good for real-time
   - 4-9: Balanced performance
   - 10-22: Maximum compression, slower

2. **Chunk Size**: Larger chunks (up to 16MB) can improve performance for very large files

3. **Parallel Threads**: Set to CPU core count for optimal performance

## Advanced Features

### Integrity Verification
All compressed files include SHA-256 hashes for integrity verification:
```bash
# Files are automatically verified during decompression
# Hash files are created as filename.zst.sha256
```

### Exclude Patterns
Use glob patterns to exclude files:
```bash
filespacer-cli compress folder/ archive.zst \
  --exclude "*.tmp" \
  --exclude "__pycache__/*" \
  --exclude ".git"
```

## Error Handling

FileSpacer provides comprehensive error handling:
- Clear error messages for common issues
- Automatic cleanup of partial files
- Safe path handling to prevent directory traversal
- Graceful handling of corrupted archives

## Contributing

Contributions are welcome! Please feel free to submit issues, fork the repository, and send pull requests.

### Running Tests
```bash
python -m pytest tests/
# Or
python -m unittest discover tests/
```

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Zstandard compression by Facebook
- Icon by [Icons8](https://icons8.com/icon/qSSG7p6hY0Gu/archive)
- Built with Python, Click, and tkinter

---

For issues or contributions, visit the [repository](https://github.com/tilltmk/filespacer).
