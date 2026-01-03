# Hebrew Subtitle Pipeline - Complete Automation Tool

## Project Overview

Build a **modular GUI application** (with standalone EXE) with **TWO separate workflows**:

### Tab 1: Pipeline (Existing - DO NOT CHANGE)
Process Hebrew subtitles that **already exist** in `Subtitle_HEBREW` folder:
- **Sync** → **RTL Fix** → **Embed into MKV**

### Tab 2: Translate (NEW - Separate workflow)
Translate English subtitles to Hebrew and **create** the `Subtitle_HEBREW` folder:
- **Input:** English SRT files from any location
- **Output:** Hebrew SRT files in a new `Subtitle_HEBREW` folder

These are **completely separate workflows** that do NOT interfere with each other.

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

### API Key (Pre-configured for Translation)

```
GEMINI_API_KEY = "REDACTED_API_KEY"
```

---

# PART 1: PIPELINE TAB (Existing Workflow)

## This is the ORIGINAL workflow - DO NOT MODIFY

### Input Structure for Pipeline Tab

```
📁 Season Folder (e.g., "עונה 6")/
│
├── 📁 Subtitle_HEBREW/              ← Hebrew subtitles MUST exist here
│   ├── ER - 6x01 - Leave It to Weaver.en.srt
│   ├── ER - 6x02 - Last Rites.en.srt
│   └── ...
│
├── ER.1994.S06E01.720p.AMZN.WEB-DL.x265-HETeam.mkv
├── ER.1994.S06E02.720p.AMZN.WEB-DL.x265-HETeam.mkv
└── ...
```

### Pipeline Tab - 3 Steps (Original)

#### Step 1: Sync (alass)
```bash
alass.exe "video.mkv" "subtitle.srt" "synced.srt"
```

#### Step 2: RTL Fix (SubtitleEdit GUI Automation)
Automate SubtitleEdit: Ctrl+A → Edit → "Reverse RTL start/end"

#### Step 3: Embed (mkvmerge)
```bash
mkvmerge.exe -o "output.mkv" "input.mkv" --language 0:heb --track-name 0:"Hebrew" "subtitle.srt"
```

### Pipeline Tab - Operation Modes

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

# PART 2: TRANSLATE TAB (NEW - Separate Workflow)

## This is a COMPLETELY SEPARATE tab for translation only

### Purpose
Translate English SRT files to Hebrew and create a `Subtitle_HEBREW` folder.
This prepares the files for the Pipeline tab.

### Translate Tab - Input

User selects TWO things:
1. **Source Folder:** Folder containing English SRT files (can be anywhere)
2. **Target Folder:** Season folder where `Subtitle_HEBREW` will be created

### Translate Tab - GUI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Pipeline]  [Translate]  [Settings]                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ╔═══════════════════════════════════════════════════════╗  │
│  ║              TRANSLATE TAB                             ║  │
│  ╚═══════════════════════════════════════════════════════╝  │
│                                                              │
│  Source (English Subtitles)                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Folder: [D:\Subtitles\ER\Season6_English  ] [Browse]│    │
│  │         ┌─────────────────────────────────┐         │    │
│  │         │  Drag and drop English SRT      │         │    │
│  │         │  folder here                    │         │    │
│  │         └─────────────────────────────────┘         │    │
│  │                                                      │    │
│  │ Found: 22 English SRT files                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Target (Where to create Subtitle_HEBREW)                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Folder: [G:\סדרות\ER\עונה 6               ] [Browse]│    │
│  │         ┌─────────────────────────────────┐         │    │
│  │         │  Drag and drop season folder    │         │    │
│  │         │  here                           │         │    │
│  │         └─────────────────────────────────┘         │    │
│  │                                                      │    │
│  │ Will create: G:\סדרות\ER\עונה 6\Subtitle_HEBREW\    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Translation Options                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ☑ Keep original filenames                           │    │
│  │ ☐ Rename to match video files (if found)            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Progress                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░]  35%      │    │
│  │ Translating: ER - 6x08 - Great Expectations.srt     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Log                                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [14:22:01] Starting translation...                  │    │
│  │ [14:22:02] Found 22 SRT files                       │    │
│  │ [14:22:15] ✓ ER - 6x01 translated (652 lines)      │    │
│  │ [14:22:45] ✓ ER - 6x02 translated (589 lines)      │    │
│  │ [14:23:12] ✓ ER - 6x03 translated (621 lines)      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                              [Clear Log]     │
│                                                              │
│  [Cancel]                                    [Translate All] │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│  💡 After translation, use the Pipeline tab to sync and     │
│     embed the subtitles into your MKV files.                │
└─────────────────────────────────────────────────────────────┘
```

### Translate Tab - Workflow

```
User selects:
├── Source: D:\Subtitles\ER\Season6_English\
│   ├── ER - 6x01 - Leave It to Weaver.srt
│   ├── ER - 6x02 - Last Rites.srt
│   └── ...
│
└── Target: G:\סדרות\ER\עונה 6\

Result:
G:\סדרות\ER\עונה 6\
├── 📁 Subtitle_HEBREW\              ← CREATED by Translate tab
│   ├── ER - 6x01 - Leave It to Weaver.srt  (Hebrew)
│   ├── ER - 6x02 - Last Rites.srt          (Hebrew)
│   └── ...
├── ER.1994.S06E01...mkv
└── ...

Now ready for Pipeline tab!
```

### Translation Implementation (Gemini API)

```python
import google.generativeai as genai
import os
import re

GEMINI_API_KEY = "REDACTED_API_KEY"

genai.configure(api_key=GEMINI_API_KEY)

def translate_srt_file(input_path, output_path):
    """
    Translate a single SRT file from English to Hebrew.
    """
    # Read the SRT file
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse SRT into blocks
    blocks = parse_srt(content)
    
    # Translate in batches of 25 blocks for context
    model = genai.GenerativeModel('gemini-1.5-flash')
    translated_blocks = []
    
    batch_size = 25
    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i + batch_size]
        
        # Include previous 5 blocks for context
        context_start = max(0, i - 5)
        context_blocks = blocks[context_start:i]
        
        translated_batch = translate_batch(model, batch, context_blocks)
        translated_blocks.extend(translated_batch)
    
    # Rebuild SRT
    output_content = build_srt(translated_blocks)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    return len(blocks)

def translate_batch(model, batch, context_blocks):
    """
    Translate a batch of subtitle blocks.
    """
    # Format subtitles for translation
    text_to_translate = "\n".join([b['text'] for b in batch])
    context_text = "\n".join([b['text'] for b in context_blocks]) if context_blocks else ""
    
    prompt = f"""Translate the following subtitles from English to Hebrew.

CRITICAL RULES:
1. ONLY translate the text, keep the EXACT same number of lines
2. Pay attention to speaker GENDER from context:
   - Use feminine forms (אמרה, הלכה, רצתה) when speaker is clearly female
   - Use masculine forms (אמר, הלך, רצה) when speaker is clearly male
3. Keep translations natural and conversational Hebrew
4. Do NOT translate names - keep them in English
5. Match the tone (formal/informal) of the original
6. Keep translations concise - suitable for subtitles

{f'CONTEXT (previous subtitles for reference, DO NOT translate these):' + chr(10) + context_text if context_text else ''}

TRANSLATE THESE LINES (return {len(batch)} lines, one translation per line):
{text_to_translate}

Return ONLY the Hebrew translations, one per line, in the same order."""

    response = model.generate_content(prompt)
    translated_lines = response.text.strip().split('\n')
    
    # Match translations to blocks
    for i, block in enumerate(batch):
        if i < len(translated_lines):
            block['text'] = translated_lines[i].strip()
    
    return batch

def parse_srt(content):
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

def build_srt(blocks):
    """Build SRT content from blocks."""
    lines = []
    for block in blocks:
        lines.append(block['index'])
        lines.append(f"{block['start']} --> {block['end']}")
        lines.append(block['text'])
        lines.append('')
    
    return '\n'.join(lines)

def translate_folder(source_folder, target_folder, progress_callback=None):
    """
    Translate all SRT files from source folder.
    Create Subtitle_HEBREW folder in target folder.
    """
    # Create output folder
    output_folder = os.path.join(target_folder, "Subtitle_HEBREW")
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all SRT files
    srt_files = [f for f in os.listdir(source_folder) if f.endswith('.srt')]
    
    results = []
    for i, filename in enumerate(srt_files):
        input_path = os.path.join(source_folder, filename)
        output_path = os.path.join(output_folder, filename)
        
        try:
            lines_count = translate_srt_file(input_path, output_path)
            results.append({
                'file': filename,
                'success': True,
                'lines': lines_count
            })
        except Exception as e:
            results.append({
                'file': filename,
                'success': False,
                'error': str(e)
            })
        
        if progress_callback:
            progress_callback(i + 1, len(srt_files), filename)
    
    return results
```

---

# PART 3: COMPLETE GUI STRUCTURE

## Three Tabs Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Hebrew Subtitle Pipeline                            [─][□][×] │
├─────────────────────────────────────────────────────────────┤
│  [Pipeline]  [Translate]  [Settings]                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│     (Content changes based on selected tab)                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Tab 1: Pipeline (Original - unchanged)
- Modes: Full Pipeline, Sync Only, RTL Fix Only, Embed Only
- Input: Season folder with existing Subtitle_HEBREW
- Output: MKV files with embedded subtitles

### Tab 2: Translate (NEW)
- Input: English SRT folder + Target season folder
- Output: Creates Subtitle_HEBREW folder with Hebrew SRTs
- No sync, no RTL fix, no embed - JUST translation

### Tab 3: Settings
- Tool paths (mkvmerge, SubtitleEdit, alass)
- Gemini API key (pre-filled)
- Subtitle settings (folder name, language code, etc.)
- RTL fix settings (menu navigation steps)

---

# PART 4: TYPICAL USER WORKFLOW

## Complete Process (Using Both Tabs)

### Step 1: Translate (Translate Tab)
```
User has:
- English subtitles in: D:\Subtitles\ER\Season6_English\
- Videos in: G:\סדרות\ER\עונה 6\

1. Open "Translate" tab
2. Source: D:\Subtitles\ER\Season6_English\
3. Target: G:\סדרות\ER\עונה 6\
4. Click "Translate All"
5. Wait for completion

Result: G:\סדרות\ER\עונה 6\Subtitle_HEBREW\ created with Hebrew SRTs
```

### Step 2: Process (Pipeline Tab)
```
1. Open "Pipeline" tab
2. Input: G:\סדרות\ER\עונה 6\
3. Mode: Full Pipeline (Sync → RTL Fix → Embed)
4. Click "Run Pipeline"
5. Wait for completion

Result: G:\סדרות\ER\עונה 6\Output\ created with final MKVs
```

---

# PART 5: TECHNICAL IMPLEMENTATION

## RTL Fix with SubtitleEdit (GUI Automation)

```python
from pywinauto import Application
import time

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
        for _ in range(11):  # Adjust if needed
            main_window.type_keys('{DOWN}')
            time.sleep(0.05)
        main_window.type_keys('{ENTER}')
        time.sleep(0.5)
        
        # Save (Ctrl+S)
        main_window.type_keys('^s')
        time.sleep(0.5)
        
        # Close (Alt+F4)
        main_window.type_keys('%{F4}')
        
        return True
        
    except Exception as e:
        print(f"RTL fix error: {e}")
        return False
```

## Episode Matching

```python
import re

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
    mkv_files = {extract_episode_number(f): f for f in os.listdir(mkv_folder) if f.endswith('.mkv')}
    srt_files = {extract_episode_number(f): f for f in os.listdir(srt_folder) if f.endswith('.srt')}
    
    matches = []
    for ep_num, mkv_file in mkv_files.items():
        if ep_num and ep_num in srt_files:
            matches.append({
                'episode': ep_num,
                'mkv': mkv_file,
                'srt': srt_files[ep_num]
            })
    
    return sorted(matches, key=lambda x: x['episode'])
```

---

# PART 6: PROJECT STRUCTURE

```
G:\Projects\SubtitlePipeline\
├── tools/
│   └── alass.exe
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point + GUI (3 tabs)
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── pipeline_tab.py  # Pipeline tab UI
│   │   ├── translate_tab.py # Translate tab UI (NEW)
│   │   └── settings_tab.py  # Settings tab UI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── translator.py    # Gemini translation (NEW)
│   │   ├── syncer.py        # alass sync
│   │   ├── rtl_fixer.py     # SubtitleEdit automation
│   │   ├── muxer.py         # mkvmerge embedding
│   │   └── matcher.py       # Episode matching
│   └── config.py            # Settings management
├── temp/
├── dist/
├── config.yaml
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

# PART 7: CONFIGURATION

## config.yaml

```yaml
tools:
  mkvmerge: "C:/Program Files/MKVToolNix/mkvmerge.exe"
  subtitleedit: "C:/Program Files/Subtitle Edit/SubtitleEdit.exe"
  alass: "G:/Projects/SubtitlePipeline/tools/alass.exe"

api:
  gemini_key: "REDACTED_API_KEY"
  gemini_model: "gemini-1.5-flash"

subtitle:
  folder_name: "Subtitle_HEBREW"
  output_folder: "Output"
  language_code: "heb"
  track_name: "Hebrew"
  default_track: true

translation:
  batch_size: 25
  context_lines: 5

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

# PART 8: BUILD & DISTRIBUTION

## Build Standalone EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "HebrewSubtitlePipeline" src/main.py
```

Output: `G:\Projects\SubtitlePipeline\dist\HebrewSubtitlePipeline.exe`

---

# PART 9: TESTING CHECKLIST

## Translate Tab Tests
- [ ] Gemini API connects successfully
- [ ] Single SRT file translates correctly
- [ ] Batch of 22 files translates without errors
- [ ] Gender context is respected (feminine/masculine)
- [ ] Subtitle_HEBREW folder is created in correct location
- [ ] Original filenames are preserved
- [ ] Progress bar updates correctly
- [ ] Errors are logged but don't crash

## Pipeline Tab Tests (Original)
- [ ] Episode matching S06E01 ↔ 6x01 works
- [ ] alass sync aligns subtitles
- [ ] RTL fix: `.אני רופא` (dot at beginning)
- [ ] MKV has Hebrew track with correct language
- [ ] Batch processing 20+ files works
- [ ] Each mode works independently

## General Tests
- [ ] All 3 tabs switch correctly
- [ ] Settings are saved and loaded
- [ ] EXE runs without Python installed
- [ ] Tool verification works

---

# PART 10: FIRST STEPS FOR CLAUDE CODE

1. **Test Gemini API:**
   ```python
   import google.generativeai as genai
   genai.configure(api_key="REDACTED_API_KEY")
   model = genai.GenerativeModel('gemini-1.5-flash')
   response = model.generate_content("Translate 'Hello, how are you?' to Hebrew")
   print(response.text)
   ```

2. **Create project structure**

3. **Build Translate tab first** (it's independent)

4. **Then update Pipeline tab** to work alongside

5. **Test on ONE episode** before batch

6. **Build EXE last**

---

# SUMMARY

| Tab | Input | Process | Output |
|-----|-------|---------|--------|
| **Translate** | English SRT folder + Season folder | Gemini API translation | `Subtitle_HEBREW/` with Hebrew SRTs |
| **Pipeline** | Season folder (with Subtitle_HEBREW) | Sync → RTL Fix → Embed | `Output/` with final MKVs |
| **Settings** | N/A | Configuration | Saved to config.yaml |

**The two tabs are INDEPENDENT and do NOT interfere with each other.**