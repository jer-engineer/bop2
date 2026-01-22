import streamlit as st
import pandas as pd
import io
import os
import json 
# --- DEBUGGING ---
st.write("📂 Τρέχων φάκελος:", os.getcwd())
st.write("📂 Αρχεία σε αυτόν τον φάκελο:", os.listdir(os.getcwd()))
# -----------------

from datetime import datetime

# --- ΡΥΘΜΙΣΕΙΣ ΣΕΛΙΔΑΣ ---
st.set_page_config(page_title="Cloud Weld Manager Pro", layout="wide", page_icon="🏗️")

# --- DEFAULT CONSTANTS ---
# Εδώ ορίζουμε τα Defaults που ζήτησες
DEFAULT_LINE_COL = "LINE No"
DEFAULT_WELD_COL = "Weld No"
DEFAULT_REF_COLS = ["TYPE 1", "TYPE 2", "SYSTEM"] # <--- ΤΑ ΝΕΑ DEFAULTS
REPO_MASTER_FILE = "bop.xlsx"
# --- 0. ΛΕΙΤΟΥΡΓΙΕΣ ΑΠΟΘΗΚΕΥΣΗΣ (PERSISTENCE) ---
SETTINGS_FILE = "settings.json"

def load_settings():
    """Φορτώνει τις ρυθμίσεις από το αρχείο αν υπάρχει."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_settings_to_file():
    """Αποθηκεύει τις τρέχουσες μεταβλητές session σε αρχείο JSON."""
    settings = {
        "col_line_name": st.session_state.col_line_name,
        "col_weld_name": st.session_state.col_weld_name,
        "auto_fill_columns": st.session_state.auto_fill_columns,
        "production_ref_columns": st.session_state.production_ref_columns,
        "custom_free_columns": st.session_state.custom_free_columns
    }
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

# Φόρτωση ρυθμίσεων κατά την εκκίνηση
saved_config = load_settings()

# --- 1. SESSION STATE (Μνήμη) ---
if 'master_df' not in st.session_state:
    st.session_state.master_df = None
if 'production_log' not in st.session_state:
    st.session_state.production_log = pd.DataFrame() 
if 'master_source' not in st.session_state:
    st.session_state.master_source = "None" # Για να ξέρουμε από πού φορτώθηκε

# --- AUTO-LOAD MASTER FROM REPO/GITHUB ---
# Αυτό το κομμάτι τρέχει μία φορά στην αρχή. Ψάχνει το master.xlsx
if st.session_state.master_df is None:
    if os.path.exists(REPO_MASTER_FILE):
        try:
            # Προσπάθεια αυτόματης φόρτωσης
            df_auto = pd.read_excel(REPO_MASTER_FILE)
            # Καθαρισμός ονομάτων στηλών
            df_auto.columns = df_auto.columns.astype(str).str.strip()
            st.session_state.master_df = df_auto
            st.session_state.master_source = "Auto-Repo"
        except Exception as e:
            print(f"Failed to auto-load: {e}")

# --- INITIALIZE VARIABLES WITH SAVED OR DEFAULT VALUES ---
if 'col_line_name' not in st.session_state:
    st.session_state.col_line_name = saved_config.get("col_line_name", DEFAULT_LINE_COL)

if 'col_weld_name' not in st.session_state:
    st.session_state.col_weld_name = saved_config.get("col_weld_name", DEFAULT_WELD_COL)

if 'auto_fill_columns' not in st.session_state:
    st.session_state.auto_fill_columns = saved_config.get("auto_fill_columns", [])

if 'production_ref_columns' not in st.session_state:
    # Εδώ βάζουμε τα Default που ζήτησες (TYPE 1, TYPE 2, SYSTEM)
    st.session_state.production_ref_columns = saved_config.get("production_ref_columns", DEFAULT_REF_COLS)

if 'custom_free_columns' not in st.session_state:
    st.session_state.custom_free_columns = saved_config.get("custom_free_columns", [])


# --- 2. SIDEBAR MENU ---
with st.sidebar:
    st.title("🎛️ Μενού")
    app_mode = st.radio("Επίλεξε Λειτουργία:", 
                        ["🔨 Daily Production", 
                         "ℹ️ Weld Info / WPS", 
                         "⚙️ Settings & Setup"])
    st.divider()
    
    # Ένδειξη Status Master File
    if st.session_state.master_df is not None:
        st.success(f"Master: Loaded ({st.session_state.master_source})")
        st.caption(f"Lines: {len(st.session_state.master_df)}")
    else:
        st.warning("Master: Not Loaded")
        
    st.divider()
    if st.button("💾 Force Save Settings"):
        save_settings_to_file()
        st.toast("Settings saved to disk!", icon="💾")


# --- 3. ΛΕΙΤΟΥΡΓΙΑ: DAILY PRODUCTION ---
if app_mode == "🔨 Daily Production":
    st.header("🔨 Καταγραφή Παραγωγής")
    
    if st.session_state.master_df is None:
        st.warning(f"⚠️ Δεν βρέθηκε '{REPO_MASTER_FILE}' στο φάκελο και δεν έχει φορτωθεί χειροκίνητα.")
        st.info("Πήγαινε στα Settings για Upload ή βεβαιώσου ότι το αρχείο υπάρχει στο GitHub repo.")
        master = pd.DataFrame()
        lines = []
        LINE_COL = st.session_state.col_line_name
        WELD_COL = st.session_state.col_weld_name
    else:
        master = st.session_state.master_df
        LINE_COL = st.session_state.col_line_name
        WELD_COL = st.session_state.col_weld_name
        lines = sorted(master[LINE_COL].astype(str).unique()) if LINE_COL in master.columns else []

    # --- 1. SELECTION ---
    c_sel1, c_sel2 = st.columns(2)
    
    if st.session_state.master_df is not None:
        sel_line = c_sel1.selectbox("Line No", lines, index=None, placeholder="Search Line...")
        
        avail_welds = []
        if sel_line and WELD_COL in master.columns:
            avail_welds = sorted(master[master[LINE_COL] == sel_line][WELD_COL].astype(str).unique())
        sel_weld = c_sel2.selectbox("Weld No", avail_welds, index=None, placeholder="Select Weld...")
    else:
        sel_line = c_sel1.text_input("Line No (Manual)")
        sel_weld = c_sel2.text_input("Weld No (Manual)")

    # --- 2. LIVE INFO PANEL ---
    if st.session_state.master_df is not None and sel_line and sel_weld:
        # Χρήση των (πλέον default) στηλών
        valid_ref_cols = [col for col in st.session_state.production_ref_columns if col in master.columns]
        
        if valid_ref_cols:
            row = master[(master[LINE_COL] == sel_line) & (master[WELD_COL] == sel_weld)]
            if not row.empty:
                st.info("ℹ️ Στοιχεία Κόλλησης (Από Master)")
                ref_data = row[valid_ref_cols].iloc[0].to_dict()
                
                cols = st.columns(len(ref_data))
                for idx, (k, v) in enumerate(ref_data.items()):
                    cols[idx % len(cols)].metric(label=k, value=str(v))
    
    st.divider()

    # --- 3. INPUT FORM ---
    with st.form("entry_form"):
        st.subheader("Στοιχεία Καταχώρησης")
        
        row1_c1, row1_c2, row1_c3 = st.columns(3)
        date_val = row1_c1.date_input("Date")
        res = row1_c2.selectbox("Result", ["Accepted", "Rejected", "Pending"])
        welder = row1_c3.text_input("WELDER", value="User")
        
        row2_c1, row2_c2, row2_c3 = st.columns(3)
        type1_val = row2_c1.text_input("HEAT NO TYPE 1")
        type2_val = row2_c2.text_input("HEAT NO TYPE 2")
        concumable_val = row2_c3.text_input("Filler / Consumable")

        # Custom Fields
        custom_values = {}
        if st.session_state.custom_free_columns:
            st.write("📝 Extra Fields")
            c_cols = st.columns(len(st.session_state.custom_free_columns))
            for idx, col_name in enumerate(st.session_state.custom_free_columns):
                custom_values[col_name] = c_cols[idx % 3].text_input(col_name)

        submitted = st.form_submit_button("➕ Προσθήκη Εγγραφής", type="primary")
        
        if submitted:
            if sel_line and sel_weld:
                formatted_date = date_val.strftime("%d/%m/%Y")

                new_entry = {
                    "Date": formatted_date,
                    "Line No": sel_line,
                    "Weld No": sel_weld,
                    "HEAT NO TYPE 1": type1_val,
                    "HEAT NO TYPE 2": type2_val,
                    "WELDER": welder,
                    "Filler": concumable_val,
                    "Result": res
                }
                
                if st.session_state.master_df is not None and st.session_state.auto_fill_columns:
                    row = master[(master[LINE_COL] == sel_line) & (master[WELD_COL] == sel_weld)]
                    if not row.empty:
                        for auto_col in st.session_state.auto_fill_columns:
                            if auto_col in row:
                                new_entry[auto_col] = row[auto_col].values[0]
                
                new_entry.update(custom_values)
                
                st.session_state.production_log = pd.concat(
                    [st.session_state.production_log, pd.DataFrame([new_entry])], 
                    ignore_index=True
                )
                st.success("Καταχωρήθηκε!")
                st.rerun()
            else:
                st.error("Πρέπει να επιλέξεις Line και Weld!")

    # --- 4. LOG (EDITABLE) ---
    st.divider()
    st.subheader("📋 Log Ημέρας (Επεξεργάσιμο)")
    
    if not st.session_state.production_log.empty:
        edited_log = st.data_editor(
            st.session_state.production_log,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_log"
        )
        
        if not edited_log.equals(st.session_state.production_log):
            st.session_state.production_log = edited_log
            st.rerun()
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            st.session_state.production_log.to_excel(writer, index=False)
        st.download_button("📥 Download Excel", buffer.getvalue(), "daily_production.xlsx")
    else:
        st.info("Δεν υπάρχουν εγγραφές ακόμα.")


# --- 4. ΛΕΙΤΟΥΡΓΙΑ: INFO TAB ---
elif app_mode == "ℹ️ Weld Info / WPS":
    st.header("ℹ️ Αναζήτηση Πληροφοριών")
    
    if st.session_state.master_df is None:
        st.error("Δεν έχει φορτωθεί Master Excel.")
    else:
        master = st.session_state.master_df
        LINE_COL = st.session_state.col_line_name
        WELD_COL = st.session_state.col_weld_name
        
        c1, c2 = st.columns([1, 2])
        lines = sorted(master[LINE_COL].astype(str).unique()) if LINE_COL in master.columns else []
        s_line = c1.selectbox("Line", lines, index=None)
        
        s_weld = None
        if s_line:
            wlist = sorted(master[master[LINE_COL] == s_line][WELD_COL].astype(str).unique())
            s_weld = c1.selectbox("Weld", wlist, index=None)
            
        if s_line and s_weld:
            row = master[(master[LINE_COL] == s_line) & (master[WELD_COL] == s_weld)]
            if not row.empty:
                st.table(row.T)


# --- 5. ΛΕΙΤΟΥΡΓΙΑ: SETTINGS ---
elif app_mode == "⚙️ Settings & Setup":
    st.header("⚙️ Ρυθμίσεις Εφαρμογής")
    
    # --- A. HEADER & UPLOAD ---
    with st.expander("1. Διαχείριση Master Excel", expanded=True):
        
        # ΕΝΔΕΙΞΗ ΑΥΤΟΜΑΤΗΣ ΦΟΡΤΩΣΗΣ
        if st.session_state.master_df is not None and st.session_state.master_source == "Auto-Repo":
            st.success(f"✅ Master loaded automatically from: {REPO_MASTER_FILE}")
            st.caption("Μπορείς να ανεβάσεις νέο αρχείο παρακάτω για να το αντικαταστήσεις προσωρινά.")
        
        col_row, col_upload = st.columns([1, 2])
        with col_row:
            header_row_val = st.number_input("Γραμμή Τίτλων:", min_value=1, value=1)
        with col_upload:
            uploaded_master = st.file_uploader("Upload Manual Excel (Overrides Auto-load)", type=["xlsx"])
        
        if uploaded_master:
            try:
                df = pd.read_excel(uploaded_master, header=header_row_val - 1)
                df.columns = df.columns.astype(str).str.strip()
                st.session_state.master_df = df
                st.session_state.master_source = "Manual-Upload"
                st.success(f"✅ Manual Master Loaded! ({len(df)} lines)")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- B. MAPPING ---
    if st.session_state.master_df is not None:
        with st.expander("2. Αντιστοίχιση Βασικών Στηλών (Mapping)", expanded=True):
            all_cols = list(st.session_state.master_df.columns)
            c1, c2 = st.columns(2)
            
            def_line_idx = all_cols.index(st.session_state.col_line_name) if st.session_state.col_line_name in all_cols else 0
            def_weld_idx = all_cols.index(st.session_state.col_weld_name) if st.session_state.col_weld_name in all_cols else 0

            sel_line_col = c1.selectbox("Στήλη LINE NO:", all_cols, index=def_line_idx)
            sel_weld_col = c2.selectbox("Στήλη WELD NO:", all_cols, index=def_weld_idx)
            
            if st.button("💾 Επιβεβαίωση Mapping", type="primary"):
                st.session_state.col_line_name = sel_line_col
                st.session_state.col_weld_name = sel_weld_col
                save_settings_to_file()
                st.toast("Mapping Saved!", icon="✅")

        # --- C. ADVANCED SETTINGS ---
        st.divider()
        st.subheader("🛠️ Διαμόρφωση Log Παραγωγής")
        
        tab1, tab2, tab3 = st.tabs(["Auto-Fill Data", "Reference Info", "Custom Fields"])
        
        with tab1:
            st.info("Ποιες στήλες του Master να αντιγράφονται στο Log;")
            valid_defaults = [c for c in st.session_state.auto_fill_columns if c in all_cols]
            # key="ms_auto_fill" για αποφυγή duplicate ID error
            sel_auto = st.multiselect("Επίλεξε στήλες:", all_cols, default=valid_defaults, key="ms_auto_fill")
            if st.button("💾 Save Auto-Fill"):
                st.session_state.auto_fill_columns = sel_auto
                save_settings_to_file()
                st.toast("Auto-fill saved!")

        with tab2:
            st.info("Ποιες στήλες να φαίνονται στο μπλε πλαίσιο πληροφοριών (Live Panel);")
            valid_defaults_ref = [c for c in st.session_state.production_ref_columns if c in all_cols]
            # key="ms_ref_cols" για αποφυγή duplicate ID error
            sel_ref = st.multiselect("Επίλεξε στήλες:", all_cols, default=valid_defaults_ref, key="ms_ref_cols")
            if st.button("💾 Save Reference"):
                st.session_state.production_ref_columns = sel_ref
                save_settings_to_file()
                st.toast("Reference saved!")

        with tab3:
            st.info("Επιπλέον στήλες (πέρα από HEAT NO, Filler, κλπ).")
            current_custom = ", ".join(st.session_state.custom_free_columns)
            custom_input = st.text_area("Ονόματα στηλών με κόμμα:", value=current_custom)
            if st.button("💾 Save Custom Fields"):
                new_list = [x.strip() for x in custom_input.split(",") if x.strip()]
                st.session_state.custom_free_columns = new_list
                save_settings_to_file()
                st.toast(f"Saved custom fields!")

    elif st.session_state.master_df is None:
         st.warning("⚠️ Waiting for Master Excel...")

# --- AUTO-RUN ---
if __name__ == '__main__':
    import sys
    import subprocess
    if not os.environ.get("STREAMLIT_RUNNING"):
        env = os.environ.copy()
        env["STREAMLIT_RUNNING"] = "true"
        file_path = os.path.abspath(__file__)
        subprocess.run([sys.executable, "-m", "streamlit", "run", file_path], env=env)
