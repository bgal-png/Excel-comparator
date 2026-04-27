"""Tool Hub — a collection of internal tools."""
import streamlit as st

from tools import comparator, sales_analyzer


st.set_page_config(
    page_title="Tool Hub",
    page_icon="🧰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Custom CSS: dark mode + custom layout ---
st.markdown(
    """
    <style>
        /* === Global background — subtle radial glow === */
        .stApp {
            background:
                radial-gradient(circle at 15% 0%, rgba(139, 92, 246, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 85% 100%, rgba(59, 130, 246, 0.10) 0%, transparent 40%),
                #0F172A;
        }

        /* === Hide default Streamlit chrome === */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* === Main content padding === */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        /* === Sidebar — dark with accent === */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1E1B4B 0%, #0F172A 100%);
            border-right: 1px solid rgba(139, 92, 246, 0.15);
        }
        section[data-testid="stSidebar"] * {
            color: #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] .stRadio > div {
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            padding: 6px;
        }
        section[data-testid="stSidebar"] .stRadio label {
            padding: 8px 12px;
            border-radius: 8px;
            transition: background 0.2s;
        }
        section[data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(139, 92, 246, 0.15);
        }

        /* === Hub header banner === */
        .hub-banner {
            background: linear-gradient(135deg, #6D28D9 0%, #4F46E5 50%, #2563EB 100%);
            color: white;
            padding: 28px 32px;
            border-radius: 16px;
            margin-bottom: 28px;
            box-shadow: 0 10px 40px rgba(109, 40, 217, 0.30);
            position: relative;
            overflow: hidden;
        }
        .hub-banner::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(255,255,255,0.10) 0%, transparent 70%);
            pointer-events: none;
        }
        .hub-banner h1 {
            margin: 0;
            font-size: 1.9rem;
            color: white;
            font-weight: 700;
            letter-spacing: -0.02em;
        }
        .hub-banner p {
            margin: 8px 0 0 0;
            opacity: 0.85;
            font-size: 1rem;
        }

        /* === Card container for tool body === */
        .tool-body {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid rgba(148, 163, 184, 0.1);
            border-radius: 14px;
            padding: 24px;
            backdrop-filter: blur(10px);
        }

        /* === Inputs / selects — softer dark === */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div, .stDateInput input {
            background: #1E293B !important;
            border: 1px solid rgba(148, 163, 184, 0.2) !important;
            color: #E2E8F0 !important;
        }

        /* === File uploader — custom look === */
        section[data-testid="stFileUploader"] {
            background: rgba(139, 92, 246, 0.05);
            border: 2px dashed rgba(139, 92, 246, 0.4);
            border-radius: 10px;
            padding: 8px;
        }

        /* === Buttons === */
        .stButton button, .stDownloadButton button {
            background: linear-gradient(90deg, #8B5CF6 0%, #6366F1 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            padding: 8px 18px;
            transition: transform 0.1s, box-shadow 0.2s;
        }
        .stButton button:hover, .stDownloadButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
        }

        /* === Metric cards === */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(139,92,246,0.08) 0%, rgba(59,130,246,0.05) 100%);
            border: 1px solid rgba(139, 92, 246, 0.20);
            border-radius: 12px;
            padding: 16px 18px;
        }
        div[data-testid="stMetric"] label {
            color: #94A3B8 !important;
            font-size: 0.85rem !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #F1F5F9 !important;
            font-size: 1.8rem !important;
            font-weight: 700 !important;
        }

        /* === Tabs === */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: rgba(30, 41, 59, 0.4);
            padding: 4px;
            border-radius: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: 8px;
            color: #94A3B8;
            padding: 8px 16px;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, #8B5CF6 0%, #6366F1 100%) !important;
            color: white !important;
        }

        /* === Expanders === */
        .stExpander {
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(148, 163, 184, 0.1);
            border-radius: 10px;
        }

        /* === DataFrames — darker rows === */
        .stDataFrame {
            border-radius: 8px;
            overflow: hidden;
        }

        /* === Dividers === */
        hr {
            border-color: rgba(148, 163, 184, 0.15) !important;
            margin: 1.5rem 0 !important;
        }

        /* === Info / warning / success boxes === */
        div[data-testid="stAlert"] {
            border-radius: 10px;
            border-width: 1px;
        }

        /* === Sidebar tool description card === */
        .tool-card {
            background: rgba(139, 92, 246, 0.10);
            border: 1px solid rgba(139, 92, 246, 0.25);
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 8px;
            color: #CBD5E1;
            font-size: 0.85rem;
            line-height: 1.4;
        }

        /* === Hub brand in sidebar === */
        .hub-brand {
            font-size: 1.4rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #C4B5FD 0%, #A5B4FC 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0;
        }
        .hub-tagline {
            color: #94A3B8 !important;
            font-size: 0.8rem;
            margin-top: 2px;
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
    st.markdown("<p class='hub-brand'>🧰 Tool Hub</p>", unsafe_allow_html=True)
    st.markdown("<p class='hub-tagline'>Internal utilities</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Choose a tool**")
    selected = st.radio(
        "Tool",
        list(TOOLS.keys()),
        label_visibility="collapsed",
    )
    st.markdown(
        f"<div class='tool-card'>{TOOLS[selected]['desc']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.75rem;opacity:0.6;'>Built with Streamlit</p>",
        unsafe_allow_html=True,
    )


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
