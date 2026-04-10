import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Excel Comparator", page_icon="📊", layout="wide")
st.title("Excel Comparator")
st.caption("Upload two Excel files to compare them cell-by-cell across all sheets.")


@st.cache_data
def load_excel(uploaded_file):
    """Load all sheets from an Excel file as string DataFrames."""
    sheets = pd.read_excel(
        uploaded_file, sheet_name=None, dtype=str, engine="openpyxl", header=0
    )
    # Replace NaN with empty string for clean comparison
    return {name: df.fillna("") for name, df in sheets.items()}


def compare_sheets(df_a: pd.DataFrame, df_b: pd.DataFrame):
    """Compare two DataFrames cell-by-cell. Returns (display_df, status_df, stats)."""
    # Build common shape
    all_cols = df_a.columns.union(df_b.columns)
    max_rows = max(len(df_a), len(df_b))
    idx = range(max_rows)

    a = df_a.reindex(index=idx, columns=all_cols, fill_value="")
    b = df_b.reindex(index=idx, columns=all_cols, fill_value="")

    # Determine status for each cell
    a_empty = a == ""
    b_empty = b == ""
    same = a == b

    status = pd.DataFrame("unchanged", index=idx, columns=all_cols)
    status[~a_empty & b_empty] = "removed"
    status[a_empty & ~b_empty] = "added"
    status[~same & ~a_empty & ~b_empty] = "changed"

    # Build display values
    display = b.copy()
    mask_changed = status == "changed"
    mask_removed = status == "removed"

    for col in all_cols:
        for row in idx:
            if mask_changed.at[row, col]:
                display.at[row, col] = f"{a.at[row, col]} → {b.at[row, col]}"
            elif mask_removed.at[row, col]:
                display.at[row, col] = a.at[row, col]

    stats = {
        "Added": int((status == "added").sum().sum()),
        "Removed": int((status == "removed").sum().sum()),
        "Changed": int((status == "changed").sum().sum()),
        "Unchanged": int((status == "unchanged").sum().sum()),
    }

    return display, status, stats


def style_dataframe(display_df, status_df):
    """Apply color styling based on the status matrix."""
    color_map = {
        "added": "background-color: #d4edda; color: black",
        "removed": "background-color: #f8d7da; color: black",
        "changed": "background-color: #fff3cd; color: black",
        "unchanged": "",
    }

    def apply_colors(val):
        # This gets called element-wise; we need the status for the same position
        return ""

    # Build a styles DataFrame matching status
    styles = status_df.map(lambda v: color_map.get(v, ""))
    return display_df.style.apply(lambda _: styles, axis=None)


# --- Sidebar: File uploads ---
with st.sidebar:
    st.header("Upload Files")
    file_a = st.file_uploader(
        "File A (original)", type=["xlsx", "xls"], key="file_a"
    )
    file_b = st.file_uploader(
        "File B (updated)", type=["xlsx", "xls"], key="file_b"
    )

if not file_a or not file_b:
    st.info("Upload two Excel files in the sidebar to begin.")
    st.stop()

# --- Load files ---
sheets_a = load_excel(file_a)
sheets_b = load_excel(file_b)

names_a = list(sheets_a.keys())
names_b = list(sheets_b.keys())
shared = sorted(set(names_a) & set(names_b))

# --- Sheet pairing ---
st.subheader("Sheet Pairing")

# Auto-pair sheets with matching names, then let user manually pair the rest
pairs = []

if shared:
    st.markdown("**Auto-matched sheets** (same name in both files):")
    auto_selected = st.multiselect("Select auto-matched sheets", shared, default=shared)
    for name in auto_selected:
        pairs.append((name, name, name))

# Manual pairing for unmatched or additional comparisons
unmatched_a = [n for n in names_a if n not in shared]
unmatched_b = [n for n in names_b if n not in shared]

st.markdown("**Manual pairing** — compare sheets with different names:")
num_manual = st.number_input("Number of manual pairs", min_value=0, max_value=min(len(names_a), len(names_b)), value=min(1, len(unmatched_a), len(unmatched_b)) if (unmatched_a and unmatched_b) else 0, step=1)

for i in range(int(num_manual)):
    col1, col2 = st.columns(2)
    default_a = unmatched_a[i] if i < len(unmatched_a) else names_a[0]
    default_b = unmatched_b[i] if i < len(unmatched_b) else names_b[0]
    with col1:
        sheet_a = st.selectbox(f"File A sheet (pair {i+1})", names_a, index=names_a.index(default_a), key=f"manual_a_{i}")
    with col2:
        sheet_b = st.selectbox(f"File B sheet (pair {i+1})", names_b, index=names_b.index(default_b), key=f"manual_b_{i}")
    pairs.append((f"{sheet_a} ↔ {sheet_b}", sheet_a, sheet_b))

if not pairs:
    st.info("No sheet pairs to compare. Use auto-matched or manual pairing above.")
    st.stop()

# --- Compare ---
all_stats = []

for label, sheet_name_a, sheet_name_b in pairs:
    display_df, status_df, stats = compare_sheets(sheets_a[sheet_name_a], sheets_b[sheet_name_b])
    stats["Sheet"] = label
    stats["Total Cells"] = stats["Added"] + stats["Removed"] + stats["Changed"] + stats["Unchanged"]
    all_stats.append(stats)

    has_diff = stats["Added"] + stats["Removed"] + stats["Changed"]

    with st.expander(f"📄 {label} — {'⚠️ ' + str(has_diff) + ' differences' if has_diff else '✅ No differences'}", expanded=bool(has_diff)):
        if has_diff:
            # Legend
            cols = st.columns(3)
            cols[0].markdown(
                '<span style="background-color:#fff3cd;color:black;padding:2px 8px;border-radius:4px;">Changed</span>',
                unsafe_allow_html=True,
            )
            cols[1].markdown(
                '<span style="background-color:#d4edda;color:black;padding:2px 8px;border-radius:4px;">Added in B</span>',
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                '<span style="background-color:#f8d7da;color:black;padding:2px 8px;border-radius:4px;">Removed from A</span>',
                unsafe_allow_html=True,
            )

            styled = style_dataframe(display_df, status_df)
            st.dataframe(styled, use_container_width=True, height=500)
        else:
            st.success("Sheets are identical.")

# --- Summary Report ---
st.divider()
st.subheader("Summary Report")

summary_df = pd.DataFrame(all_stats)[["Sheet", "Added", "Removed", "Changed", "Unchanged", "Total Cells"]]

total_added = summary_df["Added"].sum()
total_removed = summary_df["Removed"].sum()
total_changed = summary_df["Changed"].sum()
total_cells = summary_df["Total Cells"].sum()

cols = st.columns(4)
cols[0].metric("Total Added", f"{total_added:,}")
cols[1].metric("Total Removed", f"{total_removed:,}")
cols[2].metric("Total Changed", f"{total_changed:,}")
cols[3].metric("Total Cells Compared", f"{total_cells:,}")

st.dataframe(summary_df, use_container_width=True, hide_index=True)
