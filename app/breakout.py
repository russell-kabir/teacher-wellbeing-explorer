"""
Breakout Lab · Thursday 12 November (Stress, Burnout and Teacher Resilience)

A four-step tab for breakout rooms:
  1. Your issue or case   – the 9 November chat issues and the six fictional cases, with BRiTE moves
  2. Rebalance the week   – sliders for a typical week + strategy "moves"; shows hours freed and WHO controls them
  3. Post our action      – one row per room, sent to the shared Google Sheet
  4. Class board          – every room's action, grouped by who needs to act, refreshed live

Shinylive runs in each participant's browser, so shared data goes through a small Google Apps
Script web app attached to the Thursday Google Sheet (see apps_script/thursday_board.gs).
Leave BOARD_URL empty to run in demo mode (posts stay in this browser only).
"""

import asyncio
import io
import json
import urllib.parse
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from shiny import reactive, render, ui
from shinywidgets import output_widget, render_widget

# ---------------------------------------------------------------------------
# Configuration: paste the Apps Script web-app URL (ends in /exec) here.
# ---------------------------------------------------------------------------
BOARD_URL = ""
BOARD_CODE = "brite12"      # must match BOARD_CODE in apps_script/thursday_board.gs
REFRESH_SECONDS = 15        # board refresh interval while the Class board is open
ROOMS = 8

DATA = Path(__file__).parent / "data"
ISSUES = pd.read_csv(DATA / "thursday_issues.csv").fillna("")
JP_HOURS = pd.read_csv(DATA / "japan_hours.csv")

LEVELS = ["SD", "SMP", "Both · Keduanya"]
THEMES = [
    "B · Building resilience · Membangun resiliensi",
    "R · Relationships · Relasi",
    "i · Wellbeing · Kesejahteraan",
    "T · Taking initiative · Mengambil inisiatif",
    "E · Emotions · Emosi",
]
# Same strings as the Google Form, so app rows and Form rows sort together on the Sheet.
WHO = [
    "1 · Me · Saya sendiri",
    "2 · Our team, KKG or MGMP · Tim kami, KKG atau MGMP",
    "3 · School leader · Kepala sekolah",
    "4 · Dinas or beyond school · Dinas atau di luar sekolah",
]
WHO_SHORT = ["Me", "Team / KKG-MGMP", "School leader", "Dinas / beyond"]
WHO_COL = ["#1baf7a", "#2a78d6", "#eda100", "#6250d6"]

# Activities in a teacher's week. `talis` names the matching TALIS 2024 activity, where one exists.
ACTIVITIES = [
    ("teach", "Teaching · Mengajar", 24, "Teaching"),
    ("prep", "Lesson preparation · Persiapan", 8, "Lesson preparation"),
    ("mark", "Marking & feedback · Menilai", 5, None),
    ("admin", "Admin, forms & Dapodik · Administrasi", 6, "Administrative work"),
    ("meet", "Meetings · Rapat", 3, None),
    ("events", "Events, clubs & homeroom · Kepanitiaan, ekskul, wali kelas", 5, None),
    ("parents", "Parent messages, incl. after hours · Pesan orang tua", 3, None),
]
ACT_LABEL = {k: lab for k, lab, _, _ in ACTIVITIES}

# Strategy moves drawn from the Thursday workbook. who = index into WHO.
MOVES = [
    dict(id="m1", label="Standard reply + a reply window for parent messages", act="parents", who=0, est=1.5),
    dict(id="m2", label="School agrees response hours and a staffed urgent route", act="parents", who=2, est=1.0),
    dict(id="m3", label="Map one repeated workflow; drop double data entry", act="admin", who=0, est=1.0),
    dict(id="m4", label="One owner and one approved source for a recurring report", act="admin", who=2, est=1.5),
    dict(id="m5", label="Ask Dinas to align recurring report forms with Dapodik", act="admin", who=3, est=1.0),
    dict(id="m6", label="Replace one routine meeting with a written update", act="meet", who=2, est=1.0),
    dict(id="m7", label="“If I take this event, which duty moves?” Swap, don't add", act="events", who=2, est=2.0),
    dict(id="m8", label="Co-lead one event or club with a colleague", act="events", who=1, est=1.5),
    dict(id="m9", label="Shared bank of low-prep routines via KKG/MGMP", act="prep", who=1, est=1.5),
    dict(id="m10", label="Reuse a familiar lesson on a heavy day", act="prep", who=0, est=1.0),
    dict(id="m11", label="Co-design one task and rubric with a colleague", act="mark", who=1, est=1.0),
]

COMPARE = {
    "none": "No comparison",
    "intl_Elementary": "TALIS 2024 international average · elementary",
    "intl_Junior high": "TALIS 2024 international average · junior high",
    "jp_Elementary": "Japan 2024 · elementary",
    "jp_Junior high": "Japan 2024 · junior high",
}

COPY_JS = (
    "var t=document.getElementById('bk_copy_text');var b=this;"
    "function done(){b.textContent='Copied \u2713 \u00b7 Tersalin';}"
    "function fallback(){t.focus();t.select();try{document.execCommand('copy');done();}"
    "catch(e){b.textContent='Select the text and copy it manually';}}"
    "if(navigator.clipboard){navigator.clipboard.writeText(t.value).then(done,fallback);}else{fallback();}"
)

CSS = """
.bk-steps .nav-link { font-weight:600; }
.who-badge { display:inline-block; font-size:.72rem; font-weight:600; color:#fff; border-radius:999px;
             padding:.05rem .5rem; margin-left:.4rem; vertical-align:middle; }
.bk-move { border-bottom:1px solid #eeede8; padding:.35rem 0 .1rem; }
.bk-move .form-check { margin-bottom:0; }
.bk-move .irs { margin-top:-.4rem; }
.bk-issue-card { background:#fff; border:1px solid #e6e5e0; border-radius:8px; padding:1rem 1.2rem; }
.bk-issue-card h5 { margin-bottom:.2rem; }
.bk-kv { margin:.45rem 0; }
.bk-kv b { display:block; color:#52514e; font-size:.8rem; text-transform:uppercase; letter-spacing:.03em; }
.bk-big { font-size:1.6rem; font-weight:700; }
.bk-col { background:#f7f6f3; border-radius:8px; padding:.6rem; min-height:12rem; }
.bk-col-head { font-weight:700; padding:.2rem .3rem .5rem; }
.bk-card { background:#fff; border:1px solid #e6e5e0; border-radius:8px; padding:.6rem .75rem; margin-bottom:.6rem; font-size:.9rem; }
.bk-card p { margin:.25rem 0; }
.bk-card-head { font-weight:700; }
.bk-card-issue { color:#52514e; font-size:.82rem; margin-bottom:.3rem; }
.bk-card-themes { color:#8a8984; font-size:.75rem; margin-top:.35rem; }
.bk-privacy { background:#fff6e5; border-left:4px solid #eda100; padding:.5rem .8rem; border-radius:6px; font-size:.9rem; }
"""


# ---------------------------------------------------------------------------
# HTTP helper: pyfetch in the browser (Shinylive), urllib when run locally.
# ---------------------------------------------------------------------------
async def http_get_json(url):
    try:
        from pyodide.http import pyfetch  # type: ignore
    except ImportError:
        pyfetch = None
    if pyfetch is not None:
        resp = await pyfetch(url, method="GET")
        reader = getattr(resp, "text", None) or resp.string
        txt = await reader()
    else:
        import urllib.request

        def _get():
            with urllib.request.urlopen(url, timeout=20) as r:
                return r.read().decode("utf-8")

        txt = await asyncio.to_thread(_get)
    return json.loads(txt)


def who_index(s):
    s = str(s).strip()
    return int(s[0]) - 1 if s[:1] in "1234" and s[:1] else 3


def badge(i):
    return ui.span(WHO_SHORT[i], class_="who-badge", style=f"background:{WHO_COL[i]}")


def issue_choices():
    grp = {}
    for kind in ["Issue from 9 Nov chat", "Fictional case"]:
        d = ISSUES[ISSUES.kind == kind]
        name = "Issues from the 9 November chat" if kind.startswith("Issue") else "Fictional cases"
        grp[name] = {r.id: (r.title if kind.startswith("Fictional") else r.title) for r in d.itertuples()}
    return grp


def issue_label(iid):
    r = ISSUES[ISSUES.id == iid]
    if r.empty:
        return ""
    r = r.iloc[0]
    return r.title if r.kind == "Fictional case" else f"Chat issue · {r.title}"


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def breakout_ui():
    step1 = ui.nav_panel(
        "1 · Your issue or case",
        ui.layout_columns(
            ui.div(
                ui.input_select("bk_issue", "Your room's issue or case · Isu atau kasus ruang Anda",
                                issue_choices(), width="100%"),
                ui.div(
                    ui.tags.b("Room task · Tugas ruang (15 min)"),
                    ui.tags.ol(
                        ui.tags.li("Read your issue or case. Which BRiTE theme fits best?"),
                        ui.tags.li("Go to step 2 and rebalance one teacher's week."),
                        ui.tags.li("Choose one thing you can try, and one thing someone else needs to change."),
                        ui.tags.li("What would tell you in one week that the change helped? Post it in step 3."),
                    ),
                    ui.p(ui.tags.small("English or Bahasa Indonesia welcome · Boleh berbahasa Inggris atau Indonesia."),
                         class_="text-muted mb-0"),
                    class_="prompt-box",
                ),
            ),
            ui.output_ui("bk_issue_card"),
            col_widths=[5, 7],
        ),
    )

    move_rows = [
        ui.div(
            ui.layout_columns(
                ui.input_checkbox(f"bk_on_{m['id']}", ui.span(m["label"], badge(m["who"]))),
                ui.input_slider(f"bk_mv_{m['id']}", None, 0, 4, m["est"], step=0.5, post=" h", width="100%"),
                col_widths=[7, 5],
            ),
            class_="bk-move",
        )
        for m in MOVES
    ]

    step2 = ui.nav_panel(
        "2 · Rebalance the week",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.b("A typical week · Minggu biasa (hours)"),
                ui.p(ui.tags.small("Example values, not data. Move them to match a real week your room "
                                   "agrees on, without naming anyone."), class_="text-muted"),
                *[ui.input_slider(f"bk_h_{k}", lab, 0, 40 if k == "teach" else 20, v, step=0.5)
                  for k, lab, v, _ in ACTIVITIES],
                ui.hr(),
                ui.input_slider("bk_rock", "Time for my ‘rock’ this week (Monday's activity) · Waktu untuk ‘batu’ saya",
                                0, 10, 3, step=0.5, post=" h"),
                width=330,
            ),
            ui.layout_columns(
                ui.card(
                    ui.card_header("Try some moves · Coba beberapa langkah"),
                    ui.p(ui.tags.small("Tick a move, then estimate how many hours a week it could free for this teacher. "
                                       "The estimate is your room's judgment; there is no right answer. The badge shows "
                                       "who would need to act."), class_="text-muted"),
                    *move_rows,
                ),
                ui.div(
                    ui.output_ui("bk_week_summary"),
                    ui.card(
                        ui.card_header("Before and after · Sebelum dan sesudah"),
                        ui.input_select("bk_compare", None, COMPARE, selected="none", width="100%"),
                        output_widget("bk_week_plot"),
                        ui.output_ui("bk_compare_note"),
                    ),
                    ui.input_action_button("bk_to_post", "Use our biggest moves in step 3 →", class_="btn-primary w-100"),
                ),
                col_widths=[6, 6],
            ),
        ),
    )

    step3 = ui.nav_panel(
        "3 · Post our action",
        ui.layout_columns(
            ui.div(
                ui.div(ui.tags.b("One post per room · Satu kiriman per ruang. "),
                       "Please don't include names, school names, student details or personal stories. "
                       "Mohon jangan mencantumkan nama, nama sekolah, data siswa, atau cerita pribadi.",
                       class_="bk-privacy mb-3"),
                ui.layout_columns(
                    ui.input_select("bk_room", "Breakout room · Nomor ruang",
                                    {str(i): f"Room {i} · Ruang {i}" for i in range(1, ROOMS + 1)}),
                    ui.input_radio_buttons("bk_level", "Level · Jenjang", LEVELS, inline=True),
                    col_widths=[5, 7],
                ),
                ui.output_ui("bk_post_issue"),
                ui.input_checkbox_group("bk_themes", "BRiTE theme (one or two) · Tema BRiTE (satu atau dua)", THEMES, width="100%"),
                ui.input_text_area("bk_action", "One action we can try · Satu tindakan yang bisa kami coba",
                                   rows=3, width="100%"),
                ui.input_text_area("bk_support", "Support we need, and who can provide it · Dukungan yang kami butuhkan",
                                   rows=2, width="100%"),
                ui.input_radio_buttons("bk_who", "Who mainly needs to act? · Siapa yang terutama perlu bertindak?", WHO, width="100%"),
                ui.input_text("bk_check", "What we'll check in one week · Apa yang akan kami periksa dalam satu minggu",
                              width="100%"),
                ui.input_action_button("bk_submit", "Post to the class board · Kirim", class_="btn-primary"),
                ui.output_ui("bk_submit_status"),
            ),
            ui.div(
                ui.div(
                    ui.tags.b("Reporter for your room? "),
                    "After posting, press \u2018Copy for Zoom chat\u2019 and paste your room's action into the main Zoom chat. "
                    "Re-posting replaces your earlier post, so you can fix a typo or change your mind.",
                    class_="prompt-box",
                ),
                ui.output_ui("bk_post_hint"),
            ),
            col_widths=[7, 5],
        ),
    )

    step4 = ui.nav_panel(
        "4 · Class board",
        ui.layout_columns(
            ui.div(
                ui.h4("Who can make each change? · Siapa yang bisa membuat perubahan ini?", class_="mb-1"),
                ui.output_ui("bk_board_status"),
            ),
            ui.div(
                ui.input_radio_buttons("bk_filter", None, ["All", "SD", "SMP"], inline=True),
                ui.layout_columns(
                    ui.input_action_button("bk_refresh", "Refresh", class_="btn-sm"),
                    ui.download_button("bk_download", "Download CSV", class_="btn-sm"),
                    col_widths=[5, 7],
                ),
            ),
            col_widths=[8, 4],
        ),
        output_widget("bk_board_plot"),
        ui.output_ui("bk_board"),
        ui.div(
            ui.tags.b("Closing questions · Pertanyaan penutup"),
            ui.tags.ul(
                ui.tags.li("Which column is fullest? What does that say about where teacher resilience is built?"),
                ui.tags.li("Pick one action in the 'School leader' or 'Dinas' column. Who in this program could carry it forward?"),
                ui.tags.li("Next week, what will each of you check to see whether your action helped?"),
            ),
            class_="prompt-box",
        ),
    )

    return ui.nav_panel(
        "Breakout Lab",
        ui.tags.style(CSS),
        ui.h3("Breakout Lab · From stress to shared action"),
        ui.p("Thursday 12 November. Work through the four steps in your breakout room, then we'll compare every "
             "room's action on the class board. Kamis, 12 November: kerjakan empat langkah ini di ruang diskusi Anda.",
             class_="lead-text"),
        ui.navset_pill(step1, step2, step3, step4, id="bk_steps"),
        value="breakout",
    )


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
def breakout_server(input, output, session):
    local_rows = reactive.value([])   # demo mode store
    board_rows = reactive.value([])
    board_msg = reactive.value("")
    last_post = reactive.value(None)

    def current_issue():
        r = ISSUES[ISSUES.id == input.bk_issue()]
        return None if r.empty else r.iloc[0]

    # ---- Step 1 --------------------------------------------------------------
    @render.ui
    def bk_issue_card():
        r = current_issue()
        if r is None:
            return ui.div()
        kv = lambda k, v: ui.div(ui.tags.b(k), v, class_="bk-kv") if v else None
        return ui.div(
            ui.tags.small(r.kind, class_="text-muted"),
            ui.h5(r.title),
            kv("Breakout prompt", ui.tags.em(r.prompt)) if r.prompt else None,
            kv("Ryff lens", r.ryff),
            kv("BRiTE theme", r.brite),
            kv("Resources to draw on", r.resources),
            kv("A teacher or team move", r.teacher_move),
            kv("A school-level move", r.school_move),
            kv("Try this check", r.check),
            kv("Linked cases", r.links),
            class_="bk-issue-card",
        )

    # ---- Step 2 --------------------------------------------------------------
    @reactive.calc
    def plan():
        hrs = {k: float(input[f"bk_h_{k}"]() or 0) for k, _, _, _ in ACTIVITIES}
        sel = [(m, float(input[f"bk_mv_{m['id']}"]() or 0)) for m in MOVES if input[f"bk_on_{m['id']}"]()]
        asked = {}
        for m, v in sel:
            asked[m["act"]] = asked.get(m["act"], 0) + v
        eff = []
        for m, v in sel:
            tot = asked[m["act"]]
            scale = min(1.0, hrs[m["act"]] / tot) if tot > 0 else 0.0   # can't free more than the activity takes
            eff.append((m, v * scale))
        after = {k: hrs[k] - min(asked.get(k, 0), hrs[k]) for k in hrs}
        by_who = [sum(e for m, e in eff if m["who"] == i) for i in range(4)]
        return dict(before=hrs, after=after, eff=eff, by_who=by_who, freed=sum(by_who))

    @render.ui
    def bk_week_summary():
        p = plan()
        before, after, freed = sum(p["before"].values()), sum(p["after"].values()), p["freed"]
        rock = float(input.bk_rock() or 0)
        mine = p["by_who"][0]
        if freed == 0:
            msg = ui.p("Tick a move on the left to see how much time it could free, and who would need to act.",
                       class_="text-muted mb-0")
        else:
            others = freed - mine
            share = f"{mine:.1f} h is in this teacher's own hands; {others:.1f} h needs someone else to act."
            if freed >= rock:
                rock_msg = f"That covers the {rock:g} h rock."
            else:
                rock_msg = f"That's {rock - freed:.1f} h short of the {rock:g} h rock."
            msg = ui.p(share, " ", ui.tags.b(rock_msg), class_="mb-0")
        bar = ui.div(
            *[ui.div(style=f"width:{100 * v / freed:.1f}%;background:{WHO_COL[i]};height:100%",
                     title=f"{WHO_SHORT[i]}: {v:.1f} h")
              for i, v in enumerate(p["by_who"]) if freed > 0 and v > 0],
            style="display:flex;height:14px;border-radius:7px;overflow:hidden;background:#eeede8;margin:.5rem 0",
        )
        legend = ui.div(*[ui.span(badge(i), f" {v:.1f} h ", style="margin-right:.4rem;font-size:.85rem")
                          for i, v in enumerate(p["by_who"])])
        return ui.card(
            ui.layout_columns(
                ui.div(ui.tags.small("Week before", class_="text-muted"), ui.div(f"{before:.1f} h", class_="bk-big")),
                ui.div(ui.tags.small("Week after", class_="text-muted"), ui.div(f"{after:.1f} h", class_="bk-big")),
                ui.div(ui.tags.small("Hours freed", class_="text-muted"),
                       ui.div(f"{freed:.1f} h", class_="bk-big", style="color:#1baf7a")),
                col_widths=[4, 4, 4],
            ),
            bar, legend, msg,
        )

    @render_widget
    def bk_week_plot():
        p = plan()
        labs = [lab.split(" · ")[0] for _, lab, _, _ in ACTIVITIES]
        keys = [k for k, _, _, _ in ACTIVITIES]
        fig = go.Figure()
        fig.add_trace(go.Bar(y=labs, x=[p["before"][k] for k in keys], name="Before", orientation="h",
                             marker=dict(color="#cfcdc6", line=dict(color="white", width=1)),
                             hovertemplate="%{y} before: %{x:.1f} h<extra></extra>"))
        fig.add_trace(go.Bar(y=labs, x=[p["after"][k] for k in keys], name="After", orientation="h",
                             marker=dict(color="#eb6834", line=dict(color="white", width=1)),
                             hovertemplate="%{y} after: %{x:.1f} h<extra></extra>"))
        cmp_key = input.bk_compare()
        if cmp_key != "none":
            src, level = cmp_key.split("_", 1)
            col = "intl_avg_2024" if src == "intl" else "y2024"
            ref = JP_HOURS[JP_HOURS.level == level].set_index("activity")[col]
            xs, ys = [], []
            for (k, lab, _, t), short in zip(ACTIVITIES, labs):
                if t and t in ref.index:
                    xs.append(ref[t]); ys.append(short)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=COMPARE[cmp_key],
                                     marker=dict(symbol="line-ns-open", size=22, color="#0b0b0b", line=dict(width=3)),
                                     hovertemplate="%{y}: %{x} h<extra>" + COMPARE[cmp_key] + "</extra>"))
        fig.update_layout(
            barmode="group", bargap=0.25, height=380, paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="Inter, system-ui, sans-serif", size=12, color="#52514e"),
            margin=dict(l=170, r=20, t=10, b=70), hovermode="closest",
            legend=dict(orientation="h", y=-0.15, x=0),
        )
        fig.update_xaxes(title="Hours per week", gridcolor="#e6e5e0", rangemode="tozero")
        fig.update_yaxes(autorange="reversed", showgrid=False)
        return fig

    @render.ui
    def bk_compare_note():
        if input.bk_compare() == "none":
            return None
        return ui.p(ui.tags.small(
            "Black ticks show TALIS 2024 hours for the three activities TALIS measures in the same way: teaching, lesson "
            "preparation and administrative work (source: NIER/MEXT TALIS 2024 key points, full-time teachers). Indonesia "
            "does not take part in TALIS, so this is a reference point, not a benchmark."), class_="source-note")

    @reactive.effect
    @reactive.event(input.bk_to_post)
    def _prefill():
        p = plan()
        top = sorted([e for e in p["eff"] if e[1] > 0], key=lambda e: -e[1])[:2]
        if top:
            ui.update_text_area("bk_action", value="; ".join(m["label"] for m, _ in top))
            ui.update_radio_buttons("bk_who", selected=WHO[top[0][0]["who"]])
        r = current_issue()
        if r is not None and r.check and not input.bk_check():
            ui.update_text("bk_check", value=r.check)
        ui.update_navset("bk_steps", selected="3 · Post our action")

    # ---- Step 3 --------------------------------------------------------------
    @render.ui
    def bk_post_issue():
        return ui.p(ui.tags.b("Issue or case: "), issue_label(input.bk_issue()),
                    ui.tags.small("  (change it in step 1)", class_="text-muted"))

    @render.ui
    def bk_post_hint():
        r = current_issue()
        if r is None:
            return None
        return ui.div(
            ui.tags.b("Ideas from the workbook for this issue"),
            ui.p(ui.tags.small("Teacher or team: ", r.teacher_move)),
            ui.p(ui.tags.small("School: ", r.school_move)),
            class_="bk-issue-card",
        )

    posted_text = reactive.value("")

    @render.ui
    def bk_submit_status():
        lp = last_post()
        if lp is None:
            return None
        ok, msg = lp
        status = ui.p(msg, class_="mt-2 " + ("text-success" if ok else "text-danger"))
        if not ok or not posted_text():
            return status
        return ui.div(
            status,
            ui.div(
                ui.tags.b("Share it with everyone · Bagikan ke semua: "),
                "copy your post and paste it into the Zoom chat.",
                ui.tags.textarea(posted_text(), id="bk_copy_text", rows=6, readonly=True,
                                 class_="form-control mt-2", style="font-size:.85rem"),
                ui.tags.button("Copy for Zoom chat · Salin", type="button", class_="btn btn-outline-primary btn-sm mt-2",
                               onclick=COPY_JS),
                class_="prompt-box",
            ),
        )

    @reactive.effect
    @reactive.event(input.bk_submit)
    async def _submit():
        themes = list(input.bk_themes() or [])
        action = (input.bk_action() or "").strip()
        check = (input.bk_check() or "").strip()
        if not action or not check or not themes:
            last_post.set((False, "Please add a BRiTE theme, one action and a one-week check · "
                                  "Mohon isi tema, tindakan dan cek satu minggu."))
            return
        if len(themes) > 2:
            last_post.set((False, "Please choose at most two BRiTE themes · Pilih paling banyak dua tema."))
            return
        row = dict(
            room=input.bk_room(), level=input.bk_level(), issue=issue_label(input.bk_issue()),
            themes=", ".join(themes), action=action[:600], support=(input.bk_support() or "").strip()[:400],
            who=input.bk_who(), check=check[:300],
        )
        codes = ", ".join(t.split(" · ")[0] for t in themes)
        posted_text.set("\n".join(x for x in [
            f"Room {row['room']} · {row['level']} · {row['issue']}",
            f"Who needs to act: {WHO_SHORT[who_index(row['who'])]}",
            f"Try: {row['action']}",
            f"Support: {row['support']}" if row["support"] else "",
            f"Check in a week: {row['check']}",
            f"BRiTE: {codes}",
        ] if x))
        if not BOARD_URL:
            rows = [r for r in local_rows() if str(r["room"]) != str(row["room"])]
            rows.append(dict(row, time=datetime.now().isoformat(timespec="seconds")))
            local_rows.set(rows)
            last_post.set((True, f"Saved for Room {row['room']}. This version keeps posts in your own browser, so please share it in the Zoom chat."))
        else:
            params = dict(code=BOARD_CODE, op="add", room=row["room"], level=row["level"], issue=row["issue"],
                          themes=row["themes"], action_text=row["action"], support=row["support"],
                          who=row["who"], check=row["check"])
            try:
                res = await http_get_json(BOARD_URL + "?" + urllib.parse.urlencode(params))
                if res.get("ok"):
                    verb = "updated" if res.get("updated") else "posted"
                    last_post.set((True, f"Room {row['room']} {verb}. Terima kasih! Open step 4 to see the board."))
                else:
                    last_post.set((False, f"The board refused the post: {res.get('error', 'unknown error')}"))
                    return
            except Exception as e:  # network, CORS, bad URL
                last_post.set((False, f"Couldn't reach the board ({type(e).__name__}). Check the connection and try again."))
                return
        await refresh_board()

    # ---- Step 4 --------------------------------------------------------------
    async def refresh_board():
        if not BOARD_URL:
            board_rows.set(list(local_rows()))
            board_msg.set("This board shows your room's own post only. Share it in the Zoom chat so everyone can compare · Papan ini hanya menampilkan kiriman ruang Anda.")
            return
        try:
            res = await http_get_json(BOARD_URL + "?" + urllib.parse.urlencode(dict(code=BOARD_CODE, op="list")))
            if res.get("ok"):
                board_rows.set(res.get("rows", []))
                board_msg.set(f"Updated {datetime.now().strftime('%H:%M:%S')} · refreshes every {REFRESH_SECONDS} s")
            else:
                board_msg.set(f"Board error: {res.get('error', 'unknown')}")
        except Exception as e:
            board_msg.set(f"Couldn't reach the board ({type(e).__name__}). Retrying…")

    @reactive.effect
    async def _poll():
        input.bk_refresh()
        visible = input.nav() == "breakout" and input.bk_steps() == "4 · Class board"
        if not visible:
            return
        reactive.invalidate_later(REFRESH_SECONDS)
        with reactive.isolate():
            await refresh_board()

    @reactive.calc
    def filtered_rows():
        f = input.bk_filter()
        rows = board_rows()
        if f == "All":
            return rows
        return [r for r in rows if str(r.get("level", "")).startswith(f) or str(r.get("level", "")).startswith("Both")]

    @render.ui
    def bk_board_status():
        n = len(filtered_rows())
        return ui.p(ui.tags.small(f"{n} room post{'s' if n != 1 else ''} · {board_msg()}"), class_="text-muted")

    @render_widget
    def bk_board_plot():
        counts = [0, 0, 0, 0]
        for r in filtered_rows():
            counts[who_index(r.get("who", ""))] += 1
        fig = go.Figure()
        for i in range(4):
            fig.add_trace(go.Bar(x=[counts[i]], y=[""], orientation="h", name=WHO_SHORT[i],
                                 marker=dict(color=WHO_COL[i], line=dict(color="white", width=2)),
                                 text=[f"{WHO_SHORT[i]}: {counts[i]}" if counts[i] else ""],
                                 textposition="inside", insidetextanchor="middle", textfont=dict(color="white"),
                                 hovertemplate=f"{WHO_SHORT[i]}: {counts[i]} rooms<extra></extra>"))
        fig.update_layout(barmode="stack", height=56, showlegend=False, paper_bgcolor="white", plot_bgcolor="white",
                          margin=dict(l=0, r=0, t=0, b=0), font=dict(family="Inter, system-ui, sans-serif", size=13))
        fig.update_xaxes(visible=False, range=[0, max(sum(counts), 1)])
        fig.update_yaxes(visible=False)
        return fig

    @render.ui
    def bk_board():
        cols = [[], [], [], []]
        for r in sorted(filtered_rows(), key=lambda r: str(r.get("room", "")).zfill(3)):
            i = who_index(r.get("who", ""))
            cols[i].append(ui.div(
                ui.div(f"Room {r.get('room', '?')} · {r.get('level', '')}", class_="bk-card-head"),
                ui.div(str(r.get("issue", "")), class_="bk-card-issue"),
                ui.p(ui.tags.b("Try: "), str(r.get("action", ""))),
                ui.p(ui.tags.b("Support: "), str(r.get("support", ""))) if r.get("support") else None,
                ui.p(ui.tags.b("Check in a week: "), str(r.get("check", ""))),
                ui.div(str(r.get("themes", "")), class_="bk-card-themes"),
                class_="bk-card", style=f"border-top:4px solid {WHO_COL[i]}",
            ))
        return ui.layout_columns(
            *[ui.div(ui.div(badge(i), f" {len(cols[i])}", class_="bk-col-head"),
                     *(cols[i] or [ui.p(ui.tags.small("No posts yet"), class_="text-muted px-1")]),
                     class_="bk-col") for i in range(4)],
            col_widths=[3, 3, 3, 3],
        )

    @render.download_button(filename=lambda: f"thursday_board_{datetime.now():%Y%m%d_%H%M}.csv")
    def bk_download():
        df = pd.DataFrame(board_rows())
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        yield buf.getvalue()
