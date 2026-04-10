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
        "added": "background-color: #d4edda",
        "removed": "background-color: #f8d7da",
        "changed": "background-color: #fff3cd",
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

names_a = set(sheets_a.keys())
names_b = set(sheets_b.keys())
shared = sorted(names_a & names_b)
only_a = sorted(names_a - names_b)
only_b = sorted(names_b - names_a)

# --- Sheet selection ---
st.subheader("Sheets")

if only_a:
    st.warning(f"Only in File A: {', '.join(only_a)}")
if only_b:
    st.warning(f"Only in File B: {', '.join(only_b)}")

if not shared:
    st.error("No sheets in common between the two files.")
    st.stop()

selected = st.multiselect("Select sheets to compare", shared, default=shared)

if not selected:
    st.info("Select at least one sheet to compare.")
    st.stop()

# --- Compare ---
all_stats = []

for sheet_name in selected:
    display_df, status_df, stats = compare_sheets(sheets_a[sheet_name], sheets_b[sheet_name])
    stats["Sheet"] = sheet_name
    stats["Total Cells"] = stats["Added"] + stats["Removed"] + stats["Changed"] + stats["Unchanged"]
    all_stats.append(stats)

    has_diff = stats["Added"] + stats["Removed"] + stats["Changed"]

    with st.expander(f"📄 {sheet_name} — {'⚠️ ' + str(has_diff) + ' differences' if has_diff else '✅ No differences'}", expanded=bool(has_diff)):
        if has_diff:
            # Legend
            cols = st.columns(3)
            cols[0].markdown(
                '<span style="background-color:#fff3cd;padding:2px 8px;border-radius:4px;">Changed</span>',
                unsafe_allow_html=True,
            )
            cols[1].markdown(
                '<span style="background-color:#d4edda;padding:2px 8px;border-radius:4px;">Added in B</span>',
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                '<span style="background-color:#f8d7da;padding:2px 8px;border-radius:4px;">Removed from A</span>',
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
