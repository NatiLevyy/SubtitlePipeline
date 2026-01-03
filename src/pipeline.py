"""
Pipeline - Modular subtitle processing pipeline.

Supports running each step independently or all together:
- SYNC_ONLY: Just sync subtitles with video (alass)
- RTL_ONLY: Just fix RTL punctuation on existing SRT files
- EMBED_ONLY: Just embed existing SRT files into MKV
- FULL_PIPELINE: Run all 3 steps in sequence
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

from matcher import match_episodes, extract_episode_info_mkv, extract_episode_info_srt
from sync import sync_subtitle, SyncError, find_alass
from rtl_fixer import fix_rtl_file, RTLFixError
from muxer import mux_subtitle, MuxError, find_mkvmerge

logger = logging.getLogger(__name__)


class PipelineMode(Enum):
    """Available pipeline operation modes."""
    SYNC_ONLY = "sync"
    RTL_ONLY = "rtl"
    EMBED_ONLY = "embed"
    FULL_PIPELINE = "full"


@dataclass
class ProcessingResult:
    """Result of processing a single file."""
    success: bool
    input_file: Path
    output_file: Optional[Path] = None
    error_message: Optional[str] = None
    episode_id: Optional[str] = None


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    # Tool paths
    alass_path: Optional[str] = None
    mkvmerge_path: Optional[str] = None
    subtitle_edit_path: Optional[str] = None

    # Folder settings
    subtitle_folder_name: str = "Subtitle_HEBREW"
    output_folder_name: str = "Output"

    # Subtitle settings
    subtitle_language: str = "heb"
    subtitle_track_name: str = "Hebrew"
    default_subtitle: bool = True

    # Processing options
    keep_temp_files: bool = False


class Pipeline:
    """
    Modular subtitle processing pipeline.

    Supports different operation modes:
    - SYNC_ONLY: Sync subtitles to video timing
    - RTL_ONLY: Fix RTL punctuation in SRT files
    - EMBED_ONLY: Embed SRT subtitles into MKV files
    - FULL_PIPELINE: Run all steps in sequence
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize the pipeline.

        Args:
            config: Pipeline configuration
            progress_callback: Called with (message, current, total) for progress updates
            log_callback: Called with (message, level) for log messages
        """
        self.config = config or PipelineConfig()
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self._cancelled = False

    def cancel(self):
        """Cancel the current operation."""
        self._cancelled = True

    def _log(self, message: str, level: str = "info"):
        """Log a message."""
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
        if self.log_callback:
            self.log_callback(message, level)

    def _progress(self, message: str, current: int, total: int):
        """Report progress."""
        if self.progress_callback:
            self.progress_callback(message, current, total)

    def verify_tools(self, mode: PipelineMode) -> Dict[str, bool]:
        """
        Verify required tools are available for the given mode.

        Returns:
            Dict mapping tool name to availability status
        """
        results = {}

        # alass needed for sync
        if mode in (PipelineMode.SYNC_ONLY, PipelineMode.FULL_PIPELINE):
            try:
                path = find_alass(self.config.alass_path)
                results['alass'] = True
                self._log(f"alass found: {path}", "info")
            except FileNotFoundError as e:
                results['alass'] = False
                self._log(str(e), "error")

        # mkvmerge needed for embed
        if mode in (PipelineMode.EMBED_ONLY, PipelineMode.FULL_PIPELINE):
            try:
                path = find_mkvmerge(self.config.mkvmerge_path)
                results['mkvmerge'] = True
                self._log(f"mkvmerge found: {path}", "info")
            except FileNotFoundError as e:
                results['mkvmerge'] = False
                self._log(str(e), "error")

        # RTL fix uses pure Python, no external tools needed
        if mode in (PipelineMode.RTL_ONLY, PipelineMode.FULL_PIPELINE):
            results['RTL_Fixer'] = True
            self._log("RTL Fixer: Python (built-in)", "info")

        return results

    def run_sync_only(
        self,
        folder_path: Path,
        output_folder: Optional[Path] = None
    ) -> List[ProcessingResult]:
        """
        Sync subtitles to video files (alass).

        Args:
            folder_path: Path to folder with MKV files and Subtitle_HEBREW subfolder
            output_folder: Where to save synced SRT files (default: Subtitle_HEBREW/Synced)

        Returns:
            List of processing results
        """
        self._cancelled = False
        results = []

        matches = match_episodes(folder_path, self.config.subtitle_folder_name)
        if not matches:
            self._log("No matching episodes found", "warning")
            return results

        # Default output folder
        if output_folder is None:
            sub_folder = folder_path / self.config.subtitle_folder_name
            output_folder = sub_folder / "Synced"
        output_folder.mkdir(parents=True, exist_ok=True)

        total = len(matches)
        alass_path = Path(self.config.alass_path) if self.config.alass_path else None

        for i, match in enumerate(matches):
            if self._cancelled:
                self._log("Operation cancelled", "warning")
                break

            mkv = match['mkv']
            srt = match['srt']
            episode_id = f"S{match['season']:02d}E{match['episode']:02d}"

            self._progress(f"Syncing {episode_id}", i + 1, total)
            self._log(f"Syncing: {srt.name}", "info")

            output_srt = output_folder / srt.name.replace('.srt', '_synced.srt')

            try:
                sync_subtitle(mkv, srt, output_srt, alass_path)
                results.append(ProcessingResult(
                    success=True,
                    input_file=srt,
                    output_file=output_srt,
                    episode_id=episode_id
                ))
                self._log(f"Synced: {output_srt.name}", "info")
            except SyncError as e:
                results.append(ProcessingResult(
                    success=False,
                    input_file=srt,
                    error_message=str(e),
                    episode_id=episode_id
                ))
                self._log(f"Sync failed for {srt.name}: {e}", "error")

        return results

    def run_rtl_only(
        self,
        input_path: Path,
        output_folder: Optional[Path] = None
    ) -> List[ProcessingResult]:
        """
        Fix RTL punctuation in SRT files.

        Args:
            input_path: Path to folder containing SRT files, or single SRT file
            output_folder: Where to save fixed SRT files (default: same folder with _rtl suffix)

        Returns:
            List of processing results
        """
        self._cancelled = False
        results = []

        # Get list of SRT files
        if input_path.is_file():
            srt_files = [input_path]
            if output_folder is None:
                output_folder = input_path.parent
        else:
            srt_files = list(input_path.glob("*.srt"))
            if output_folder is None:
                output_folder = input_path / "RTL_Fixed"

        if not srt_files:
            self._log("No SRT files found", "warning")
            return results

        output_folder.mkdir(parents=True, exist_ok=True)
        total = len(srt_files)

        for i, srt in enumerate(srt_files):
            if self._cancelled:
                self._log("Operation cancelled", "warning")
                break

            self._progress(f"Fixing RTL: {srt.name}", i + 1, total)
            self._log(f"Fixing RTL: {srt.name}", "info")

            # Generate output filename
            if input_path.is_file():
                output_srt = output_folder / srt.name.replace('.srt', '_rtl.srt')
            else:
                output_srt = output_folder / srt.name

            try:
                fix_rtl_file(srt, output_srt)
                results.append(ProcessingResult(
                    success=True,
                    input_file=srt,
                    output_file=output_srt
                ))
                self._log(f"Fixed: {output_srt.name}", "info")
            except (RTLFixError, Exception) as e:
                results.append(ProcessingResult(
                    success=False,
                    input_file=srt,
                    error_message=str(e)
                ))
                self._log(f"RTL fix failed for {srt.name}: {e}", "error")

        return results

    def run_embed_only(
        self,
        folder_path: Path,
        output_folder: Optional[Path] = None
    ) -> List[ProcessingResult]:
        """
        Embed SRT subtitles into MKV files.

        Args:
            folder_path: Path to folder with MKV files and Subtitle_HEBREW subfolder
            output_folder: Where to save output MKV files (default: Output subfolder)

        Returns:
            List of processing results
        """
        self._cancelled = False
        results = []

        matches = match_episodes(folder_path, self.config.subtitle_folder_name)
        if not matches:
            self._log("No matching episodes found", "warning")
            return results

        # Default output folder
        if output_folder is None:
            output_folder = folder_path / self.config.output_folder_name
        output_folder.mkdir(parents=True, exist_ok=True)

        total = len(matches)
        mkvmerge_path = Path(self.config.mkvmerge_path) if self.config.mkvmerge_path else None

        for i, match in enumerate(matches):
            if self._cancelled:
                self._log("Operation cancelled", "warning")
                break

            mkv = match['mkv']
            srt = match['srt']
            episode_id = f"S{match['season']:02d}E{match['episode']:02d}"

            self._progress(f"Embedding {episode_id}", i + 1, total)
            self._log(f"Embedding: {srt.name} into {mkv.name}", "info")

            output_mkv = output_folder / mkv.name

            # Skip if exists
            if output_mkv.exists():
                self._log(f"Skipping {episode_id}: Output already exists", "warning")
                results.append(ProcessingResult(
                    success=True,
                    input_file=mkv,
                    output_file=output_mkv,
                    episode_id=episode_id
                ))
                continue

            try:
                mux_subtitle(
                    mkv, srt, output_mkv,
                    language=self.config.subtitle_language,
                    track_name=self.config.subtitle_track_name,
                    default_track=self.config.default_subtitle,
                    mkvmerge_path=mkvmerge_path
                )
                results.append(ProcessingResult(
                    success=True,
                    input_file=mkv,
                    output_file=output_mkv,
                    episode_id=episode_id
                ))
                self._log(f"Embedded: {output_mkv.name}", "info")
            except MuxError as e:
                results.append(ProcessingResult(
                    success=False,
                    input_file=mkv,
                    error_message=str(e),
                    episode_id=episode_id
                ))
                self._log(f"Embed failed for {mkv.name}: {e}", "error")

        return results

    def run_full_pipeline(
        self,
        folder_path: Path,
        output_folder: Optional[Path] = None
    ) -> List[ProcessingResult]:
        """
        Run the complete pipeline: Sync -> RTL Fix -> Embed.

        Args:
            folder_path: Path to folder with MKV files and Subtitle_HEBREW subfolder
            output_folder: Where to save output MKV files (default: Output subfolder)

        Returns:
            List of processing results
        """
        self._cancelled = False
        results = []

        matches = match_episodes(folder_path, self.config.subtitle_folder_name)
        if not matches:
            self._log("No matching episodes found", "warning")
            return results

        # Create output and temp directories
        if output_folder is None:
            output_folder = folder_path / self.config.output_folder_name
        temp_dir = folder_path / "temp"
        output_folder.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        total = len(matches)
        alass_path = Path(self.config.alass_path) if self.config.alass_path else None
        mkvmerge_path = Path(self.config.mkvmerge_path) if self.config.mkvmerge_path else None

        for i, match in enumerate(matches):
            if self._cancelled:
                self._log("Operation cancelled", "warning")
                break

            mkv = match['mkv']
            srt = match['srt']
            season = match['season']
            episode = match['episode']
            episode_id = f"S{season:02d}E{episode:02d}"

            output_mkv = output_folder / mkv.name

            # Skip if exists
            if output_mkv.exists():
                self._log(f"Skipping {episode_id}: Output already exists", "warning")
                results.append(ProcessingResult(
                    success=True,
                    input_file=mkv,
                    output_file=output_mkv,
                    episode_id=episode_id
                ))
                continue

            self._progress(f"Processing {episode_id}", i + 1, total)

            # Temp files
            synced_srt = temp_dir / f"{episode_id}_synced.srt"
            fixed_srt = temp_dir / f"{episode_id}_fixed.srt"

            try:
                # Step 1: Sync
                self._log(f"[{episode_id}] Syncing subtitle...", "info")
                sync_subtitle(mkv, srt, synced_srt, alass_path)

                # Step 2: RTL Fix
                self._log(f"[{episode_id}] Fixing RTL...", "info")
                fix_rtl_file(synced_srt, fixed_srt)

                # Step 3: Embed
                self._log(f"[{episode_id}] Embedding into MKV...", "info")
                mux_subtitle(
                    mkv, fixed_srt, output_mkv,
                    language=self.config.subtitle_language,
                    track_name=self.config.subtitle_track_name,
                    default_track=self.config.default_subtitle,
                    mkvmerge_path=mkvmerge_path
                )

                results.append(ProcessingResult(
                    success=True,
                    input_file=mkv,
                    output_file=output_mkv,
                    episode_id=episode_id
                ))
                self._log(f"[{episode_id}] Complete: {output_mkv.name}", "info")

            except (SyncError, MuxError, RTLFixError) as e:
                results.append(ProcessingResult(
                    success=False,
                    input_file=mkv,
                    error_message=str(e),
                    episode_id=episode_id
                ))
                self._log(f"[{episode_id}] Failed: {e}", "error")
            except Exception as e:
                results.append(ProcessingResult(
                    success=False,
                    input_file=mkv,
                    error_message=str(e),
                    episode_id=episode_id
                ))
                self._log(f"[{episode_id}] Unexpected error: {e}", "error")
            finally:
                # Cleanup temp files
                if not self.config.keep_temp_files:
                    synced_srt.unlink(missing_ok=True)
                    fixed_srt.unlink(missing_ok=True)

        # Cleanup temp directory if empty
        if temp_dir.exists() and not any(temp_dir.iterdir()):
            temp_dir.rmdir()

        return results

    def run(
        self,
        mode: PipelineMode,
        input_path: Path,
        output_folder: Optional[Path] = None
    ) -> List[ProcessingResult]:
        """
        Run the pipeline in the specified mode.

        Args:
            mode: Pipeline operation mode
            input_path: Input folder or file path
            output_folder: Optional output folder

        Returns:
            List of processing results
        """
        if mode == PipelineMode.SYNC_ONLY:
            return self.run_sync_only(input_path, output_folder)
        elif mode == PipelineMode.RTL_ONLY:
            return self.run_rtl_only(input_path, output_folder)
        elif mode == PipelineMode.EMBED_ONLY:
            return self.run_embed_only(input_path, output_folder)
        elif mode == PipelineMode.FULL_PIPELINE:
            return self.run_full_pipeline(input_path, output_folder)
        else:
            raise ValueError(f"Unknown mode: {mode}")
