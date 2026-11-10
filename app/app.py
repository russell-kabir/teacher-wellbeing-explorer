"""
Teacher Well-being Explorer
Stress, burnout and flourishing among teachers in Indonesia, Japan, the United States and ASEAN.

Built for the Kabir Lab teacher psychological well-being short course (Hiroshima University).
Runs fully in the browser via Shinylive (Shiny for Python + Pyodide).
Every number comes from a cited public source; see the "Sources & caveats" tab and data/*.csv.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

from breakout import breakout_server, breakout_ui

DATA = Path(__file__).parent / "data"


def load(name):
    return pd.read_csv(DATA / name)


ptr = load("ptr_series.csv")
ptr_asean = load("ptr_asean_latest.csv")
idn_bps = load("indonesia_bps_ptr.csv")
talis = load("talis2024.csv")
jp_hours = load("japan_hours.csv")
jp_leave = load("japan_mental_leave.csv")
rand_us = load("rand_us.csv")
mbi = load("mbi_studies.csv")
flour = load("flourishing_studies.csv")

# ---------------------------------------------------------------------------
# Colour follows the entity, never its rank (validated categorical palette).
# ---------------------------------------------------------------------------
COLORS = {
    "Japan": "#2a78d6",
    "Indonesia": "#eb6834",
    "United States": "#1baf7a",
    "Singapore": "#eda100",
    "Thailand": "#e87ba4",
    "Malaysia": "#008300",
    "Viet Nam": "#6250d6",
    "Vietnam": "#6250d6",
    "Philippines": "#e34948",
    "Brunei": "#8a8984",
    "OECD average": "#52514e",
    "OECD members": "#52514e",
    "Italy": "#2a78d6",
    "South Africa": "#eb6834",
    "Ukraine": "#1baf7a",
}
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e6e5e0"
FONT = "Inter, system-ui, -apple-system, Segoe UI, sans-serif"


def base_layout(fig, title=None, ytitle=None, xtitle=None, height=430, legend=True):
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16, color=INK)) if title else None,
        font=dict(family=FONT, size=13, color=INK2),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=height,
        margin=dict(l=60, r=140, t=60 if title else 20, b=90),
        hovermode="x unified",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="left", x=0, title=None),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, color=INK)),
    )
    fig.update_xaxes(title=xtitle, showgrid=False, linecolor=MUTED, ticks="outside", tickcolor=MUTED)
    fig.update_yaxes(title=ytitle, gridcolor=GRID, zeroline=False, linecolor=MUTED)
    return fig


def source_note(text):
    return ui.p(ui.tags.small(ui.HTML(text)), class_="source-note")


def prompt_box(*questions):
    return ui.div(
        ui.tags.strong("Discussion prompts"),
        ui.tags.ul(*[ui.tags.li(q) for q in questions]),
        class_="prompt-box",
    )


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
CSS = """
body { font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; color:#0b0b0b; background:#fcfcfb; }
.navbar { border-bottom: 1px solid #e6e5e0; }
.lead-text { font-size: 1.05rem; color:#52514e; max-width: 62rem; }
.source-note { color:#52514e; margin-top:.35rem; }
.prompt-box { background:#f3f2ee; border-left:4px solid #2a78d6; padding:.8rem 1rem; border-radius:6px; margin:1rem 0; }
.caveat { background:#fff6e5; border-left:4px solid #eda100; padding:.7rem 1rem; border-radius:6px; margin:.6rem 0 1rem; color:#3d3c39; }
.gap-box { background:#f3f2ee; border:1px dashed #8a8984; padding:.7rem 1rem; border-radius:6px; margin:.6rem 0; color:#3d3c39; }
.card { border:1px solid #e6e5e0; box-shadow:none; }
.bslib-value-box .value-box-value { font-size: 1.9rem; }
.verdict { font-size:1.4rem; font-weight:600; }
table.dataframe, .table { font-size: .88rem; }
"""

overview = ui.nav_panel(
    "Overview",
    ui.h2("Teacher Well-being Explorer"),
    ui.p(
        "How stressed, burned out and well are teachers in Indonesia, Japan, the United States and "
        "ASEAN? This app puts the best public numbers side by side, from elementary to high school, so "
        "you can see the patterns for yourself and question them.",
        class_="lead-text",
    ),
    ui.layout_columns(
        ui.value_box("Japan: weekly hours, junior high teachers (TALIS 2024)", "55.1 h",
                     "Longest of all 55 systems. OECD average: 41.0 h", theme="primary"),
        ui.value_box("US teachers reporting frequent job stress (RAND 2026)", "55%",
                     "vs 34% of similar working adults", theme="success"),
        ui.value_box("Japan: teachers on mental-illness leave (FY2024)", "7,087",
                     "0.77% of all public-school teachers (MEXT)", theme="secondary"),
        ui.value_box("Viet Nam: teachers stressed 'a lot' (TALIS 2024)", "4%",
                     "vs 19% OECD average; 92% feel valued by society", theme="info"),
        col_widths=[3, 3, 3, 3],
    ),
    ui.h4("How to use the tabs", class_="mt-4"),
    ui.tags.ol(
        ui.tags.li(ui.tags.b("Workforce over time:"), " Our World in Data-style trend lines for pupil–teacher ratios, which are a rough measure of workload."),
        ui.tags.li(ui.tags.b("TALIS 2024:"), " OECD survey indicators for stress, hours, intention to leave and where teachers' time goes."),
        ui.tags.li(ui.tags.b("Occupational health:"), " Year-by-year national records: Japan's mental-illness sick leave and US teacher stress."),
        ui.tags.li(ui.tags.b("Burnout (MBI):"), " Published Maslach Burnout Inventory means, plus a converter for comparing scores fairly across different scales."),
        ui.tags.li(ui.tags.b("Well-being (PWB/MHC):"), " Keyes' flourishing–languishing model with an interactive classifier, plus Ryff's six dimensions."),
        ui.tags.li(ui.tags.b("Breakout Lab:"), " Thursday's room activity: pick an issue or case, rebalance a teacher's week, and post your room's action to a shared class board."),
        ui.tags.li(ui.tags.b("Sources & caveats:"), " Where every number comes from, and what each one can't tell you."),
    ),
    ui.div(
        ui.tags.b("Reading rule for this whole app: "),
        "Cross-country comparisons of self-reported stress are shaped by language, culture and response "
        "style. Use the differences to start discussions, not to rank countries. Indonesia does not take "
        "part in TALIS, so its picture comes from national statistics and individual studies.",
        class_="caveat",
    ),
)

workforce = ui.nav_panel(
    "Workforce over time",
    ui.h3("Pupils per teacher, 1990–2018"),
    ui.p("A pupil–teacher ratio (PTR) divides enrolled pupils by teachers at a given school level. It is a rough "
         "workload signal: it says nothing about class size, hours or administrative load.", class_="lead-text"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_radio_buttons("ptr_level", "School level",
                                   ["Primary", "Lower secondary", "Upper secondary"], selected="Primary"),
            ui.input_checkbox_group(
                "ptr_countries", "Countries",
                ["Indonesia", "Japan", "United States", "Thailand", "OECD members"],
                selected=["Indonesia", "Japan", "United States", "Thailand"],
            ),
            ui.p(ui.tags.small("OECD members only has data for lower secondary."), class_="text-muted"),
            width=260,
        ),
        output_widget("ptr_plot"),
        source_note("Source: UNESCO Institute for Statistics via World Bank WDI (indicators SE.PRM.ENRL.TC.ZS, "
                    "SE.SEC.ENRL.LO.TC.ZS, SE.SEC.ENRL.UP.TC.ZS), as mirrored by IndexMundi (WDI release of January 2020). "
                    "The Japan and US series in that release start in 2013–14."),
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Sub-view: ASEAN plus comparison countries, latest primary PTR"),
            output_widget("asean_plot"),
            source_note("Source: UIS via WDI/IndexMundi, latest year available (2017–2018)."),
        ),
        ui.card(
            ui.card_header("Sub-view: Indonesia 2023/24, national averages hide regional gaps"),
            output_widget("idn_plot"),
            source_note("Source: BPS-Statistics Indonesia, <i>Education Statistics 2024</i>, via Katadata Databoks. "
                        "The dashed line marks the 1 teacher : 20 pupils ideal in Government Regulation 74/2008, Art. 17."),
        ),
        col_widths=[6, 6],
    ),
    prompt_box(
        "Indonesia's primary PTR fell from about 23 to about 17 between 1990 and 2018. Did workload fall with it? What would a PTR miss (for example, honorary teachers or multi-shift schools)?",
        "Thailand's upper-secondary ratio rose sharply after 2008. What policy or demographic changes might lie behind that?",
        "Indonesia's national SD ratio is about 15, but Papua Pegunungan's is above 34. Which teachers in your region carry that load?",
    ),
)

talis_tab = ui.nav_panel(
    "TALIS 2024",
    ui.h3("OECD Teaching and Learning International Survey 2024: lower-secondary teachers"),
    ui.p("TALIS 2024 surveyed teachers and principals in 55 education systems. Japan, the United States, Singapore "
         "and Viet Nam took part; Indonesia did not.", class_="lead-text"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("talis_ind", "Indicator", list(dict.fromkeys(talis["indicator"])),
                            selected='Stress "a lot" (%)'),
            ui.p(ui.tags.small("Systems appear only where a published figure was found. A missing bar means "
                               "the value wasn't available, not that it is zero."), class_="text-muted"),
            width=300,
        ),
        output_widget("talis_plot"),
        source_note("Sources: OECD (2025) <i>Results from TALIS 2024</i> and the country notes for Japan, the US and Singapore "
                    "(country-note values via TherapyRoute's TALIS compilation); OECD <i>Insights &amp; Interpretations</i>; "
                    "Education International (7 Oct 2025); Viet Nam Ministry of Education and Training release (Viet Nam News, Nov 2025); "
                    "EDUtech Asia report (Singapore hours); Newsweek Japan (US hours)."),
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Sub-view: where a Japanese teacher's week goes, 2018 → 2024"),
            ui.input_radio_buttons("jp_level", None, ["Elementary", "Junior high"], selected="Junior high", inline=True),
            output_widget("jp_hours_plot"),
            source_note("Source: NIER / MEXT, <i>TALIS 2024 key points</i> (full-time teachers, hours per week). Grey ticks "
                        "show the 2024 international average. The 2018 values are recomputed on the 2024 basis, which is why "
                        "the junior-high figure is 59.1 h rather than the 56.0 h in the 2018 report."),
        ),
        ui.card(
            ui.card_header("Sub-view: stress vs. harm to mental health"),
            output_widget("stress_scatter"),
            source_note("Each dot is one system: the share stressed 'a lot' against the share saying the job harms their "
                        "mental health 'a lot'. Only systems with both values published are shown."),
        ),
        col_widths=[7, 5],
    ),
    prompt_box(
        "Japan cut 4 hours a week between 2018 and 2024, mostly from club activities and paperwork, yet the share stressed 'a lot' rose. Why might fewer hours not mean less stress?",
        "Only 4% of Vietnamese teachers report stress 'a lot', and 92% feel valued by society. How far do you think social recognition protects teachers, and how much is response style?",
        "Which of these indicators would you most want measured for Indonesian teachers, and how?",
    ),
)

occ_tab = ui.nav_panel(
    "Occupational health",
    ui.h3("Year-by-year national records"),
    ui.layout_columns(
        ui.card(
            ui.card_header("Japan: public-school teachers on sick leave for mental illness"),
            ui.input_radio_buttons("leave_metric", None, ["Number of teachers", "% of all teachers"], inline=True),
            output_widget("jp_leave_plot"),
            source_note("Source: MEXT, <i>Survey on personnel administration of public-school staff</i> "
                        "(公立学校教職員の人事行政状況調査), FY2015–FY2024. Percentages are shown only for years where MEXT "
                        "published them in the sources consulted. Teachers on more than one month of sick leave "
                        "(1か月以上の病気休暇) are not included; adding them brings FY2024 to 13,310."),
        ),
        ui.card(
            ui.card_header("United States: share reporting frequent job-related stress"),
            output_widget("rand_plot"),
            source_note("Source: RAND, <i>State of the American Teacher</i> surveys, 2021–2026 (K–12 public school teachers), with the "
                        "American Life Panel as the comparison group of working adults. Adult values are shown only where reported."),
        ),
        col_widths=[6, 6],
    ),
    ui.div(
        ui.tags.b("Indonesia: a gap to fill. "),
        "No national, repeated measure of teacher stress or mental-health leave could be found in public "
        "statistics. The teacher studies that exist are mostly single-site samples (see the Burnout tab). "
        "This gap could make a good group project for the course: what would a minimal national monitoring "
        "indicator look like?",
        class_="gap-box",
    ),
    prompt_box(
        "Japan's mental-illness leave numbers stayed around 5,000 a year until 2020, then rose steeply. What changed? Consider the pandemic, reporting practices, and the age profile of new teachers.",
        "US stress fell from 78% (2021) but stayed well above the level among other workers. What would 'recovery' mean for a profession?",
        "Sick-leave records count people too ill to work, while surveys count people still working. How do the two kinds of number complement each other?",
    ),
)

mbi_tab = ui.nav_panel(
    "Burnout (MBI)",
    ui.h3("Maslach Burnout Inventory: comparing like with like"),
    ui.p("The MBI-Educators Survey has three subscales: Emotional Exhaustion (EE, 9 items), Depersonalization "
         "(DP, 5 items) and Personal Accomplishment (PA, 8 items, where higher is better), each rated 0–6 for "
         "frequency. Studies often change the response format or drop items, so raw means are not directly "
         "comparable. The converter rescales every mean to POMP: the percent of the maximum possible score.",
         class_="lead-text"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_radio_buttons("mbi_metric", "Show", ["POMP (0–100)", "Raw sum score"], selected="POMP (0–100)"),
            ui.hr(),
            ui.tags.b("Add your own sample"),
            ui.p(ui.tags.small("For example, your school's results or a study you're reading. The entry stays in your browser only."),
                 class_="text-muted"),
            ui.input_text("my_label", "Label", "My school (Indonesia)"),
            ui.input_select("my_sub", "Subscale", ["EE", "DP", "PA"], selected="EE"),
            ui.input_numeric("my_mean", "Reported mean", 3.1, step=0.1),
            ui.input_radio_buttons("my_type", "The mean is…", ["an item average", "a sum score"], selected="an item average"),
            ui.input_numeric("my_items", "Number of items", 9, min=1),
            ui.layout_columns(
                ui.input_numeric("my_min", "Scale min", 1),
                ui.input_numeric("my_max", "Scale max", 5),
                col_widths=[6, 6],
            ),
            ui.output_ui("my_pomp"),
            width=300,
        ),
        output_widget("mbi_plot"),
        ui.div(
            ui.tags.b("Commonly used MBI-ES bands (0–6 sum scores): "),
            "EE low ≤16 · moderate 17–26 · high ≥27; DP low ≤6 · moderate 7–12 · high ≥13; PA high ≥39 · "
            "moderate 31–38 · low ≤30 (low PA = more burnout). Different sources draw these bands ±1 point apart, "
            "and the 4th-edition manual warns against treating them as diagnostic cut-offs. They are shown here to "
            "help you read the scores, not to diagnose anyone.",
            class_="caveat",
        ),
        ui.output_data_frame("mbi_table"),
        source_note("Studies included are only those whose means and SDs could be checked against the publication. "
                    "Japan: the Japanese MBI-ES was validated by Okumura, Mori, Miyashita, Nishimura & Kitajima (2015), "
                    "<i>Shinrigaku Kenkyu</i> 86(4), 323–332, but its descriptive statistics could not be retrieved here. "
                    "Indonesia: Prasojo et al. (2020, <i>Heliyon</i>; N = 876 teachers in Jambi, Bandung and Yogyakarta) used a "
                    "shortened 15-item MBI, and its raw data is open on Mendeley Data (doi:10.17632/6jmv43nffk.2), which would "
                    "make it a good dataset to compute and add."),
    ),
    prompt_box(
        "Thai teachers' mean depersonalization (2.6 out of 30) is very low. Is that a floor effect, a cultural norm against admitting cynicism toward students, or real?",
        "Two Indonesian studies report '45% moderate exhaustion' and '57.8% high exhaustion'. What would you need to know before comparing them?",
        "Try the converter: a mean of 3.1 on a 1–5 scale is a POMP of 52.5. Where does that sit next to the 0–6 studies?",
    ),
)

ITEMS = [
    ("EWB", "Happy"), ("EWB", "Interested in life"), ("EWB", "Satisfied with life"),
    ("SWB", "Social contribution"), ("SWB", "Social integration"), ("SWB", "Social growth (actualization)"),
    ("SWB", "Social acceptance"), ("SWB", "Social coherence"),
    ("PWB", "Self-acceptance"), ("PWB", "Environmental mastery"), ("PWB", "Positive relations"),
    ("PWB", "Personal growth"), ("PWB", "Autonomy"), ("PWB", "Purpose in life"),
]
FREQ = ["0 never", "1 once or twice", "2 about once a week", "3 2–3 times a week", "4 almost every day", "5 every day"]

wb_tab = ui.nav_panel(
    "Well-being (PWB / MHC)",
    ui.h3("From languishing to flourishing"),
    ui.p("Keyes' Mental Health Continuum–Short Form (MHC-SF) combines emotional well-being (hedonic) with Ryff's "
         "psychological well-being and social well-being (eudaimonic). People are classified as flourishing, "
         "moderately mentally healthy or languishing based on how often they experience each feeling over the past month.",
         class_="lead-text"),
    ui.layout_columns(
        ui.card(
            ui.card_header("Interactive classifier: move the frequencies, watch the diagnosis"),
            ui.p(ui.tags.small("Each slider is one MHC-SF dimension, rated from 0 (never) to 5 (every day) over the past month. "
                               "The rule: flourishing = at least 1 of 3 emotional items at 4–5 and at least 6 of the 11 "
                               "social/psychological items at 4–5. Languishing is the mirror image at 0–1. Everything else "
                               "is 'moderate'.")),
            ui.layout_columns(
                ui.div(ui.tags.b("Emotional (EWB)"),
                       *[ui.input_slider(f"mhc{i}", lab, 0, 5, 3, step=1) for i, (d, lab) in enumerate(ITEMS) if d == "EWB"]),
                ui.div(ui.tags.b("Social (SWB)"),
                       *[ui.input_slider(f"mhc{i}", lab, 0, 5, 3, step=1) for i, (d, lab) in enumerate(ITEMS) if d == "SWB"]),
                ui.div(ui.tags.b("Psychological (PWB, Ryff)"),
                       *[ui.input_slider(f"mhc{i}", lab, 0, 5, 3, step=1) for i, (d, lab) in enumerate(ITEMS) if d == "PWB"]),
                col_widths=[4, 4, 4],
            ),
            ui.layout_columns(
                ui.input_action_button("preset_flour", "Example: flourishing"),
                ui.input_action_button("preset_mod", "Example: 'busy but OK'"),
                ui.input_action_button("preset_lang", "Example: languishing"),
                col_widths=[4, 4, 4],
            ),
            ui.output_ui("mhc_verdict"),
        ),
        ui.card(
            ui.card_header("Published teacher samples: % in each MHC-SF category"),
            output_widget("flour_plot"),
            source_note("Only teacher samples using Keyes' MHC-SF categories are shown. Taiwanese teachers (Yu & Chen; N = 2,400; "
                        "21.7% flourishing) used a different typology, so they are excluded. Nigerian female primary "
                        "teachers (N = 2,389; 62% flourishing) reported flourishing versus not flourishing only, so they are "
                        "described here but not plotted."),
            ui.div(
                ui.tags.b("US, Japan and Indonesia: a gap to fill. "),
                ui.HTML("No teacher sample with published MHC-SF flourishing rates was found for these three countries. "
                "Indonesian versions exist (MHC-SF: Putra, 2023, <i>Psychocentrum Review</i> 5(2); MHC-LF: Sari et al., 2023) "
                "and have been used with PE teachers (Juriana et al., 2024, <i>IJDSHS</i> 7(5), N = 248; most in the moderate category). "
                "Ryff's PWB has been studied with Jakarta kindergarten teachers (N = 260; 65.4% in the 'low' band, with "
                "autonomy and environmental mastery lowest). Data you collect in this course could fill this gap."),
                class_="gap-box",
            ),
        ),
        col_widths=[7, 5],
    ),
    prompt_box(
        "Set every eudaimonic slider to 4 but all three emotional ones to 3. Why does Keyes require both kinds of well-being before calling someone 'flourishing'?",
        "Picture a teacher with high purpose in life but low autonomy and environmental mastery (the two lowest dimensions among the Jakarta kindergarten teachers). Set the sliders that way: how does that profile classify, and what does it suggest for intervention?",
        "Is flourishing an individual property, or something a school ecosystem produces? Connect this to your Day 5 policy plan.",
    ),
)

sources_tab = ui.nav_panel(
    "Sources & caveats",
    ui.h3("Where every number comes from"),
    ui.markdown(
        """
**Workforce (pupil–teacher ratios).** UNESCO Institute for Statistics, via World Bank WDI, as mirrored by IndexMundi
(WDI release of 1 Jan 2020). BPS-Statistics Indonesia, *Education Statistics 2024* (via Katadata Databoks). Indonesia
Government Regulation 74/2008 on Teachers, Art. 17 (the 1:20 ideal ratio).

**TALIS 2024.** OECD (2025), *Results from TALIS 2024: The State of Teaching*, plus the country notes for Japan, the
United States, Singapore and Viet Nam. National Institute for Educational Policy Research (NIER),
*TALIS 2024 key points* (talis2024_point.pdf), used for Japan's hour breakdown, 2018 vs. 2024. Education International
press release (7 Oct 2025), used for OECD averages on stress sources and mental-health harm. Viet Nam MoET results
(Viet Nam News / VietnamPlus, Nov 2025).

**Occupational health.** MEXT, *公立学校教職員の人事行政状況調査* (FY2015–FY2024 releases). RAND Corporation,
*State of the American Teacher* survey reports and press releases, 2021–2026.

**Burnout.** Iwanicki & Schwab (1981), *Educational and Psychological Measurement* 41(4). *Mental health and burnout
among teachers in Thailand*, *Journal of Health Research* (doi:10.1108/JHR-05-2020-0181).

**Well-being.** Keyes (2002), *Journal of Health and Social Behavior* 43, 207–222 (MHC model and diagnostic rule).
Capone & Petrillo (2020), *Current Psychology* 39. Redelinghuys & Rothmann (2020), *SA Journal of Industrial
Psychology* 46 (citing Boshoff et al., 2014). Handzilevska, Tsurkan & Škorvagová (Ukraine).

### Caveats worth teaching

- **Vintage.** The international PTR series end in 2017–2018, the last year in that WDI mirror. Newer UIS figures
  exist but could not be downloaded when the app was built.
- **TALIS is lower-secondary.** Most TALIS figures describe junior-high teachers. Japan's hour breakdown also covers
  elementary teachers.
- **Self-report and culture.** "Stress a lot" depends on how a language and culture talk about strain. TALIS itself
  advises caution with cross-country comparisons.
- **Single studies are not national estimates.** Every MBI and MHC sample here is a convenience or regional sample.
- **Missing ≠ zero.** Wherever a bar or point is missing, the value has not been found yet.
- **ILO labour statistics.** ILOSTAT's education-sector series (hours, wages) were not reachable from the build
  environment. They would make a natural next tab.

Data files are in the repository's `app/data/` folder. To add a study, add a row to the relevant CSV
and include its citation.
"""
    ),
)

app_ui = ui.page_navbar(
    overview, workforce, talis_tab, occ_tab, mbi_tab, wb_tab, breakout_ui(), sources_tab,
    title="Teacher Well-being Explorer",
    id="nav",
    header=ui.tags.style(CSS),
    footer=ui.div(
        ui.tags.small("Kabir Lab · Hiroshima University · Built for the Indonesian teacher psychological well-being short course. "
                      "All figures are cited; see 'Sources & caveats'."),
        class_="text-center text-muted py-3",
    ),
)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
def server(input, output, session):
    breakout_server(input, output, session)

    # ---- Workforce -------------------------------------------------------
    @render_widget
    def ptr_plot():
        lvl = input.ptr_level()
        fig = go.Figure()
        ends = []
        for c in input.ptr_countries():
            d = ptr[(ptr.country == c) & (ptr.level == lvl)].sort_values("year")
            if d.empty:
                continue
            fig.add_trace(go.Scatter(
                x=d.year, y=d.value, name=c, mode="lines+markers",
                line=dict(color=COLORS[c], width=2.5), marker=dict(size=7, line=dict(color="white", width=2)),
                hovertemplate=f"{c}: %{{y:.1f}} pupils per teacher<extra></extra>",
            ))
            last = d.iloc[-1]
            ends.append([c, last.year, last.value, last.value])
        # dodge end labels so they never collide (min gap ~1.3 pupils)
        ends.sort(key=lambda e: e[2])
        for i in range(1, len(ends)):
            if ends[i][3] - ends[i - 1][3] < 1.3:
                ends[i][3] = ends[i - 1][3] + 1.3
        for c, x, v, ylab in ends:
            fig.add_annotation(x=x, y=ylab, text=f"<b>{c}</b> {v:.1f}", showarrow=False,
                               xanchor="left", xshift=8, font=dict(color=INK2, size=12))
        base_layout(fig, f"Pupil–teacher ratio, {lvl.lower()}", "Pupils per teacher", None)
        fig.update_xaxes(range=[1989, 2021])
        fig.update_yaxes(rangemode="tozero")
        return fig

    @render_widget
    def asean_plot():
        d = ptr_asean.sort_values("value")
        fig = go.Figure(go.Bar(
            x=d.value, y=d.country, orientation="h",
            marker=dict(color=[COLORS.get(c, MUTED) for c in d.country], line=dict(color="white", width=2)),
            text=[f"{v:.1f} ({y})" for v, y in zip(d.value, d.year)], textposition="outside",
            textfont=dict(color=INK2), hovertemplate="%{y}: %{x:.1f}<extra></extra>",
        ))
        base_layout(fig, None, None, "Pupils per primary teacher", height=360, legend=False)
        fig.update_layout(margin=dict(l=110, r=60, t=10, b=50), hovermode="closest")
        fig.update_xaxes(range=[0, 35], gridcolor=GRID, showgrid=True)
        fig.update_yaxes(showgrid=False)
        return fig

    @render_widget
    def idn_plot():
        d = idn_bps.copy()
        d["label"] = d.unit + " · " + d.level
        fig = go.Figure(go.Bar(
            x=d.value, y=d.label, orientation="h",
            marker=dict(color=["#eb6834" if u == "National" else "#a8441c" for u in d.unit],
                        line=dict(color="white", width=2)),
            text=[f"{v:.2f}" for v in d.value], textposition="outside", textfont=dict(color=INK2),
            hovertemplate="%{y}: %{x:.2f}<extra></extra>",
        ))
        fig.add_vline(x=20, line=dict(color=INK2, dash="dash", width=1.5))
        fig.add_annotation(x=20, y=1.04, yref="paper", text="PP 74/2008 ideal: 20", showarrow=False,
                           font=dict(size=11, color=INK2), xanchor="left", xshift=4)
        base_layout(fig, None, None, "Pupils per teacher (2023/24)", height=360, legend=False)
        fig.update_layout(margin=dict(l=230, r=60, t=30, b=50), hovermode="closest")
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(range=[0, 40], showgrid=True, gridcolor=GRID)
        return fig

    # ---- TALIS -----------------------------------------------------------
    @render_widget
    def talis_plot():
        ind = input.talis_ind()
        d = talis[talis.indicator == ind].copy()
        d = d.sort_values("value")
        is_hours = "hours" in ind.lower()
        fig = go.Figure(go.Bar(
            x=d.value, y=d.system, orientation="h",
            marker=dict(color=[COLORS.get(s, MUTED) for s in d.system], line=dict(color="white", width=2)),
            text=[f"{v:g}{'' if is_hours else '%'}" for v in d.value], textposition="outside",
            textfont=dict(color=INK, size=13),
            customdata=d.note.fillna(""),
            hovertemplate="%{y}: %{x}<br>%{customdata}<extra></extra>",
        ))
        base_layout(fig, ind, None, "Hours per week" if is_hours else "% of lower-secondary teachers",
                    height=380, legend=False)
        fig.update_layout(margin=dict(l=120, r=60, t=60, b=50), hovermode="closest")
        fig.update_xaxes(range=[0, max(d.value) * 1.2], showgrid=True, gridcolor=GRID)
        fig.update_yaxes(showgrid=False)
        return fig

    @render_widget
    def jp_hours_plot():
        d = jp_hours[(jp_hours.level == input.jp_level()) & (jp_hours.activity != "Total")]
        tot = jp_hours[(jp_hours.level == input.jp_level()) & (jp_hours.activity == "Total")].iloc[0]
        fig = go.Figure()
        for _, r in d.iterrows():
            fig.add_trace(go.Scatter(x=[r.y2018, r.y2024], y=[r.activity, r.activity], mode="lines",
                                     line=dict(color="#9fc3ee", width=4), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=d.y2018, y=d.activity, mode="markers", name="Japan 2018",
                                 marker=dict(size=12, color="#9fc3ee", line=dict(color="white", width=2)),
                                 hovertemplate="%{y} 2018: %{x} h<extra></extra>"))
        fig.add_trace(go.Scatter(x=d.y2024, y=d.activity, mode="markers+text", name="Japan 2024",
                                 marker=dict(size=12, color="#2a78d6", line=dict(color="white", width=2)),
                                 text=[f"{v} h" for v in d.y2024], textposition="top center",
                                 textfont=dict(color=INK2, size=11),
                                 hovertemplate="%{y} 2024: %{x} h<extra></extra>"))
        fig.add_trace(go.Scatter(x=d.intl_avg_2024, y=d.activity, mode="markers", name="International avg 2024",
                                 marker=dict(symbol="line-ns-open", size=18, color=INK2, line=dict(width=3)),
                                 hovertemplate="%{y} international avg: %{x} h<extra></extra>"))
        base_layout(fig, f"Hours per week. Total: {tot.y2018} h → {tot.y2024} h (international avg {tot.intl_avg_2024} h)",
                    None, None, height=360)
        fig.update_layout(margin=dict(l=150, r=30, t=80, b=110), hovermode="closest")
        fig.update_yaxes(showgrid=False, autorange="reversed")
        fig.update_xaxes(showgrid=True, gridcolor=GRID, rangemode="tozero")
        return fig

    @render_widget
    def stress_scatter():
        a = talis[talis.indicator == 'Stress "a lot" (%)'].set_index("system").value
        b = talis[talis.indicator == 'Job harms mental health "a lot" (%)'].set_index("system").value
        both = [s for s in a.index if s in b.index]
        fig = go.Figure()
        for s in both:
            pos = {"Japan": "top left", "United States": "bottom right"}.get(s, "top center")
            fig.add_trace(go.Scatter(x=[a[s]], y=[b[s]], mode="markers+text", name=s, text=[s],
                                     textposition=pos, textfont=dict(color=INK2),
                                     marker=dict(size=14, color=COLORS.get(s, MUTED), line=dict(color="white", width=2)),
                                     hovertemplate=f"{s}<br>Stress a lot: %{{x}}%<br>Harms mental health: %{{y}}%<extra></extra>"))
        base_layout(fig, None, "Job harms mental health 'a lot' (%)", "Stress 'a lot' (%)", height=360, legend=False)
        fig.update_layout(margin=dict(l=60, r=30, t=20, b=50), hovermode="closest")
        fig.update_xaxes(range=[0, 40], showgrid=True, gridcolor=GRID)
        fig.update_yaxes(range=[0, 20])
        return fig

    # ---- Occupational health ---------------------------------------------
    @render_widget
    def jp_leave_plot():
        pct = input.leave_metric() == "% of all teachers"
        d = jp_leave.dropna(subset=["rate_pct"]) if pct else jp_leave
        y = d.rate_pct if pct else d["count"]
        fig = go.Figure(go.Scatter(
            x=d.fiscal_year, y=y, mode="lines+markers", name="Japan",
            line=dict(color="#2a78d6", width=2.5), marker=dict(size=8, line=dict(color="white", width=2)),
            hovertemplate="FY%{x}: %{y}" + ("%" if pct else " teachers") + "<extra></extra>",
        ))
        last = d.iloc[-1]
        fig.add_annotation(x=last.fiscal_year, y=(last.rate_pct if pct else last["count"]),
                           text=f"<b>FY{int(last.fiscal_year)}</b> {last.rate_pct if pct else int(last['count']):,}{'%' if pct else ''}",
                           showarrow=False, xanchor="left", xshift=8, font=dict(color=INK2))
        if not pct:
            fig.add_vrect(x0=2019.6, x1=2020.4, fillcolor="#e6e5e0", opacity=0.5, line_width=0)
            fig.add_annotation(x=2020, y=1.02, yref="paper", text="COVID-19 closures", showarrow=False,
                               font=dict(size=11, color=INK2))
        base_layout(fig, None, "% of teachers" if pct else "Teachers on leave", "Fiscal year (April–March)", height=380, legend=False)
        fig.update_yaxes(rangemode="tozero")
        fig.update_xaxes(dtick=1, range=[2014.5, 2025.5], tickangle=0)
        fig.update_layout(margin=dict(l=60, r=110, t=30, b=60))
        return fig

    @render_widget
    def rand_plot():
        fig = go.Figure()
        for g, col in [("Teachers", "#1baf7a"), ("Working adults", MUTED)]:
            d = rand_us[rand_us.group == g].sort_values("year")
            fig.add_trace(go.Scatter(
                x=d.year, y=d.frequent_stress_pct, name=g, mode="lines+markers" if g == "Teachers" else "markers",
                line=dict(color=col, width=2.5, dash="solid" if g == "Teachers" else "dot"),
                marker=dict(size=8, line=dict(color="white", width=2)),
                hovertemplate=f"{g}: %{{y}}%<extra></extra>", connectgaps=True,
            ))
            last = d.iloc[-1]
            fig.add_annotation(x=last.year, y=last.frequent_stress_pct, text=f"<b>{g}</b> {last.frequent_stress_pct}%",
                               showarrow=False, xanchor="left", xshift=8, font=dict(color=INK2))
        base_layout(fig, None, "% reporting frequent job-related stress", None, height=380)
        fig.update_yaxes(range=[0, 100])
        fig.update_xaxes(dtick=1, range=[2020.6, 2026.4])
        fig.update_layout(margin=dict(l=60, r=150, t=20, b=90))
        return fig

    # ---- MBI -------------------------------------------------------------
    MAXSUM = {"EE": 54, "DP": 30, "PA": 48}

    @reactive.calc
    def my_pomp_value():
        try:
            m, k, lo, hi = float(input.my_mean()), float(input.my_items()), float(input.my_min()), float(input.my_max())
        except (TypeError, ValueError):
            return None
        if hi <= lo or k <= 0:
            return None
        item_mean = m if input.my_type() == "an item average" else m / k
        return (item_mean - lo) / (hi - lo) * 100

    @render.ui
    def my_pomp():
        v = my_pomp_value()
        if v is None:
            return ui.p("Check the scale min/max and item count.", class_="text-danger")
        warn = "" if 0 <= v <= 100 else " ⚠ outside 0–100: check the inputs"
        return ui.p(ui.tags.b(f"POMP = {v:.1f}"), warn)

    @render_widget
    def mbi_plot():
        pomp = input.mbi_metric().startswith("POMP")
        fig = go.Figure()
        subs = ["EE", "DP", "PA"]
        names = {"EE": "Emotional exhaustion", "DP": "Depersonalization", "PA": "Personal accomplishment"}
        for _, r in mbi.iterrows():
            xs, ys, errs = [], [], []
            for s in subs:
                m, sd = r[f"{s}_M"], r[f"{s}_SD"]
                if pd.isna(m):
                    continue
                f = 100 / MAXSUM[s] if pomp else 1
                xs.append(names[s]); ys.append(m * f); errs.append(sd * f)
            fig.add_trace(go.Bar(
                x=xs, y=ys, name=r.country, marker=dict(color=COLORS.get(r.country, MUTED), line=dict(color="white", width=2)),
                error_y=dict(type="data", array=errs, color=INK2, thickness=1.2, width=4),
                text=[f"{v:.1f}" for v in ys], textposition="inside", insidetextanchor="start",
                textfont=dict(color="white"),
                hovertemplate=f"{r.country}<br>%{{x}}: %{{y:.1f}} (±1 SD shown)<extra></extra>",
            ))
        v = my_pomp_value()
        if pomp and v is not None:
            fig.add_trace(go.Bar(
                x=[names[input.my_sub()]], y=[v], name=input.my_label() or "My sample",
                marker=dict(color="#eb6834", pattern=dict(shape="/", fgcolor="white", size=8),
                            line=dict(color="white", width=2)),
                text=[f"{v:.1f}"], textposition="inside", insidetextanchor="start", textfont=dict(color=INK),
                hovertemplate="%{x}: POMP %{y:.1f}<extra>your entry</extra>",
            ))
        base_layout(fig, None, "POMP (% of maximum possible)" if pomp else "Raw sum score (0–6 items)", None, height=420)
        fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08, hovermode="closest")
        fig.update_xaxes(categoryorder="array", categoryarray=[names[s] for s in subs])
        if pomp:
            fig.update_yaxes(range=[0, 100])
        return fig

    @render.data_frame
    def mbi_table():
        t = mbi[["country", "sample", "N", "EE_M", "EE_SD", "DP_M", "DP_SD", "PA_M", "PA_SD", "scale", "citation"]].copy()
        t.columns = ["Country", "Sample", "N", "EE M", "EE SD", "DP M", "DP SD", "PA M", "PA SD", "Scale", "Citation"]
        return render.DataGrid(t.fillna("–"), width="100%")

    # ---- Well-being ------------------------------------------------------
    def set_all(e, s, p):
        for i, v in enumerate(list(e) + list(s) + list(p)):
            ui.update_slider(f"mhc{i}", value=v)

    @reactive.effect
    @reactive.event(input.preset_flour)
    def _():
        set_all([5, 4, 4], [3, 4, 3, 4, 4], [4, 5, 5, 4, 3, 5])

    @reactive.effect
    @reactive.event(input.preset_mod)
    def _():
        set_all([3, 4, 3], [2, 3, 2, 3, 3], [4, 3, 4, 4, 2, 5])

    @reactive.effect
    @reactive.event(input.preset_lang)
    def _():
        set_all([1, 2, 1], [1, 0, 1, 2, 1], [1, 1, 2, 1, 0, 2])

    @render.ui
    def mhc_verdict():
        vals = [input[f"mhc{i}"]() for i in range(len(ITEMS))]
        ewb = vals[:3]
        eud = vals[3:]
        hi_e, hi_u = sum(v >= 4 for v in ewb), sum(v >= 4 for v in eud)
        lo_e, lo_u = sum(v <= 1 for v in ewb), sum(v <= 1 for v in eud)
        if hi_e >= 1 and hi_u >= 6:
            verdict, color = "Flourishing", "#1baf7a"
        elif lo_e >= 1 and lo_u >= 6:
            verdict, color = "Languishing", "#e34948"
        else:
            verdict, color = "Moderately mentally healthy", "#eda100"
        return ui.div(
            ui.p(ui.span("● ", style=f"color:{color}"), ui.span(verdict, class_="verdict")),
            ui.p(
                f"Emotional items at 4–5: {hi_e}/3 (need ≥1) · Social + psychological items at 4–5: {hi_u}/11 (need ≥6) · "
                f"Emotional items at 0–1: {lo_e}/3 · Social + psychological items at 0–1: {lo_u}/11.  "
                f"Continuous total: {sum(vals)}/70."
            , class_="text-muted"),
            class_="mt-3",
        )

    @render_widget
    def flour_plot():
        d = flour.copy()
        fig = go.Figure()
        for cat, col in [("languishing", "#e34948"), ("moderate", "#cfcdc6"), ("flourishing", "#1baf7a")]:
            fig.add_trace(go.Bar(
                y=d.country, x=d[cat], name=cat.capitalize(), orientation="h",
                marker=dict(color=col, line=dict(color="white", width=2)),
                text=[f"{v:g}%" if v >= 10 else "" for v in d[cat]], textposition="inside", textangle=0,
                textfont=dict(color=INK if cat == "moderate" else "white"),
                customdata=d.citation, hovertemplate="%{y}: %{x}% " + cat + "<br>%{customdata}<extra></extra>",
            ))
        base_layout(fig, None, None, None, height=300)
        fig.update_layout(barmode="stack", hovermode="closest", margin=dict(l=100, r=20, t=20, b=110))
        fig.update_xaxes(range=[0, 100.5])
        fig.update_yaxes(showgrid=False)
        return fig


app = App(app_ui, server)
