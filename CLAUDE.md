# Hebrew Subtitle Pipeline Automation Tool

## Project Overview

Build an automated tool that processes Hebrew subtitles for TV series/movies:
1. **Sync** subtitles to video using AutoSubSync (alass engine)
2. **Fix RTL** punctuation alignment for Hebrew text
3. **Embed** subtitles into MKV files using MKVToolNix

The user has hundreds of video files to process - manual work is not feasible.

---

## User's Environment

- **OS:** Windows
- **Project folder:** `G:\Projects\SubtitlePipeline\`
- **Language:** Hebrew subtitles only (RTL)
- **Output type:** Soft subs (switchable subtitles, not burned-in)

### Installed Tools (verify paths on first run)

| Tool | Expected Location | Purpose |
|------|-------------------|---------|
| AutoSubSync | Check Program Files or user install | Subtitle synchronization |
| MKVToolNix | `C:\Program Files\MKVToolNix\` | Embedding subtitles into MKV |
| SubtitleEdit | Check Program Files | RTL fixing (optional, can use Python) |
| Python | System PATH | Script execution |
| FFmpeg | May need installation | Audio extraction (AutoSubSync dependency) |

---

## Input Structure (CRITICAL)

The user's files follow this pattern:

```
📁 Season Folder (e.g., "עונה 6")/
   ├── 📁 Subtitle_HEBREW/
   │   ├── ER - 6x01 - Leave It to Weaver.en.srt
   │   ├── ER - 6x02 - Last Rites.en.srt
   │   └── ... (episode title in filename)
   │
   ├── ER.1994.S06E01.720p.AMZN.WEB-DL.x265-HETeam.mkv
   ├── ER.1994.S06E02.720p.AMZN.WEB-DL.x265-HETeam.mkv
   └── ... (standard release naming)
```

### Key Challenge: Episode Matching

**MKV filename:** `ER.1994.S06E01.720p.AMZN.WEB-DL.x265-HETeam.mkv`
**SRT filename:** `ER - 6x01 - Leave It to Weaver.en.srt`

Must extract and match:
- `S06E01` → Season 6, Episode 1
- `6x01` → Season 6, Episode 1

**Regex patterns to implement:**
```python
# For MKV files (standard naming)
mkv_pattern = r'[Ss](\d{1,2})[Ee](\d{1,2})'  # Matches S06E01

# For SRT files (various formats)
srt_patterns = [
    r'(\d{1,2})x(\d{1,2})',      # Matches 6x01
    r'[Ss](\d{1,2})[Ee](\d{1,2})', # Matches S06E01 if present
    r'(\d{1,2})(\d{2})',          # Matches 601 (season+episode concatenated)
]
```

---

## Output Structure

```
📁 Season Folder/
   ├── 📁 Subtitle_HEBREW/
   │   └── (original files unchanged)
   ├── 📁 Output/                          ← NEW FOLDER
   │   ├── ER.1994.S06E01.720p...HETeam.mkv  (with embedded Hebrew subs)
   │   ├── ER.1994.S06E02.720p...HETeam.mkv
   │   └── ...
   ├── (original MKV files unchanged)
   └── ...
```

---

## Processing Pipeline

### Step 1: Subtitle Synchronization (AutoSubSync)

Use AutoSubSync CLI or call alass directly:

```bash
# Option A: AutoSubSync CLI (if available)
assy-cli --video "input.mkv" --subtitle "input.srt" --output "synced.srt" --tool alass

# Option B: alass directly (faster, recommended)
alass "input.mkv" "input.srt" "synced.srt"
```

**Important:** 
- alass is the fastest and most accurate for this use case
- It uses audio analysis to align subtitles
- No need for speech recognition - it matches audio patterns

### Step 2: RTL Punctuation Fix

Hebrew subtitles need RTL Unicode control characters to display punctuation correctly.

**Implementation (Python):**
```python
import re

# RTL Unicode markers
RLM = '\u200F'  # Right-to-Left Mark
LRM = '\u200E'  # Left-to-Right Mark

def fix_rtl_punctuation(text):
    """
    Fix punctuation placement in Hebrew text.
    Ensures punctuation marks appear on the correct side.
    """
    # Add RLM at start of each line containing Hebrew
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Check if line contains Hebrew characters
        if re.search(r'[\u0590-\u05FF]', line):
            # Add RLM at beginning if not timestamp or index
            if not re.match(r'^\d+$', line.strip()) and '-->' not in line:
                line = RLM + line
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)
```

**Alternative: SubtitleEdit CLI**
```bash
SubtitleEdit /convert "input.srt" "output.srt" /fixrtl
```

### Step 3: Embed into MKV (MKVToolNix)

Use `mkvmerge` command-line tool:

```bash
mkvmerge -o "output.mkv" "input.mkv" --language 0:heb --track-name 0:"Hebrew" "synced.srt"
```

**Parameters:**
- `-o` : Output file
- `--language 0:heb` : Set subtitle language to Hebrew
- `--track-name 0:"Hebrew"` : Display name in player
- Can also use `--default-track 0:yes` to make it default subtitle

---

## Tool Architecture

Create a Python-based CLI tool with the following structure:

```
📁 G:\Projects\SubtitlePipeline\
   ├── 📁 tools/                    # Store tool executables here
   │   ├── alass.exe               # Download if needed
   │   └── (symlinks or copies)
   ├── 📁 src/
   │   ├── __init__.py
   │   ├── main.py                 # Entry point
   │   ├── matcher.py              # Episode matching logic
   │   ├── sync.py                 # AutoSubSync/alass wrapper
   │   ├── rtl_fixer.py            # Hebrew RTL fixes
   │   └── muxer.py                # MKVToolNix wrapper
   ├── 📁 temp/                     # Temporary processing files
   ├── config.yaml                 # Tool paths, preferences
   ├── requirements.txt
   ├── README.md
   └── CLAUDE.md                   # This file
```

---

## User Interface Requirements

### Option A: CLI (Minimum Viable Product)
```bash
python main.py "G:\סדרות\ER\עונה 6"
```

### Option B: Simple GUI (Nice to have)
- Drag & drop folder
- Progress bar
- Log output
- Settings for tool paths

### Option C: Batch File (Simplest)
```batch
@echo off
python "G:\Projects\SubtitlePipeline\src\main.py" %1
pause
```

---

## Configuration File (config.yaml)

```yaml
tools:
  mkvmerge: "C:/Program Files/MKVToolNix/mkvmerge.exe"
  alass: "G:/Projects/SubtitlePipeline/tools/alass.exe"
  # subtitleedit: "C:/Program Files/Subtitle Edit/SubtitleEdit.exe"

settings:
  subtitle_folder_name: "Subtitle_HEBREW"  # Name of subtitle subfolder
  output_folder_name: "Output"              # Name of output subfolder
  subtitle_language: "heb"                  # ISO 639-2 code
  subtitle_track_name: "Hebrew"             # Display name in player
  default_subtitle: true                    # Make Hebrew default track
  
processing:
  sync_engine: "alass"                      # alass | ffsubsync | autosubsync
  fix_rtl: true
  keep_temp_files: false
```

---

## Error Handling

1. **No matching episode found:**
   - Log warning with both filenames
   - Continue processing other files
   - Generate report at end

2. **Sync fails:**
   - Try alternative sync engine (ffsubsync)
   - If all fail, skip file and log

3. **MKVMerge fails:**
   - Check encoding (convert to UTF-8 if needed)
   - Log error with details

4. **Missing tools:**
   - Check on startup
   - Provide download links/instructions

---

## First Steps for Claude Code

1. **Verify installed tools:**
   ```bash
   where mkvmerge
   where alass
   where python
   ```

2. **Check if FFmpeg is installed:**
   ```bash
   where ffmpeg
   ```
   If not, may need to install for AutoSubSync.

3. **Create project structure** at `G:\Projects\SubtitlePipeline\`

4. **Download alass.exe** if not present:
   - https://github.com/kaegi/alass/releases
   - Place in `tools/` folder

5. **Build MVP** - Start with CLI that:
   - Takes folder path as argument
   - Matches episodes
   - Runs pipeline on each pair
   - Outputs to `Output/` subfolder

6. **Test with one file first** before batch processing

---

## Testing Checklist

- [ ] Episode matching works for `S06E01` ↔ `6x01`
- [ ] alass syncs subtitles correctly
- [ ] RTL punctuation displays correctly in VLC
- [ ] MKV has Hebrew subtitle track with correct language tag
- [ ] Batch processing handles 20+ files without issues
- [ ] Errors are logged, don't crash the whole process

---

## Additional Notes

- User is a QA tester - appreciates robust error handling
- User works with media services company (MediaWave)
- Process should be repeatable for different TV series
- Hebrew encoding: Ensure UTF-8 throughout pipeline
- The `.en.srt` suffix in subtitle files is misleading - they are actually Hebrew

---

## Quick Reference Commands

```bash
# Sync subtitle
alass "video.mkv" "subtitle.srt" "synced.srt"

# Embed subtitle into MKV
mkvmerge -o "output.mkv" "input.mkv" --language 0:heb --track-name 0:"Hebrew" "subtitle.srt"

# Full pipeline for one file
alass "video.mkv" "input.srt" "temp_synced.srt"
python rtl_fixer.py "temp_synced.srt" "temp_fixed.srt"
mkvmerge -o "output.mkv" "video.mkv" --language 0:heb "temp_fixed.srt"
```
# Additional Requirements - IMPORTANT

## Modular Architecture

The tool MUST be modular, allowing the user to run each step independently OR all steps together:

### Individual Modes:
1. **Sync Only** - Just sync subtitles with video (alass), output synced SRT files
2. **RTL Fix Only** - Just fix RTL punctuation on existing SRT files
3. **Embed Only** - Just embed existing SRT files into MKV (mkvmerge)
4. **Full Pipeline** - Run all 3 steps in sequence (Sync → RTL Fix → Embed)

### Why This Matters:
- Sometimes subtitles are already synced, user just needs RTL fix + embed
- Sometimes user wants to manually review synced subtitles before embedding
- Flexibility for different workflows and use cases

---

## GUI Application (Required)

Build a graphical user interface using **PyQt5** or **tkinter** with:

### Main Window:
- **Mode selector:** Radio buttons or tabs for (Sync Only | RTL Fix Only | Embed Only | Full Pipeline)
- **Input folder:** Browse button + drag & drop support
- **Output folder:** Browse button (default: subfolder "Output" in input folder)
- **Start button:** Begin processing
- **Progress bar:** Show overall progress
- **Log area:** Scrollable text area showing real-time processing logs

### Settings Panel:
- Path to mkvmerge.exe (auto-detect or browse)
- Path to alass.exe (auto-detect or browse)
- Subtitle language code (default: "heb")
- Subtitle track name (default: "Hebrew")
- Checkbox: "Set as default subtitle track"
- Checkbox: "Keep temporary files"

### Visual Feedback:
- Green checkmark for successfully processed files
- Red X for failed files
- Summary at the end: "Processed: X, Failed: Y, Skipped: Z"

---

## Executable Build (Required)

Package the final application as a **standalone Windows EXE** using **PyInstaller**:

```bash
pyinstaller --onefile --windowed --name "SubtitlePipeline" --icon=icon.ico main.py
```

### Requirements:
- Single EXE file (--onefile flag)
- No console window (--windowed flag)
- Include all dependencies
- Place final EXE in `G:\Projects\SubtitlePipeline\dist\`

### The user should be able to:
1. Double-click the EXE to run
2. No Python installation required on target machine
3. Optionally create desktop shortcut

---

## Summary of Deliverables:

1. ✅ Modular Python code with separate functions for each step
2. ✅ GUI application with mode selection
3. ✅ Standalone EXE file
4. ✅ Config file for tool paths and settings
5. ✅ README with usage instructions