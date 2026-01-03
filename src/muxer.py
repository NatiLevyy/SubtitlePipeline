"""
Muxer - Embed subtitles into MKV files using MKVToolNix.

Wraps mkvmerge CLI to add Hebrew subtitle tracks to MKV containers.
"""

import subprocess
from pathlib import Path
from typing import Optional
import logging
import shutil

logger = logging.getLogger(__name__)


class MuxError(Exception):
    """Raised when muxing fails."""
    pass


def find_mkvmerge(config_path: Optional[str] = None) -> Path:
    """
    Find the mkvmerge executable.

    Args:
        config_path: Path from config file

    Returns:
        Path to mkvmerge executable

    Raises:
        FileNotFoundError: If mkvmerge cannot be found
    """
    # Check config path first
    if config_path:
        config_mkvmerge = Path(config_path)
        if config_mkvmerge.exists():
            return config_mkvmerge

    # Check common locations
    common_paths = [
        Path("C:/Program Files/MKVToolNix/mkvmerge.exe"),
        Path("C:/Program Files (x86)/MKVToolNix/mkvmerge.exe"),
    ]

    for path in common_paths:
        if path.exists():
            return path

    # Check if in PATH
    mkvmerge_in_path = shutil.which("mkvmerge")
    if mkvmerge_in_path:
        return Path(mkvmerge_in_path)

    raise FileNotFoundError(
        "mkvmerge not found. Please install MKVToolNix from "
        "https://mkvtoolnix.download/"
    )


def mux_subtitle(
    video_path: Path,
    subtitle_path: Path,
    output_path: Path,
    language: str = "heb",
    track_name: str = "Hebrew",
    default_track: bool = True,
    mkvmerge_path: Optional[Path] = None
) -> Path:
    """
    Embed a subtitle file into an MKV container.

    Args:
        video_path: Path to the input video file (MKV)
        subtitle_path: Path to the subtitle file (SRT)
        output_path: Path for the output MKV with embedded subtitle
        language: ISO 639-2 language code (default: "heb")
        track_name: Display name for the subtitle track
        default_track: Whether to set as default subtitle track
        mkvmerge_path: Optional path to mkvmerge executable

    Returns:
        Path to the output MKV file

    Raises:
        MuxError: If muxing fails
    """
    if mkvmerge_path is None:
        mkvmerge_path = find_mkvmerge()

    logger.info(f"Muxing: {subtitle_path.name} into {video_path.name}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build mkvmerge command
    cmd = [
        str(mkvmerge_path),
        "-o", str(output_path),
        str(video_path),
        "--language", f"0:{language}",
        "--track-name", f"0:{track_name}",
    ]

    if default_track:
        cmd.extend(["--default-track", "0:yes"])

    cmd.append(str(subtitle_path))

    logger.debug(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for large files
        )

        # mkvmerge returns 0 for success, 1 for warnings, 2 for errors
        if result.returncode == 2:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"mkvmerge failed: {error_msg}")
            raise MuxError(f"mkvmerge failed: {error_msg}")

        if result.returncode == 1:
            logger.warning(f"mkvmerge completed with warnings: {result.stdout}")

        if not output_path.exists():
            raise MuxError(f"mkvmerge did not create output file: {output_path}")

        logger.info(f"Mux complete: {output_path.name}")
        return output_path

    except subprocess.TimeoutExpired:
        logger.error(f"mkvmerge timed out processing: {video_path.name}")
        raise MuxError(f"Mux timed out for {video_path.name}")

    except FileNotFoundError:
        logger.error(f"mkvmerge executable not found: {mkvmerge_path}")
        raise MuxError(f"mkvmerge executable not found: {mkvmerge_path}")


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
            result = mux_subtitle(video, subtitle, output)
            print(f"Muxed file saved to: {result}")
        except MuxError as e:
            print(f"Mux failed: {e}")
            sys.exit(1)
    else:
        print("Usage: python muxer.py <video.mkv> <subtitle.srt> <output.mkv>")
