"""Sales Analyzer tool — top-selling glasses per eshop, split by Eyeglasses/Sunglasses."""
import streamlit as st
import pandas as pd
import re
import csv
import io


# Eshop ID → display name
ESHOP_NAMES = {
    "36": "Čočky-online.cz",
    "38": "Ihre-kontaktlinsen.de",
    "47": "Lentes-de-contacto.es",
    "15": "Leshti.bg",
    "116": "Mataki.gr",
}

MONTH_NAMES = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}


@st.cache_data
def load_sales_csv(file_bytes: bytes) -> pd.DataFrame:
    """Load the sales CSV. The file uses ; separator and may have extra trailing
    fields per row, so we parse manually and truncate to the header length."""
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    header = next(reader)
    n = len(header)
    rows = [row[:n] + [""] * (n - len(row)) for row in reader]
    df = pd.DataFrame(rows, columns=header)
    return df


def extract_type(name: str) -> str | None:
    """Detect Eyeglasses or Sunglasses inside the parentheses at the end of the name."""
    if not isinstance(name, str):
        return None
    m = re.search(r"\((Eyeglasses|Sunglasses)\b", name, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).capitalize()


def format_months(months: list[str]) -> str:
    """Format a list of month numbers ('04', '03') into 'April' or 'March AND April'."""
    valid = sorted({m for m in months if m and m in MONTH_NAMES})
    names = [MONTH_NAMES[m] for m in valid]
    if not names:
        return "Unknown month"
    if len(names) == 1:
        return f"Data from {names[0]}"
    return f"Data from {' AND '.join(names)}"


def render():
    st.markdown("### 🕶️ Sales Analyzer")
    st.caption(
        "Upload the sells export to see top-selling **Eyeglasses** and **Sunglasses** "
        "per eshop in the given date range."
    )

    with st.sidebar:
        st.markdown("#### Upload File")
        uploaded = st.file_uploader(
            "Sales CSV export",
            type=["csv"],
            key="sales_csv",
            help="Semicolon-separated CSV with columns including ref_projects, orderMonth, commonName.",
        )

        st.markdown("#### Options")
        top_n = st.slider("Top N items per category", min_value=5, max_value=50, value=10, step=5)
        exclude_cancelled = st.checkbox(
            "Exclude cancelled orders",
            value=True,
            help="Skip rows where orderstatecancel = 1.",
        )

    if not uploaded:
        st.info("⬅ Upload a sales CSV in the sidebar to begin.")
        return

    # Load
    df = load_sales_csv(uploaded.getvalue())

    required = {"ref_projects", "orderMonth", "commonName"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"CSV is missing required columns: {', '.join(missing)}")
        return

    # Optional cancellation filter
    if exclude_cancelled and "orderstatecancel" in df.columns:
        before = len(df)
        df = df[df["orderstatecancel"].fillna("0") != "1"]
        st.caption(f"Excluded {before - len(df)} cancelled orders.")

    # Detect type
    df["type"] = df["commonName"].apply(extract_type)
    df_typed = df[df["type"].isin(["Eyeglasses", "Sunglasses"])].copy()

    # Normalize month column
    df_typed["orderMonth"] = df_typed["orderMonth"].fillna("").astype(str).str.zfill(2)

    months_in_data = sorted({m for m in df_typed["orderMonth"].unique() if m in MONTH_NAMES})
    full_label = format_months(months_in_data)

    # Top-line month banner (shows ALL months in the file)
    st.info(f"📅 {full_label}")

    # Month filter — only show when there are 2+ months
    if len(months_in_data) > 1:
        month_options = [MONTH_NAMES[m] for m in months_in_data]
        # Default to the latest month (most recent = "last month" they typically want)
        default_month = [month_options[-1]]
        selected_month_names = st.multiselect(
            "🗓 Filter by month",
            month_options,
            default=default_month,
            help="Pick one or more months to analyze. Defaults to the latest month.",
        )
        if not selected_month_names:
            st.info("Select at least one month above.")
            return
        # Map back to month numbers
        name_to_num = {v: k for k, v in MONTH_NAMES.items()}
        selected_months = [name_to_num[n] for n in selected_month_names]
        df_typed = df_typed[df_typed["orderMonth"].isin(selected_months)].copy()
        st.caption(f"Showing data for: **{format_months(selected_months).replace('Data from ', '')}** "
                   f"({len(df_typed):,} glasses orders)")

    cols = st.columns(4)
    cols[0].metric("Total orders", f"{len(df):,}")
    cols[1].metric("Glasses orders", f"{len(df_typed):,}")
    cols[2].metric("Eyeglasses", f"{(df_typed['type']=='Eyeglasses').sum():,}")
    cols[3].metric("Sunglasses", f"{(df_typed['type']=='Sunglasses').sum():,}")

    st.divider()

    # Eshop selector
    available_ids = [eid for eid in ESHOP_NAMES if eid in df_typed["ref_projects"].unique()]
    if not available_ids:
        st.warning("No data found for any of the known eshop IDs (36, 38, 47, 15, 116).")
        return

    eshop_options = [f"{ESHOP_NAMES[eid]} (ID {eid})" for eid in available_ids]
    selected_labels = st.multiselect(
        "Select eshops to analyze",
        eshop_options,
        default=eshop_options,
    )
    selected_ids = [
        available_ids[i] for i, label in enumerate(eshop_options) if label in selected_labels
    ]

    if not selected_ids:
        st.info("Select at least one eshop above.")
        return

    # Per-eshop tabs
    tab_labels = [ESHOP_NAMES[eid] for eid in selected_ids]
    tabs = st.tabs(tab_labels)

    for tab, eid in zip(tabs, selected_ids):
        with tab:
            sub = df_typed[df_typed["ref_projects"] == eid]
            shop_name = ESHOP_NAMES[eid]

            st.markdown(f"#### {shop_name}")
            sub_months = sub["orderMonth"].dropna().astype(str).str.zfill(2).tolist()
            st.caption(f"{format_months(sub_months)} • {len(sub)} glasses orders")

            if sub.empty:
                st.info("No glasses orders for this eshop.")
                continue

            col_l, col_r = st.columns(2)

            for col, type_name, emoji in [
                (col_l, "Eyeglasses", "👓"),
                (col_r, "Sunglasses", "🕶️"),
            ]:
                with col:
                    st.markdown(f"**{emoji} Top {type_name}**")
                    type_sub = sub[sub["type"] == type_name]
                    if type_sub.empty:
                        st.caption(f"No {type_name.lower()} sold.")
                        continue

                    counts = (
                        type_sub.groupby("commonName")
                        .size()
                        .reset_index(name="Sold")
                        .sort_values("Sold", ascending=False)
                        .head(top_n)
                        .reset_index(drop=True)
                    )
                    counts.index = counts.index + 1
                    counts.columns = ["Product", "Sold"]
                    st.dataframe(counts, use_container_width=True, height=min(400, 50 + 35 * len(counts)))

            # Combined download
            combined = (
                sub.groupby(["type", "commonName"])
                .size()
                .reset_index(name="Sold")
                .sort_values(["type", "Sold"], ascending=[True, False])
            )
            csv_bytes = combined.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"⬇ Download full ranking for {shop_name}",
                data=csv_bytes,
                file_name=f"top_sales_{shop_name}.csv",
                mime="text/csv",
                key=f"dl_{eid}",
            )
