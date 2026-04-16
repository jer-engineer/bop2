import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Welding Log",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Mobile-friendly CSS ──────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        /* Compact padding for mobile */
        .block-container { padding: 0.75rem 0.6rem 2rem; max-width: 900px; }

        /* Filter labels */
        div[data-testid="stSelectbox"] label,
        div[data-testid="stTextInput"] label { font-weight: 700; font-size: 0.9rem; }

        /* Weld card */
        .weld-card {
            background: #1e2130;
            border: 1px solid #3a3f55;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.6rem;
        }
        .weld-card.welder-ok {
            background: #1f3a2a;
            border-color: #2f7a4e;
        }
        .weld-card.welder-missing {
            background: #4a341f;
            border-color: #b56b2c;
        }
        .weld-card .card-header {
            font-size: 1rem;
            font-weight: 700;
            color: #e8eaf6;
            margin-bottom: 0.4rem;
        }
        .weld-card .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 0.4rem;
        }
        .badge {
            background: #2e3450;
            border: 1px solid #4a5080;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.78rem;
            color: #cdd3f5;
        }
        .badge span { color: #7986cb; font-weight: 600; }
        .badge.highlight { border-color: #7986cb; background: #283060; }
        .badge.ok   { border-color: #4caf50; color: #a5d6a7; }
        .badge.warn { border-color: #ff9800; color: #ffcc80; }
        .badge.none { border-color: #555; color: #777; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ────────────────────────────────────────────────────────────────
DEFAULT_FILE = Path(__file__).parent / "welding_log.xlsx"
HEADER_ROW   = 9   # 0-based → row 10 in Excel
DISPLAY_COLS = ["SYSTEM", "LINE No", "Weld No", "WPS",
                "PT Scope", "MT Scope", "RT Scope", "UT Scope",
                "Preheat", "PWHT"]
NDT_COLS     = ["PT Scope", "MT Scope", "RT Scope", "UT Scope"]
JOINT_COLS   = [
    "Joint Type",
    "Shop (S) / Field (F)",
    "WELD INCHES",
    "THK",
    "Material",
    "SCH",
    "TYPE 1",
    "TYPE 2",
    "Preheat",
    "PWHT",
    "PAGE No.",
    "PAGE No",
]

# ── Load data ────────────────────────────────────────────────────────────────
st.title("🔧 Welding Log")

uploaded = st.file_uploader("Ανέβασε Excel αρχείο (προαιρετικό)", type=["xlsx", "xls"])

@st.cache_data(show_spinner="Φόρτωση δεδομένων…")
def load_excel(source) -> pd.DataFrame:
    df = pd.read_excel(source, header=HEADER_ROW, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.fillna("")
    return df

if uploaded is not None:
    df = load_excel(uploaded)
elif DEFAULT_FILE.exists():
    df = load_excel(str(DEFAULT_FILE))
else:
    st.warning(
        "Δεν βρέθηκε αρχείο. Βάλε ένα `welding_log.xlsx` στον ίδιο φάκελο "
        "ή ανέβασέ το παραπάνω."
    )
    st.stop()

# ── Helper: options list with "Όλα" ─────────────────────────────────────────
def opts(col: str) -> list:
    if col not in df.columns:
        return ["— (δεν υπάρχει στήλη) —"]
    return ["Όλα"] + sorted(df[col].unique().tolist())

# ── Filters (selectbox = built-in search-as-you-type) ───────────────────────
st.subheader("Φίλτρα")

c1, c2, c3 = st.columns(3)
with c1:
    f_system = st.selectbox("SYSTEM",  opts("SYSTEM"),  index=0)
with c2:
    f_line   = st.selectbox("LINE No", opts("LINE No"), index=0)
with c3:
    f_weld   = st.selectbox("Weld No", opts("Weld No"), index=0)

t1, t2, t3 = st.columns(3)
with t1:
    q_system = st.text_input("SYSTEM (text)", placeholder="γράψε για μερική αναζήτηση")
with t2:
    q_line = st.text_input("LINE No (text)", placeholder="γράψε για μερική αναζήτηση")
with t3:
    q_weld = st.text_input("Weld No (text)", placeholder="γράψε για μερική αναζήτηση")

filtered = df.copy()
if f_system != "Όλα" and "SYSTEM"  in filtered.columns:
    filtered = filtered[filtered["SYSTEM"]  == f_system]
if f_line   != "Όλα" and "LINE No" in filtered.columns:
    filtered = filtered[filtered["LINE No"] == f_line]
if f_weld   != "Όλα" and "Weld No" in filtered.columns:
    filtered = filtered[filtered["Weld No"] == f_weld]
if q_system.strip() and "SYSTEM" in filtered.columns:
    filtered = filtered[filtered["SYSTEM"].str.contains(q_system.strip(), case=False, na=False)]
if q_line.strip() and "LINE No" in filtered.columns:
    filtered = filtered[filtered["LINE No"].str.contains(q_line.strip(), case=False, na=False)]
if q_weld.strip() and "Weld No" in filtered.columns:
    filtered = filtered[filtered["Weld No"].str.contains(q_weld.strip(), case=False, na=False)]

st.divider()

# ── Results ──────────────────────────────────────────────────────────────────
count = len(filtered)
st.markdown(f"**{count}** εγγραφές βρέθηκαν")

def ndt_class(val: str) -> str:
    v = val.strip().upper()
    if v in ("", "-", "N/A", "NO"):
        return "none"
    if "%" in v or v.isdigit():
        return "ok"
    return "warn"


def first_existing_col(columns, candidates: list[str]) -> str | None:
    lower_map = {str(c).strip().lower(): c for c in columns}
    for cand in candidates:
        hit = lower_map.get(cand.lower())
        if hit is not None:
            return hit
    return None

def render_cards(
    data: pd.DataFrame,
    visible_cols: list[str],
    second_row_cols: list[str] | None = None,
    header_extra: list[str] | None = None,
    welder_bg: bool = False,
) -> None:
    selected_cols = [c for c in visible_cols if c in data.columns]
    key_cols = ["SYSTEM", "LINE No", "Weld No"]
    badge_cols = [c for c in selected_cols if c not in key_cols]
    second_row_set = set(second_row_cols or [])

    def build_badge(row: pd.Series, col: str) -> str:
        val = row.get(col, "")
        display = val if str(val).strip() else "—"

        if col == "WPS":
            cls = "highlight"
        elif col in NDT_COLS:
            cls = ndt_class(str(val))
        else:
            cls = ""

        class_attr = f"badge {cls}".strip()
        return f'<span class="{class_attr}"><span>{col}:</span> {display}</span>'

    for _, row in data.iterrows():
        system  = row.get("SYSTEM", "")
        line    = row.get("LINE No", "")
        weld    = row.get("Weld No", "")
        welder_val = row.get(first_existing_col(data.columns, ["WELDER", "Welder", "welder"]) or "", "")
        date_val = row.get(first_existing_col(data.columns, ["DATE", "Date", "date"]) or "", "")

        card_class = "weld-card"
        if welder_bg:
            card_class += " welder-ok" if str(welder_val).strip() else " welder-missing"

        header_parts = [f"{system or '—'} &nbsp;›&nbsp; {line or '—'} &nbsp;›&nbsp; 🔩 {weld or '—'}"]
        if header_extra:
            for col in header_extra:
                if col.upper() == "WELDER":
                    header_parts.append(f"<span class=\"badge\"><span>WELDER:</span> {welder_val or '—'}</span>")
                elif col.upper() == "DATE":
                    header_parts.append(f"<span class=\"badge\"><span>DATE:</span> {date_val or '—'}</span>")

        header_html = " &nbsp; ".join(header_parts)

        row1_cols = [c for c in badge_cols if c not in second_row_set]
        row2_cols = [c for c in badge_cols if c in second_row_set]
        badges_row1 = "".join(build_badge(row, col) for col in row1_cols)
        badges_row2 = "".join(build_badge(row, col) for col in row2_cols)
        row2_html = f'<div class="badge-row">{badges_row2}</div>' if badges_row2 else ""

        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="card-header">
                    {header_html}
                </div>
                <div class="badge-row">
                    {badges_row1}
                </div>
                {row2_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

if count > 0:
    tab1, tab2, tab3, tab4 = st.tabs([
        "Κύριες Στήλες",
        "Joint / Material",
        "Custom Στήλες",
        "Όλες οι Στήλες",
    ])

    with tab1:
        st.caption("Προβολή μόνο των βασικών στηλών welding")
        tab1_cols = DISPLAY_COLS + [
            "WELDER",
            "Date",
            "Joint Type",
            "Shop (S) / Field (F)",
            "WELD INCHES",
            "THK",
            "Material",
            "SCH",
            "TYPE 1",
            "TYPE 2",
        ]
        render_cards(
            filtered,
            tab1_cols,
            second_row_cols=[
                "WELDER",
                "Date",
                "Joint Type",
                "Shop (S) / Field (F)",
                "WELD INCHES",
                "THK",
                "Material",
                "SCH",
                "TYPE 1",
                "TYPE 2",
            ],
        )

    with tab2:
        st.caption("Joint Type / Shop-Field / Weld Inches / THK / Material / SCH / TYPE 1 / TYPE 2")
        render_cards(filtered, JOINT_COLS)

    with tab3:
        st.caption("Custom compact view με WELDER / DATE και status χρώμα")
        welder_col = first_existing_col(filtered.columns, ["WELDER", "Welder", "welder"])
        date_col = first_existing_col(filtered.columns, ["DATE", "Date", "date"])
        custom_options = [c for c in [welder_col, date_col] if c is not None]
        custom_cols = st.multiselect(
            "Στήλες για εμφάνιση",
            options=custom_options,
            default=custom_options,
            help="Dropdown με check (μόνο WELDER και DATE)",
        )

        if custom_options:
            render_cards(
                filtered,
                custom_cols,
                header_extra=["WELDER", "DATE"],
                welder_bg=True,
            )
        else:
            st.info("Δεν βρέθηκαν στήλες WELDER/DATE στο αρχείο.")

    with tab4:
        st.caption("Προβολή όλων των στηλών του αρχείου")
        render_cards(filtered, filtered.columns.tolist())

    # Download
    csv = filtered.reset_index(drop=True).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Κατέβασε ως CSV",
        data=csv,
        file_name="welding_log_filtered.csv",
        mime="text/csv",
    )
else:
    st.info("Δεν βρέθηκαν εγγραφές με τα επιλεγμένα φίλτρα.")
