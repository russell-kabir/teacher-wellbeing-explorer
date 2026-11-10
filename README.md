# Teacher Well-being Explorer

An interactive Shiny for Python app on teacher **stress, burnout and flourishing** in **Indonesia, Japan, the United States and ASEAN**. It was built for the Kabir Lab (Hiroshima University) teacher psychological well-being short course for Indonesian teachers.

The app runs entirely in the browser through [Shinylive](https://shiny.posit.co/py/docs/shinylive.html) (WebAssembly), so it needs no server and can be hosted free on GitHub Pages or embedded in a Google Site.

## Tabs
| Tab | What it shows | Sub-visualizations |
|---|---|---|
| Workforce over time | Pupil–teacher ratios 1990–2018 (UIS/WDI), Our World in Data style | ASEAN latest-year ranking; Indonesia 2023/24 ratios by level and province vs. the PP 74/2008 1:20 ideal |
| TALIS 2024 | Stress "a lot", harm to mental health, hours, intention to leave, stress sources | Japan's weekly hours 2018 → 2024 by activity vs. the international average; stress vs. mental-health scatter |
| Occupational health | Japan MEXT mental-illness leave FY2015–2024; US RAND frequent job stress 2021–2026 | — |
| Burnout (MBI) | Published MBI-ES means ± SD | POMP converter: rescale any MBI mean (any response format) to compare fairly |
| Well-being (PWB / MHC) | Keyes MHC-SF flourishing / moderate / languishing in published teacher samples | Interactive Keyes diagnostic classifier (14 dimensions, presets) |
| Breakout Lab | Thursday 12 Nov room activity (stress, burnout and resilience): BRiTE issues and fictional cases, a week rebalancer, and a shared class board | Week rebalancer shows hours freed and *who* controls them (me / team / school leader / Dinas); live class board grouped by who needs to act |
| Sources & caveats | Full source list and limitations | — |

## Deploy on GitHub Pages
The exported static site is in `docs/`. In the repository, go to **Settings → Pages → Build and deployment**, choose **Deploy from a branch**, then pick `main` and the `/docs` folder. The app will appear at `https://russell-kabir.github.io/teacher-wellbeing-explorer/`.

To embed it in a Google Site, use **Insert → Embed → By URL** and paste the Pages URL.

## Breakout Lab: connecting the shared class board
Shinylive runs in each participant's browser, so the class board is stored in a Google Sheet through a small Apps Script web app (`apps_script/thursday_board.gs`).

1. At script.google.com, create a project, paste `apps_script/thursday_board.gs`, and run `setup()`. This creates the Sheet (with a Board tab) and an optional backup Google Form.
2. **Deploy → New deployment → Web app**, Execute as *Me*, access *Anyone*. Copy the URL ending in `/exec`.
3. Paste it into `BOARD_URL` at the top of `app/breakout.py` and rebuild (below).

With `BOARD_URL` empty, the tab runs in demo mode: posts stay in the participant's own browser. Before the session, run `clearTestResponses()` to wipe test posts. The session code (`BOARD_CODE`) must match in both files.

## Edit or add data
Every figure lives in `app/data/*.csv`, one row per value, each with its source. To add a study (for example, a new Indonesian MBI-ES sample), add a row to `mbi_studies.csv` or `flourishing_studies.csv`, then rebuild:

```bash
pip install shiny shinylive shinywidgets plotly pandas
shiny run app/app.py            # preview locally
shinylive export app docs       # rebuild the static site
touch docs/.nojekyll
```

## Data notes
- The international pupil–teacher ratio series come from the WDI release of January 2020 and end in 2017–2018.
- TALIS figures describe lower-secondary teachers unless marked otherwise. Indonesia does not take part in TALIS.
- MBI and MHC-SF entries are single studies, not national estimates. Only means, SDs and percentages that could be checked against the publication are included. Gaps are labelled as gaps.
