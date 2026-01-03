# FIX: Improved Translation Prompt

## Update the translation prompt in translator.py

### Find the current prompt and REPLACE it with this improved version:

```python
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
  - Abbreviations that are used in Hebrew too (OK, CT)
  
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

### 4. CONTEXT AWARENESS
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
```

---

## Example Translations:

### Input:
```
1. I told you I can't do this anymore!
2. She doesn't understand what I'm going through.
3. Brenner, get me 10cc of epinephrine!
4. I'm a doctor, not a miracle worker.
5. Elizabeth, are you okay?
```

### Good Output (Female speaking lines 1-2, then ER scene):
```
1. אמרתי לך שאני לא יכולה יותר!
2. היא לא מבינה מה אני עוברת.
3. ברנר, תביא לי 10 סמ"ק אפינפרין!
4. אני רופא, לא עושה נסים.
5. אליזבת, את בסדר?
```

### Bad Output (ignoring gender, keeping English):
```
1. אמרתי לך שאני לא יכול יותר!  ← WRONG gender
2. היא לא מבינה מה אני עובר.    ← WRONG gender
3. Brenner, תביא לי 10cc של epinephrine!  ← English names/terms
4. אני דוקטור, לא miracle worker.  ← Mixed language
5. Elizabeth, את OK?  ← English name
```

---

## Medical Terms Translation Guide:

| English | Hebrew |
|---------|--------|
| Doctor / Dr. | דוקטור / ד"ר |
| Nurse | אחות / אח |
| Patient | מטופל / מטופלת |
| Emergency Room / ER | חדר מיון |
| Surgery | ניתוח |
| Diagnosis | אבחנה |
| Treatment | טיפול |
| Medication | תרופה |
| IV | עירוי |
| Blood pressure | לחץ דם |
| Heart rate | דופק |
| X-ray | צילום רנטגן |
| CT scan | CT (נשאר באנגלית) |
| MRI | MRI (נשאר באנגלית) |
| CPR | החייאה |
| Intubation | אינטובציה |
| Epinephrine | אפינפרין |
| cc / ml | סמ"ק |
| mg | מ"ג |
| Stat! | מיד! / עכשיו! |
| Code Blue | קוד כחול |

---

## Also update batch_size for better context:

```python
# In the translation loop, increase context for better gender detection:
batch_size = 20  # Subtitles per batch
context_lines = 10  # Previous lines for context (increased from 5)
```

---

## Summary of Changes:

1. **Names:** Transliterate ALL to Hebrew (ברנר, ג'ון, אליזבת)
2. **Gender:** Detailed instructions for detecting male/female
3. **Medical terms:** Hebrew equivalents provided
4. **English exceptions:** Only DNA, HIV, CT, MRI, OK
5. **Context:** Increased to 10 lines for better gender detection
