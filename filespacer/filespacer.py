#!/usr/bin/env python3

import os
import sys
import zipfile
import zlib
import zstandard as zstd
import hashlib
import logging
import json
import tarfile
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm.auto import tqdm
from pathlib import Path
from typing import Optional, Callable, Union, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CompressionStats:
    """Statistics for compression operations."""

    original_size: int
    compressed_size: int
    duration: float
    files_processed: int
    compression_ratio: float

    def to_dict(self) -> Dict:
        return {
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "duration": self.duration,
            "files_processed": self.files_processed,
            "compression_ratio": self.compression_ratio,
        }


class FileSpacerError(Exception):
    """Base exception for FileSpacer."""

    pass


class CompressionError(FileSpacerError):
    """Raised when compression fails."""

    pass


class ExtractionError(FileSpacerError):
    """Raised when extraction fails."""

    pass


class FileSpacer:
    """Core file compression and extraction logic with advanced features."""

    DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    DEFAULT_COMPRESSION_LEVEL = 3

    def __init__(
        self,
        progress_callback: Optional[Callable] = None,
        config: Optional[Dict] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.progress_callback = progress_callback or self._default_progress
        self.config = config or self._load_default_config()
        self.logger = logger or self._setup_logger()
        self.chunk_size = self.config.get("chunk_size", self.DEFAULT_CHUNK_SIZE)
        self._stats = None

    def _setup_logger(self) -> logging.Logger:
        """Setup default logger."""
        logger = logging.getLogger("filespacer")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _load_default_config(self) -> Dict:
        """Load default configuration."""
        config_path = Path.home() / ".filespacer" / "config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "chunk_size": self.DEFAULT_CHUNK_SIZE,
            "compression_level": self.DEFAULT_COMPRESSION_LEVEL,
            "verify_integrity": True,
            "parallel_threads": os.cpu_count() or 4,
        }

    def _default_progress(self, message: str):
        """Default progress output to stdout."""
        print(message, end="")

    def _calculate_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate file hash for integrity verification."""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            while chunk := f.read(self.chunk_size):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def extract_zip(
        self,
        input_zip: Union[str, Path],
        output_dir: Union[str, Path],
        exclude_files: Optional[List[str]] = None,
        password: Optional[str] = None,
        verify_integrity: bool = True,
    ) -> bool:
        """Extract ZIP file with optional exclusion and password."""
        input_zip = Path(input_zip)
        output_dir = Path(output_dir)
        exclude_files = exclude_files or []

        self.logger.info(f"Starting extraction of {input_zip}")

        if not input_zip.exists():
            error_msg = f"The file {input_zip} does not exist."
            self.logger.error(error_msg)
            raise ExtractionError(error_msg)

        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(input_zip, "r") as zip_ref:
                if password:
                    zip_ref.setpassword(password.encode())

                members = zip_ref.namelist()
                total_members = len(members)
                extracted_count = 0
                failed_files = []

                self.progress_callback(f"Extracting {total_members} files...\n")

                # Verify integrity if requested
                if verify_integrity and self.config.get("verify_integrity", True):
                    try:
                        result = zip_ref.testzip()
                        if result:
                            self.logger.warning(f"Corrupted file detected: {result}")
                    except Exception as e:
                        self.logger.warning(f"Integrity check failed: {e}")

                with tqdm(total=total_members, unit="file", desc="Extracting") as pbar:
                    for member in members:
                        # Skip excluded files
                        if any(exclude in member for exclude in exclude_files):
                            pbar.update(1)
                            continue

                        try:
                            # Extract with path sanitization
                            target_path = output_dir / member
                            if not str(target_path).startswith(str(output_dir)):
                                self.logger.warning(f"Skipping potentially unsafe path: {member}")
                                continue

                            zip_ref.extract(member, output_dir)
                            extracted_count += 1
                        except (zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error) as e:
                            self.logger.error(f"Failed to extract {member}: {e}")
                            failed_files.append((member, str(e)))
                        finally:
                            pbar.update(1)

                # Report results
                if failed_files:
                    self.progress_callback(f"\nExtraction completed with {len(failed_files)} errors.\n")
                    for file, error in failed_files[:5]:  # Show first 5 errors
                        self.progress_callback(f"  - {file}: {error}\n")
                    if len(failed_files) > 5:
                        self.progress_callback(f"  ... and {len(failed_files) - 5} more errors\n")
                else:
                    self.progress_callback(f"\nExtraction completed successfully. {extracted_count} files extracted.\n")

                self.logger.info(f"Extraction completed: {extracted_count}/{total_members} files")
                return len(failed_files) == 0

        except zipfile.BadZipFile as e:
            error_msg = f"{input_zip} is not a valid zip file."
            self.logger.error(error_msg)
            raise ExtractionError(error_msg) from e
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise ExtractionError(f"Extraction failed: {e}") from e

    def compress_file(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        compression_level: Optional[int] = None,
        calculate_hash: bool = True,
    ) -> CompressionStats:
        """Compress a single file using zstandard."""
        input_path = Path(input_path)
        output_path = Path(output_path)
        compression_level = compression_level or self.config.get("compression_level", self.DEFAULT_COMPRESSION_LEVEL)

        self.logger.info(f"Compressing {input_path} with level {compression_level}")

        if not input_path.exists():
            error_msg = f"{input_path} does not exist."
            self.logger.error(error_msg)
            raise CompressionError(error_msg)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = datetime.now()

        try:
            file_size = input_path.stat().st_size
            cctx = zstd.ZstdCompressor(level=compression_level, threads=self.config.get("parallel_threads", 1))

            self.progress_callback(f"Compressing {input_path.name}...\n")

            # Calculate input hash if requested
            input_hash = None
            if calculate_hash:
                self.progress_callback("Calculating input file hash...\n")
                input_hash = self._calculate_hash(input_path)

            bytes_processed = 0
            with open(input_path, "rb") as infile, open(output_path, "wb") as outfile:
                with cctx.stream_writer(outfile) as compressor:
                    with tqdm(total=file_size, unit="B", unit_scale=True, desc="Compressing") as pbar:
                        while True:
                            chunk = infile.read(self.chunk_size)
                            if not chunk:
                                break
                            compressor.write(chunk)
                            bytes_processed += len(chunk)
                            pbar.update(len(chunk))

            # Get compressed size
            compressed_size = output_path.stat().st_size
            duration = (datetime.now() - start_time).total_seconds()

            # Store hash in extended attributes or sidecar file
            if input_hash:
                hash_file = output_path.with_suffix(output_path.suffix + ".sha256")
                hash_file.write_text(f"{input_hash}  {input_path.name}\n")

            stats = CompressionStats(
                original_size=file_size,
                compressed_size=compressed_size,
                duration=duration,
                files_processed=1,
                compression_ratio=file_size / compressed_size if compressed_size > 0 else 0,
            )

            self.progress_callback(f"\nCompression completed successfully.\n")
            self.progress_callback(f"Original: {file_size:,} bytes, Compressed: {compressed_size:,} bytes\n")
            self.progress_callback(f"Ratio: {stats.compression_ratio:.2f}:1, Time: {duration:.2f}s\n")

            self.logger.info(f"Compression stats: {stats.to_dict()}")
            self._stats = stats
            return stats

        except Exception as e:
            self.logger.error(f"Compression failed: {e}")
            # Clean up partial output
            if output_path.exists():
                output_path.unlink()
            raise CompressionError(f"Compression failed: {e}") from e

    def compress_folder(
        self,
        input_folder: Union[str, Path],
        output_path: Union[str, Path],
        compression_level: Optional[int] = None,
        exclude_patterns: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> CompressionStats:
        """Compress entire folder into a single zstandard-compressed tar file."""
        input_folder = Path(input_folder)
        output_path = Path(output_path)
        compression_level = compression_level or self.config.get("compression_level", self.DEFAULT_COMPRESSION_LEVEL)
        exclude_patterns = exclude_patterns or []

        self.logger.info(f"Compressing folder {input_folder}")

        if not input_folder.exists() or not input_folder.is_dir():
            error_msg = f"{input_folder} is not a valid directory."
            self.logger.error(error_msg)
            raise CompressionError(error_msg)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        start_time = datetime.now()

        try:
            self.progress_callback(f"Compressing folder {input_folder.name}...\n")

            # Collect files to compress
            files_to_compress = []
            total_size = 0

            for file_path in input_folder.rglob("*"):
                if file_path.is_file():
                    # Check exclusions
                    relative_path = file_path.relative_to(input_folder)
                    if any(pattern in str(relative_path) for pattern in exclude_patterns):
                        continue

                    files_to_compress.append(file_path)
                    total_size += file_path.stat().st_size

            total_files = len(files_to_compress)
            self.progress_callback(f"Found {total_files} files ({total_size:,} bytes)\n")

            cctx = zstd.ZstdCompressor(
                level=compression_level, threads=self.config.get("parallel_threads", 1) if parallel else 1
            )

            files_processed = 0
            with open(output_path, "wb") as outfile:
                with cctx.stream_writer(outfile) as compressor:
                    with tarfile.open(fileobj=compressor, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                        with tqdm(total=total_files, unit="file", desc="Compressing") as pbar:
                            for file_path in files_to_compress:
                                try:
                                    arcname = file_path.relative_to(input_folder.parent)
                                    tar.add(file_path, arcname=str(arcname))
                                    files_processed += 1
                                except Exception as e:
                                    self.logger.warning(f"Failed to add {file_path}: {e}")
                                finally:
                                    pbar.update(1)

            compressed_size = output_path.stat().st_size
            duration = (datetime.now() - start_time).total_seconds()

            stats = CompressionStats(
                original_size=total_size,
                compressed_size=compressed_size,
                duration=duration,
                files_processed=files_processed,
                compression_ratio=total_size / compressed_size if compressed_size > 0 else 0,
            )

            self.progress_callback(f"\nFolder compression completed successfully.\n")
            self.progress_callback(f"Processed {files_processed}/{total_files} files\n")
            self.progress_callback(f"Original: {total_size:,} bytes, Compressed: {compressed_size:,} bytes\n")
            self.progress_callback(f"Ratio: {stats.compression_ratio:.2f}:1, Time: {duration:.2f}s\n")

            self.logger.info(f"Folder compression stats: {stats.to_dict()}")
            self._stats = stats
            return stats

        except Exception as e:
            self.logger.error(f"Folder compression failed: {e}")
            if output_path.exists():
                output_path.unlink()
            raise CompressionError(f"Folder compression failed: {e}") from e

    def extract_zst(self, input_path: Union[str, Path], output_path: Union[str, Path], verify_hash: bool = True) -> bool:
        """Extract zstandard compressed file."""
        input_path = Path(input_path)
        output_path = Path(output_path)

        self.logger.info(f"Extracting {input_path}")

        if not input_path.exists():
            error_msg = f"{input_path} does not exist."
            self.logger.error(error_msg)
            raise ExtractionError(error_msg)

        try:
            dctx = zstd.ZstdDecompressor()

            self.progress_callback(f"Decompressing {input_path.name}...\n")

            # Check for hash file
            hash_file = input_path.with_suffix(input_path.suffix + ".sha256")
            expected_hash = None
            if verify_hash and hash_file.exists():
                try:
                    expected_hash = hash_file.read_text().split()[0]
                    self.progress_callback("Found integrity hash file\n")
                except Exception as e:
                    self.logger.warning(f"Could not read hash file: {e}")

            # Detect if it's a tar archive by checking magic bytes
            is_tar = False
            with open(input_path, "rb") as infile:
                # Use stream reader to properly decompress and check format
                try:
                    with dctx.stream_reader(infile) as reader:
                        # Read first 512 bytes to check tar format
                        decompressed_sample = reader.read(512)
                        is_tar = self._is_tar_format(decompressed_sample)
                except Exception as e:
                    self.logger.debug(f"Format detection error: {e}")
                    is_tar = False

            # Now open the file again for actual extraction
            with open(input_path, "rb") as infile:
                if is_tar:
                    # Extract tar archive
                    self.progress_callback("Detected tar archive format\n")
                    output_path.mkdir(parents=True, exist_ok=True)

                    extracted_files = 0
                    with dctx.stream_reader(infile) as reader:
                        with tarfile.open(fileobj=reader, mode="r|") as tar:
                            with tqdm(unit="file", desc="Extracting") as pbar:
                                for member in tar:
                                    try:
                                        # Security check for path traversal
                                        target_path = output_path / member.name
                                        if not str(target_path).startswith(str(output_path)):
                                            self.logger.warning(f"Skipping unsafe path: {member.name}")
                                            continue

                                        tar.extract(member, path=output_path)
                                        extracted_files += 1
                                    except Exception as e:
                                        self.logger.error(f"Failed to extract {member.name}: {e}")
                                    finally:
                                        pbar.update(1)

                    self.progress_callback(f"\nExtracted {extracted_files} files\n")
                else:
                    # Single file extraction
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    file_size = input_path.stat().st_size
                    with open(output_path, "wb") as outfile:
                        with tqdm(total=file_size, unit="B", unit_scale=True, desc="Decompressing") as pbar:
                            with dctx.stream_reader(infile) as reader:
                                while True:
                                    chunk = reader.read(self.chunk_size)
                                    if not chunk:
                                        break
                                    outfile.write(chunk)
                                    pbar.update(len(chunk))

                    # Verify hash if available
                    if expected_hash and verify_hash:
                        self.progress_callback("Verifying file integrity...\n")
                        actual_hash = self._calculate_hash(output_path)
                        if actual_hash != expected_hash:
                            self.logger.error("Hash verification failed!")
                            self.progress_callback("WARNING: File integrity check failed!\n")
                        else:
                            self.progress_callback("File integrity verified\n")

            self.progress_callback("\nDecompression completed successfully.\n")
            self.logger.info(f"Decompression completed: {input_path} -> {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Decompression failed: {e}")
            if output_path.exists():
                if output_path.is_file():
                    output_path.unlink()
                else:
                    import shutil

                    shutil.rmtree(output_path)
            raise ExtractionError(f"Decompression failed: {e}") from e

    def _is_tar_format(self, data: bytes) -> bool:
        """Check if data appears to be tar format."""
        # Check for ustar magic or common tar patterns
        if b"ustar" in data[:512]:
            return True
        # Check for common tar header patterns
        try:
            # Tar headers are 512 bytes and contain specific patterns
            if len(data) >= 512:
                # Check for reasonable file mode in octal (offset 100-108)
                mode_field = data[100:108].strip(b"\x00 ")
                # Check for reasonable uid/gid in octal (offset 108-124)
                uid_field = data[108:116].strip(b"\x00 ")
                gid_field = data[116:124].strip(b"\x00 ")
                
                # Valid tar files have octal mode/uid/gid fields
                if (mode_field and all(c in b"01234567" for c in mode_field) and
                    uid_field and all(c in b"01234567" for c in uid_field) and
                    gid_field and all(c in b"01234567" for c in gid_field)):
                    return True
                    
                # Alternative: Check if it starts with a filename (non-null bytes)
                # followed by null padding up to offset 100
                filename_end = data.find(b"\x00")
                if 0 < filename_end < 100:
                    # Check if mode field looks reasonable
                    if mode_field and len(mode_field) > 0:
                        return True
        except Exception:
            pass
        return False

    def get_stats(self) -> Optional[CompressionStats]:
        """Get statistics from last operation."""
        return self._stats
