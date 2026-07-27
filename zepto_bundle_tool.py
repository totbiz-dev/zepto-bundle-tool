"""
Zepto Virtual Bundle Image Tool
--------------------------------
Reads an Excel file with columns (case-insensitive, flexible naming):
    PVID | IMAGE LINK | BUNDLE COUNT
Downloads each product image from its Google Drive link, stamps a purple
"N Pieces" balloon badge on the top-right corner (matching the reference
catalog style), and saves the result as <PVID>.png in the output folder.

USAGE:
    python3 zepto_bundle_tool.py input.xlsx output_folder

Excel column matching is flexible: it looks for any column containing
"pvid", any column containing "link" or "drive" or "image", and any column
containing "count", "piece", or "bundle". Rename your headers to match
these if auto-detection picks the wrong column.

Requirements:
    pip install pandas openpyxl pillow gdown --break-system-packages
"""

import sys
import os
import re
import zipfile
import pandas as pd
from badge import apply_badge

try:
    import gdown
except ImportError:
    gdown = None


def find_column(columns, keywords):
    for col in columns:
        low = str(col).strip().lower()
        if any(k in low for k in keywords):
            return col
    return None


def extract_drive_id(link):
    """Pull the Google Drive file ID out of common share-link formats."""
    if not isinstance(link, str):
        return None
    patterns = [
        r"/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, link)
        if m:
            return m.group(1)
    # if it's already just an ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{15,}", link.strip()):
        return link.strip()
    return None


def download_drive_image(link, dest_path):
    file_id = extract_drive_id(link)
    if not file_id:
        raise ValueError(f"Could not parse a Google Drive file ID from: {link}")
    if gdown is None:
        raise RuntimeError("gdown is not installed. Run: pip install gdown --break-system-packages")
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, dest_path, quiet=True, fuzzy=True)
    if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
        raise RuntimeError(f"Download failed for {link}")


def process_excel(excel_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    tmp_dir = os.path.join(output_dir, "_downloads")
    os.makedirs(tmp_dir, exist_ok=True)

    df = pd.read_excel(excel_path)
    cols = list(df.columns)

    pvid_col = find_column(cols, ["pvid"])
    link_col = find_column(cols, ["link", "drive", "image"])
    count_col = find_column(cols, ["count", "piece", "bundle"])

    if not all([pvid_col, link_col, count_col]):
        raise ValueError(
            f"Could not auto-detect required columns. Found columns: {cols}\n"
            f"Detected -> PVID: {pvid_col}, Link: {link_col}, Count: {count_col}\n"
            "Please rename your Excel headers to include the words "
            "'PVID', 'link'/'image', and 'count'/'piece'/'bundle'."
        )

    results = []
    for idx, row in df.iterrows():
        pvid = str(row[pvid_col]).strip()
        link = str(row[link_col]).strip()
        count = row[count_col]
        try:
            count = int(float(count))
        except Exception:
            results.append((pvid, "FAILED", f"Invalid bundle count: {count}"))
            continue

        raw_path = os.path.join(tmp_dir, f"{pvid}_raw.png")
        out_path = os.path.join(output_dir, f"{pvid}.png")

        try:
            download_drive_image(link, raw_path)
            apply_badge(raw_path, count, out_path)
            results.append((pvid, "OK", out_path))
        except Exception as e:
            results.append((pvid, "FAILED", str(e)))

    # zip final outputs (excluding _downloads temp folder)
    zip_path = os.path.join(output_dir, "bundle_images.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in os.listdir(output_dir):
            if f.endswith(".png"):
                zf.write(os.path.join(output_dir, f), arcname=f)

    return results, zip_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 zepto_bundle_tool.py input.xlsx output_folder")
        sys.exit(1)

    excel_path, output_dir = sys.argv[1], sys.argv[2]
    results, zip_path = process_excel(excel_path, output_dir)

    ok = sum(1 for r in results if r[1] == "OK")
    print(f"\nDone: {ok}/{len(results)} succeeded.")
    for pvid, status, info in results:
        print(f"  [{status}] {pvid} -> {info}")
    print(f"\nZip created at: {zip_path}")
