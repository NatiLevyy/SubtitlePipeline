"""
RTL Fixer - Fixes Right-to-Left punctuation in Hebrew subtitles.

Reverses punctuation placement for proper RTL display:
- "אני רופא." becomes ".אני רופא" (visually correct for most players)
"""

import re
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RTLFixError(Exception):
    """Raised when RTL fix fails."""
    pass


# Hebrew character range pattern
HEBREW_PATTERN = re.compile(r'[\u0590-\u05FF]')

# Punctuation patterns
# End punctuation: characters that typically appear at the end of sentences
END_PUNCT_PATTERN = re.compile(r'[.!?,;:\-\"\'\)\]\}]+$')
# Start punctuation: characters that typically appear at the start
START_PUNCT_PATTERN = re.compile(r'^[.!?,;:\-\"\'\(\[\{]+')


def contains_hebrew(text: str) -> bool:
    """Check if text contains Hebrew characters."""
    return bool(HEBREW_PATTERN.search(text))


def is_content_line(line: str) -> bool:
    """
    Check if a line is subtitle content (not index or timestamp).
    """
    stripped = line.strip()

    # Empty line
    if not stripped:
        return False

    # Index line (just a number)
    if stripped.isdigit():
        return False

    # Timestamp line
    if '-->' in stripped:
        return False

    return True


def reverse_rtl_punctuation_line(line: str) -> str:
    """
    Reverse punctuation for a single line of RTL Hebrew text.

    Moves ending punctuation to the beginning for proper visual display.
    If punctuation is already at the beginning, leave it there.

    Args:
        line: A single line of subtitle text

    Returns:
        The line with reversed punctuation
    """
    if not contains_hebrew(line):
        return line

    stripped = line.strip()
    if not stripped:
        return line

    # Check if punctuation is already at the start - if so, don't change
    start_match = START_PUNCT_PATTERN.search(stripped)
    if start_match:
        # Punctuation already at start, leave as-is
        return line

    # Find punctuation at end
    end_match = END_PUNCT_PATTERN.search(stripped)

    if not end_match:
        # No punctuation at end either, nothing to do
        return line

    # Move end punctuation to start
    end_punct = end_match.group()
    content = stripped[:-len(end_punct)]
    result = end_punct + content

    # Preserve leading whitespace from original line
    leading_space = line[:len(line) - len(line.lstrip())]

    return leading_space + result


def reverse_rtl_punctuation(content: str) -> str:
    """
    Reverse RTL punctuation for an entire SRT file content.

    Args:
        content: The full content of an SRT file

    Returns:
        The content with reversed punctuation for Hebrew lines
    """
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        if is_content_line(line):
            fixed_lines.append(reverse_rtl_punctuation_line(line))
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def fix_rtl_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    unused_param: Optional[Path] = None  # Kept for API compatibility
) -> Path:
    """
    Fix RTL punctuation in an SRT file.

    Reverses punctuation placement for proper RTL display in video players.

    Args:
        input_path: Path to the input SRT file
        output_path: Path for the output file (optional, defaults to _rtl suffix)
        unused_param: Unused, kept for backward compatibility

    Returns:
        Path to the output file

    Raises:
        RTLFixError: If RTL fix fails
    """
    logger.info(f"Fixing RTL in: {input_path.name}")

    # Determine output path
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_rtl{input_path.suffix}"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try reading with different encodings
    content = None
    encodings_to_try = ['utf-8-sig', 'utf-8', 'cp1255', 'iso-8859-8']
    used_encoding = 'utf-8'

    for enc in encodings_to_try:
        try:
            content = input_path.read_text(encoding=enc)
            used_encoding = enc
            logger.debug(f"Successfully read file with encoding: {enc}")
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise RTLFixError(f"Could not read file with any known encoding: {input_path}")

    # Apply RTL fix
    fixed_content = reverse_rtl_punctuation(content)

    # Write output as UTF-8 with BOM for compatibility
    try:
        output_path.write_text(fixed_content, encoding='utf-8-sig')
    except Exception as e:
        raise RTLFixError(f"Failed to write output file: {e}")

    logger.info(f"RTL fix complete: {output_path.name}")
    return output_path


# For backward compatibility with pipeline.py
def find_subtitle_edit(config_path: Optional[str] = None) -> Path:
    """
    Stub function for backward compatibility.
    RTL fix no longer requires SubtitleEdit.
    """
    # Return a dummy path - this function is no longer used
    # but kept for API compatibility with pipeline.py
    return Path("python_rtl_fixer")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) >= 2:
        input_file = Path(sys.argv[1])
        output_file = Path(sys.argv[2]) if len(sys.argv) >= 3 else None

        if input_file.exists():
            try:
                result = fix_rtl_file(input_file, output_file)
                print(f"Fixed file saved to: {result}")
            except RTLFixError as e:
                print(f"Error: {e}")
                sys.exit(1)
        else:
            print(f"File not found: {input_file}")
            sys.exit(1)
    else:
        print("Usage: python rtl_fixer.py <input.srt> [output.srt]")
        print()
        print("Reverses punctuation for RTL Hebrew subtitles.")
        print("Example: 'אני רופא.' becomes '.אני רופא'")
