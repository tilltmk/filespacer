"""FileSpacer - A powerful tool for compressing and decompressing files."""

from .filespacer import (
    FileSpacer, 
    CompressionStats, 
    FileSpacerError, 
    CompressionError, 
    ExtractionError
)

__version__ = '1.0.0'
__all__ = [
    'FileSpacer', 
    'CompressionStats', 
    'FileSpacerError', 
    'CompressionError', 
    'ExtractionError'
]