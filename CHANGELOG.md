# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-11

### Added
- Complete refactoring from monolithic to modular architecture
- Modern CLI interface using Click framework
- Lightweight GUI with tkinter (no external dependencies)
- Optional modern themed GUI with ttkbootstrap
- File integrity verification with SHA-256 hashes
- Comprehensive error handling and logging
- Progress tracking for all operations
- Configuration file support (~/.filespacer/config.json)
- Multi-threaded compression for better performance
- Support for excluding files/patterns during compression
- Detailed compression statistics
- Comprehensive test suite
- Full documentation and examples

### Changed
- Migrated from customtkinter to standard tkinter for better compatibility
- Improved compression performance with chunked streaming
- Enhanced error messages and user feedback
- Better handling of corrupted archives

### Fixed
- Path traversal security issues
- Memory efficiency for large files
- Proper cleanup on operation failures

### Security
- Added path sanitization for ZIP extraction
- Protected against directory traversal attacks
- Secure password handling for encrypted archives

## [0.1.0] - Initial Release

### Added
- Basic ZIP extraction functionality
- Zstandard compression/decompression
- Simple GUI with customtkinter
- Basic password protection support