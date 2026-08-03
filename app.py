"""
Zepto Virtual Bundle Image Tool — Web App
-------------------------------------------
Run locally:
    pip install streamlit pandas openpyxl pillow gdown --break-system-packages
    streamlit run app.py

Or deploy for free with a shareable link via Streamlit Community Cloud:
    1. Push this folder (app.py, badge.py, requirements.txt) to a GitHub repo
    2. Go to https://share.streamlit.io -> New app -> pick your repo -> deploy

The app lets you upload the Excel file (PVID, Google Drive image link,
bundle count), processes every row, shows progress + a preview, and gives
you a single ZIP download of all finished catalog images.
"""

import streamlit as st
import pandas as pd
import os
import shutil
import zipfile
import tempfile
from badge import apply_badge
from zepto_bundle_tool import find_column, download_drive_image

st.set_page_config(page_title="Zepto Bundle Badge Tool", layout="centered")

# ---------- Simple password gate ----------
# Set your password via Streamlit secrets (recommended) or the fallback below.
# In Streamlit Community Cloud: App settings -> Secrets -> add:
#   APP_PASSWORD = "your-password-here"
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "changeme123")

if "authed" not in st.session_state:
    st.session_state.authed = False

if not st.session_state.authed:
    st.title("🔒 Zepto Bundle Badge Tool")
    pwd = st.text_input("Enter access password", type="password")
    if st.button("Enter"):
        if pwd == APP_PASSWORD:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
# ---------- End password gate ----------

st.title("🛍️ Zepto Virtual Bundle Image Tool")
st.write(
    "Upload an Excel file with 3 columns — **PVID**, **Image Link**, "
    "**Number of Pieces** — and get back each image with the purple "
    "'N Pieces' badge added, ready to download."
)

uploaded_excel = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

if uploaded_excel is not None:
    df = pd.read_excel(uploaded_excel)
    st.write(f"Found **{len(df)}** rows.")
    st.dataframe(df.head())

    cols = list(df.columns)
    pvid_col = find_column(cols, ["pvid"])
    link_col = find_column(cols, ["link", "drive", "image"])
    count_col = find_column(cols, ["count", "piece", "bundle"])

    if not all([pvid_col, link_col, count_col]):
        st.error(
            f"Could not auto-detect required columns from: {cols}. "
            "Please rename headers to include 'PVID', 'link'/'image', and 'count'/'piece'/'bundle'."
        )
    else:
        st.success(f"Detected columns → PVID: `{pvid_col}` | Link: `{link_col}` | Count: `{count_col}`")

        if st.button("🚀 Process all images"):
            work_dir = tempfile.mkdtemp()
            out_dir = os.path.join(work_dir, "output")
            raw_dir = os.path.join(work_dir, "raw")
            os.makedirs(out_dir, exist_ok=True)
            os.makedirs(raw_dir, exist_ok=True)

            progress = st.progress(0)
            status_area = st.empty()
            results = []

            for i, row in df.iterrows():
                pvid = str(row[pvid_col]).strip()
                link = str(row[link_col]).strip()
                try:
                    count = int(float(row[count_col]))
                except Exception:
                    results.append((pvid, "FAILED", "Invalid bundle count"))
                    progress.progress((i + 1) / len(df))
                    continue

                raw_path = os.path.join(raw_dir, f"{pvid}_raw.png")
                out_path = os.path.join(out_dir, f"{pvid}.png")
                status_area.text(f"Processing {pvid} ({i+1}/{len(df)})...")

                try:
                    download_drive_image(link, raw_path)
                    apply_badge(raw_path, count, out_path)
                    results.append((pvid, "OK", out_path))
                except Exception as e:
                    results.append((pvid, "FAILED", str(e)))

                progress.progress((i + 1) / len(df))

            status_area.empty()
            ok_count = sum(1 for r in results if r[1] == "OK")
            st.write(f"### Done: {ok_count}/{len(results)} succeeded")

            # one row per PVID: thumbnail + individual download link
            for pvid, status, info in results:
                row_cols = st.columns([1, 2, 1])
                if status == "OK":
                    with row_cols[0]:
                        st.image(info, width=90)
                    with row_cols[1]:
                        st.write(f"**{pvid}** ✅")
                    with row_cols[2]:
                        with open(info, "rb") as f:
                            st.download_button(
                                "Download",
                                data=f.read(),
                                file_name=f"{pvid}.png",
                                mime="image/png",
                                key=f"dl_{pvid}",
                            )
                else:
                    with row_cols[1]:
                        st.write(f"**{pvid}** ❌ {info}")

            if ok_count > 1:
                zip_path = os.path.join(work_dir, "bundle_images.zip")
                with zipfile.ZipFile(zip_path, "w") as zf:
                    for f in os.listdir(out_dir):
                        zf.write(os.path.join(out_dir, f), arcname=f)
                with open(zip_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download all as one ZIP",
                        data=f.read(),
                        file_name="bundle_images.zip",
                        mime="application/zip",
                    )
