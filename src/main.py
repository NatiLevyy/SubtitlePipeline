"""
Hebrew Subtitle Pipeline - CLI Entry Point

Modular tool for processing Hebrew subtitles:
1. Sync subtitles to video using alass
2. Fix RTL punctuation for Hebrew text
3. Embed subtitles into MKV files

Supports running each step independently or all together.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict

import yaml

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        GREEN = RED = YELLOW = CYAN = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

from pipeline import Pipeline, PipelineMode, PipelineConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict:
    """Load configuration from YAML file."""
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def print_status(message: str, level: str = "info"):
    """Print colored status message."""
    colors = {
        "info": "",
        "success": Fore.GREEN,
        "error": Fore.RED,
        "warning": Fore.YELLOW,
    }
    color = colors.get(level, "")
    print(f"{color}{message}{Style.RESET_ALL}")


def create_pipeline_config(config: Dict) -> PipelineConfig:
    """Create PipelineConfig from loaded YAML config."""
    tools = config.get('tools', {})
    settings = config.get('settings', {})
    processing = config.get('processing', {})

    return PipelineConfig(
        alass_path=tools.get('alass'),
        mkvmerge_path=tools.get('mkvmerge'),
        subtitle_edit_path=tools.get('subtitle_edit'),
        subtitle_folder_name=settings.get('subtitle_folder_name', 'Subtitle_HEBREW'),
        output_folder_name=settings.get('output_folder_name', 'Output'),
        subtitle_language=settings.get('subtitle_language', 'heb'),
        subtitle_track_name=settings.get('subtitle_track_name', 'Hebrew'),
        default_subtitle=settings.get('default_subtitle', True),
        keep_temp_files=processing.get('keep_temp_files', False),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Hebrew Subtitle Pipeline - Process and embed Hebrew subtitles into MKV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  full    - Run full pipeline: Sync -> RTL Fix -> Embed (default)
  sync    - Sync subtitles to video timing only (alass)
  rtl     - Fix RTL punctuation in SRT files only
  embed   - Embed SRT subtitles into MKV files only

Examples:
  python main.py "G:\\Shows\\ER\\Season 6"
  python main.py "G:\\Shows\\ER\\Season 6" --mode sync
  python main.py "G:\\Subtitles" --mode rtl
  python main.py . --mode embed --output "G:\\Output"
  python main.py --verify-only --mode full
        """
    )
    parser.add_argument(
        "folder",
        type=str,
        nargs='?',
        default='.',
        help="Path to the folder to process (default: current directory)"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=['full', 'sync', 'rtl', 'embed'],
        default='full',
        help="Operation mode (default: full)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output folder (optional, uses default based on mode)"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config.yaml"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify tools are installed, don't process files"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical user interface"
    )

    args = parser.parse_args()

    # Launch GUI if requested
    if args.gui:
        try:
            from gui import main as gui_main
            gui_main()
            return
        except ImportError as e:
            print_status(f"GUI not available: {e}", "error")
            print_status("Install PyQt5: pip install PyQt5", "info")
            sys.exit(1)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config
    if args.config:
        config_path = Path(args.config)
    else:
        script_dir = Path(__file__).parent
        config_path = script_dir.parent / "config.yaml"
        if not config_path.exists():
            config_path = script_dir / "config.yaml"

    config = load_config(config_path)
    if config:
        print_status(f"Loaded config: {config_path}", "success")
    else:
        print_status("No config file found, using defaults", "warning")

    # Map mode string to enum
    mode_map = {
        'full': PipelineMode.FULL_PIPELINE,
        'sync': PipelineMode.SYNC_ONLY,
        'rtl': PipelineMode.RTL_ONLY,
        'embed': PipelineMode.EMBED_ONLY,
    }
    mode = mode_map[args.mode]

    # Create pipeline
    pipeline_config = create_pipeline_config(config)
    pipeline = Pipeline(
        config=pipeline_config,
        progress_callback=lambda msg, cur, tot: print_status(f"[{cur}/{tot}] {msg}"),
        log_callback=lambda msg, lvl: print_status(msg, lvl)
    )

    print()
    print_status(f"Mode: {mode.value}", "info")
    print()

    # Verify tools
    print_status("Verifying tools...", "info")
    tool_status = pipeline.verify_tools(mode)

    if not all(tool_status.values()):
        missing = [k for k, v in tool_status.items() if not v]
        print_status(f"Missing tools: {', '.join(missing)}", "error")
        sys.exit(1)

    print_status("All required tools available", "success")
    print()

    if args.verify_only:
        print_status("Tool verification complete", "success")
        sys.exit(0)

    # Process folder
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print_status(f"Folder not found: {folder_path}", "error")
        sys.exit(1)

    output_path = Path(args.output) if args.output else None

    # Run pipeline
    results = pipeline.run(mode, folder_path, output_path)

    # Print summary
    print()
    print("=" * 50)
    success = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    print_status(f"Successful: {success}", "success")
    print_status(f"Failed: {failed}", "error" if failed > 0 else "info")
    print("=" * 50)

    if failed > 0:
        print()
        print_status("Failed files:", "error")
        for r in results:
            if not r.success:
                print_status(f"  {r.input_file.name}: {r.error_message}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
