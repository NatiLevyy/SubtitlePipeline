"""
Hebrew Subtitle Pipeline - GUI Application

PyQt5-based graphical user interface with:
- Pipeline tab: Mode selector (Sync Only | RTL Fix Only | Embed Only | Full Pipeline)
- Translate tab: English to Hebrew translation using Gemini API
- Settings tab: Tool paths and API configuration
- Drag & drop folder selection
- Progress bar and log area
"""

import sys
import os
from pathlib import Path
from typing import Optional, List
import yaml

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

        # API settings
        self.api_key_edit.setText(api.get('gemini_key', ''))
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
        self.config['api'] = {
            'gemini_key': self.api_key_edit.text(),
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
