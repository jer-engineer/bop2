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
        div[data-testid="stSelectbox"] label { font-weight: 700; font-size: 0.9rem; }

        /* Weld card */
        .weld-card {
            background: #1e2130;
            border: 1px solid #3a3f55;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.6rem;
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

# ── Load data ────────────────────────────────────────────────────────────────
st.title("🔧 Welding Log")

uploaded = st.file_uploader("Ανέβασε Excel αρχείο (προαιρετικό)", type=["xlsx", "xls"])

@st.cache_data(show_spinner="Φόρτωση δεδομένων…")
def load_excel(source) -> pd.DataFrame:
    df = pd.read_excel(source, header=HEADER_ROW, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.fillna("")
    cols = [c for c in DISPLAY_COLS if c in df.columns]
    return df[cols]

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

filtered = df.copy()
if f_system != "Όλα" and "SYSTEM"  in filtered.columns:
    filtered = filtered[filtered["SYSTEM"]  == f_system]
if f_line   != "Όλα" and "LINE No" in filtered.columns:
    filtered = filtered[filtered["LINE No"] == f_line]
if f_weld   != "Όλα" and "Weld No" in filtered.columns:
    filtered = filtered[filtered["Weld No"] == f_weld]

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

if count > 0:
    for _, row in filtered.iterrows():
        system  = row.get("SYSTEM",  "")
        line    = row.get("LINE No", "")
        weld    = row.get("Weld No", "")
        wps     = row.get("WPS",     "")
        preheat = row.get("Preheat", "")
        pwht    = row.get("PWHT",    "")

        ndt_badges = ""
        for col in NDT_COLS:
            val = row.get(col, "")
            cls = ndt_class(val)
            display = val if val.strip() else "—"
            ndt_badges += f'<span class="badge {cls}"><span>{col}:</span> {display}</span>'

        extra_badges = (
            f'<span class="badge"><span>Preheat:</span> {preheat or "—"}</span>'
            f'<span class="badge"><span>PWHT:</span> {pwht or "—"}</span>'
        )

        st.markdown(
            f"""
            <div class="weld-card">
                <div class="card-header">
                    {system} &nbsp;›&nbsp; {line} &nbsp;›&nbsp; 🔩 {weld}
                </div>
                <div class="badge-row">
                    <span class="badge highlight"><span>WPS:</span> {wps or "—"}</span>
                    {ndt_badges}
                    {extra_badges}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
