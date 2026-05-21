"""Glasses Image Renamer — rename product images to match a canonical product list.

Source filenames use short brand codes (BOSS, MIS, FT...) in various formats:
  BOSS 1880_G_S_807IR_P00.jpg
  Tommy-Hilfiger-TH-2357-S-003-IR.png
  MM5049_071.jpg
  FT0926_01E_01.jpg

List entries use full brand names with / as the model/color separator:
  Hugo Boss BOSS 1880/G/S 807/IR
  Tommy Hilfiger TH 2357/S 003

Target filenames: <Full Brand> <model_with_underscores> <color_with_underscores>.<ext>
  e.g. Hugo Boss BOSS 1880_G_S 807_IR.jpg
"""
import streamlit as st
import pandas as pd
import re
import io
import zipfile
from pathlib import Path


# Brand short code -> full brand name as written in the product list.
# Add new brands here as they appear.
BRAND_MAP = {
    "BOSS": "Hugo Boss BOSS",
    "HG": "Hugo Boss HG",
    "MJ": "Marc Jacobs MJ",
    "MARC": "Marc Jacobs MARC",
    "TH": "Tommy Hilfiger TH",
    "TJ": "Tommy Hilfiger TJ",
    "D2": "Dsquared2 D2",
    "ICON": "Dsquared2 ICON",
    "DB": "David Beckham DB",
    "IM": "Isabel Marant IM",
    "HER": "Carolina Herrera HER",
    "ETRO": "Etro ETRO",
    "MIS": "Missoni MIS",
    "MOS": "Moschino MOS",
    "LV": "Levi's LV",
    "PLD": "Polaroid PLD",  # 8xxx models -> Polaroid Kids PLD (handled at match time)
    "CARRERA": "Carrera CARRERA",
    "CA": "Carrera CA",
    "C SPORT": "Carrera C SPORT",
    "VICTORY": "Carrera VICTORY",
    "MM": "Max Mara MM",
    "MO": "MAX&Co. MO",
    "FT": "Tom Ford FT",
}

# Multi-word brand codes that contain a space.
MULTI_WORD_BRANDS = {k for k in BRAND_MAP if " " in k}

# Brands whose model number range affects the "full brand" (e.g. Polaroid Kids = PLD 8xxx).
KIDS_LINE = {
    "PLD": ("Polaroid Kids PLD", lambda m: m and m[0].startswith("8")),
}


# ---------- List parsing ----------

def parse_list_entry(line: str):
    """Parse a product list line into a structured dict, or None if unparseable."""
    line = line.strip()
    if not line:
        return None

    words = line.split()
    brand_idx = None
    brand_short = None

    # 1. Multi-word brand (e.g. "C SPORT")
    for i in range(len(words) - 1):
        pair = f"{words[i]} {words[i+1]}".upper()
        if pair in MULTI_WORD_BRANDS:
            brand_short = pair
            brand_idx = i + 1
            break

    if brand_short is None:
        # 2. Single-word brand — search only in the words BEFORE the last two
        #    (last two are model + color). Take the LAST match in case a brand-name
        #    word like 'Boss' precedes the actual short code 'BOSS'.
        candidate_range = words[:-2] if len(words) >= 3 else words
        for i, w in enumerate(candidate_range):
            wu = w.upper()
            if wu in BRAND_MAP and wu not in MULTI_WORD_BRANDS:
                brand_short = wu
                brand_idx = i
                # keep iterating — last match wins

    if brand_short is None:
        # 3. Glued brand+model (e.g. FT0926)
        for i, w in enumerate(words):
            wu = w.upper()
            m = re.match(r"^([A-Z]+)(\d.*)$", wu)
            if m and m.group(1) in BRAND_MAP:
                brand_short = m.group(1)
                brand_idx = i
                # NOTE: do NOT split the token — we preserve the glued form in output
                break

    if brand_short is None:
        return None

    full_brand_from_list = " ".join(words[: brand_idx + 1])

    # If the brand token is glued (FT0926), the "after_brand" content is inside that token plus the rest
    glued_match = re.match(r"^([A-Z]+)(\d.*)$", words[brand_idx].upper())
    if glued_match and glued_match.group(1) == brand_short:
        # First "after" word is the model digits part inside the glued token
        after_brand = [glued_match.group(2)] + words[brand_idx + 1 :]
        # full_brand_from_list keeps the glued form (used for target generation via raw line)
    else:
        after_brand = words[brand_idx + 1 :]

    if not after_brand:
        return None

    model_group = after_brand[0]
    color_group = after_brand[1] if len(after_brand) > 1 else ""

    model_parts = model_group.split("/")
    color_parts = color_group.split("/") if color_group else []

    full_brand = full_brand_from_list
    if brand_short in KIDS_LINE:
        kids_full, predicate = KIDS_LINE[brand_short]
        if predicate(model_parts):
            full_brand = kids_full

    return {
        "raw": line,
        "brand_short": brand_short,
        "full_brand": full_brand,
        "model_parts": model_parts,
        "color_parts": color_parts,
    }


# ---------- Source filename parsing ----------

PHOTO_SUFFIX_RE = re.compile(r"^P\d{1,3}$", re.IGNORECASE)


def tokenize_source(filename: str) -> list[str]:
    """Strip extension, normalize separators, split into tokens, split glued brand prefix."""
    stem = Path(filename).stem
    # Replace _ and - with space
    norm = re.sub(r"[_\-]+", " ", stem)
    tokens = norm.split()
    if not tokens:
        return []

    # Try to split a glued brand+digit prefix in the first token
    m = re.match(r"^([A-Za-z]+)(\d.*)$", tokens[0])
    if m and m.group(1).upper() in BRAND_MAP:
        tokens = [m.group(1), m.group(2)] + tokens[1:]

    return tokens


def strip_trailing_noise(tokens: list[str]) -> list[str]:
    """Remove trailing photo-number suffixes like P00, P01."""
    out = list(tokens)
    while out and PHOTO_SUFFIX_RE.match(out[-1]):
        out.pop()
    return out


def find_brand_in_tokens(tokens: list[str]) -> tuple[int, str] | tuple[None, None]:
    """Return (index_of_brand_token, brand_short_uppercase) — finds the LAST occurrence
    so 'Boss by Hugo Boss BOSS 1542' picks BOSS at the right position."""
    last_idx = None
    last_brand = None

    # Multi-word brands first
    for i in range(len(tokens) - 1):
        pair = f"{tokens[i]} {tokens[i+1]}".upper()
        if pair in BRAND_MAP:
            last_idx = i + 1
            last_brand = pair

    # Single-word brands (later occurrence wins for files like "Boss by Hugo Boss BOSS")
    for i, t in enumerate(tokens):
        if t.upper() in BRAND_MAP:
            last_idx = i
            last_brand = t.upper()

    if last_brand is None:
        return None, None
    return last_idx, last_brand


# ---------- Matching ----------

def match_tokens_to_entry(tokens_after_brand: list[str], entry: dict) -> tuple[bool, int]:
    """Check whether the tokens (after the brand) match a list entry.
    Returns (matched, tokens_consumed)."""
    model = [m.upper() for m in entry["model_parts"]]
    color = [c.upper() for c in entry["color_parts"]]

    if not model:
        return False, 0
    if len(tokens_after_brand) < len(model):
        return False, 0

    # All model parts must appear consecutively
    for i, mp in enumerate(model):
        if tokens_after_brand[i].upper() != mp:
            return False, 0
    cursor = len(model)

    if not color:
        return True, cursor

    if cursor >= len(tokens_after_brand):
        return False, 0

    src_color = tokens_after_brand[cursor].upper()
    full_color_concat = "".join(color)

    # Case 1: glued match — '807IR' equals '807' + 'IR'
    if src_color == full_color_concat:
        return True, cursor + 1
    # Case 2: prefix match — source starts with the concatenation
    if src_color.startswith(full_color_concat):
        return True, cursor + 1
    # Case 3: color parts split across tokens — '807' 'IR'
    if src_color == color[0]:
        for j, cp in enumerate(color[1:], start=1):
            idx = cursor + j
            if idx >= len(tokens_after_brand) or tokens_after_brand[idx].upper() != cp:
                return False, 0
        return True, cursor + len(color)
    # Case 4: source has just the primary color (sub-color missing in source)
    if src_color == color[0] and len(color) == 1:
        return True, cursor + 1

    return False, 0


def match_filename(filename: str, entries: list[dict]) -> dict:
    """Match a single source filename against the parsed list entries."""
    tokens = tokenize_source(filename)
    if not tokens:
        return {"status": "error", "reason": "Empty filename after parsing"}

    tokens_clean = strip_trailing_noise(tokens)
    brand_idx, brand_short = find_brand_in_tokens(tokens_clean)
    if brand_short is None:
        return {"status": "unknown_brand", "tokens": tokens_clean}

    after_brand = tokens_clean[brand_idx + 1 :]

    # Try matching every list entry with the same brand
    candidates = [e for e in entries if e["brand_short"] == brand_short]
    if not candidates:
        return {
            "status": "no_brand_in_list",
            "brand_short": brand_short,
        }

    best_match = None
    best_consumed = -1
    for entry in candidates:
        ok, consumed = match_tokens_to_entry(after_brand, entry)
        if ok and consumed > best_consumed:
            best_match = entry
            best_consumed = consumed

    if best_match is None:
        return {
            "status": "no_match",
            "brand_short": brand_short,
            "tokens_after_brand": after_brand,
        }

    return {"status": "matched", "entry": best_match}


# ---------- Target name generation ----------

INVALID_FS_CHARS = set('<>:"/\\|?*')


def safe_name(s: str) -> str:
    """Replace any filesystem-illegal character with _."""
    return "".join("_" if c in INVALID_FS_CHARS else c for c in s)


def target_name_for(entry: dict, ext: str) -> str:
    """Build the target filename by taking the raw list entry and replacing / with _.
    This preserves the list's exact formatting (glued FT0926 stays glued, etc.)."""
    base = entry["raw"].replace("/", "_")
    return safe_name(base) + ext


# ---------- Collision resolution ----------

PXX_RE = re.compile(r"_P(\d{2,3})$", re.IGNORECASE)


def extract_photo_suffix(filename: str) -> str | None:
    """Find a trailing _Pxx suffix (before extension) in the original filename."""
    stem = Path(filename).stem
    m = re.search(r"[_\-]P(\d{2,3})$", stem, re.IGNORECASE)
    if m:
        return f"P{m.group(1)}"
    return None


def resolve_collisions(plan: list[dict]) -> list[dict]:
    """Append P00/P01/... to disambiguate target names that collide."""
    # Group by target
    groups: dict[str, list[dict]] = {}
    for row in plan:
        if row["status"] != "matched":
            continue
        groups.setdefault(row["target"], []).append(row)

    for target, rows in groups.items():
        if len(rows) < 2:
            continue
        # Try to use existing P-suffixes if both files have them
        existing = [extract_photo_suffix(r["source"]) for r in rows]
        if all(existing) and len(set(existing)) == len(existing):
            # All distinct
            stem, ext = Path(target).stem, Path(target).suffix
            for r, sfx in zip(rows, existing):
                r["target"] = f"{stem} {sfx}{ext}"
                r["collision"] = f"used original suffix {sfx}"
        else:
            stem, ext = Path(target).stem, Path(target).suffix
            for i, r in enumerate(rows):
                r["target"] = f"{stem} P{i:02d}{ext}"
                r["collision"] = f"auto-suffix P{i:02d}"
    return plan


# ---------- Streamlit UI ----------

def render():
    st.write(
        "Rename glasses product images to match canonical names from your product list. "
        "Source filenames use short brand codes; list entries use full brand names. "
        "The tool maps between them and replaces `/` with `_` for Windows compatibility."
    )

    with st.sidebar:
        st.header("Inputs")
        uploaded_images = st.file_uploader(
            "Upload images (.jpg / .png)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="ren_images",
        )

    st.subheader("Product list")
    list_text = st.text_area(
        "One product per line — `Full Brand MODEL[/PART/PART] COLOR[/SUBCOLOR]`",
        height=200,
        placeholder=(
            "Marc Jacobs MJ 882/S 12J/HA\n"
            "Hugo Boss BOSS 1880/G/S 807/IR\n"
            "Missoni MIS 0266 ZI9\n"
            "Tom Ford FT0926 01E"
        ),
        key="ren_list",
    )

    if not uploaded_images:
        st.info("⬅ Upload one or more images in the sidebar to begin.")
        return
    if not list_text.strip():
        st.info("Paste a product list above to continue.")
        return

    # Parse list
    raw_lines = [ln for ln in list_text.splitlines() if ln.strip()]
    entries = []
    list_warnings = []
    for ln in raw_lines:
        parsed = parse_list_entry(ln)
        if parsed is None:
            list_warnings.append(ln)
        else:
            entries.append(parsed)

    if list_warnings:
        with st.expander(f"⚠️ {len(list_warnings)} unparseable list lines", expanded=False):
            for w in list_warnings:
                st.write(f"`{w}`")

    if not entries:
        st.error("No valid list entries parsed. Check the format.")
        return

    # Build rename plan
    plan = []
    for f in uploaded_images:
        result = match_filename(f.name, entries)
        row = {"source": f.name, "status": result["status"], "_file": f}
        if result["status"] == "matched":
            entry = result["entry"]
            ext = Path(f.name).suffix
            row["target"] = target_name_for(entry, ext)
            row["matched_entry"] = entry["raw"]
        else:
            row["target"] = None
            row["matched_entry"] = None
            row["reason"] = result
        plan.append(row)

    plan = resolve_collisions(plan)

    # Find list entries with no matching file
    matched_entry_raws = {row["matched_entry"] for row in plan if row["status"] == "matched"}
    missing_entries = [e["raw"] for e in entries if e["raw"] not in matched_entry_raws]

    # Top-line metrics
    n_total = len(plan)
    n_matched = sum(1 for r in plan if r["status"] == "matched")
    n_unmatched = n_total - n_matched
    n_collisions = sum(1 for r in plan if r.get("collision"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total files", n_total)
    c2.metric("Matched", n_matched)
    c3.metric("Unmatched", n_unmatched)
    c4.metric("Collisions resolved", n_collisions)

    # Preview tables
    st.subheader("Preview")
    matched_rows = [r for r in plan if r["status"] == "matched"]
    if matched_rows:
        df = pd.DataFrame([
            {
                "Source": r["source"],
                "→": "→",
                "Target": r["target"],
                "Note": r.get("collision", ""),
                "Already correct": r["source"] == r["target"],
            }
            for r in matched_rows
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("No files matched any list entry.")

    # Warnings
    unmatched_rows = [r for r in plan if r["status"] != "matched"]
    if unmatched_rows:
        with st.expander(f"⚠️ {len(unmatched_rows)} unmatched files", expanded=False):
            for r in unmatched_rows:
                reason = r.get("reason", {}).get("status", "unknown")
                detail = ""
                if reason == "unknown_brand":
                    detail = " (no brand code recognized)"
                elif reason == "no_brand_in_list":
                    detail = f" (brand {r['reason']['brand_short']} not in product list)"
                elif reason == "no_match":
                    detail = f" (brand {r['reason']['brand_short']} found, but no model/color match)"
                st.write(f"`{r['source']}` — {reason}{detail}")

    if missing_entries:
        with st.expander(f"⚠️ {len(missing_entries)} list entries with no matching file", expanded=False):
            for e in missing_entries:
                st.write(f"`{e}`")

    # Apply
    st.divider()
    actionable = [r for r in matched_rows if r["source"] != r["target"]]
    if not actionable:
        st.success("✅ All matched files already have the correct names — nothing to rename.")
        return

    st.subheader("Apply renames")
    st.caption(
        f"{len(actionable)} files will be renamed. The output is a ZIP containing all "
        "renamed images (unmatched files are skipped) plus a `rename_log.csv` for auditing."
    )

    if st.button("📦 Build renamed ZIP", type="primary"):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in matched_rows:
                file_bytes = r["_file"].getvalue()
                zf.writestr(r["target"], file_bytes)
            # Write log
            log_df = pd.DataFrame([
                {
                    "source": r["source"],
                    "target": r["target"] if r["status"] == "matched" else "",
                    "status": r["status"],
                    "matched_entry": r.get("matched_entry") or "",
                    "note": r.get("collision", ""),
                }
                for r in plan
            ])
            zf.writestr("rename_log.csv", log_df.to_csv(index=False))
        zip_buf.seek(0)
        st.download_button(
            "⬇ Download ZIP",
            data=zip_buf,
            file_name="renamed_glasses.zip",
            mime="application/zip",
        )
        st.success(f"ZIP ready — {len(matched_rows)} files included.")
