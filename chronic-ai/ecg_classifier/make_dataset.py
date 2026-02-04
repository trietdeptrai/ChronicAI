"""
make_dataset_detection_3by4_batched.py

Batched generator for ONLY the DETECTION dataset (images + YOLO-style bbox labels),
and ONLY for the 12-lead 3by4 layout.

Key features:
- Runs in batches: each run processes only a slice of the work
- Resume-safe: can skip already-generated files
- Does NOT delete your dataset unless you pass --fresh 1
- Saves logs per batch to avoid overwriting

Outputs:
  ./dataset/ECG-Dataset/detection/{train,val,test}/images/*.jpg
  ./dataset/ECG-Dataset/detection/{train,val,test}/labels/*.txt
  ./dataset/ECG-Dataset/logs_detection_{split}_batch{batch_id}.json

Example:
  python make_dataset_detection_3by4_batched.py --num_batches 5 --batch_id 0 --fresh 1
  python make_dataset_detection_3by4_batched.py --num_batches 5 --batch_id 1
  ...
"""

import os
import ast
import json
import shutil
import argparse

import numpy as np
import pandas as pd
import wfdb
import matplotlib.pyplot as plt
from tqdm import tqdm
from dotenv import load_dotenv

from utils import generate_bounding_boxes, plot_ecg_multilead, save_figure_as_jpg


# ---------------------- Helpers ----------------------
def get_env_int(var: str, default: int) -> int:
    return int(os.getenv(var, default))


def get_env_list(var: str, default: str):
    return os.getenv(var, default).split(",")


def load_raw_data(metadata_df: pd.DataFrame, sampling_rate: int, raw_path: str) -> np.ndarray:
    """
    Returns signals with shape (num_records, signal_length, num_leads).
    """
    if sampling_rate == 100:
        data = [wfdb.rdsamp(os.path.join(raw_path, f)) for f in metadata_df.filename_lr]
    else:
        data = [wfdb.rdsamp(os.path.join(raw_path, f)) for f in metadata_df.filename_hr]
    signals = np.array([signal for signal, meta in data])
    return signals


def aggregate_diagnostic(annotation_dict, agg_df):
    """
    Not required for detection generation, but kept for parity with your original code.
    """
    classes = []
    for key in annotation_dict.keys():
        if key in agg_df.index:
            classes.append(agg_df.loc[key].diagnostic_class)
    return list(set(classes))


def slice_for_batch(items, batch_id: int, num_batches: int):
    """
    Evenly split a list into num_batches chunks and return chunk batch_id.
    """
    if num_batches <= 1:
        return items
    if batch_id < 0 or batch_id >= num_batches:
        raise ValueError(f"batch_id must be in [0, {num_batches - 1}]")
    n = len(items)
    start = (n * batch_id) // num_batches
    end = (n * (batch_id + 1)) // num_batches
    return items[start:end]


def ensure_detection_directories(detection_dir: str):
    """
    Create the directory tree needed for detection, without deleting anything.
    """
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(detection_dir, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(detection_dir, split, "labels"), exist_ok=True)


def fresh_detection_directories(detection_dir: str):
    """
    Delete detection_dir and recreate empty tree.
    """
    if os.path.exists(detection_dir):
        shutil.rmtree(detection_dir)
    ensure_detection_directories(detection_dir)


def process_sample_detection_only(
    sample_idx: int,
    lead_format: str,
    lead_cfg: dict,
    signals: np.ndarray,
    sampling_rate: int,
    row_height: int,
    lead_names,
    detection_export_path: str,
    padding_x: int,
    padding_y: int,
    border: int,
    dpi: int,
    horizontal_scale: float,
    vertical_scale: float,
    fontsize: float,
    n_empty_cell_at_left: float,
    n_empty_cell_at_right: float,
    n_empty_cell_at_up: float,
    n_empty_cell_at_down: float,
    show_lead_name: float,
    show_grid: float,
    show_separate_line: float,
):
    """
    Generate one detection image + bbox label file (YOLO-like format).
    """
    sample_name = f"{sample_idx}_{lead_format}"
    img_path = os.path.join(detection_export_path, "images", sample_name + ".jpg")
    lbl_path = os.path.join(detection_export_path, "labels", sample_name + ".txt")

    log = plot_ecg_multilead(
        ecg=signals[sample_idx, : lead_cfg["length"], : lead_cfg["n_leads"]].T,
        full_ecg=signals[sample_idx, :, 1].T,
        full_ecg_name=lead_cfg["full_ecg_name"],
        sample_rate=sampling_rate,
        columns=lead_cfg["n_column"],
        lead_index=lead_names,
        title="",
        lead_order=lead_cfg["lead_order"],
        show_lead_name=show_lead_name,
        show_grid=show_grid,
        show_separate_line=show_separate_line,
        row_height=row_height,
        style=None,
        save_path=img_path,
        dpi=dpi,
        horizontal_scale=horizontal_scale,
        vertical_scale=vertical_scale,
        fontsize=fontsize,
        n_empty_cell_at_left=n_empty_cell_at_left,
        n_empty_cell_at_right=n_empty_cell_at_right,
        n_empty_cell_at_up=n_empty_cell_at_up,
        n_empty_cell_at_down=n_empty_cell_at_down,
    )

    # required by bbox generator
    log["padding_x"] = padding_x
    log["padding_y"] = padding_y
    log["border"] = border

    # make logs more usable downstream
    log["sample_idx"] = int(sample_idx)
    log["lead_format"] = str(lead_format)

    # save figure and generate labels
    fig = plt.gcf()
    fig.canvas.draw()
    image_array = np.array(fig.canvas.renderer._renderer)

    save_figure_as_jpg(img_path, dpi=dpi)
    generate_bounding_boxes(sample=log, mode="online", save_bb_path=lbl_path, img_array=image_array)

    return log


# ---------------------- Args ----------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Batched PTB-XL -> ECG image detection dataset generator (3by4 only)."
    )

    # These now mean "number of 3by4 samples" per split.
    parser.add_argument("--sample_each_lead_train", type=int, default=get_env_int("SAMPLE_EACH_LEAD_TRAIN", 5))
    parser.add_argument("--sample_each_lead_val", type=int, default=get_env_int("SAMPLE_EACH_LEAD_VAL", 2))
    parser.add_argument("--sample_each_lead_test", type=int, default=get_env_int("SAMPLE_EACH_LEAD_TEST", 2))

    parser.add_argument("--row_height", type=int, default=get_env_int("ROW_HEIGHT", 3))

    parser.add_argument("--signal_dataset_path", type=str, default="./dataset/signal_dataset")
    parser.add_argument("--raw_signal_path", type=str, default="./dataset/signal_dataset/physionet.org/files/ptb-xl/1.0.3")
    parser.add_argument("--datasets_path", type=str, default="./dataset")

    parser.add_argument("--horizontal_scale", type=float, default=0.2)
    parser.add_argument("--vertical_scale", type=float, default=0.5)
    parser.add_argument("--fontsize", type=float, default=6)
    parser.add_argument("--n_empty_cell_at_left", type=float, default=3.25)
    parser.add_argument("--n_empty_cell_at_right", type=float, default=3)
    parser.add_argument("--n_empty_cell_at_up", type=float, default=6)
    parser.add_argument("--n_empty_cell_at_down", type=float, default=6)
    parser.add_argument("--show_lead_name", type=float, default=1)
    parser.add_argument("--show_grid", type=float, default=1)
    parser.add_argument("--show_separate_line", type=float, default=1)

    parser.add_argument("--max_records", type=int, default=int(os.getenv("MAX_RECORDS", 10000)))

    # batching controls
    parser.add_argument("--batch_id", type=int, default=0, help="Which batch to run (0-based).")
    parser.add_argument("--num_batches", type=int, default=1, help="Total number of batches.")
    parser.add_argument("--skip_existing", type=int, default=1, help="Skip if image+label already exist (1/0).")

    # directory behavior
    parser.add_argument("--fresh", type=int, default=0, help="If 1, delete and recreate detection dirs (use for batch 0).")

    return parser.parse_args()


# ---------------------- Main ----------------------
if __name__ == "__main__":
    load_dotenv()
    args = parse_args()

    # core config
    SAMPLING_RATE = get_env_int("SAMPLING_RATE", 100)
    DPI = get_env_int("DPI", 700)
    PADDING_X = get_env_int("PADDING_X", 30)
    PADDING_Y = get_env_int("PADDING_Y", 30)
    BORDER = get_env_int("BORDER", 34)

    MAX_RECORDS = args.max_records

    # leads
    LEAD_INDEX = get_env_list("LEAD_INDEX", "I,II,III,aVL,aVR,aVF,V1,V2,V3,V4,V5,V6")

    # ONLY 3by4 layout
    LEAD_FORMAT_ONLY = "3by4"
    LEAD_CFG_ONLY = {
        "n_column": get_env_int("LEAD_3BY4_N_COLUMN", 4),
        "length": get_env_int("LEAD_3BY4_LENGTH", 250),
        "lead_order": [0, 1, 2, 4, 3, 5, 6, 7, 8, 9, 10, 11],
        "full_ecg_name": None,
        "n_leads": get_env_int("LEAD_3BY4_N_LEADS", 12),
    }

    # load or build signals
    signal_file = os.path.join(args.signal_dataset_path, f"all_signals_{SAMPLING_RATE}Hz.npy")

    if not os.path.exists(signal_file):
        metadata_df = pd.read_csv(os.path.join(args.raw_signal_path, "ptbxl_database.csv"), index_col="ecg_id")
        metadata_df = metadata_df.iloc[:MAX_RECORDS].copy()
        metadata_df.scp_codes = metadata_df.scp_codes.apply(lambda x: ast.literal_eval(x))

        # not needed for detection, but left here if you later want classification export
        agg_df = pd.read_csv(os.path.join(args.raw_signal_path, "scp_statements.csv"), index_col=0)
        agg_df = agg_df[agg_df.diagnostic == 1]
        metadata_df["diagnostic_superclass"] = metadata_df.scp_codes.apply(lambda x: aggregate_diagnostic(x, agg_df))

        signals = load_raw_data(metadata_df, SAMPLING_RATE, args.raw_signal_path)

        os.makedirs(args.signal_dataset_path, exist_ok=True)
        np.save(signal_file, signals)
        print(f"Signal dataset saved into {signal_file}")
    else:
        signals = np.load(signal_file)
        print(f"{signal_file} loaded")

    # truncation safety if the cached .npy is bigger than MAX_RECORDS
    if signals.shape[0] > MAX_RECORDS:
        signals = signals[:MAX_RECORDS]
        print(f"Signals truncated to first {signals.shape[0]} records (MAX_RECORDS={MAX_RECORDS}).")

    # split sizes
    n_train = args.sample_each_lead_train
    n_val = args.sample_each_lead_val
    n_test = args.sample_each_lead_test

    if n_train + n_val + n_test > signals.shape[0]:
        raise ValueError(
            f"Requested train+val+test = {n_train+n_val+n_test} exceeds available signals = {signals.shape[0]}."
        )

    # output dirs
    dataset_root = os.path.join(args.datasets_path, "ECG-Dataset")
    detection_dir = os.path.join(dataset_root, "detection")
    os.makedirs(dataset_root, exist_ok=True)

    if args.fresh:
        fresh_detection_directories(detection_dir)
    else:
        ensure_detection_directories(detection_dir)

    # create index lists (3by4 only)
    train_indices = [(i, LEAD_FORMAT_ONLY, LEAD_CFG_ONLY) for i in range(0, n_train)]
    val_indices = [(i, LEAD_FORMAT_ONLY, LEAD_CFG_ONLY) for i in range(n_train, n_train + n_val)]
    test_start = signals.shape[0] - n_test
    test_indices = [(i, LEAD_FORMAT_ONLY, LEAD_CFG_ONLY) for i in range(test_start, signals.shape[0])]

    # apply batching per split
    train_indices = slice_for_batch(train_indices, args.batch_id, args.num_batches)
    val_indices = slice_for_batch(val_indices, args.batch_id, args.num_batches)
    test_indices = slice_for_batch(test_indices, args.batch_id, args.num_batches)

    logs = {"train": [], "val": [], "test": []}

    # process
    for split_indices, split_name in [(train_indices, "train"), (val_indices, "val"), (test_indices, "test")]:
        export_path = os.path.join(detection_dir, split_name)

        for idx, lead_format, lead_cfg in tqdm(split_indices, desc=f"Processing {split_name} (batch {args.batch_id}/{args.num_batches})"):
            sample_name = f"{idx}_{lead_format}"
            img_path = os.path.join(export_path, "images", sample_name + ".jpg")
            lbl_path = os.path.join(export_path, "labels", sample_name + ".txt")

            if args.skip_existing and os.path.exists(img_path) and os.path.exists(lbl_path):
                continue

            log = process_sample_detection_only(
                sample_idx=idx,
                lead_format=lead_format,
                lead_cfg=lead_cfg,
                signals=signals,
                sampling_rate=SAMPLING_RATE,
                row_height=args.row_height,
                lead_names=LEAD_INDEX,
                detection_export_path=export_path,
                padding_x=PADDING_X,
                padding_y=PADDING_Y,
                border=BORDER,
                dpi=DPI,
                horizontal_scale=args.horizontal_scale,
                vertical_scale=args.vertical_scale,
                fontsize=args.fontsize,
                n_empty_cell_at_left=args.n_empty_cell_at_left,
                n_empty_cell_at_right=args.n_empty_cell_at_right,
                n_empty_cell_at_up=args.n_empty_cell_at_up,
                n_empty_cell_at_down=args.n_empty_cell_at_down,
                show_lead_name=args.show_lead_name,
                show_grid=args.show_grid,
                show_separate_line=args.show_separate_line,
            )
            logs[split_name].append(log)

    # save per-batch logs (do not overwrite)
    for split_name, split_logs in logs.items():
        out_path = os.path.join(dataset_root, f"logs_detection_{split_name}_batch{args.batch_id}.json")
        with open(out_path, "w") as f:
            json.dump({"frequency": SAMPLING_RATE, "samples": split_logs}, f)

    print("Done.")
    print(f"Batch: {args.batch_id}/{args.num_batches}")
    print(f"Logs saved under: {dataset_root}/logs_detection_*_batch{args.batch_id}.json")
