# Hebrew Subtitle Pipeline - Complete Automation Tool

## Project Overview

Build a **modular GUI application** (with standalone EXE) with **FOUR tabs**:

| Tab | Purpose |
|-----|---------|
| **Pipeline** | Process existing Hebrew subs: Sync → RTL Fix → Embed |
| **Translate** | Translate English → Hebrew (creates Subtitle_HEBREW folder) |
| **Full Process** | **Complete workflow:** Translate → Sync → RTL Fix → Embed |
| **Settings** | Configuration |

---

## User's Environment

- **OS:** Windows
- **Project folder:** `G:\Projects\SubtitlePipeline\`
- **Language:** Hebrew subtitles only (RTL)
- **Output type:** Soft subs (switchable subtitles, not burned-in)

### Pre-installed Tools

| Tool | Location | Purpose |
|------|----------|---------|
| MKVToolNix | `C:\Program Files\MKVToolNix\mkvmerge.exe` | Embedding subtitles |
| SubtitleEdit | `C:\Program Files\Subtitle Edit\SubtitleEdit.exe` | RTL fixing (GUI automation) |
| alass | `G:\Projects\SubtitlePipeline\tools\alass.exe` | Subtitle synchronization |
| Python | System PATH | Script execution |

### API Key Configuration

API key is stored in `.env` file (not in git):
```
GEMINI_API_KEY=your_api_key_here
```

Get your API key from: https://aistudio.google.com/app/apikey

**Model:** `gemini-2.0-flash` (recommended for paid accounts)

---

# PART 1: PIPELINE TAB

## Process existing Hebrew subtitles (Subtitle_HEBREW must exist)

### Input Structure

```
📁 Season Folder (e.g., "עונה 6")/
│
├── 📁 Subtitle_HEBREW/              ← Hebrew subtitles MUST exist here
│   ├── ER - 6x01 - Leave It to Weaver.srt
│   ├── ER - 6x02 - Last Rites.srt
│   └── ...
│
├── ER.1994.S06E01.720p.AMZN.WEB-DL.x265-HETeam.mkv
├── ER.1994.S06E02.720p.AMZN.WEB-DL.x265-HETeam.mkv
└── ...
```

### Pipeline - 3 Steps

#### Step 1: Sync (alass)
```bash
alass.exe "video.mkv" "subtitle.srt" "synced.srt"
```

#### Step 2: RTL Fix (SubtitleEdit GUI Automation)
Automate SubtitleEdit: Ctrl+A → Edit → "Reverse RTL start/end"

#### Step 3: Embed (mkvmerge)
```bash
mkvmerge.exe -o "output.mkv" "input.mkv" --language 0:heb --track-name 0:"Hebrew" --default-track 0:yes "subtitle.srt"
```

### Pipeline - Operation Modes

| Mode | Steps |
|------|-------|
| Full Pipeline | Sync → RTL Fix → Embed |
| Sync Only | Sync only |
| RTL Fix Only | RTL Fix only |
| Embed Only | Embed only |

### Pipeline Output

```
📁 Season Folder/
├── 📁 Subtitle_HEBREW/    ← Original (unchanged)
├── 📁 Output/             ← Final MKVs with embedded subs
│   ├── ER.1994.S06E01...mkv
│   └── ...
└── ...
```

---

# PART 2: TRANSLATE TAB

## Translate English subtitles to Hebrew (creates Subtitle_HEBREW folder)

### Input
1. **Source Folder:** English SRT files (any location)
2. **Target Folder:** Season folder where `Subtitle_HEBREW` will be created

### Translate Tab - GUI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Source (English Subtitles)                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Folder: [D:\Subtitles\ER\Season6_English  ] [Browse]│    │
│  │ Found: 22 English SRT files                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Target (Where to create Subtitle_HEBREW)                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Folder: [G:\סדרות\ER\עונה 6               ] [Browse]│    │
│  │ Will create: G:\סדרות\ER\עונה 6\Subtitle_HEBREW\    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Progress                                                    │
│  [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░]  35%             │
│                                                              │
│  [Cancel]                                    [Translate All] │
└─────────────────────────────────────────────────────────────┘
```

### Output

```
G:\סדרות\ER\עונה 6\
├── 📁 Subtitle_HEBREW\              ← CREATED by Translate tab
│   ├── ER - 6x01 - Leave It to Weaver.srt  (Hebrew)
│   └── ...
└── ...
```

---

# PART 3: FULL PROCESS TAB (NEW!)

## Complete workflow: English SRT → Final MKV with Hebrew subs

This is the **"one-click" solution** for processing an entire season.

### Input
1. **Source Folder:** English SRT files
2. **Target Folder:** Season folder with MKV files

### Full Process - 4 Stages

```
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: TRANSLATE                                         │
│  English SRT → Hebrew SRT (Gemini API)                      │
│  Creates: Subtitle_HEBREW/                                  │
├─────────────────────────────────────────────────────────────┤
│  STAGE 2: SYNC                                              │
│  Align Hebrew subtitles to video audio (alass)              │
├─────────────────────────────────────────────────────────────┤
│  STAGE 3: RTL FIX                                           │
│  Fix Hebrew punctuation (SubtitleEdit)                      │
├─────────────────────────────────────────────────────────────┤
│  STAGE 4: EMBED                                             │
│  Merge subtitles into MKV (mkvmerge)                        │
└─────────────────────────────────────────────────────────────┘
```

### Full Process - GUI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Pipeline]  [Translate]  [Full Process]  [Settings]         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ╔═══════════════════════════════════════════════════════╗  │
│  ║   FULL PROCESS - Complete Workflow                     ║  │
│  ║   English SRT → Translate → Sync → RTL → Embed         ║  │
│  ╚═══════════════════════════════════════════════════════╝  │
│                                                              │
│  Source (English Subtitles)                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Folder: [D:\Subtitles\ER\Season6_English  ] [Browse]│    │
│  │ Found: 22 English SRT files                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Target (Season folder with MKV files)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Folder: [G:\סדרות\ER\עונה 6               ] [Browse]│    │
│  │ Found: 22 MKV files                                 │    │
│  │ Matched: 22/22 episodes ✓                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Current Stage                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ● Translate  ○ Sync  ○ RTL Fix  ○ Embed             │    │
│  │                                                      │    │
│  │ Overall: [████████░░░░░░░░░░░░░░░░░░░░░░]  28%      │    │
│  │ Current: [██████████████░░░░░░░░░░░░░░░░]  45%      │    │
│  │                                                      │    │
│  │ Stage 1/4: Translating S06E10...                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Log                                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [14:22:01] ═══ STAGE 1: TRANSLATION ═══             │    │
│  │ [14:22:02] Found 22 English SRT files               │    │
│  │ [14:22:15] ✓ 6x01 translated (643 lines)           │    │
│  │ [14:22:45] ✓ 6x02 translated (589 lines)           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Options                                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ☑ Delete temporary folders after completion         │    │
│  │ ☐ Keep Subtitle_HEBREW folder (for manual review)   │    │
│  │ ☐ Stop on first error                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  [Cancel]                                [Start Full Process]│
└─────────────────────────────────────────────────────────────┘
```

### Full Process - Output

```
📁 Season Folder/
├── 📁 Subtitle_HEBREW/    ← Created in Stage 1
├── 📁 Output/             ← Final MKVs (Stage 4)
│   ├── ER.1994.S06E01...mkv  (with Hebrew subs!)
│   └── ...
└── ...
```

### Full Process - Time Estimate

| Stage | Time per Episode |
|-------|------------------|
| Translate | ~1-2 minutes |
| Sync | ~10 seconds |
| RTL Fix | ~10 seconds |
| Embed | ~10 seconds |
| **Total** | **~2-3 minutes** |

**Full season (22 episodes): ~45-60 minutes**

---

# PART 4: TRANSLATION PROMPT (CRITICAL!)

## Use this EXACT prompt for high-quality Hebrew translation:

```python
TRANSLATION_PROMPT = """You are a professional Hebrew subtitle translator. Translate the following subtitles from English to Hebrew.

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
  - Ross → רוס
  - Rachel → רייצ'ל
  - County General → קאונטי ג'נרל
  
- ONLY keep English for:
  - Technical codes: DNA, HIV, CT, MRI, EKG
  - Common abbreviations: OK

### 2. GENDER DETECTION - VERY IMPORTANT!
Analyze the context carefully to determine speaker gender:

**Clues for FEMALE speaker:**
- Words like "she", "her", "actress", "mother", "sister", "wife", "girlfriend", "nurse", "pregnant"
- Female names: Elizabeth, Susan, Carol, Rachel, Abby, Kerry, Cynthia
- Response to "ma'am", "miss", "Mrs."
- Previous lines mentioning a woman

**Clues for MALE speaker:**
- Words like "he", "him", "actor", "father", "brother", "husband", "boyfriend"
- Male names: John, Mark, Doug, Peter, Carter, Benton, Greene
- Response to "sir", "Mr."
- Previous lines mentioning a man

**Use correct Hebrew verb forms:**
- Female present: אני רוצָה, אני יודעַת, אני חושבת, אני עושָׂה
- Male present: אני רוצֶה, אני יודֵע, אני חושב, אני עושֶׂה

**When UNCLEAR:** Look at surrounding context. Default to male only if absolutely no hints.

### 3. NATURAL HEBREW
- Use conversational, natural Israeli Hebrew
- Contractions are OK: מה קורה, איך הולך, תגיד לי, מה נשמע
- Keep subtitles concise for quick reading
- Medical drama tone: professional but human

### 4. MEDICAL TERMS
| English | Hebrew |
|---------|--------|
| Doctor / Dr. | דוקטור / ד"ר |
| Nurse | אחות (f) / אח (m) |
| Patient | מטופל / מטופלת |
| ER / Emergency Room | חדר מיון |
| Surgery | ניתוח |
| Trauma | טראומה |
| IV | עירוי |
| Blood pressure | לחץ דם |
| Heart rate | דופק |
| Intubation | אינטובציה |
| cc / ml | סמ"ק |
| mg | מ"ג |
| Stat! | מיד! / עכשיו! |
| Code Blue | קוד כחול |
| Crash cart | עגלת החייאה |

{context_section}

### TRANSLATE THESE {num_lines} LINES:
{text_to_translate}

### OUTPUT:
Return exactly {num_lines} Hebrew translations, one per line, same order as input:"""
```

---

# PART 5: TRANSLATION IMPLEMENTATION

```python
import google.generativeai as genai
import time
import os
import re

# Configuration - load from environment
import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL = "gemini-2.0-flash"

genai.configure(api_key=GEMINI_API_KEY)

class Translator:
    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.batch_size = 20
        self.context_lines = 10
        self.delay_between_requests = 2  # seconds
    
    def translate_srt_file(self, input_path, output_path, progress_callback=None):
        """Translate a single SRT file from English to Hebrew."""
        
        # Read and parse SRT
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        blocks = self.parse_srt(content)
        total_batches = (len(blocks) + self.batch_size - 1) // self.batch_size
        
        translated_blocks = []
        
        for i in range(0, len(blocks), self.batch_size):
            batch = blocks[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            # Get context from previous blocks
            context_start = max(0, i - self.context_lines)
            context_blocks = blocks[context_start:i]
            
            # Translate with retry
            translated = self.translate_batch_with_retry(batch, context_blocks)
            translated_blocks.extend(translated)
            
            if progress_callback:
                progress_callback(batch_num, total_batches)
            
            # Rate limit protection
            time.sleep(self.delay_between_requests)
        
        # Build and save output
        output_content = self.build_srt(translated_blocks)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        return len(blocks)
    
    def translate_batch_with_retry(self, batch, context_blocks, max_retries=5):
        """Translate a batch with retry logic."""
        
        text_to_translate = "\n".join([b['text'] for b in batch])
        context_text = "\n".join([b['text'] for b in context_blocks]) if context_blocks else ""
        
        context_section = ""
        if context_text:
            context_section = f"""
### CONTEXT (previous subtitles - DO NOT translate, use for gender/tone understanding):
{context_text}
"""
        
        prompt = TRANSLATION_PROMPT.format(
            context_section=context_section,
            num_lines=len(batch),
            text_to_translate=text_to_translate
        )
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                translated_lines = response.text.strip().split('\n')
                
                # Match translations to blocks
                for i, block in enumerate(batch):
                    if i < len(translated_lines):
                        block['text'] = translated_lines[i].strip()
                
                return batch
                
            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    wait_time = 30 * (attempt + 1)
                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise e
        
        raise Exception("Translation failed after max retries")
    
    def parse_srt(self, content):
        """Parse SRT content into blocks."""
        blocks = []
        pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*(?:\n|$))*?)(?=\n\d+\n|\Z)'
        
        for match in re.finditer(pattern, content):
            blocks.append({
                'index': match.group(1),
                'start': match.group(2),
                'end': match.group(3),
                'text': match.group(4).strip()
            })
        
        return blocks
    
    def build_srt(self, blocks):
        """Build SRT content from blocks."""
        lines = []
        for block in blocks:
            lines.append(block['index'])
            lines.append(f"{block['start']} --> {block['end']}")
            lines.append(block['text'])
            lines.append('')
        
        return '\n'.join(lines)
```

---

# PART 6: RTL FIX (SubtitleEdit Automation)

```python
from pywinauto import Application
import time
import shutil

def fix_rtl_with_subtitleedit(srt_path, subtitleedit_path="C:\\Program Files\\Subtitle Edit\\SubtitleEdit.exe"):
    """
    Automate SubtitleEdit GUI to apply "Reverse RTL start/end" function.
    """
    try:
        # Launch SubtitleEdit with the subtitle file
        app = Application(backend="uia").start(
            f'"{subtitleedit_path}" "{srt_path}"',
            timeout=15
        )
        
        time.sleep(3)
        
        main_window = app.window(title_re=".*Subtitle Edit.*")
        main_window.wait('ready', timeout=15)
        
        # Select All (Ctrl+A)
        main_window.type_keys('^a')
        time.sleep(0.5)
        
        # Open Edit menu (Alt+E)
        main_window.type_keys('%e')
        time.sleep(0.3)
        
        # Navigate to "Reverse RTL start/end (for selected lines)"
        for _ in range(11):  # Adjust in settings if needed
            main_window.type_keys('{DOWN}')
            time.sleep(0.05)
        main_window.type_keys('{ENTER}')
        time.sleep(0.5)
        
        # Save (Ctrl+S)
        main_window.type_keys('^s')
        time.sleep(0.5)
        
        # Close (Alt+F4)
        main_window.type_keys('%{F4}')
        
        # Handle save dialog if appears
        try:
            time.sleep(0.3)
            app.window(title_re=".*").type_keys('n')
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"RTL fix error: {e}")
        try:
            app.kill()
        except:
            pass
        return False
```

---

# PART 7: EPISODE MATCHING

```python
import re
import os

def extract_episode_number(filename):
    """Extract season and episode from filename."""
    patterns = [
        r'[Ss](\d{1,2})[Ee](\d{1,2})',  # S06E01
        r'(\d{1,2})x(\d{1,2})',          # 6x01
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
            return (season, episode)
    
    return None

def match_files(mkv_folder, srt_folder):
    """Match MKV files with SRT files by episode number."""
    mkv_files = {}
    for f in os.listdir(mkv_folder):
        if f.endswith('.mkv'):
            ep = extract_episode_number(f)
            if ep:
                mkv_files[ep] = f
    
    srt_files = {}
    for f in os.listdir(srt_folder):
        if f.endswith('.srt'):
            ep = extract_episode_number(f)
            if ep:
                srt_files[ep] = f
    
    matches = []
    for ep_num, mkv_file in mkv_files.items():
        if ep_num in srt_files:
            matches.append({
                'episode': ep_num,
                'mkv': mkv_file,
                'srt': srt_files[ep_num]
            })
    
    return sorted(matches, key=lambda x: x['episode'])
```

---

# PART 8: FULL PROCESS IMPLEMENTATION

```python
import subprocess
import shutil

def run_full_process(english_srt_folder, season_folder, config, progress_callback=None, log_callback=None):
    """
    Complete workflow: Translate → Sync → RTL Fix → Embed
    """
    
    def log(message):
        if log_callback:
            log_callback(message)
        print(message)
    
    # ═══════════════════════════════════════════════════════
    # STAGE 1: TRANSLATION
    # ═══════════════════════════════════════════════════════
    log("═══ STAGE 1: TRANSLATION ═══")
    
    hebrew_srt_folder = os.path.join(season_folder, "Subtitle_HEBREW")
    os.makedirs(hebrew_srt_folder, exist_ok=True)
    
    english_files = [f for f in os.listdir(english_srt_folder) if f.endswith('.srt')]
    translator = Translator()
    
    for i, filename in enumerate(english_files):
        input_path = os.path.join(english_srt_folder, filename)
        output_path = os.path.join(hebrew_srt_folder, filename)
        
        log(f"Translating {filename}...")
        try:
            lines = translator.translate_srt_file(input_path, output_path)
            log(f"✓ {filename} translated ({lines} lines)")
        except Exception as e:
            log(f"✗ {filename} failed: {e}")
        
        if progress_callback:
            progress_callback(stage=1, current=i+1, total=len(english_files))
    
    # ═══════════════════════════════════════════════════════
    # STAGE 2: SYNC
    # ═══════════════════════════════════════════════════════
    log("═══ STAGE 2: SYNC ═══")
    
    matches = match_files(season_folder, hebrew_srt_folder)
    synced_folder = os.path.join(season_folder, "temp_synced")
    os.makedirs(synced_folder, exist_ok=True)
    
    for i, match in enumerate(matches):
        mkv_path = os.path.join(season_folder, match['mkv'])
        srt_path = os.path.join(hebrew_srt_folder, match['srt'])
        synced_path = os.path.join(synced_folder, match['srt'])
        
        log(f"Syncing {match['srt']}...")
        result = subprocess.run([
            config.alass_path, mkv_path, srt_path, synced_path
        ], capture_output=True)
        
        if result.returncode == 0:
            log(f"✓ {match['srt']} synced")
        else:
            log(f"✗ {match['srt']} sync failed")
            shutil.copy(srt_path, synced_path)  # Use original if sync fails
        
        if progress_callback:
            progress_callback(stage=2, current=i+1, total=len(matches))
    
    # ═══════════════════════════════════════════════════════
    # STAGE 3: RTL FIX
    # ═══════════════════════════════════════════════════════
    log("═══ STAGE 3: RTL FIX ═══")
    
    rtl_folder = os.path.join(season_folder, "temp_rtl_fixed")
    os.makedirs(rtl_folder, exist_ok=True)
    
    synced_files = [f for f in os.listdir(synced_folder) if f.endswith('.srt')]
    
    for i, filename in enumerate(synced_files):
        src = os.path.join(synced_folder, filename)
        dst = os.path.join(rtl_folder, filename)
        shutil.copy(src, dst)
        
        log(f"Fixing RTL for {filename}...")
        if fix_rtl_with_subtitleedit(dst, config.subtitleedit_path):
            log(f"✓ {filename} RTL fixed")
        else:
            log(f"✗ {filename} RTL fix failed")
        
        if progress_callback:
            progress_callback(stage=3, current=i+1, total=len(synced_files))
    
    # ═══════════════════════════════════════════════════════
    # STAGE 4: EMBED
    # ═══════════════════════════════════════════════════════
    log("═══ STAGE 4: EMBED ═══")
    
    output_folder = os.path.join(season_folder, "Output")
    os.makedirs(output_folder, exist_ok=True)
    
    for i, match in enumerate(matches):
        mkv_path = os.path.join(season_folder, match['mkv'])
        srt_path = os.path.join(rtl_folder, match['srt'])
        output_path = os.path.join(output_folder, match['mkv'])
        
        log(f"Embedding into {match['mkv']}...")
        result = subprocess.run([
            config.mkvmerge_path,
            "-o", output_path,
            mkv_path,
            "--language", "0:heb",
            "--track-name", "0:Hebrew",
            "--default-track", "0:yes",
            srt_path
        ], capture_output=True)
        
        if result.returncode == 0:
            log(f"✓ {match['mkv']} complete")
        else:
            log(f"✗ {match['mkv']} embed failed")
        
        if progress_callback:
            progress_callback(stage=4, current=i+1, total=len(matches))
    
    # ═══════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════
    if not config.keep_temp_files:
        shutil.rmtree(synced_folder, ignore_errors=True)
        shutil.rmtree(rtl_folder, ignore_errors=True)
    
    log("═══ FULL PROCESS COMPLETE ═══")
    log(f"Output folder: {output_folder}")
    
    return {'success': True, 'output_folder': output_folder}
```

---

# PART 9: PROJECT STRUCTURE

```
G:\Projects\SubtitlePipeline\
├── tools/
│   └── alass.exe
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point + GUI
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── pipeline_tab.py      # Pipeline tab
│   │   ├── translate_tab.py     # Translate tab
│   │   ├── full_process_tab.py  # Full Process tab (NEW)
│   │   └── settings_tab.py      # Settings tab
│   ├── core/
│   │   ├── __init__.py
│   │   ├── translator.py        # Gemini translation
│   │   ├── syncer.py            # alass sync
│   │   ├── rtl_fixer.py         # SubtitleEdit automation
│   │   ├── muxer.py             # mkvmerge embedding
│   │   ├── matcher.py           # Episode matching
│   │   └── full_process.py      # Full process orchestration (NEW)
│   └── config.py                # Settings management
├── temp/
├── dist/
├── config.yaml
├── requirements.txt
└── CLAUDE.md
```

---

# PART 10: CONFIGURATION

## config.yaml

```yaml
tools:
  mkvmerge: "C:/Program Files/MKVToolNix/mkvmerge.exe"
  subtitleedit: "C:/Program Files/Subtitle Edit/SubtitleEdit.exe"
  alass: "G:/Projects/SubtitlePipeline/tools/alass.exe"

api:
  # API key loaded from .env file (GEMINI_API_KEY environment variable)
  gemini_model: "gemini-2.0-flash"

subtitle:
  folder_name: "Subtitle_HEBREW"
  output_folder: "Output"
  language_code: "heb"
  track_name: "Hebrew"
  default_track: true

translation:
  batch_size: 20
  context_lines: 10
  delay_between_requests: 2

rtl:
  menu_steps: 11

processing:
  keep_temp_files: false
```

## requirements.txt

```
PyQt5>=5.15.0
pywinauto>=0.6.8
google-generativeai>=0.3.0
PyYAML>=6.0
pyinstaller>=5.0
```

---

# PART 11: BUILD EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "HebrewSubtitlePipeline" src/main.py
```

Output: `G:\Projects\SubtitlePipeline\dist\HebrewSubtitlePipeline.exe`

---

# PART 12: TESTING CHECKLIST

## Translation Tests
- [ ] API connects (new paid key)
- [ ] Model is gemini-1.5-flash (NOT 2.0)
- [ ] Names transliterated (Brenner → ברנר)
- [ ] Gender detection works
- [ ] No rate limit errors
- [ ] 100% Hebrew output (except DNA, CT, OK)

## Pipeline Tests
- [ ] Episode matching S06E01 ↔ 6x01
- [ ] alass sync works
- [ ] RTL fix: punctuation at start (`.שלום`)
- [ ] MKV has Hebrew track

## Full Process Tests
- [ ] All 4 stages run in sequence
- [ ] Progress updates correctly
- [ ] Temp folders cleaned up
- [ ] Final MKVs in Output/

## General Tests
- [ ] All 4 tabs work
- [ ] Settings saved/loaded
- [ ] EXE runs standalone

---

# SUMMARY

| Tab | Input | Process | Output |
|-----|-------|---------|--------|
| **Pipeline** | Season folder + Subtitle_HEBREW | Sync → RTL → Embed | Output/ with MKVs |
| **Translate** | English SRT folder → Season folder | Gemini translation | Subtitle_HEBREW/ |
| **Full Process** | English SRT folder + Season folder | Translate → Sync → RTL → Embed | Output/ with MKVs |
| **Settings** | N/A | Configuration | config.yaml |