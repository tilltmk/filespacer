#!/usr/bin/env python3

import click
import sys
import logging
import json
from pathlib import Path
from filespacer import FileSpacer, FileSpacerError, CompressionStats


@click.group()
@click.version_option(version="1.0.0", prog_name="FileSpacer")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress output")
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
@click.pass_context
def cli(ctx, verbose, quiet, config):
    """FileSpacer - A powerful tool for compressing and decompressing files."""
    ctx.ensure_object(dict)

    # Setup logging
    log_level = logging.WARNING
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR

    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Load config
    config_data = {}
    if config:
        config_path = Path(config)
        if config_path.exists():
            with open(config_path) as f:
                config_data = json.load(f)

    # Progress callback
    def progress_callback(msg):
        if not quiet:
            click.echo(msg, nl=False)

    ctx.obj["filespacer"] = FileSpacer(
        progress_callback=progress_callback, config=config_data, logger=logging.getLogger("filespacer")
    )
    ctx.obj["quiet"] = quiet


@cli.command()
@click.argument("input_zip", type=click.Path(exists=True))
@click.argument("output_dir", type=click.Path())
@click.option("--exclude", "-e", multiple=True, help="Files/patterns to exclude (can be used multiple times)")
@click.option("--password", "-p", help="Password for encrypted zip files")
@click.option("--no-verify", is_flag=True, help="Skip integrity verification")
@click.pass_context
def extract(ctx, input_zip, output_dir, exclude, password, no_verify):
    """Extract ZIP files with optional exclusion and password protection."""
    fs = ctx.obj["filespacer"]

    try:
        success = fs.extract_zip(
            input_zip,
            output_dir,
            exclude_files=list(exclude) if exclude else None,
            password=password,
            verify_integrity=not no_verify,
        )
        if success:
            if not ctx.obj["quiet"]:
                click.echo(click.style("✓ Extraction completed successfully", fg="green"))
        else:
            click.echo(click.style("⚠ Extraction completed with errors", fg="yellow"), err=True)
            sys.exit(1)
    except FileSpacerError as e:
        click.echo(click.style(f"✗ {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option("--level", "-l", type=click.IntRange(1, 22), help="Compression level (1-22, default from config or 3)")
@click.option("--exclude", "-e", multiple=True, help="Patterns to exclude from folder compression")
@click.option("--no-hash", is_flag=True, help="Skip hash calculation")
@click.option("--no-parallel", is_flag=True, help="Disable parallel compression")
@click.option("--stats", "-s", is_flag=True, help="Show detailed statistics")
@click.pass_context
def compress(ctx, input_path, output_path, level, exclude, no_hash, no_parallel, stats):
    """Compress files or folders using zstandard."""
    fs = ctx.obj["filespacer"]
    input_p = Path(input_path)

    try:
        if input_p.is_file():
            result = fs.compress_file(input_path, output_path, compression_level=level, calculate_hash=not no_hash)
        elif input_p.is_dir():
            result = fs.compress_folder(
                input_path,
                output_path,
                compression_level=level,
                exclude_patterns=list(exclude) if exclude else None,
                parallel=not no_parallel,
            )
        else:
            raise click.ClickException(f"{input_path} is neither a file nor a directory")

        if not ctx.obj["quiet"]:
            click.echo(click.style("✓ Compression completed successfully", fg="green"))

            if stats and isinstance(result, CompressionStats):
                click.echo("\nCompression Statistics:")
                click.echo(f"  Original size: {result.original_size:,} bytes")
                click.echo(f"  Compressed size: {result.compressed_size:,} bytes")
                click.echo(f"  Compression ratio: {result.compression_ratio:.2f}:1")
                click.echo(f"  Files processed: {result.files_processed}")
                click.echo(f"  Duration: {result.duration:.2f} seconds")
                click.echo(f"  Speed: {result.original_size / result.duration / 1024 / 1024:.2f} MB/s")

    except FileSpacerError as e:
        click.echo(click.style(f"✗ {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command()
@click.argument("input_zst", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option("--no-verify", is_flag=True, help="Skip hash verification")
@click.pass_context
def decompress(ctx, input_zst, output_path, no_verify):
    """Decompress zstandard (.zst) files."""
    fs = ctx.obj["filespacer"]

    try:
        success = fs.extract_zst(input_zst, output_path, verify_hash=not no_verify)
        if not ctx.obj["quiet"]:
            click.echo(click.style("✓ Decompression completed successfully", fg="green"))
    except FileSpacerError as e:
        click.echo(click.style(f"✗ {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command()
@click.option("--user", is_flag=True, help="Create user config file")
@click.option("--show", is_flag=True, help="Show current configuration")
@click.pass_context
def config(ctx, user, show):
    """Manage FileSpacer configuration."""
    config_dir = Path.home() / ".filespacer"
    config_file = config_dir / "config.json"

    if show:
        fs = ctx.obj["filespacer"]
        click.echo("Current configuration:")
        click.echo(json.dumps(fs.config, indent=2))
        return

    if user:
        config_dir.mkdir(exist_ok=True)

        default_config = {"chunk_size": 1048576, "compression_level": 3, "verify_integrity": True, "parallel_threads": 4}

        if config_file.exists():
            click.confirm(f"Config file already exists at {config_file}. Overwrite?", abort=True)

        with open(config_file, "w") as f:
            json.dump(default_config, f, indent=2)

        click.echo(f"Created config file at: {config_file}")
        click.echo("You can edit this file to customize FileSpacer behavior.")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def info(ctx, file_path):
    """Show information about compressed files."""
    file_path = Path(file_path)

    if not file_path.suffix == ".zst":
        click.echo("This command only works with .zst files", err=True)
        sys.exit(1)

    # Check for hash file
    hash_file = file_path.with_suffix(file_path.suffix + ".sha256")

    click.echo(f"File: {file_path}")
    click.echo(f"Size: {file_path.stat().st_size:,} bytes")

    if hash_file.exists():
        try:
            hash_content = hash_file.read_text().strip()
            click.echo(f"SHA256: {hash_content.split()[0]}")
        except Exception:
            click.echo("SHA256: <error reading hash file>")
    else:
        click.echo("SHA256: <no hash file found>")

    # Try to detect if it's a tar archive
    try:
        import zstandard as zstd

        dctx = zstd.ZstdDecompressor()

        with open(file_path, "rb") as f:
            sample = f.read(1024 * 64)
            decompressed = dctx.decompress(sample, max_output_size=1024)

            if b"ustar" in decompressed[:512]:
                click.echo("Type: Compressed TAR archive (folder)")
            else:
                click.echo("Type: Compressed single file")
    except Exception:
        click.echo("Type: Unknown")


if __name__ == "__main__":
    cli(obj={})
