#!/usr/bin/env python3
"""
make_classification_labels.py

Build classification labels by scanning generated detection images and
looking up labels from PTB-XL's ptbxl_database.csv (plus scp_statements.csv).

Compatible with the NEW generator:
- detection-only
- 3by4-only (optional filter)
- batched generation
- does NOT rely on logs (so it won't miss blocks like 8100-8199)

Output:
  ./dataset/ECG-Dataset/classification_labels_3by4.csv
"""

import os
import re
import ast
import glob
import pandas as pd


# ---------------------- CONFIG ----------------------
RAW_SIGNAL_PATH = "./dataset/signal_dataset/physionet.org/files/ptb-xl/1.0.3"
DATASET_ROOT = "./dataset/ECG-Dataset"

MAX_RECORDS = 10000  # must be the same as (or <=) what you used when generating signals/images
TARGET_LEAD_FORMAT = "3by4"  # set to None to include other formats too


# ---------------------- PTB-XL MAPPING ----------------------
def build_scp_to_diagclass_map(raw_signal_path: str):
    """
    Returns a dict: scp_code -> diagnostic_class (e.g. 'NORM', 'MI', 'STTC', 'CD', 'HYP', ...)
    Only includes rows where diagnostic == 1.
    """
    agg_df = pd.read_csv(os.path.join(raw_signal_path, "scp_statements.csv"), index_col=0)
    agg_df = agg_df[agg_df["diagnostic"] == 1]
    # index is scp_code, column diagnostic_class contains the target superclass
    return agg_df["diagnostic_class"].to_dict()


def load_ptbxl_metadata(raw_signal_path: str, max_records: int):
    """
    Loads ptbxl_database.csv and truncates to max_records in the same way your generator did.
    """
    df = pd.read_csv(os.path.join(raw_signal_path, "ptbxl_database.csv"), index_col="ecg_id")
    df = df.iloc[:max_records].copy()
    # parse scp_codes from string -> dict
    df["scp_codes"] = df["scp_codes"].apply(lambda x: ast.literal_eval(x))
    return df


def diagnostic_superclass_from_scp(scp_codes: dict, scp_to_diagclass: dict):
    """
    scp_codes is dict like {"NORM": 100, "STTC": 50, ...} (weights irrelevant here)
    We map keys -> diagnostic_class and take unique set.
    """
    classes = set()
    for code in scp_codes.keys():
        diag_class = scp_to_diagclass.get(code)
        if diag_class is not None:
            classes.add(diag_class)
    return sorted(list(classes))


# ---------------------- IMAGE SCAN ----------------------
def parse_image_filename(path: str):
    """
    Parse "{idx}_{format}.jpg" -> (idx:int, format:str)
    """
    base = os.path.basename(path)
    m = re.match(r"^(\d+)_([A-Za-z0-9]+)\.jpg$", base)
    if not m:
        return None, None
    return int(m.group(1)), m.group(2)


def build_labels_csv():
    scp_to_diagclass = build_scp_to_diagclass_map(RAW_SIGNAL_PATH)
    metadata_df = load_ptbxl_metadata(RAW_SIGNAL_PATH, MAX_RECORDS)

    rows = []
    missing_meta = 0

    for split in ["train", "val", "test"]:
        images_dir = os.path.join(DATASET_ROOT, "detection", split, "images")
        if not os.path.isdir(images_dir):
            print(f"Warning: missing images dir: {images_dir}")
            continue

        image_paths = sorted(glob.glob(os.path.join(images_dir, "*.jpg")))
        if not image_paths:
            print(f"Warning: no images found in: {images_dir}")
            continue

        for img_path in image_paths:
            ecg_index, lead_format = parse_image_filename(img_path)
            if ecg_index is None:
                continue

            if TARGET_LEAD_FORMAT is not None and lead_format != TARGET_LEAD_FORMAT:
                continue

            if ecg_index < 0 or ecg_index >= len(metadata_df):
                missing_meta += 1
                continue

            scp_codes = metadata_df.iloc[ecg_index]["scp_codes"]
            diag = diagnostic_superclass_from_scp(scp_codes, scp_to_diagclass)

            image_id = f"{ecg_index}_{lead_format}"

            rows.append(
                {
                    "image_id": image_id,
                    "split": split,
                    "lead_format": lead_format,
                    "ecg_index": int(ecg_index),
                    "image_path": img_path,
                    "diagnostic_superclass": diag,                 # list
                    "diagnostic_superclass_str": ",".join(diag),  # string
                }
            )

    out_csv = os.path.join(DATASET_ROOT, "classification_labels_3by4.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False)

    print(f"Saved: {out_csv} ({len(rows)} rows)")
    if missing_meta:
        print(f"Warning: {missing_meta} images had ecg_index outside metadata_df (check MAX_RECORDS).")


if __name__ == "__main__":
    build_labels_csv()
