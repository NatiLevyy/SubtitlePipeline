"""
Sync - Subtitle synchronization using alass.

Wraps the alass CLI tool to sync subtitles to video files
based on audio pattern matching.
"""

import subprocess
from pathlib import Path
from typing import Optional
import logging
import shutil

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Raised when subtitle synchronization fails."""
    pass


def find_alass(config_path: Optional[str] = None) -> Path:
    """
    Find the alass executable.

    Args:
        config_path: Path from config file

    Returns:
        Path to alass executable

    Raises:
        FileNotFoundError: If alass cannot be found
    """
    # Check config path first
    if config_path:
        config_alass = Path(config_path)
        if config_alass.exists():
            return config_alass

    # Check common locations
    common_paths = [
        Path("G:/Projects/SubtitlePipeline/tools/alass-windows64/alass-windows64/bin/alass-cli.exe"),
        Path("./tools/alass-cli.exe"),
        Path("./tools/alass.exe"),
    ]

    for path in common_paths:
        if path.exists():
            return path

    # Check if in PATH
    alass_in_path = shutil.which("alass-cli") or shutil.which("alass")
    if alass_in_path:
        return Path(alass_in_path)

    raise FileNotFoundError(
        "alass executable not found. Please download from "
        "https://github.com/kaegi/alass/releases and place in tools/ folder"
    )


def sync_subtitle(
    video_path: Path,
    subtitle_path: Path,
    output_path: Path,
    alass_path: Optional[Path] = None
) -> Path:
    """
    Synchronize a subtitle file to a video using alass.

    Args:
        video_path: Path to the video file (MKV)
        subtitle_path: Path to the input subtitle file (SRT)
        output_path: Path for the synchronized output subtitle
        alass_path: Optional path to alass executable

    Returns:
        Path to the synchronized subtitle file

    Raises:
        SyncError: If synchronization fails
    """
    if alass_path is None:
        alass_path = find_alass()

    logger.info(f"Syncing: {subtitle_path.name} -> {video_path.name}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build alass command
    cmd = [
        str(alass_path),
        str(video_path),
        str(subtitle_path),
        str(output_path)
    ]

    logger.debug(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"alass failed: {error_msg}")
            raise SyncError(f"alass failed with code {result.returncode}: {error_msg}")

        if not output_path.exists():
            raise SyncError(f"alass did not create output file: {output_path}")

        logger.info(f"Sync complete: {output_path.name}")
        return output_path

    except subprocess.TimeoutExpired:
        logger.error(f"alass timed out processing: {video_path.name}")
        raise SyncError(f"Sync timed out for {video_path.name}")

    except FileNotFoundError:
        logger.error(f"alass executable not found: {alass_path}")
        raise SyncError(f"alass executable not found: {alass_path}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) >= 4:
        video = Path(sys.argv[1])
        subtitle = Path(sys.argv[2])
        output = Path(sys.argv[3])

        if not video.exists():
            print(f"Video not found: {video}")
            sys.exit(1)
        if not subtitle.exists():
            print(f"Subtitle not found: {subtitle}")
            sys.exit(1)

        try:
            result = sync_subtitle(video, subtitle, output)
            print(f"Synced subtitle saved to: {result}")
        except SyncError as e:
            print(f"Sync failed: {e}")
            sys.exit(1)
    else:
        print("Usage: python sync.py <video.mkv> <subtitle.srt> <output.srt>")
