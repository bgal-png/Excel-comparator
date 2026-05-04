"""Tool Hub — a collection of internal tools."""
import streamlit as st

from tools import comparator, sales_analyzer


st.set_page_config(
    page_title="Tool Hub",
    page_icon="🧰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Tool registry ---
TOOLS = {
    "📊 Excel Comparator": {
        "desc": "Compare two Excel files cell-by-cell across sheets.",
        "module": comparator,
    },
    "🕶️ Sales Analyzer": {
        "desc": "Top-selling glasses per eshop, split by Eyeglasses & Sunglasses.",
        "module": sales_analyzer,
    },
}


# --- Sidebar navigation ---
with st.sidebar:
    st.title("🧰 Tool Hub")
    st.caption("Internal utilities")
    st.divider()
    selected = st.radio("Choose a tool", list(TOOLS.keys()))
    st.caption(TOOLS[selected]["desc"])
    st.divider()


# --- Header ---
st.title(selected)
st.caption(TOOLS[selected]["desc"])
st.divider()


# --- Render selected tool ---
TOOLS[selected]["module"].render()
