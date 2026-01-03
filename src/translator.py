"""
Translator - Translate English SRT files to Hebrew using Gemini API.

Uses Google's Gemini 1.5 Flash model for translation with:
- Batch processing for context awareness
- Gender-aware translation
- Rate limit handling with retry logic
- Request delays to avoid rate limits
"""

import re
import time
import logging
from pathlib import Path
from typing import Callable, List, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when translation fails."""
    pass


@dataclass
class TranslationResult:
    """Result of translating a single file."""
    success: bool
    input_file: Path
    output_file: Optional[Path] = None
    lines_count: int = 0
    error_message: Optional[str] = None


@dataclass
class TranslatorConfig:
    """Configuration for the translator."""
    api_key: str
    model: str = "gemini-2.0-flash"  # Use 2.0-flash for paid accounts
    batch_size: int = 20  # Reduced for better quality
    context_lines: int = 10  # Increased for better gender detection
    retry_delay: float = 30.0
    max_retries: int = 5
    request_delay: float = 2.0  # Delay between API calls (2s for paid tier)


def parse_srt(content: str) -> List[Dict[str, Any]]:
    """
    Parse SRT content into blocks.

    Args:
        content: The full SRT file content

    Returns:
        List of subtitle blocks with index, start, end, and text
    """
    blocks = []
    # Pattern to match SRT blocks
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*(?:\n|$))*?)(?=\n\d+\n|\Z)'

    for match in re.finditer(pattern, content, re.MULTILINE):
        blocks.append({
            'index': match.group(1),
            'start': match.group(2),
            'end': match.group(3),
            'text': match.group(4).strip()
        })

    return blocks


def build_srt(blocks: List[Dict[str, Any]]) -> str:
    """
    Build SRT content from blocks.

    Args:
        blocks: List of subtitle blocks

    Returns:
        SRT formatted string
    """
    lines = []
    for block in blocks:
        lines.append(block['index'])
        lines.append(f"{block['start']} --> {block['end']}")
        lines.append(block['text'])
        lines.append('')

    return '\n'.join(lines)


class Translator:
    """
    Translator for English to Hebrew subtitle translation.

    Uses Gemini API with batch processing and context awareness.
    """

    def __init__(
        self,
        config: TranslatorConfig,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize the translator.

        Args:
            config: Translator configuration
            progress_callback: Called with (message, current, total) for progress
            log_callback: Called with (message, level) for logging
        """
        self.config = config
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self._cancelled = False
        self._client = None

    def _log(self, message: str, level: str = "info"):
        """Log a message."""
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
        if self.log_callback:
            self.log_callback(message, level)

    def _progress(self, message: str, current: int, total: int):
        """Report progress."""
        if self.progress_callback:
            self.progress_callback(message, current, total)

    def cancel(self):
        """Cancel the current operation."""
        self._cancelled = True

    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.config.api_key)
            except ImportError:
                raise TranslationError(
                    "google-genai package not installed. "
                    "Run: pip install google-genai"
                )
        return self._client

    def _translate_batch(
        self,
        batch: List[Dict[str, Any]],
        context_blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Translate a batch of subtitle blocks.

        Args:
            batch: Current batch of blocks to translate
            context_blocks: Previous blocks for context

        Returns:
            Batch with translated text
        """
        client = self._get_client()

        # Format text for translation
        text_to_translate = "\n".join([b['text'] for b in batch])
        context_text = "\n".join([b['text'] for b in context_blocks]) if context_blocks else ""

        prompt = f"""You are a professional Hebrew subtitle translator. Translate the following subtitles from English to Hebrew.

## CRITICAL RULES:

### 1. EVERYTHING IN HEBREW
- Output must be 100% Hebrew characters
- TRANSLITERATE all names to Hebrew:
  - Brenner → ברנר
  - John → ג'ון
  - Elizabeth → אליזבת
  - Michael → מייקל
  - Dr. Green → ד"ר גרין
  - Carter → קרטר
  - County General → קאונטי ג'נרל

- ONLY keep English for:
  - Technical codes (DNA, HIV, CPR, EKG, IV)
  - Abbreviations that are used in Hebrew too (OK, CT, MRI)

### 2. GENDER DETECTION - VERY IMPORTANT!
Analyze the context carefully to determine speaker gender:

**Clues for FEMALE speaker:**
- Words like "she", "her", "actress", "mother", "sister", "wife", "girlfriend", "nurse" (often), "pregnant"
- Female names mentioned as the speaker
- Response to "ma'am", "miss", "Mrs."
- Context of previous lines mentioning a woman

**Clues for MALE speaker:**
- Words like "he", "him", "actor", "father", "brother", "husband", "boyfriend"
- Male names mentioned as the speaker
- Response to "sir", "Mr."
- Context of previous lines mentioning a man

**Use correct Hebrew verb forms:**
- Female: אמרתי, הלכתי, רציתי, עשיתי, ידעתי, חשבתי, אני רוצָה, אני יודעַת
- Male: אמרתי, הלכתי, רציתי, עשיתי, ידעתי, חשבתי, אני רוצֶה, אני יודֵע

**When UNCLEAR:** Default to male, but look for ANY hint of gender in surrounding context.

### 3. NATURAL HEBREW
- Use conversational, natural Hebrew - not formal/literary
- Use common Israeli slang where appropriate
- Contractions are OK: מה קורה, איך הולך, תגיד לי
- Keep subtitles concise - suitable for reading quickly

### 4. MEDICAL TERMS (translate to Hebrew):
- Doctor / Dr. → דוקטור / ד"ר
- Nurse → אחות / אח
- Emergency Room / ER → חדר מיון
- Surgery → ניתוח
- IV → עירוי
- Blood pressure → לחץ דם
- X-ray → צילום רנטגן
- CPR → החייאה
- Epinephrine → אפינפרין
- cc / ml → סמ"ק
- Stat! → מיד! / עכשיו!

### 5. CONTEXT AWARENESS
- Use the previous lines (context) to understand:
  - WHO is speaking (male/female)
  - WHAT is the situation
  - The TONE (angry, sad, happy, sarcastic)
- Maintain consistency in character voice

{f'### CONTEXT (previous subtitles - DO NOT translate, use for understanding only):' + chr(10) + context_text if context_text else ''}

### TRANSLATE THESE LINES:
Return exactly {len(batch)} lines, one translation per line, in the same order.

{text_to_translate}

### OUTPUT:
Hebrew translations only, one per line, same order as input:"""

        # Retry logic for rate limits
        for attempt in range(self.config.max_retries):
            try:
                response = client.models.generate_content(
                    model=self.config.model,
                    contents=prompt
                )
                translated_lines = response.text.strip().split('\n')

                # Filter out empty lines
                translated_lines = [line for line in translated_lines if line.strip()]

                # Match translations to blocks
                for i, block in enumerate(batch):
                    if i < len(translated_lines):
                        block['text'] = translated_lines[i].strip()
                    else:
                        # If we got fewer lines, keep original
                        self._log(f"Warning: Missing translation for line {i+1}", "warning")

                # Add delay after successful request to respect rate limits
                # Free tier: 15 requests per minute = 1 request every 4 seconds
                time.sleep(self.config.request_delay)

                return batch

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < self.config.max_retries - 1:
                        # Progressive backoff: 30s, 60s, 90s, 120s
                        wait_time = min(self.config.retry_delay * (attempt + 1), 120)
                        self._log(f"Rate limited. Waiting {wait_time}s before retry ({attempt + 1}/{self.config.max_retries})...", "warning")
                        time.sleep(wait_time)
                        continue
                raise TranslationError(f"Translation failed: {e}")

        raise TranslationError("Max retries exceeded")

    def translate_file(
        self,
        input_path: Path,
        output_path: Path
    ) -> int:
        """
        Translate a single SRT file.

        Args:
            input_path: Path to English SRT file
            output_path: Path for Hebrew output

        Returns:
            Number of lines translated

        Raises:
            TranslationError: If translation fails
        """
        self._log(f"Translating: {input_path.name}", "info")

        # Read input file with encoding detection
        content = None
        encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1']

        for enc in encodings:
            try:
                content = input_path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise TranslationError(f"Could not read file with any known encoding: {input_path}")

        # Parse SRT
        blocks = parse_srt(content)
        if not blocks:
            raise TranslationError(f"No subtitle blocks found in file: {input_path}")

        self._log(f"Found {len(blocks)} subtitle blocks", "info")

        # Translate in batches
        translated_blocks = []
        batch_size = self.config.batch_size
        total_batches = (len(blocks) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            if self._cancelled:
                raise TranslationError("Operation cancelled")

            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(blocks))
            batch = blocks[start_idx:end_idx]

            # Get context from previous blocks
            context_start = max(0, start_idx - self.config.context_lines)
            context_blocks = blocks[context_start:start_idx]

            self._log(f"Translating batch {batch_num + 1}/{total_batches}...", "info")

            try:
                translated_batch = self._translate_batch(batch, context_blocks)
                translated_blocks.extend(translated_batch)
            except TranslationError:
                raise
            except Exception as e:
                raise TranslationError(f"Batch translation failed: {e}")

        # Build output SRT
        output_content = build_srt(translated_blocks)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write output as UTF-8 with BOM for Hebrew compatibility
        output_path.write_text(output_content, encoding='utf-8-sig')

        self._log(f"Saved: {output_path.name}", "success")
        return len(blocks)

    def translate_folder(
        self,
        source_folder: Path,
        target_folder: Path,
        subtitle_folder_name: str = "Subtitle_HEBREW"
    ) -> List[TranslationResult]:
        """
        Translate all SRT files from source folder.

        Creates Subtitle_HEBREW folder in target folder with Hebrew translations.

        Args:
            source_folder: Folder containing English SRT files
            target_folder: Season folder where Subtitle_HEBREW will be created
            subtitle_folder_name: Name of output folder (default: Subtitle_HEBREW)

        Returns:
            List of translation results
        """
        self._cancelled = False
        results = []

        # Create output folder
        output_folder = target_folder / subtitle_folder_name
        output_folder.mkdir(parents=True, exist_ok=True)

        self._log(f"Output folder: {output_folder}", "info")

        # Find all SRT files
        srt_files = sorted(source_folder.glob("*.srt"))

        if not srt_files:
            self._log("No SRT files found in source folder", "warning")
            return results

        self._log(f"Found {len(srt_files)} SRT files to translate", "info")
        total = len(srt_files)

        for i, srt_file in enumerate(srt_files):
            if self._cancelled:
                self._log("Operation cancelled", "warning")
                break

            self._progress(f"Translating {srt_file.name}", i + 1, total)

            output_path = output_folder / srt_file.name

            try:
                lines_count = self.translate_file(srt_file, output_path)
                results.append(TranslationResult(
                    success=True,
                    input_file=srt_file,
                    output_file=output_path,
                    lines_count=lines_count
                ))
                self._log(f"Translated: {srt_file.name} ({lines_count} lines)", "success")

            except TranslationError as e:
                results.append(TranslationResult(
                    success=False,
                    input_file=srt_file,
                    error_message=str(e)
                ))
                self._log(f"Failed: {srt_file.name} - {e}", "error")

            except Exception as e:
                results.append(TranslationResult(
                    success=False,
                    input_file=srt_file,
                    error_message=str(e)
                ))
                self._log(f"Error: {srt_file.name} - {e}", "error")

        return results


def test_api_connection(api_key: str, model: str = "gemini-2.0-flash") -> bool:
    """
    Test if the Gemini API connection works.

    Args:
        api_key: Gemini API key
        model: Model to use (default: gemini-2.0-flash for paid accounts)

    Returns:
        True if connection successful

    Raises:
        TranslationError: If connection fails
    """
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents="Say 'API working' in Hebrew, just the translation."
        )

        result = response.text.strip()
        logger.info(f"API test response: {result}")
        return True

    except ImportError:
        raise TranslationError(
            "google-genai package not installed. "
            "Run: pip install google-genai"
        )
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            # Rate limited but API key is valid
            return True
        raise TranslationError(f"API connection failed: {e}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # Test API connection with paid account key
    api_key = "REDACTED_API_KEY"
    model = "gemini-2.0-flash"

    print("Testing Gemini API connection...")
    print(f"Using model: {model}")
    try:
        if test_api_connection(api_key, model):
            print("API connection successful!")
    except TranslationError as e:
        print(f"API test failed: {e}")
        sys.exit(1)
