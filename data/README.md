# data/

`Microdata/` holds the AHS2024 agricultural household survey files (Stata `.dta`).
**They are not committed to Git** (the crop file is 130 MB, over GitHub's 100 MB limit, and they contain
household-level records). Share them through a drive or similar and keep them only on the team's computers.

## Rebuilding the numbers on the "Our story" page
```bash
pip install pandas
python data/build_story_data.py
```
This reads the survey files and writes small anonymous summary numbers to
`frontend/assets/data/story.json`, which is the only data the website uses. Run it again if the survey files change.

All numbers are plain counts and shares of the surveyed households and crop plots (not weighted to the whole
country). The notes at the bottom of the story page say so.
