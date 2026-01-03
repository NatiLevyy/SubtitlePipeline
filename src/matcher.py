"""
Episode Matcher - Matches MKV files with their corresponding SRT subtitle files.

Handles various naming conventions:
- MKV: S06E01, s06e01
- SRT: 6x01, S06E01, 601
"""

import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import logging

logger = logging.getLogger(__name__)


def extract_episode_info_mkv(filename: str) -> Optional[Tuple[int, int]]:
    """
    Extract season and episode numbers from MKV filename.

    Args:
        filename: The MKV filename (e.g., "ER.1994.S06E01.720p.mkv")

    Returns:
        Tuple of (season, episode) or None if not found
    """
    pattern = r'[Ss](\d{1,2})[Ee](\d{1,2})'
    match = re.search(pattern, filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def extract_episode_info_srt(filename: str) -> Optional[Tuple[int, int]]:
    """
    Extract season and episode numbers from SRT filename.

    Args:
        filename: The SRT filename (e.g., "ER - 6x01 - Title.en.srt")

    Returns:
        Tuple of (season, episode) or None if not found
    """
    patterns = [
        r'(\d{1,2})x(\d{1,2})',           # Matches 6x01
        r'[Ss](\d{1,2})[Ee](\d{1,2})',    # Matches S06E01
        r'[Ss](\d{1,2})\.?[Ee](\d{1,2})', # Matches S6.E1 or S6E1
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1)), int(match.group(2))

    return None


def find_subtitle_folder(season_folder: Path, subtitle_folder_name: str) -> Optional[Path]:
    """
    Find the subtitle folder within a season folder.

    Args:
        season_folder: Path to the season folder
        subtitle_folder_name: Expected name of subtitle folder

    Returns:
        Path to subtitle folder or None if not found
    """
    subtitle_folder = season_folder / subtitle_folder_name
    if subtitle_folder.exists() and subtitle_folder.is_dir():
        return subtitle_folder

    # Try case-insensitive search
    for item in season_folder.iterdir():
        if item.is_dir() and item.name.lower() == subtitle_folder_name.lower():
            return item

    return None


def match_episodes(
    season_folder: Path,
    subtitle_folder_name: str = "Subtitle_HEBREW"
) -> List[Dict]:
    """
    Match MKV files with their corresponding SRT files in a season folder.

    Args:
        season_folder: Path to the season folder containing MKVs and subtitle subfolder
        subtitle_folder_name: Name of the subtitle subfolder

    Returns:
        List of dicts with 'mkv', 'srt', 'season', 'episode' keys
        Unmatched files are logged as warnings
    """
    matches = []
    unmatched_mkv = []
    unmatched_srt = []

    # Find all MKV files in season folder
    mkv_files = list(season_folder.glob("*.mkv"))

    # Find subtitle folder
    subtitle_folder = find_subtitle_folder(season_folder, subtitle_folder_name)
    if not subtitle_folder:
        logger.warning(f"Subtitle folder '{subtitle_folder_name}' not found in {season_folder}")
        return []

    # Find all SRT files
    srt_files = list(subtitle_folder.glob("*.srt"))

    # Build lookup dict for SRT files by episode
    srt_by_episode: Dict[Tuple[int, int], Path] = {}
    for srt in srt_files:
        info = extract_episode_info_srt(srt.name)
        if info:
            srt_by_episode[info] = srt
        else:
            unmatched_srt.append(srt)
            logger.warning(f"Could not extract episode info from SRT: {srt.name}")

    # Match MKV files to SRT files
    for mkv in mkv_files:
        info = extract_episode_info_mkv(mkv.name)
        if info:
            season, episode = info
            if info in srt_by_episode:
                matches.append({
                    'mkv': mkv,
                    'srt': srt_by_episode[info],
                    'season': season,
                    'episode': episode
                })
                logger.info(f"Matched: S{season:02d}E{episode:02d} -> {mkv.name}")
            else:
                unmatched_mkv.append(mkv)
                logger.warning(f"No SRT found for MKV: {mkv.name} (S{season:02d}E{episode:02d})")
        else:
            unmatched_mkv.append(mkv)
            logger.warning(f"Could not extract episode info from MKV: {mkv.name}")

    # Log summary
    logger.info(f"Matched {len(matches)} episodes")
    if unmatched_mkv:
        logger.warning(f"Unmatched MKV files: {len(unmatched_mkv)}")
    if unmatched_srt:
        logger.warning(f"Unmatched SRT files: {len(unmatched_srt)}")

    # Sort by season and episode
    matches.sort(key=lambda x: (x['season'], x['episode']))

    return matches


if __name__ == "__main__":
    # Test the matcher
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
        if folder.exists():
            results = match_episodes(folder)
            for r in results:
                print(f"S{r['season']:02d}E{r['episode']:02d}: {r['mkv'].name} <-> {r['srt'].name}")
        else:
            print(f"Folder not found: {folder}")
    else:
        print("Usage: python matcher.py <season_folder>")
