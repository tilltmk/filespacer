#!/usr/bin/env python3

import unittest
import tempfile
import shutil
import zipfile
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filespacer import FileSpacer, CompressionStats, FileSpacerError, CompressionError, ExtractionError


class TestFileSpacer(unittest.TestCase):
    """Test cases for FileSpacer core functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.filespacer = FileSpacer()
        
        # Create test files
        self.test_file = Path(self.test_dir) / "test.txt"
        self.test_file.write_text("Hello, World! " * 1000)
        
        self.test_folder = Path(self.test_dir) / "test_folder"
        self.test_folder.mkdir()
        
        for i in range(5):
            (self.test_folder / f"file_{i}.txt").write_text(f"Test content {i}\n" * 100)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_compress_file(self):
        """Test single file compression."""
        output_file = Path(self.test_dir) / "test.zst"
        
        result = self.filespacer.compress_file(self.test_file, output_file)
        
        self.assertIsInstance(result, CompressionStats)
        self.assertTrue(output_file.exists())
        self.assertGreater(result.compression_ratio, 1.0)
        self.assertEqual(result.files_processed, 1)
        
        # Check hash file
        hash_file = output_file.with_suffix('.zst.sha256')
        self.assertTrue(hash_file.exists())
    
    def test_compress_file_without_hash(self):
        """Test file compression without hash calculation."""
        output_file = Path(self.test_dir) / "test_no_hash.zst"
        
        result = self.filespacer.compress_file(
            self.test_file, output_file, calculate_hash=False
        )
        
        self.assertTrue(output_file.exists())
        hash_file = output_file.with_suffix('.zst.sha256')
        self.assertFalse(hash_file.exists())
    
    def test_compress_folder(self):
        """Test folder compression."""
        output_file = Path(self.test_dir) / "folder.zst"
        
        result = self.filespacer.compress_folder(self.test_folder, output_file)
        
        self.assertIsInstance(result, CompressionStats)
        self.assertTrue(output_file.exists())
        self.assertEqual(result.files_processed, 5)
    
    def test_compress_folder_with_exclusions(self):
        """Test folder compression with exclusions."""
        output_file = Path(self.test_dir) / "folder_exclude.zst"
        
        result = self.filespacer.compress_folder(
            self.test_folder, output_file, 
            exclude_patterns=['file_0', 'file_1']
        )
        
        self.assertEqual(result.files_processed, 3)
    
    def test_extract_zst_file(self):
        """Test decompression of single file."""
        # First compress
        compressed = Path(self.test_dir) / "test.zst"
        self.filespacer.compress_file(self.test_file, compressed)
        
        # Then extract
        output_file = Path(self.test_dir) / "extracted.txt"
        success = self.filespacer.extract_zst(compressed, output_file)
        
        self.assertTrue(success)
        self.assertTrue(output_file.exists())
        self.assertEqual(output_file.read_text(), self.test_file.read_text())
    
    def test_extract_zst_folder(self):
        """Test decompression of folder archive."""
        # First compress folder
        compressed = Path(self.test_dir) / "folder.zst"
        self.filespacer.compress_folder(self.test_folder, compressed)
        
        # Then extract
        output_dir = Path(self.test_dir) / "extracted_folder"
        success = self.filespacer.extract_zst(compressed, output_dir)
        
        self.assertTrue(success)
        self.assertTrue(output_dir.exists())
        
        # Check files
        for i in range(5):
            extracted_file = output_dir / "test_folder" / f"file_{i}.txt"
            self.assertTrue(extracted_file.exists())
    
    def test_extract_zip(self):
        """Test ZIP extraction."""
        # Create test ZIP
        zip_file = Path(self.test_dir) / "test.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.write(self.test_file, "test.txt")
            for i in range(3):
                zf.writestr(f"file_{i}.txt", f"Content {i}")
        
        # Extract
        output_dir = Path(self.test_dir) / "zip_extracted"
        success = self.filespacer.extract_zip(zip_file, output_dir)
        
        self.assertTrue(success)
        self.assertTrue((output_dir / "test.txt").exists())
        self.assertTrue((output_dir / "file_0.txt").exists())
    
    def test_extract_zip_with_exclusion(self):
        """Test ZIP extraction with exclusions."""
        # Create test ZIP
        zip_file = Path(self.test_dir) / "test_exclude.zip"
        with zipfile.ZipFile(zip_file, 'w') as zf:
            for i in range(5):
                zf.writestr(f"file_{i}.txt", f"Content {i}")
        
        # Extract with exclusions
        output_dir = Path(self.test_dir) / "zip_excluded"
        success = self.filespacer.extract_zip(
            zip_file, output_dir, 
            exclude_files=["file_0.txt", "file_1.txt"]
        )
        
        self.assertTrue(success)
        self.assertFalse((output_dir / "file_0.txt").exists())
        self.assertFalse((output_dir / "file_1.txt").exists())
        self.assertTrue((output_dir / "file_2.txt").exists())
    
    def test_extract_zip_with_password(self):
        """Test password-protected ZIP extraction."""
        # Create password-protected ZIP
        zip_file = Path(self.test_dir) / "test_password.zip"
        password = "secret123"
        
        with zipfile.ZipFile(zip_file, 'w') as zf:
            zf.setpassword(password.encode())
            zf.writestr("secret.txt", "Secret content", compress_type=zipfile.ZIP_DEFLATED)
        
        # Extract with password
        output_dir = Path(self.test_dir) / "zip_password"
        success = self.filespacer.extract_zip(
            zip_file, output_dir, password=password
        )
        
        self.assertTrue(success)
        self.assertTrue((output_dir / "secret.txt").exists())
    
    def test_compression_levels(self):
        """Test different compression levels."""
        sizes = []
        
        for level in [1, 10, 22]:
            output_file = Path(self.test_dir) / f"test_level_{level}.zst"
            result = self.filespacer.compress_file(
                self.test_file, output_file, 
                compression_level=level
            )
            sizes.append(result.compressed_size)
        
        # Higher compression levels should produce smaller files
        self.assertGreater(sizes[0], sizes[1])
        self.assertGreater(sizes[1], sizes[2])
    
    def test_error_handling(self):
        """Test error handling."""
        # Non-existent file
        with self.assertRaises(CompressionError):
            self.filespacer.compress_file(
                Path("/non/existent/file.txt"),
                Path(self.test_dir) / "output.zst"
            )
        
        # Non-existent ZIP
        with self.assertRaises(ExtractionError):
            self.filespacer.extract_zip(
                Path("/non/existent/file.zip"),
                Path(self.test_dir)
            )
    
    def test_integrity_verification(self):
        """Test file integrity verification."""
        # Compress with hash
        compressed = Path(self.test_dir) / "test_integrity.zst"
        self.filespacer.compress_file(self.test_file, compressed)
        
        # Extract with verification
        output_file = Path(self.test_dir) / "verified.txt"
        success = self.filespacer.extract_zst(compressed, output_file, verify_hash=True)
        
        self.assertTrue(success)
        
        # Corrupt the hash file
        hash_file = compressed.with_suffix('.zst.sha256')
        hash_file.write_text("invalid_hash  test.txt\n")
        
        # Extract should still succeed but warn about failed verification
        output_file2 = Path(self.test_dir) / "verified2.txt"
        success = self.filespacer.extract_zst(compressed, output_file2, verify_hash=True)
        self.assertTrue(success)  # Should succeed with warning
    
    def test_stats_retrieval(self):
        """Test statistics retrieval."""
        output_file = Path(self.test_dir) / "test_stats.zst"
        
        # No stats initially
        self.assertIsNone(self.filespacer.get_stats())
        
        # Compress and check stats
        result = self.filespacer.compress_file(self.test_file, output_file)
        stats = self.filespacer.get_stats()
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats.files_processed, result.files_processed)
        self.assertEqual(stats.compression_ratio, result.compression_ratio)


class TestCompressionStats(unittest.TestCase):
    """Test CompressionStats class."""
    
    def test_stats_creation(self):
        """Test stats object creation."""
        stats = CompressionStats(
            original_size=1000,
            compressed_size=100,
            duration=2.5,
            files_processed=5,
            compression_ratio=10.0
        )
        
        self.assertEqual(stats.original_size, 1000)
        self.assertEqual(stats.compressed_size, 100)
        self.assertEqual(stats.duration, 2.5)
        self.assertEqual(stats.files_processed, 5)
        self.assertEqual(stats.compression_ratio, 10.0)
    
    def test_stats_to_dict(self):
        """Test stats dictionary conversion."""
        stats = CompressionStats(
            original_size=1000,
            compressed_size=100,
            duration=2.5,
            files_processed=5,
            compression_ratio=10.0
        )
        
        stats_dict = stats.to_dict()
        
        self.assertIsInstance(stats_dict, dict)
        self.assertEqual(stats_dict['original_size'], 1000)
        self.assertEqual(stats_dict['compression_ratio'], 10.0)


if __name__ == '__main__':
    unittest.main()