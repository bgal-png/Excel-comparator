"""Tool Hub — a collection of internal tools."""
import streamlit as st

from tools import comparator, sales_analyzer


st.set_page_config(
    page_title="Tool Hub",
    page_icon="🧰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Custom CSS for a friendlier look ---
st.markdown(
    """
    <style>
        /* Tighten top spacing */
        .block-container { padding-top: 2rem; }

        /* Sidebar header */
        section[data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, #4F46E5 0%, #6366F1 100%);
        }
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2,
        section[data-testid="stSidebar"] .stMarkdown h3,
        section[data-testid="stSidebar"] .stMarkdown h4,
        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] label {
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"] .stRadio label {
            color: #FFFFFF !important;
        }

        /* Tool cards in sidebar */
        .tool-card {
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.20);
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 8px;
            color: #FFFFFF;
        }

        /* Header banner */
        .hub-banner {
            background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
            color: white;
            padding: 18px 24px;
            border-radius: 10px;
            margin-bottom: 18px;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.25);
        }
        .hub-banner h1 {
            margin: 0;
            font-size: 1.6rem;
            color: white;
        }
        .hub-banner p {
            margin: 4px 0 0 0;
            opacity: 0.9;
            font-size: 0.95rem;
        }

        /* Metric cards */
        div[data-testid="stMetric"] {
            background: #F9FAFB;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
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
    st.markdown("# 🧰 Tool Hub")
    st.markdown("---")
    st.markdown("#### Select a tool")
    selected = st.radio(
        "Tool",
        list(TOOLS.keys()),
        label_visibility="collapsed",
    )
    st.markdown(
        f"<div class='tool-card'><small>{TOOLS[selected]['desc']}</small></div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")


# --- Header banner ---
st.markdown(
    f"""
    <div class='hub-banner'>
        <h1>{selected}</h1>
        <p>{TOOLS[selected]['desc']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- Render selected tool ---
TOOLS[selected]["module"].render()
