"""
Hebrew Subtitle Pipeline - GUI Application

PyQt5-based graphical user interface with:
- Pipeline tab: Mode selector (Sync Only | RTL Fix Only | Embed Only | Full Pipeline)
- Translate tab: English to Hebrew translation using Gemini API
- Full Process tab: Complete workflow (Translate → Sync → RTL Fix → Embed)
- Settings tab: Tool paths and API configuration
- Drag & drop folder selection
- Progress bar and log area
"""

import sys
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QGroupBox, QTabWidget, QFormLayout, QCheckBox,
    QMessageBox, QSplitter, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon

from pipeline import Pipeline, PipelineMode, PipelineConfig, ProcessingResult
from translator import Translator, TranslatorConfig, TranslationResult, TranslationError, test_api_connection
from matcher import match_episodes
from sync import sync_subtitle, SyncError, find_alass
from rtl_fixer import fix_rtl_file, RTLFixError
from muxer import mux_subtitle, MuxError, find_mkvmerge


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running as compiled
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script
        base_path = Path(__file__).parent.parent
    return base_path / relative_path


class PipelineWorker(QThread):
    """Worker thread for running pipeline operations."""
    progress = pyqtSignal(str, int, int)  # message, current, total
    log = pyqtSignal(str, str)  # message, level
    finished = pyqtSignal(list)  # results

    def __init__(
        self,
        mode: PipelineMode,
        input_path: Path,
        output_path: Optional[Path],
        config: PipelineConfig
    ):
        super().__init__()
        self.mode = mode
        self.input_path = input_path
        self.output_path = output_path
        self.config = config
        self.pipeline: Optional[Pipeline] = None

    def run(self):
        self.pipeline = Pipeline(
            config=self.config,
            progress_callback=self._on_progress,
            log_callback=self._on_log
        )

        try:
            results = self.pipeline.run(self.mode, self.input_path, self.output_path)
            self.finished.emit(results)
        except Exception as e:
            self.log.emit(f"Pipeline error: {e}", "error")
            self.finished.emit([])

    def _on_progress(self, message: str, current: int, total: int):
        self.progress.emit(message, current, total)

    def _on_log(self, message: str, level: str):
        self.log.emit(message, level)

    def cancel(self):
        if self.pipeline:
            self.pipeline.cancel()


class TranslationWorker(QThread):
    """Worker thread for running translation operations."""
    progress = pyqtSignal(str, int, int)  # message, current, total
    log = pyqtSignal(str, str)  # message, level
    finished = pyqtSignal(list)  # results

    def __init__(
        self,
        source_folder: Path,
        target_folder: Path,
        config: TranslatorConfig,
        subtitle_folder_name: str = "Subtitle_HEBREW"
    ):
        super().__init__()
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.config = config
        self.subtitle_folder_name = subtitle_folder_name
        self.translator: Optional[Translator] = None

    def run(self):
        self.translator = Translator(
            config=self.config,
            progress_callback=self._on_progress,
            log_callback=self._on_log
        )

        try:
            results = self.translator.translate_folder(
                self.source_folder,
                self.target_folder,
                self.subtitle_folder_name
            )
            self.finished.emit(results)
        except Exception as e:
            self.log.emit(f"Translation error: {e}", "error")
            self.finished.emit([])

    def _on_progress(self, message: str, current: int, total: int):
        self.progress.emit(message, current, total)

    def _on_log(self, message: str, level: str):
        self.log.emit(message, level)

    def cancel(self):
        if self.translator:
            self.translator.cancel()


class FullProcessWorker(QThread):
    """
    Worker thread for running the complete workflow:
    Translate → Sync → RTL Fix → Embed
    """
    progress = pyqtSignal(str, int, int, int)  # message, stage, current, total
    log = pyqtSignal(str, str)  # message, level
    finished = pyqtSignal(dict)  # results dict

    def __init__(
        self,
        english_srt_folder: Path,
        season_folder: Path,
        translator_config: TranslatorConfig,
        pipeline_config: PipelineConfig,
        keep_temp_files: bool = False
    ):
        super().__init__()
        self.english_srt_folder = english_srt_folder
        self.season_folder = season_folder
        self.translator_config = translator_config
        self.pipeline_config = pipeline_config
        self.keep_temp_files = keep_temp_files
        self._cancelled = False
        self._translator: Optional[Translator] = None

    def cancel(self):
        """Cancel the operation."""
        self._cancelled = True
        if self._translator:
            self._translator.cancel()

    def _log(self, message: str, level: str = "info"):
        self.log.emit(message, level)

    def _progress(self, message: str, stage: int, current: int, total: int):
        self.progress.emit(message, stage, current, total)

    def run(self):
        """Run the complete workflow."""
        results = {
            'success': False,
            'translated': 0,
            'synced': 0,
            'rtl_fixed': 0,
            'embedded': 0,
            'failed': [],
            'output_folder': None
        }

        try:
            # ═══════════════════════════════════════════════════════
            # STAGE 1: TRANSLATION
            # ═══════════════════════════════════════════════════════
            self._log("═══ STAGE 1: TRANSLATION ═══", "info")

            hebrew_folder = self.season_folder / self.pipeline_config.subtitle_folder_name
            hebrew_folder.mkdir(parents=True, exist_ok=True)

            # Find English SRT files
            english_files = sorted(self.english_srt_folder.glob("*.srt"))
            if not english_files:
                raise Exception("No English SRT files found")

            self._log(f"Found {len(english_files)} English SRT files", "info")

            # Create translator
            self._translator = Translator(
                config=self.translator_config,
                progress_callback=lambda msg, cur, tot: self._progress(msg, 1, cur, tot),
                log_callback=self._log
            )

            # Translate each file
            for i, srt_file in enumerate(english_files):
                if self._cancelled:
                    raise Exception("Operation cancelled")

                self._progress(f"Translating {srt_file.name}", 1, i + 1, len(english_files))

                try:
                    output_path = hebrew_folder / srt_file.name
                    self._translator.translate_file(srt_file, output_path)
                    results['translated'] += 1
                    self._log(f"✓ Translated: {srt_file.name}", "success")
                except Exception as e:
                    results['failed'].append(('translate', srt_file.name, str(e)))
                    self._log(f"✗ Translation failed: {srt_file.name} - {e}", "error")

            self._log(f"Translation complete: {results['translated']} files", "info")

            # ═══════════════════════════════════════════════════════
            # STAGE 2: SYNC
            # ═══════════════════════════════════════════════════════
            self._log("═══ STAGE 2: SYNC ═══", "info")

            # Match episodes - use subtitle folder name since we just created it
            matches = match_episodes(self.season_folder, self.pipeline_config.subtitle_folder_name)
            if not matches:
                raise Exception("No episode matches found between MKV and SRT files")

            self._log(f"Matched {len(matches)} episodes", "info")

            # Create temp synced folder
            synced_folder = self.season_folder / "temp_synced"
            synced_folder.mkdir(parents=True, exist_ok=True)

            # Find alass
            alass_path = find_alass(self.pipeline_config.alass_path)

            for i, match in enumerate(matches):
                if self._cancelled:
                    raise Exception("Operation cancelled")

                mkv_file = match['mkv']
                srt_file = match['srt']
                episode_id = f"S{match['season']:02d}E{match['episode']:02d}"

                self._progress(f"Syncing {srt_file.name}", 2, i + 1, len(matches))

                try:
                    synced_path = synced_folder / srt_file.name
                    sync_subtitle(mkv_file, srt_file, synced_path, alass_path)
                    results['synced'] += 1
                    self._log(f"✓ [{episode_id}] Synced: {srt_file.name}", "success")
                except Exception as e:
                    results['failed'].append(('sync', srt_file.name, str(e)))
                    self._log(f"✗ [{episode_id}] Sync failed: {srt_file.name} - {e}", "error")
                    # Copy original to synced folder so we can continue
                    shutil.copy(srt_file, synced_folder / srt_file.name)

            self._log(f"Sync complete: {results['synced']} files", "info")

            # ═══════════════════════════════════════════════════════
            # STAGE 3: RTL FIX
            # ═══════════════════════════════════════════════════════
            self._log("═══ STAGE 3: RTL FIX ═══", "info")

            # Create temp RTL fixed folder
            rtl_folder = self.season_folder / "temp_rtl_fixed"
            rtl_folder.mkdir(parents=True, exist_ok=True)

            synced_files = sorted(synced_folder.glob("*.srt"))

            for i, srt_file in enumerate(synced_files):
                if self._cancelled:
                    raise Exception("Operation cancelled")

                self._progress(f"Fixing RTL: {srt_file.name}", 3, i + 1, len(synced_files))

                try:
                    fixed_path = rtl_folder / srt_file.name
                    fix_rtl_file(srt_file, fixed_path)
                    results['rtl_fixed'] += 1
                    self._log(f"✓ RTL fixed: {srt_file.name}", "success")
                except Exception as e:
                    results['failed'].append(('rtl_fix', srt_file.name, str(e)))
                    self._log(f"✗ RTL fix failed: {srt_file.name} - {e}", "error")
                    # Copy original so we can continue
                    shutil.copy(srt_file, rtl_folder / srt_file.name)

            self._log(f"RTL fix complete: {results['rtl_fixed']} files", "info")

            # ═══════════════════════════════════════════════════════
            # STAGE 4: EMBED INTO MKV
            # ═══════════════════════════════════════════════════════
            self._log("═══ STAGE 4: EMBED ═══", "info")

            output_folder = self.season_folder / self.pipeline_config.output_folder_name
            output_folder.mkdir(parents=True, exist_ok=True)

            # Find mkvmerge
            mkvmerge_path = find_mkvmerge(self.pipeline_config.mkvmerge_path)

            for i, match in enumerate(matches):
                if self._cancelled:
                    raise Exception("Operation cancelled")

                mkv_file = match['mkv']
                srt_file = match['srt']
                episode_id = f"S{match['season']:02d}E{match['episode']:02d}"

                self._progress(f"Embedding: {mkv_file.name}", 4, i + 1, len(matches))

                try:
                    fixed_srt = rtl_folder / srt_file.name
                    if not fixed_srt.exists():
                        raise Exception(f"RTL fixed subtitle not found: {fixed_srt}")

                    output_mkv = output_folder / mkv_file.name
                    mux_subtitle(
                        mkv_file,
                        fixed_srt,
                        output_mkv,
                        mkvmerge_path,
                        self.pipeline_config.subtitle_language,
                        self.pipeline_config.subtitle_track_name,
                        self.pipeline_config.default_subtitle
                    )
                    results['embedded'] += 1
                    self._log(f"✓ [{episode_id}] Embedded: {mkv_file.name}", "success")
                except Exception as e:
                    results['failed'].append(('embed', mkv_file.name, str(e)))
                    self._log(f"✗ [{episode_id}] Embed failed: {mkv_file.name} - {e}", "error")

            self._log(f"Embed complete: {results['embedded']} files", "info")

            # ═══════════════════════════════════════════════════════
            # CLEANUP
            # ═══════════════════════════════════════════════════════
            if not self.keep_temp_files:
                self._log("Cleaning up temporary files...", "info")
                shutil.rmtree(synced_folder, ignore_errors=True)
                shutil.rmtree(rtl_folder, ignore_errors=True)

            results['success'] = True
            results['output_folder'] = output_folder

            self._log("═══ FULL PROCESS COMPLETE ═══", "success")
            self._log(f"Output: {output_folder}", "info")
            self._log(f"Translated: {results['translated']}, Synced: {results['synced']}, "
                     f"RTL Fixed: {results['rtl_fixed']}, Embedded: {results['embedded']}", "info")

            if results['failed']:
                self._log(f"⚠ {len(results['failed'])} errors occurred", "warning")

        except Exception as e:
            self._log(f"✗ Critical error: {e}", "error")
            results['success'] = False

        self.finished.emit(results)


class DropLabel(QLabel):
    """Label that accepts drag and drop."""

    dropped = pyqtSignal(str)

    def __init__(self, text: str = ""):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                padding: 20px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #0078d4;
                background-color: #e8f4fc;
            }
        """)
        self.setMinimumHeight(80)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #0078d4;
                    border-radius: 8px;
                    padding: 20px;
                    background-color: #e8f4fc;
                    color: #0078d4;
                    font-size: 14px;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                padding: 20px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.dropped.emit(path)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                padding: 20px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
        """)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.worker: Optional[PipelineWorker] = None
        self.translation_worker: Optional[TranslationWorker] = None
        self.full_process_worker: Optional[FullProcessWorker] = None
        self.config_path = get_resource_path("config.yaml")

        self.setWindowTitle("Hebrew Subtitle Pipeline")
        self.setMinimumSize(800, 600)

        # Load config
        self.config = self.load_config()

        # Setup UI
        self.setup_ui()

        # Load saved settings
        self.load_settings_to_ui()

    def load_config(self) -> dict:
        """Load configuration from YAML file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                return {}
        return {}

    def save_config(self):
        """Save configuration to YAML file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False)
        except Exception as e:
            self.log(f"Failed to save config: {e}", "error")

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Pipeline tab
        pipeline_tab = QWidget()
        tabs.addTab(pipeline_tab, "Pipeline")
        self.setup_pipeline_tab(pipeline_tab)

        # Translate tab
        translate_tab = QWidget()
        tabs.addTab(translate_tab, "Translate")
        self.setup_translate_tab(translate_tab)

        # Full Process tab
        full_process_tab = QWidget()
        tabs.addTab(full_process_tab, "Full Process")
        self.setup_full_process_tab(full_process_tab)

        # Settings tab
        settings_tab = QWidget()
        tabs.addTab(settings_tab, "Settings")
        self.setup_settings_tab(settings_tab)

    def setup_pipeline_tab(self, tab: QWidget):
        """Setup the pipeline execution tab."""
        layout = QVBoxLayout(tab)

        # Mode selector
        mode_group = QGroupBox("Operation Mode")
        mode_layout = QHBoxLayout(mode_group)

        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Full Pipeline (Sync → RTL Fix → Embed)",
            "Sync Only (alass)",
            "RTL Fix Only",
            "Embed Only (mkvmerge)"
        ])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo, 1)

        layout.addWidget(mode_group)

        # Input/Output selection
        io_group = QGroupBox("Input / Output")
        io_layout = QVBoxLayout(io_group)

        # Input folder
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input:"))
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Drag folder here or click Browse...")
        input_layout.addWidget(self.input_edit, 1)
        self.input_browse_btn = QPushButton("Browse...")
        self.input_browse_btn.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_browse_btn)
        io_layout.addLayout(input_layout)

        # Drop zone
        self.drop_label = DropLabel("Drag and drop a folder here")
        self.drop_label.dropped.connect(self.on_folder_dropped)
        io_layout.addWidget(self.drop_label)

        # Output folder (optional)
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("(Optional) Leave empty for default location")
        output_layout.addWidget(self.output_edit, 1)
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_browse_btn)
        io_layout.addLayout(output_layout)

        layout.addWidget(io_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_group)

        # Log area
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        log_layout.addWidget(self.log_text)

        # Clear log button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_btn)

        layout.addWidget(log_group, 1)  # Give log area stretch

        # Action buttons
        button_layout = QHBoxLayout()

        self.verify_btn = QPushButton("Verify Tools")
        self.verify_btn.clicked.connect(self.verify_tools)
        button_layout.addWidget(self.verify_btn)

        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_operation)
        button_layout.addWidget(self.cancel_btn)

        self.run_btn = QPushButton("Run Pipeline")
        self.run_btn.setDefault(True)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.run_btn.clicked.connect(self.run_pipeline)
        button_layout.addWidget(self.run_btn)

        layout.addLayout(button_layout)

    def setup_translate_tab(self, tab: QWidget):
        """Setup the translation tab."""
        layout = QVBoxLayout(tab)

        # Source folder (English subtitles)
        source_group = QGroupBox("Source (English Subtitles)")
        source_layout = QVBoxLayout(source_group)

        source_input_layout = QHBoxLayout()
        source_input_layout.addWidget(QLabel("Folder:"))
        self.translate_source_edit = QLineEdit()
        self.translate_source_edit.setPlaceholderText("Folder containing English SRT files...")
        self.translate_source_edit.textChanged.connect(self.update_source_file_count)
        source_input_layout.addWidget(self.translate_source_edit, 1)
        source_browse_btn = QPushButton("Browse...")
        source_browse_btn.clicked.connect(self.browse_translate_source)
        source_input_layout.addWidget(source_browse_btn)
        source_layout.addLayout(source_input_layout)

        # Drop zone for source
        self.translate_source_drop = DropLabel("Drag and drop English SRT folder here")
        self.translate_source_drop.dropped.connect(self.on_translate_source_dropped)
        source_layout.addWidget(self.translate_source_drop)

        # File count label
        self.source_file_count_label = QLabel("")
        source_layout.addWidget(self.source_file_count_label)

        layout.addWidget(source_group)

        # Target folder (where to create Subtitle_HEBREW)
        target_group = QGroupBox("Target (Where to create Subtitle_HEBREW)")
        target_layout = QVBoxLayout(target_group)

        target_input_layout = QHBoxLayout()
        target_input_layout.addWidget(QLabel("Folder:"))
        self.translate_target_edit = QLineEdit()
        self.translate_target_edit.setPlaceholderText("Season folder where Subtitle_HEBREW will be created...")
        self.translate_target_edit.textChanged.connect(self.update_target_preview)
        target_input_layout.addWidget(self.translate_target_edit, 1)
        target_browse_btn = QPushButton("Browse...")
        target_browse_btn.clicked.connect(self.browse_translate_target)
        target_input_layout.addWidget(target_browse_btn)
        target_layout.addLayout(target_input_layout)

        # Drop zone for target
        self.translate_target_drop = DropLabel("Drag and drop season folder here")
        self.translate_target_drop.dropped.connect(self.on_translate_target_dropped)
        target_layout.addWidget(self.translate_target_drop)

        # Preview label
        self.target_preview_label = QLabel("")
        target_layout.addWidget(self.target_preview_label)

        layout.addWidget(target_group)

        # Progress section
        translate_progress_group = QGroupBox("Progress")
        translate_progress_layout = QVBoxLayout(translate_progress_group)

        self.translate_progress_bar = QProgressBar()
        self.translate_progress_bar.setMinimum(0)
        self.translate_progress_bar.setMaximum(100)
        self.translate_progress_bar.setValue(0)
        translate_progress_layout.addWidget(self.translate_progress_bar)

        self.translate_status_label = QLabel("Ready")
        translate_progress_layout.addWidget(self.translate_status_label)

        layout.addWidget(translate_progress_group)

        # Log area
        translate_log_group = QGroupBox("Log")
        translate_log_layout = QVBoxLayout(translate_log_group)

        self.translate_log_text = QTextEdit()
        self.translate_log_text.setReadOnly(True)
        self.translate_log_text.setFont(QFont("Consolas", 9))
        self.translate_log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        translate_log_layout.addWidget(self.translate_log_text)

        clear_translate_log_btn = QPushButton("Clear Log")
        clear_translate_log_btn.clicked.connect(self.translate_log_text.clear)
        translate_log_layout.addWidget(clear_translate_log_btn)

        layout.addWidget(translate_log_group, 1)

        # Hint label
        hint_label = QLabel("After translation, use the Pipeline tab to sync and embed subtitles into MKV files.")
        hint_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(hint_label)

        # Action buttons
        translate_button_layout = QHBoxLayout()

        self.test_api_btn = QPushButton("Test API")
        self.test_api_btn.clicked.connect(self.test_gemini_api)
        translate_button_layout.addWidget(self.test_api_btn)

        translate_button_layout.addStretch()

        self.translate_cancel_btn = QPushButton("Cancel")
        self.translate_cancel_btn.setEnabled(False)
        self.translate_cancel_btn.clicked.connect(self.cancel_translation)
        translate_button_layout.addWidget(self.translate_cancel_btn)

        self.translate_btn = QPushButton("Translate All")
        self.translate_btn.setDefault(True)
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0e6b0e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.translate_btn.clicked.connect(self.run_translation)
        translate_button_layout.addWidget(self.translate_btn)

        layout.addLayout(translate_button_layout)

    def setup_full_process_tab(self, tab: QWidget):
        """Setup the Full Process tab - complete workflow."""
        layout = QVBoxLayout(tab)

        # Header
        header_label = QLabel("FULL PROCESS - Complete Workflow")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #0078d4;
                padding: 10px;
                background-color: #e8f4fc;
                border-radius: 4px;
            }
        """)
        layout.addWidget(header_label)

        workflow_label = QLabel("English SRT → Translate → Sync → RTL Fix → Embed → Final MKV")
        workflow_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(workflow_label)

        # Source folder (English subtitles)
        source_group = QGroupBox("Source (English Subtitles)")
        source_layout = QVBoxLayout(source_group)

        source_input_layout = QHBoxLayout()
        source_input_layout.addWidget(QLabel("Folder:"))
        self.fp_source_edit = QLineEdit()
        self.fp_source_edit.setPlaceholderText("Folder containing English SRT files...")
        self.fp_source_edit.textChanged.connect(self.update_fp_source_count)
        source_input_layout.addWidget(self.fp_source_edit, 1)
        fp_source_browse_btn = QPushButton("Browse...")
        fp_source_browse_btn.clicked.connect(self.browse_fp_source)
        source_input_layout.addWidget(fp_source_browse_btn)
        source_layout.addLayout(source_input_layout)

        # Drop zone for source
        self.fp_source_drop = DropLabel("Drag and drop English SRT folder here")
        self.fp_source_drop.dropped.connect(self.on_fp_source_dropped)
        source_layout.addWidget(self.fp_source_drop)

        # File count label
        self.fp_source_count_label = QLabel("")
        source_layout.addWidget(self.fp_source_count_label)

        layout.addWidget(source_group)

        # Target folder (Season folder with MKVs)
        target_group = QGroupBox("Target (Season folder with MKV files)")
        target_layout = QVBoxLayout(target_group)

        target_input_layout = QHBoxLayout()
        target_input_layout.addWidget(QLabel("Folder:"))
        self.fp_target_edit = QLineEdit()
        self.fp_target_edit.setPlaceholderText("Season folder containing MKV files...")
        self.fp_target_edit.textChanged.connect(self.update_fp_target_info)
        target_input_layout.addWidget(self.fp_target_edit, 1)
        fp_target_browse_btn = QPushButton("Browse...")
        fp_target_browse_btn.clicked.connect(self.browse_fp_target)
        target_input_layout.addWidget(fp_target_browse_btn)
        target_layout.addLayout(target_input_layout)

        # Drop zone for target
        self.fp_target_drop = DropLabel("Drag and drop season folder here")
        self.fp_target_drop.dropped.connect(self.on_fp_target_dropped)
        target_layout.addWidget(self.fp_target_drop)

        # Info labels
        self.fp_mkv_count_label = QLabel("")
        target_layout.addWidget(self.fp_mkv_count_label)
        self.fp_match_label = QLabel("")
        target_layout.addWidget(self.fp_match_label)

        layout.addWidget(target_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        # Stage indicators
        stage_layout = QHBoxLayout()
        self.fp_stage_labels = []
        stages = ["Translate", "Sync", "RTL Fix", "Embed"]
        for stage in stages:
            label = QLabel(f"○ {stage}")
            label.setStyleSheet("color: #888;")
            self.fp_stage_labels.append(label)
            stage_layout.addWidget(label)
        stage_layout.addStretch()
        progress_layout.addLayout(stage_layout)

        # Overall progress bar
        overall_layout = QHBoxLayout()
        overall_layout.addWidget(QLabel("Overall:"))
        self.fp_overall_progress = QProgressBar()
        self.fp_overall_progress.setMinimum(0)
        self.fp_overall_progress.setMaximum(100)
        self.fp_overall_progress.setValue(0)
        overall_layout.addWidget(self.fp_overall_progress, 1)
        progress_layout.addLayout(overall_layout)

        # Current progress bar
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current:"))
        self.fp_current_progress = QProgressBar()
        self.fp_current_progress.setMinimum(0)
        self.fp_current_progress.setMaximum(100)
        self.fp_current_progress.setValue(0)
        current_layout.addWidget(self.fp_current_progress, 1)
        progress_layout.addLayout(current_layout)

        # Status label
        self.fp_status_label = QLabel("Ready")
        progress_layout.addWidget(self.fp_status_label)

        layout.addWidget(progress_group)

        # Log area
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self.fp_log_text = QTextEdit()
        self.fp_log_text.setReadOnly(True)
        self.fp_log_text.setFont(QFont("Consolas", 9))
        self.fp_log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        log_layout.addWidget(self.fp_log_text)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.fp_log_text.clear)
        log_layout.addWidget(clear_log_btn)

        layout.addWidget(log_group, 1)

        # Action buttons
        button_layout = QHBoxLayout()

        button_layout.addStretch()

        self.fp_cancel_btn = QPushButton("Cancel")
        self.fp_cancel_btn.setEnabled(False)
        self.fp_cancel_btn.clicked.connect(self.cancel_full_process)
        button_layout.addWidget(self.fp_cancel_btn)

        self.fp_run_btn = QPushButton("Start Full Process")
        self.fp_run_btn.setDefault(True)
        self.fp_run_btn.setStyleSheet("""
            QPushButton {
                background-color: #5c2d91;
                color: white;
                padding: 10px 25px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a2377;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.fp_run_btn.clicked.connect(self.run_full_process)
        button_layout.addWidget(self.fp_run_btn)

        layout.addLayout(button_layout)

    def setup_settings_tab(self, tab: QWidget):
        """Setup the settings tab."""
        layout = QVBoxLayout(tab)

        # Tool paths
        tools_group = QGroupBox("Tool Paths")
        tools_layout = QFormLayout(tools_group)

        self.alass_edit = QLineEdit()
        alass_browse = QPushButton("...")
        alass_browse.setMaximumWidth(30)
        alass_browse.clicked.connect(lambda: self.browse_tool(self.alass_edit, "alass"))
        alass_layout = QHBoxLayout()
        alass_layout.addWidget(self.alass_edit)
        alass_layout.addWidget(alass_browse)
        tools_layout.addRow("alass:", alass_layout)

        self.mkvmerge_edit = QLineEdit()
        mkvmerge_browse = QPushButton("...")
        mkvmerge_browse.setMaximumWidth(30)
        mkvmerge_browse.clicked.connect(lambda: self.browse_tool(self.mkvmerge_edit, "mkvmerge"))
        mkvmerge_layout = QHBoxLayout()
        mkvmerge_layout.addWidget(self.mkvmerge_edit)
        mkvmerge_layout.addWidget(mkvmerge_browse)
        tools_layout.addRow("mkvmerge:", mkvmerge_layout)

        self.subtitle_edit_edit = QLineEdit()
        subtitle_edit_browse = QPushButton("...")
        subtitle_edit_browse.setMaximumWidth(30)
        subtitle_edit_browse.clicked.connect(lambda: self.browse_tool(self.subtitle_edit_edit, "SubtitleEdit"))
        subtitle_edit_layout = QHBoxLayout()
        subtitle_edit_layout.addWidget(self.subtitle_edit_edit)
        subtitle_edit_layout.addWidget(subtitle_edit_browse)
        tools_layout.addRow("SubtitleEdit:", subtitle_edit_layout)

        layout.addWidget(tools_group)

        # Folder settings
        folders_group = QGroupBox("Folder Names")
        folders_layout = QFormLayout(folders_group)

        self.subtitle_folder_edit = QLineEdit()
        self.subtitle_folder_edit.setPlaceholderText("Subtitle_HEBREW")
        folders_layout.addRow("Subtitle folder:", self.subtitle_folder_edit)

        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Output")
        folders_layout.addRow("Output folder:", self.output_folder_edit)

        layout.addWidget(folders_group)

        # Subtitle settings
        subtitle_group = QGroupBox("Subtitle Settings")
        subtitle_layout = QFormLayout(subtitle_group)

        self.language_edit = QLineEdit()
        self.language_edit.setPlaceholderText("heb")
        subtitle_layout.addRow("Language code:", self.language_edit)

        self.track_name_edit = QLineEdit()
        self.track_name_edit.setPlaceholderText("Hebrew")
        subtitle_layout.addRow("Track name:", self.track_name_edit)

        self.default_sub_check = QCheckBox("Set as default subtitle track")
        self.default_sub_check.setChecked(True)
        subtitle_layout.addRow("", self.default_sub_check)

        self.keep_temp_check = QCheckBox("Keep temporary files")
        subtitle_layout.addRow("", self.keep_temp_check)

        layout.addWidget(subtitle_group)

        # API settings
        api_group = QGroupBox("Gemini API (Translation)")
        api_layout = QFormLayout(api_group)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("AIza...")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.api_key_edit)

        self.api_model_edit = QLineEdit()
        self.api_model_edit.setPlaceholderText("gemini-2.0-flash")
        api_layout.addRow("Model:", self.api_model_edit)

        self.batch_size_edit = QLineEdit()
        self.batch_size_edit.setPlaceholderText("25")
        api_layout.addRow("Batch size:", self.batch_size_edit)

        layout.addWidget(api_group)

        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()

    def load_settings_to_ui(self):
        """Load settings from config to UI elements."""
        tools = self.config.get('tools', {})
        settings = self.config.get('settings', {})
        processing = self.config.get('processing', {})
        api = self.config.get('api', {})

        self.alass_edit.setText(tools.get('alass', ''))
        self.mkvmerge_edit.setText(tools.get('mkvmerge', ''))
        self.subtitle_edit_edit.setText(tools.get('subtitle_edit', ''))

        self.subtitle_folder_edit.setText(settings.get('subtitle_folder_name', 'Subtitle_HEBREW'))
        self.output_folder_edit.setText(settings.get('output_folder_name', 'Output'))
        self.language_edit.setText(settings.get('subtitle_language', 'heb'))
        self.track_name_edit.setText(settings.get('subtitle_track_name', 'Hebrew'))
        self.default_sub_check.setChecked(settings.get('default_subtitle', True))
        self.keep_temp_check.setChecked(processing.get('keep_temp_files', False))

        # API settings - prefer environment variable over config file
        env_api_key = os.environ.get('GEMINI_API_KEY', '')
        self.api_key_edit.setText(env_api_key or api.get('gemini_key', ''))
        self.api_model_edit.setText(api.get('gemini_model', 'gemini-2.0-flash'))
        self.batch_size_edit.setText(str(api.get('batch_size', 25)))

    def save_settings(self):
        """Save settings from UI to config."""
        self.config['tools'] = {
            'alass': self.alass_edit.text(),
            'mkvmerge': self.mkvmerge_edit.text(),
            'subtitle_edit': self.subtitle_edit_edit.text(),
        }
        self.config['settings'] = {
            'subtitle_folder_name': self.subtitle_folder_edit.text() or 'Subtitle_HEBREW',
            'output_folder_name': self.output_folder_edit.text() or 'Output',
            'subtitle_language': self.language_edit.text() or 'heb',
            'subtitle_track_name': self.track_name_edit.text() or 'Hebrew',
            'default_subtitle': self.default_sub_check.isChecked(),
        }
        self.config['processing'] = {
            'keep_temp_files': self.keep_temp_check.isChecked(),
        }
        # Don't save API key to config file - it should stay in .env
        self.config['api'] = {
            'gemini_model': self.api_model_edit.text() or 'gemini-2.0-flash',
            'batch_size': int(self.batch_size_edit.text() or '25'),
        }

        self.save_config()
        self.log("Settings saved", "info")
        QMessageBox.information(self, "Settings", "Settings saved successfully!")

    def get_pipeline_config(self) -> PipelineConfig:
        """Create PipelineConfig from current settings."""
        return PipelineConfig(
            alass_path=self.alass_edit.text() or None,
            mkvmerge_path=self.mkvmerge_edit.text() or None,
            subtitle_edit_path=self.subtitle_edit_edit.text() or None,
            subtitle_folder_name=self.subtitle_folder_edit.text() or 'Subtitle_HEBREW',
            output_folder_name=self.output_folder_edit.text() or 'Output',
            subtitle_language=self.language_edit.text() or 'heb',
            subtitle_track_name=self.track_name_edit.text() or 'Hebrew',
            default_subtitle=self.default_sub_check.isChecked(),
            keep_temp_files=self.keep_temp_check.isChecked(),
        )

    def get_selected_mode(self) -> PipelineMode:
        """Get the currently selected pipeline mode."""
        index = self.mode_combo.currentIndex()
        modes = [
            PipelineMode.FULL_PIPELINE,
            PipelineMode.SYNC_ONLY,
            PipelineMode.RTL_ONLY,
            PipelineMode.EMBED_ONLY,
        ]
        return modes[index]

    def on_mode_changed(self, index: int):
        """Handle mode selection change."""
        mode = self.get_selected_mode()
        if mode == PipelineMode.RTL_ONLY:
            self.input_edit.setPlaceholderText("Folder with SRT files or single SRT file...")
        else:
            self.input_edit.setPlaceholderText("Season folder with MKV files and Subtitle_HEBREW subfolder...")

    def browse_input(self):
        """Browse for input folder."""
        mode = self.get_selected_mode()

        if mode == PipelineMode.RTL_ONLY:
            # Can select file or folder
            path = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Season Folder")

        if path:
            self.input_edit.setText(path)
            self.drop_label.setText(path)

    def browse_output(self):
        """Browse for output folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_edit.setText(path)

    def browse_tool(self, line_edit: QLineEdit, tool_name: str):
        """Browse for a tool executable."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {tool_name} executable",
            "",
            "Executables (*.exe);;All Files (*)"
        )
        if path:
            line_edit.setText(path)

    def on_folder_dropped(self, path: str):
        """Handle folder dropped on drop zone."""
        self.input_edit.setText(path)
        self.drop_label.setText(f"Selected: {Path(path).name}")

    def log(self, message: str, level: str = "info"):
        """Add message to log area."""
        colors = {
            "info": "#d4d4d4",
            "warning": "#dcdcaa",
            "error": "#f14c4c",
            "success": "#4ec9b0",
        }
        color = colors.get(level, "#d4d4d4")
        self.log_text.append(f'<span style="color: {color}">{message}</span>')

    def verify_tools(self):
        """Verify that required tools are available."""
        self.log("Verifying tools...", "info")

        mode = self.get_selected_mode()
        config = self.get_pipeline_config()
        pipeline = Pipeline(config=config, log_callback=self.log)

        results = pipeline.verify_tools(mode)

        all_ok = all(results.values())
        if all_ok:
            self.log("All tools verified successfully!", "success")
        else:
            self.log("Some tools are missing or not found", "error")

    def run_pipeline(self):
        """Start the pipeline operation."""
        input_path = self.input_edit.text().strip()
        if not input_path:
            QMessageBox.warning(self, "Input Required", "Please select an input folder.")
            return

        input_path = Path(input_path)
        if not input_path.exists():
            QMessageBox.warning(self, "Invalid Path", f"Path does not exist: {input_path}")
            return

        output_path = None
        output_text = self.output_edit.text().strip()
        if output_text:
            output_path = Path(output_text)

        mode = self.get_selected_mode()
        config = self.get_pipeline_config()

        # Verify tools first
        pipeline = Pipeline(config=config)
        tool_status = pipeline.verify_tools(mode)
        if not all(tool_status.values()):
            missing = [k for k, v in tool_status.items() if not v]
            QMessageBox.warning(
                self,
                "Missing Tools",
                f"The following tools are missing: {', '.join(missing)}\n\n"
                "Please configure the tool paths in the Settings tab."
            )
            return

        # Start worker thread
        self.worker = PipelineWorker(mode, input_path, output_path, config)
        self.worker.progress.connect(self.on_progress)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_finished)

        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")
        self.log(f"Starting {mode.value} operation...", "info")

        self.worker.start()

    def cancel_operation(self):
        """Cancel the running operation."""
        if self.worker:
            self.worker.cancel()
            self.log("Cancelling operation...", "warning")

    def on_progress(self, message: str, current: int, total: int):
        """Handle progress updates from worker."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.status_label.setText(f"{message} ({current}/{total})")

    def on_finished(self, results: list):
        """Handle pipeline completion."""
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(100)

        success = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        self.status_label.setText(f"Complete: {success} succeeded, {failed} failed")
        self.log(f"Pipeline complete: {success} succeeded, {failed} failed", "success" if failed == 0 else "warning")

        if failed > 0:
            for r in results:
                if not r.success:
                    self.log(f"  Failed: {r.input_file.name} - {r.error_message}", "error")

    # ==================== Translation Tab Methods ====================

    def translate_log(self, message: str, level: str = "info"):
        """Add message to translation log area."""
        colors = {
            "info": "#d4d4d4",
            "warning": "#dcdcaa",
            "error": "#f14c4c",
            "success": "#4ec9b0",
        }
        color = colors.get(level, "#d4d4d4")
        self.translate_log_text.append(f'<span style="color: {color}">{message}</span>')

    def browse_translate_source(self):
        """Browse for source folder (English subtitles)."""
        path = QFileDialog.getExistingDirectory(self, "Select English Subtitles Folder")
        if path:
            self.translate_source_edit.setText(path)
            self.translate_source_drop.setText(f"Selected: {Path(path).name}")
            self.update_source_file_count()

    def browse_translate_target(self):
        """Browse for target folder (where to create Subtitle_HEBREW)."""
        path = QFileDialog.getExistingDirectory(self, "Select Season Folder")
        if path:
            self.translate_target_edit.setText(path)
            self.translate_target_drop.setText(f"Selected: {Path(path).name}")
            self.update_target_preview()

    def on_translate_source_dropped(self, path: str):
        """Handle source folder dropped."""
        self.translate_source_edit.setText(path)
        self.translate_source_drop.setText(f"Selected: {Path(path).name}")
        self.update_source_file_count()

    def on_translate_target_dropped(self, path: str):
        """Handle target folder dropped."""
        self.translate_target_edit.setText(path)
        self.translate_target_drop.setText(f"Selected: {Path(path).name}")
        self.update_target_preview()

    def update_source_file_count(self):
        """Update the source file count label."""
        source_path = self.translate_source_edit.text().strip()
        if source_path and Path(source_path).exists():
            srt_files = list(Path(source_path).glob("*.srt"))
            count = len(srt_files)
            self.source_file_count_label.setText(f"Found: {count} SRT file(s)")
            self.source_file_count_label.setStyleSheet(
                "color: #4ec9b0;" if count > 0 else "color: #f14c4c;"
            )
        else:
            self.source_file_count_label.setText("")

    def update_target_preview(self):
        """Update the target preview label."""
        target_path = self.translate_target_edit.text().strip()
        if target_path:
            subtitle_folder = self.subtitle_folder_edit.text() or "Subtitle_HEBREW"
            output_path = Path(target_path) / subtitle_folder
            self.target_preview_label.setText(f"Will create: {output_path}")
            self.target_preview_label.setStyleSheet("color: #666;")
        else:
            self.target_preview_label.setText("")

    def get_translator_config(self) -> TranslatorConfig:
        """Create TranslatorConfig from current settings."""
        api = self.config.get('api', {})
        return TranslatorConfig(
            api_key=self.api_key_edit.text() or api.get('gemini_key', ''),
            model=self.api_model_edit.text() or api.get('gemini_model', 'gemini-2.0-flash'),
            batch_size=int(self.batch_size_edit.text() or api.get('batch_size', 25)),
        )

    def test_gemini_api(self):
        """Test the Gemini API connection."""
        api_key = self.api_key_edit.text() or self.config.get('api', {}).get('gemini_key', '')
        model = self.api_model_edit.text() or self.config.get('api', {}).get('gemini_model', 'gemini-2.0-flash')

        if not api_key:
            QMessageBox.warning(
                self,
                "API Key Required",
                "Please enter your Gemini API key in the Settings tab."
            )
            return

        self.translate_log("Testing Gemini API connection...", "info")
        self.test_api_btn.setEnabled(False)

        try:
            if test_api_connection(api_key, model):
                self.translate_log("API connection successful!", "success")
                QMessageBox.information(self, "API Test", "Gemini API connection successful!")
        except TranslationError as e:
            self.translate_log(f"API test failed: {e}", "error")
            QMessageBox.warning(self, "API Test Failed", str(e))
        finally:
            self.test_api_btn.setEnabled(True)

    def run_translation(self):
        """Start the translation operation."""
        source_path = self.translate_source_edit.text().strip()
        target_path = self.translate_target_edit.text().strip()

        if not source_path:
            QMessageBox.warning(self, "Source Required", "Please select a source folder with English subtitles.")
            return

        if not target_path:
            QMessageBox.warning(self, "Target Required", "Please select a target folder where Subtitle_HEBREW will be created.")
            return

        source_path = Path(source_path)
        target_path = Path(target_path)

        if not source_path.exists():
            QMessageBox.warning(self, "Invalid Path", f"Source folder does not exist: {source_path}")
            return

        if not target_path.exists():
            QMessageBox.warning(self, "Invalid Path", f"Target folder does not exist: {target_path}")
            return

        # Check for SRT files
        srt_files = list(source_path.glob("*.srt"))
        if not srt_files:
            QMessageBox.warning(self, "No Files", "No SRT files found in source folder.")
            return

        # Check API key
        config = self.get_translator_config()
        if not config.api_key:
            QMessageBox.warning(
                self,
                "API Key Required",
                "Please enter your Gemini API key in the Settings tab."
            )
            return

        subtitle_folder = self.subtitle_folder_edit.text() or "Subtitle_HEBREW"

        # Start worker thread
        self.translation_worker = TranslationWorker(
            source_path, target_path, config, subtitle_folder
        )
        self.translation_worker.progress.connect(self.on_translate_progress)
        self.translation_worker.log.connect(self.translate_log)
        self.translation_worker.finished.connect(self.on_translate_finished)

        self.translate_btn.setEnabled(False)
        self.translate_cancel_btn.setEnabled(True)
        self.translate_progress_bar.setValue(0)
        self.translate_status_label.setText("Starting translation...")
        self.translate_log(f"Starting translation of {len(srt_files)} files...", "info")

        self.translation_worker.start()

    def cancel_translation(self):
        """Cancel the translation operation."""
        if self.translation_worker:
            self.translation_worker.cancel()
            self.translate_log("Cancelling translation...", "warning")

    def on_translate_progress(self, message: str, current: int, total: int):
        """Handle translation progress updates."""
        if total > 0:
            percent = int((current / total) * 100)
            self.translate_progress_bar.setValue(percent)
        self.translate_status_label.setText(f"{message} ({current}/{total})")

    def on_translate_finished(self, results: list):
        """Handle translation completion."""
        self.translate_btn.setEnabled(True)
        self.translate_cancel_btn.setEnabled(False)
        self.translate_progress_bar.setValue(100)

        success = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_lines = sum(r.lines_count for r in results if r.success)

        self.translate_status_label.setText(f"Complete: {success} succeeded, {failed} failed")
        self.translate_log(
            f"Translation complete: {success} files, {total_lines} lines translated",
            "success" if failed == 0 else "warning"
        )

        if failed > 0:
            for r in results:
                if not r.success:
                    self.translate_log(f"  Failed: {r.input_file.name} - {r.error_message}", "error")

    # ==================== Full Process Tab Methods ====================

    def fp_log(self, message: str, level: str = "info"):
        """Add message to full process log area."""
        colors = {
            "info": "#d4d4d4",
            "warning": "#dcdcaa",
            "error": "#f14c4c",
            "success": "#4ec9b0",
        }
        color = colors.get(level, "#d4d4d4")
        self.fp_log_text.append(f'<span style="color: {color}">{message}</span>')

    def browse_fp_source(self):
        """Browse for source folder (English subtitles)."""
        path = QFileDialog.getExistingDirectory(self, "Select English Subtitles Folder")
        if path:
            self.fp_source_edit.setText(path)
            self.fp_source_drop.setText(f"Selected: {Path(path).name}")
            self.update_fp_source_count()

    def browse_fp_target(self):
        """Browse for target folder (season folder with MKVs)."""
        path = QFileDialog.getExistingDirectory(self, "Select Season Folder")
        if path:
            self.fp_target_edit.setText(path)
            self.fp_target_drop.setText(f"Selected: {Path(path).name}")
            self.update_fp_target_info()

    def on_fp_source_dropped(self, path: str):
        """Handle source folder dropped."""
        self.fp_source_edit.setText(path)
        self.fp_source_drop.setText(f"Selected: {Path(path).name}")
        self.update_fp_source_count()

    def on_fp_target_dropped(self, path: str):
        """Handle target folder dropped."""
        self.fp_target_edit.setText(path)
        self.fp_target_drop.setText(f"Selected: {Path(path).name}")
        self.update_fp_target_info()

    def update_fp_source_count(self):
        """Update the source file count label."""
        source_path = self.fp_source_edit.text().strip()
        if source_path and Path(source_path).exists():
            srt_files = list(Path(source_path).glob("*.srt"))
            count = len(srt_files)
            self.fp_source_count_label.setText(f"Found: {count} English SRT file(s)")
            self.fp_source_count_label.setStyleSheet(
                "color: #4ec9b0;" if count > 0 else "color: #f14c4c;"
            )
        else:
            self.fp_source_count_label.setText("")

    def update_fp_target_info(self):
        """Update the target folder info labels."""
        target_path = self.fp_target_edit.text().strip()
        if target_path and Path(target_path).exists():
            mkv_files = list(Path(target_path).glob("*.mkv"))
            count = len(mkv_files)
            self.fp_mkv_count_label.setText(f"Found: {count} MKV file(s)")
            self.fp_mkv_count_label.setStyleSheet(
                "color: #4ec9b0;" if count > 0 else "color: #f14c4c;"
            )

            # Show output folder preview
            output_folder = self.output_folder_edit.text() or "Output"
            self.fp_match_label.setText(f"Output: {Path(target_path) / output_folder}")
            self.fp_match_label.setStyleSheet("color: #666;")
        else:
            self.fp_mkv_count_label.setText("")
            self.fp_match_label.setText("")

    def run_full_process(self):
        """Start the full process operation."""
        source_path = self.fp_source_edit.text().strip()
        target_path = self.fp_target_edit.text().strip()

        if not source_path:
            QMessageBox.warning(self, "Source Required", "Please select a source folder with English subtitles.")
            return

        if not target_path:
            QMessageBox.warning(self, "Target Required", "Please select a target folder with MKV files.")
            return

        source_path = Path(source_path)
        target_path = Path(target_path)

        if not source_path.exists():
            QMessageBox.warning(self, "Invalid Path", f"Source folder does not exist: {source_path}")
            return

        if not target_path.exists():
            QMessageBox.warning(self, "Invalid Path", f"Target folder does not exist: {target_path}")
            return

        # Check for SRT files
        srt_files = list(source_path.glob("*.srt"))
        if not srt_files:
            QMessageBox.warning(self, "No Files", "No SRT files found in source folder.")
            return

        # Check for MKV files
        mkv_files = list(target_path.glob("*.mkv"))
        if not mkv_files:
            QMessageBox.warning(self, "No Files", "No MKV files found in target folder.")
            return

        # Check API key
        translator_config = self.get_translator_config()
        if not translator_config.api_key:
            QMessageBox.warning(
                self,
                "API Key Required",
                "Please enter your Gemini API key in the Settings tab."
            )
            return

        # Verify tools
        pipeline_config = self.get_pipeline_config()
        try:
            find_alass(pipeline_config.alass_path)
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "alass Not Found",
                "alass tool is required for syncing. Please configure it in Settings."
            )
            return

        try:
            find_mkvmerge(pipeline_config.mkvmerge_path)
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "mkvmerge Not Found",
                "mkvmerge tool is required for embedding. Please configure it in Settings."
            )
            return

        # Reset progress UI
        for label in self.fp_stage_labels:
            label.setStyleSheet("color: #888;")
        self.fp_overall_progress.setValue(0)
        self.fp_current_progress.setValue(0)

        # Start worker thread
        self.full_process_worker = FullProcessWorker(
            source_path,
            target_path,
            translator_config,
            pipeline_config,
            self.keep_temp_check.isChecked()
        )
        self.full_process_worker.progress.connect(self.on_fp_progress)
        self.full_process_worker.log.connect(self.fp_log)
        self.full_process_worker.finished.connect(self.on_fp_finished)

        self.fp_run_btn.setEnabled(False)
        self.fp_cancel_btn.setEnabled(True)
        self.fp_status_label.setText("Starting full process...")
        self.fp_log(f"Starting full process: {len(srt_files)} files...", "info")

        self.full_process_worker.start()

    def cancel_full_process(self):
        """Cancel the full process operation."""
        if self.full_process_worker:
            self.full_process_worker.cancel()
            self.fp_log("Cancelling operation...", "warning")

    def on_fp_progress(self, message: str, stage: int, current: int, total: int):
        """Handle full process progress updates."""
        # Update stage indicators
        stages = ["Translate", "Sync", "RTL Fix", "Embed"]
        for i, label in enumerate(self.fp_stage_labels):
            if i + 1 < stage:
                label.setText(f"✓ {stages[i]}")
                label.setStyleSheet("color: #4ec9b0;")
            elif i + 1 == stage:
                label.setText(f"● {stages[i]}")
                label.setStyleSheet("color: #0078d4; font-weight: bold;")
            else:
                label.setText(f"○ {stages[i]}")
                label.setStyleSheet("color: #888;")

        # Update current progress
        if total > 0:
            percent = int((current / total) * 100)
            self.fp_current_progress.setValue(percent)

        # Calculate overall progress
        # Stage weights: Translate 40%, Sync 20%, RTL 20%, Embed 20%
        stage_weights = {1: (0, 40), 2: (40, 60), 3: (60, 80), 4: (80, 100)}
        if stage in stage_weights:
            start, end = stage_weights[stage]
            if total > 0:
                stage_progress = (current / total) * (end - start)
                overall = int(start + stage_progress)
                self.fp_overall_progress.setValue(overall)

        self.fp_status_label.setText(f"Stage {stage}/4: {message} ({current}/{total})")

    def on_fp_finished(self, results: dict):
        """Handle full process completion."""
        self.fp_run_btn.setEnabled(True)
        self.fp_cancel_btn.setEnabled(False)
        self.fp_overall_progress.setValue(100)
        self.fp_current_progress.setValue(100)

        # Mark all stages complete
        stages = ["Translate", "Sync", "RTL Fix", "Embed"]
        for i, label in enumerate(self.fp_stage_labels):
            label.setText(f"✓ {stages[i]}")
            label.setStyleSheet("color: #4ec9b0;")

        if results['success']:
            self.fp_status_label.setText(
                f"Complete: {results['embedded']} files processed"
            )
            self.fp_log(
                f"Full process complete! Output: {results['output_folder']}",
                "success"
            )
        else:
            self.fp_status_label.setText("Process failed or incomplete")
            self.fp_log("Process failed or was cancelled", "error")

        if results['failed']:
            self.fp_log(f"⚠ {len(results['failed'])} errors occurred:", "warning")
            for stage, filename, error in results['failed']:
                self.fp_log(f"  [{stage}] {filename}: {error}", "error")


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Set application metadata
    app.setApplicationName("Hebrew Subtitle Pipeline")
    app.setOrganizationName("SubtitlePipeline")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
