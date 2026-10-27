"""Segment yeast cells once and measure their raw FLIM-channel pixel values.

Input is OME-TIFF exported from LAS X. Segmentation is run on one reference
plane; the resulting fixed cell masks are applied to every time point in the
measurement stack. This keeps changing fluorescence from changing the ROIs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from argparse import Namespace
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import tifffile
from skimage.segmentation import find_boundaries
from scipy import ndimage as ndi
from cellpose import models


GENERAL_CELLPOSE_MODELS = {"cpsam_v2", "cpsam", "cpdino"}
_LENGTH_TO_METERS = {
    "m": 1.0,
    "mm": 1e-3,
    "µm": 1e-6,
    "um": 1e-6,
    "micrometer": 1e-6,
    "nm": 1e-9,
}


def _ome_length(attributes: dict[str, str], key: str) -> float | None:
    value = attributes.get(key)
    if value is None:
        return None
    unit = attributes.get(f"{key}Unit", "µm")
    scale = _LENGTH_TO_METERS.get(unit)
    if scale is None:
        raise ValueError(f"Unsupported OME spatial unit {unit!r} for {key}.")
    length = float(value) * scale
    if not math.isfinite(length) or (
        key.startswith("PhysicalSize") and length <= 0
    ):
        raise ValueError(f"OME spatial metadata {key} must be a finite positive length.")
    return length


def _ome_spatial_metadata(
    ome_xml: str | None,
    series_index: int,
    *,
    time_index: int,
    channel_index: int,
    z_index: int,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "pixel_size_x_m": None,
        "pixel_size_y_m": None,
        "position_x_m": None,
        "position_y_m": None,
        "positions_by_time_m": {},
    }
    if not ome_xml:
        return metadata

    root = ET.fromstring(ome_xml)
    images = [element for element in root if element.tag.rsplit("}", 1)[-1] == "Image"]
    if not 0 <= series_index < len(images):
        return metadata
    pixels = next(
        (element for element in images[series_index] if element.tag.rsplit("}", 1)[-1] == "Pixels"),
        None,
    )
    if pixels is None:
        return metadata

    metadata["pixel_size_x_m"] = _ome_length(pixels.attrib, "PhysicalSizeX")
    metadata["pixel_size_y_m"] = _ome_length(pixels.attrib, "PhysicalSizeY")
    planes = [element for element in pixels if element.tag.rsplit("}", 1)[-1] == "Plane"]
    positions_by_time: dict[int, dict[str, float | None]] = {}
    for plane in planes:
        if (
            int(plane.attrib.get("TheC", "0")) != channel_index
            or int(plane.attrib.get("TheZ", "0")) != z_index
        ):
            continue
        plane_time = int(plane.attrib.get("TheT", "0"))
        positions_by_time[plane_time] = {
            "position_x_m": _ome_length(plane.attrib, "PositionX"),
            "position_y_m": _ome_length(plane.attrib, "PositionY"),
        }
    metadata["positions_by_time_m"] = positions_by_time
    selected_position = positions_by_time.get(time_index)
    if selected_position is not None:
        metadata["position_x_m"] = selected_position["position_x_m"]
        metadata["position_y_m"] = selected_position["position_y_m"]
    return metadata


def load_series(
    path: Path,
    series_index: int,
    *,
    time_index: int = 0,
    channel_index: int = 0,
    z_index: int = 0,
) -> tuple[np.ndarray, str, dict[str, object]]:
    with tifffile.TiffFile(path) as tif:
        if series_index < 0 or series_index >= len(tif.series):
            raise ValueError(f"Series {series_index} is unavailable in {path}.")
        series = tif.series[series_index]
        return (
            series.asarray(),
            series.axes.upper(),
            _ome_spatial_metadata(
                tif.ome_metadata,
                series_index,
                time_index=time_index,
                channel_index=channel_index,
                z_index=z_index,
            ),
        )


def select_plane(
    data: np.ndarray,
    axes: str,
    *,
    time_index: int,
    channel_index: int,
    z_index: int,
) -> np.ndarray:
    """Select a 2D YX plane and reject any unselected non-singleton axis."""
    if len(axes) != data.ndim:
        raise ValueError(f"TIFF axes {axes!r} do not match array shape {data.shape}.")
    if len(set(axes)) != len(axes):
        raise ValueError(f"TIFF axes contain duplicates: {axes!r}.")
    index: list[int | slice] = []
    remaining: list[str] = []
    for axis, size in zip(axes, data.shape):
        if axis == "Y" or axis == "X":
            index.append(slice(None))
            remaining.append(axis)
        elif axis == "T":
            if not 0 <= time_index < size:
                raise ValueError(f"Time index {time_index} is outside T={size}.")
            index.append(time_index)
        elif axis == "C":
            if not 0 <= channel_index < size:
                raise ValueError(f"Channel index {channel_index} is outside C={size}.")
            index.append(channel_index)
        elif axis == "Z":
            if not 0 <= z_index < size:
                raise ValueError(f"Z index {z_index} is outside Z={size}.")
            index.append(z_index)
        elif size == 1:
            index.append(0)
        else:
            raise ValueError(
                f"Unselected TIFF axis {axis!r} has size {size}; export a 2D/2D+T "
                "OME-TIFF or update the axis selection."
            )
    if set(remaining) != {"Y", "X"}:
        raise ValueError(f"Expected Y and X axes, got {remaining} from {axes!r}.")
    plane = np.asarray(data[tuple(index)])
    if remaining == ["X", "Y"]:
        plane = plane.T
    if plane.ndim != 2:
        raise ValueError(f"Expected one 2D plane, got shape {plane.shape}.")
    return plane


def time_planes(
    data: np.ndarray,
    axes: str,
    *,
    channel_index: int,
    z_index: int,
) -> list[np.ndarray]:
    n_time = data.shape[axes.index("T")] if "T" in axes else 1
    return [
        select_plane(
            data,
            axes,
            time_index=t,
            channel_index=channel_index,
            z_index=z_index,
        )
        for t in range(n_time)
    ]


def clean_masks(masks: np.ndarray, min_area: int, max_area: int | None) -> np.ndarray:
    if masks.ndim != 2:
        raise ValueError(f"Cellpose must return a 2D label mask, got shape {masks.shape}.")
    labels, counts = np.unique(masks, return_counts=True)
    out = np.zeros(masks.shape, dtype=np.uint32)
    next_id = 1
    for label, area in zip(labels, counts):
        if label == 0 or area < min_area or (max_area is not None and area > max_area):
            continue
        out[masks == label] = next_id
        next_id += 1
    return out


def validate_alignment(
    segmentation_shape: tuple[int, int],
    signal_shape: tuple[int, int],
    segmentation_metadata: dict[str, object],
    signal_metadata: dict[str, object],
) -> dict[str, object]:
    if segmentation_shape != signal_shape:
        raise ValueError(
            "Segmentation and signal planes must have identical canonical YX dimensions "
            f"(got {segmentation_shape} and {signal_shape}); register/crop the exports first."
        )

    checks: dict[str, bool | str] = {"xy_shape_matches": True}
    for axis in ("x", "y"):
        seg_size = segmentation_metadata[f"pixel_size_{axis}_m"]
        sig_size = signal_metadata[f"pixel_size_{axis}_m"]
        if not isinstance(seg_size, (int, float)):
            seg_size = None if seg_size is None else float(seg_size)
        if not isinstance(sig_size, (int, float)):
            sig_size = None if sig_size is None else float(sig_size)
        seg_size = float(seg_size) if seg_size is not None else None
        sig_size = float(sig_size) if sig_size is not None else None
        if seg_size is not None and sig_size is not None:
            matches = math.isclose(seg_size, sig_size, rel_tol=1e-6, abs_tol=1e-12)
            checks[f"pixel_size_{axis}_matches"] = matches
            if not matches:
                raise ValueError(
                    f"OME-TIFF physical pixel size differs on {axis.upper()} "
                    f"({seg_size:g} m vs {sig_size:g} m); resample/register before analysis."
                )
        else:
            checks[f"pixel_size_{axis}_matches"] = "not recorded in both OME-TIFFs"

        seg_position = segmentation_metadata[f"position_{axis}_m"]
        if seg_position is not None:
            seg_position = float(seg_position)
        pixel_size = seg_size if seg_size is not None else sig_size
        positions_by_time = signal_metadata.get("positions_by_time_m", {})
        time_checks: dict[str, bool | str] = {}
        if isinstance(positions_by_time, dict) and positions_by_time:
            for time_index, position in positions_by_time.items():
                if not isinstance(position, dict):
                    time_checks[str(time_index)] = "not recorded in both OME-TIFFs"
                    continue
                signal_position = position.get(f"position_{axis}_m")
                if (
                    seg_position is not None
                    and signal_position is not None
                    and pixel_size is not None
                ):
                    matches = math.isclose(
                        float(seg_position),
                        float(signal_position),
                        rel_tol=0.0,
                        abs_tol=pixel_size / 2,
                    )
                    time_checks[str(time_index)] = matches
                    if not matches:
                        raise ValueError(
                            f"OME-TIFF stage positions differ by more than half a pixel "
                            f"on {axis.upper()} at signal time {time_index}; register "
                            "the images before analysis."
                        )
                else:
                    time_checks[str(time_index)] = "not recorded in both OME-TIFFs"
        else:
            signal_position = signal_metadata[f"position_{axis}_m"]
            if (
                seg_position is not None
                and signal_position is not None
                and pixel_size is not None
            ):
                matches = math.isclose(
                    float(seg_position),
                    float(signal_position),
                    rel_tol=0.0,
                    abs_tol=pixel_size / 2,
                )
                time_checks["0"] = matches
                if not matches:
                    raise ValueError(
                        f"OME-TIFF stage positions differ by more than half a pixel on "
                        f"{axis.upper()}; register the images before analysis."
                    )
            else:
                time_checks["0"] = "not recorded in both OME-TIFFs"
        checks[f"stage_position_{axis}_matches_by_time"] = time_checks
        checks[f"stage_position_{axis}_matches"] = time_checks.get(
            "0", "not recorded in both OME-TIFFs"
        )
    return checks


def prepare_measurement_rois(
    masks: np.ndarray, ring_width: int
) -> list[tuple[int, tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray], int]]:
    """Build fixed cell and local-background pixel indices once for the full series.

    Morphology runs on a bounding-box crop padded by the ring width (clipped at the
    image edge, so border behaviour matches a full-frame operation). Indices are
    returned in full-image coordinates and can be used directly to index a frame.
    """
    if ring_width < 1:
        raise ValueError("Background ring width must be at least 1 pixel.")
    height, width = masks.shape
    all_cells = masks > 0
    prepared = []
    for cell_id, bbox in enumerate(ndi.find_objects(masks.astype(np.int64)), start=1):
        if bbox is None:
            continue
        y0 = max(bbox[0].start - ring_width - 1, 0)
        y1 = min(bbox[0].stop + ring_width + 1, height)
        x0 = max(bbox[1].start - ring_width - 1, 0)
        x1 = min(bbox[1].stop + ring_width + 1, width)
        crop = masks[y0:y1, x0:x1] == cell_id
        expanded = ndi.binary_dilation(crop, iterations=ring_width)
        inner = ndi.binary_erosion(crop, iterations=ring_width)
        ring = expanded & ~inner & ~all_cells[y0:y1, x0:x1]
        roi_y, roi_x = np.nonzero(crop)
        ring_y, ring_x = np.nonzero(ring)
        prepared.append(
            (
                int(cell_id),
                (roi_y + y0, roi_x + x0),
                (ring_y + y0, ring_x + x0),
                int(roi_y.size),
            )
        )
    return prepared


def quantify(
    masks: np.ndarray,
    image: np.ndarray,
    ring_width: int,
    prepared_rois: list | None = None,
) -> list[dict[str, float | int]]:
    if masks.shape != image.shape:
        raise ValueError(f"Mask shape {masks.shape} != image shape {image.shape}.")
    if prepared_rois is None:
        prepared_rois = prepare_measurement_rois(masks, ring_width)
    results = []
    for cell_id, roi, ring, area in prepared_rois:
        vals = image[roi].astype(np.float64, copy=False)
        bg = image[ring].astype(np.float64, copy=False)
        bg_median = float(np.median(bg)) if bg.size else float("nan")
        raw_mean = float(np.mean(vals))
        raw_sum = float(np.sum(vals))
        results.append(
            {
                "cell_id": int(cell_id),
                "area_px": area,
                "mean_raw_pixel_value": raw_mean,
                "integrated_raw_pixel_value": raw_sum,
                "local_background_median": bg_median,
                "mean_background_corrected": raw_mean - bg_median,
                "integrated_background_corrected": raw_sum - bg_median * area,
                "background_pixel_count": int(bg.size),
            }
        )
    return results


def mask_qc_rows(masks: np.ndarray) -> list[dict[str, int | float | bool]]:
    height, width = masks.shape
    rows = []
    for cell_id in np.unique(masks):
        if cell_id == 0:
            continue
        y, x = np.where(masks == cell_id)
        area = int(y.size)
        rows.append(
            {
                "cell_id": int(cell_id),
                "area_px": area,
                "fraction_image_area": area / (height * width),
                "centroid_y_px": float(np.mean(y)),
                "centroid_x_px": float(np.mean(x)),
                "bbox_y_min_px": int(y.min()),
                "bbox_y_max_exclusive_px": int(y.max()) + 1,
                "bbox_x_min_px": int(x.min()),
                "bbox_x_max_exclusive_px": int(x.max()) + 1,
                "touches_image_border": bool(
                    np.any(y == 0) or np.any(y == height - 1)
                    or np.any(x == 0) or np.any(x == width - 1)
                ),
            }
        )
    return rows


def _source_record(path: Path, axes: str, data: np.ndarray) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "series_axes": axes,
        "series_shape": list(data.shape),
        "dtype": str(data.dtype),
    }


def analyze(args: argparse.Namespace) -> Path:
    if args.model not in GENERAL_CELLPOSE_MODELS:
        raise ValueError(
            f"Unsupported Cellpose model {args.model!r}; choose one of "
            f"{', '.join(sorted(GENERAL_CELLPOSE_MODELS))}. Custom checkpoints are disabled."
        )
    if args.diameter is not None and (
        not math.isfinite(args.diameter) or args.diameter <= 0
    ):
        raise ValueError("Cellpose diameter must be a positive finite number.")
    if args.min_area < 1:
        raise ValueError("Minimum cell area must be at least 1 pixel.")
    if args.max_area is not None and args.max_area < args.min_area:
        raise ValueError("Maximum cell area must be greater than or equal to minimum area.")
    if args.background_ring < 1:
        raise ValueError("Background ring width must be at least 1 pixel.")
    if not math.isfinite(args.cellprob_threshold) or not math.isfinite(args.flow_threshold):
        raise ValueError("Cellpose thresholds must be finite numbers.")

    progress = getattr(args, "progress", None)

    def report(phase, done=None, total=None):
        if progress is not None:
            progress.update(phase, done, total)

    report("segmentation")
    segmentation_path = Path(args.segmentation).expanduser().resolve()
    signal_path = Path(args.signal).expanduser().resolve()
    seg_data, seg_axes, seg_metadata = load_series(
        segmentation_path,
        args.seg_series,
        time_index=args.seg_time,
        channel_index=args.seg_channel,
        z_index=args.seg_z,
    )
    seg_plane = select_plane(
        seg_data,
        seg_axes,
        time_index=args.seg_time,
        channel_index=args.seg_channel,
        z_index=args.seg_z,
    )
    if not np.isfinite(seg_plane).all():
        raise ValueError("The selected segmentation plane contains NaN or infinite values.")

    model = models.CellposeModel(gpu=args.gpu, pretrained_model=args.model)
    masks, *_ = model.eval(
        seg_plane,
        channel_axis=None,
        channels=[0, 0],
        normalize=True,
        resample=True,
        diameter=args.diameter,
        cellprob_threshold=args.cellprob_threshold,
        flow_threshold=args.flow_threshold,
    )
    masks = clean_masks(np.asarray(masks), args.min_area, args.max_area)
    if not np.any(masks):
        raise ValueError(
            "Cellpose found no cells after area filtering. Review the reference image, "
            "model, diameter, and area limits."
        )

    signal_data, signal_axes, signal_metadata = load_series(
        signal_path,
        args.signal_series,
        time_index=0,
        channel_index=args.signal_channel,
        z_index=args.signal_z,
    )
    signal_frames = time_planes(
        signal_data,
        signal_axes,
        channel_index=args.signal_channel,
        z_index=args.signal_z,
    )
    if not signal_frames:
        raise ValueError("The signal OME-TIFF contains no time planes.")
    alignment = validate_alignment(
        tuple(seg_plane.shape),
        tuple(signal_frames[0].shape),
        seg_metadata,
        signal_metadata,
    )
    if any(frame.shape != masks.shape for frame in signal_frames):
        raise ValueError("A signal time plane does not match the fixed mask dimensions.")
    if any(not np.isfinite(frame).all() for frame in signal_frames):
        raise ValueError("A selected signal plane contains NaN or infinite values.")

    out_dir = Path(args.output).expanduser().resolve()
    processed_dir = Path(args.processed_output).expanduser().resolve()
    if (
        out_dir == processed_dir
        or out_dir in processed_dir.parents
        or processed_dir in out_dir.parents
    ):
        raise ValueError("Analysis results and processed masks must use separate directories.")
    out_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    # A new run must never leave artifacts of an earlier run that look complete.
    for stale in (
        out_dir / "yeast_analysis_manifest.json",
        out_dir / "yeast_cell_intensity.csv",
        out_dir / "yeast_cell_intensity.csv.part",
        out_dir / "yeast_mask_qc.csv",
        out_dir / "yeast_segmentation_overlay.png",
        processed_dir / "yeast_cell_masks.ome.tif",
    ):
        stale.unlink(missing_ok=True)
    mask_path = processed_dir / "yeast_cell_masks.ome.tif"
    ome_mask_metadata: dict[str, object] = {"axes": "YX"}
    for axis in ("X", "Y"):
        pixel_size = seg_metadata[f"pixel_size_{axis.lower()}_m"]
        if isinstance(pixel_size, (int, float)):
            ome_mask_metadata[f"PhysicalSize{axis}"] = float(pixel_size) * 1e6
            ome_mask_metadata[f"PhysicalSize{axis}Unit"] = "µm"
    tifffile.imwrite(
        mask_path,
        masks.astype(np.uint32, copy=False),
        ome=True,
        metadata=ome_mask_metadata,
        photometric="minisblack",
    )
    from PIL import Image
    low, high = np.percentile(seg_plane, (1, 99.5))
    gray = np.clip(
        (seg_plane.astype(np.float32) - low) / max(float(high - low), 1e-8), 0, 1
    )
    overlay = np.repeat((gray * 255).astype(np.uint8)[..., None], 3, axis=2)
    overlay[find_boundaries(masks, mode="outer")] = (255, 40, 40)
    Image.fromarray(overlay).save(out_dir / "yeast_segmentation_overlay.png")

    qc_rows = mask_qc_rows(masks)
    qc_path = out_dir / "yeast_mask_qc.csv"
    qc_fields = [
        "cell_id", "area_px", "fraction_image_area", "centroid_y_px",
        "centroid_x_px", "bbox_y_min_px", "bbox_y_max_exclusive_px",
        "bbox_x_min_px", "bbox_x_max_exclusive_px", "touches_image_border",
    ]
    with qc_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=qc_fields)
        writer.writeheader()
        writer.writerows(qc_rows)

    csv_path = out_dir / "yeast_cell_intensity.csv"
    part_path = out_dir / "yeast_cell_intensity.csv.part"
    report("quantification", 0, len(signal_frames))
    prepared_rois = prepare_measurement_rois(masks, args.background_ring)
    expected_rows = len(signal_frames) * len(prepared_rois)
    written_rows = 0
    fieldnames = [
        "time_index",
        "cell_id",
        "area_px",
        "mean_raw_pixel_value",
        "integrated_raw_pixel_value",
        "local_background_median",
        "mean_background_corrected",
        "integrated_background_corrected",
        "background_pixel_count",
    ]
    # Write to a temporary file and publish it only after every time point is complete.
    with part_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for time_index, frame in enumerate(signal_frames):
            for row in quantify(masks, frame, args.background_ring, prepared_rois):
                writer.writerow({"time_index": time_index, **row})
                written_rows += 1
            report("quantification", time_index + 1, len(signal_frames))
        report("finalizing")
        f.flush()
        os.fsync(f.fileno())
    if written_rows != expected_rows:
        raise RuntimeError(
            f"Intensity table incomplete: wrote {written_rows} of {expected_rows} rows."
        )
    os.replace(part_path, csv_path)

    from importlib.metadata import PackageNotFoundError, version

    software_versions = {}
    for package in ("cellpose", "numpy", "tifffile", "scipy", "scikit-image", "readlif"):
        try:
            software_versions[package] = version(package)
        except PackageNotFoundError:
            software_versions[package] = "unknown"
    lif_selection = getattr(args, "lif_selection", None) or {}
    acquisition = lif_selection.get("acquisition") or {}
    manifest = {
        "analysis": "yeast_cellpose_raw_intensity",
        "status": "complete",
        "completeness": {
            "signal_timepoints": len(signal_frames),
            "cell_count": len(prepared_rois),
            "expected_intensity_rows": expected_rows,
            "written_intensity_rows": written_rows,
        },
        "time_axis": acquisition.get("timestamps"),
        "registration": acquisition.get("registration"),
        "lifetime_phasor": {
            "computed": False,
            "reason": (
                "Only the raw FLIM Compressed/Intensity series is analysed. No fluorescence "
                "lifetime or phasor value is computed or reported by this workflow."
            ),
            "leica_flim_products_in_lif": acquisition.get("flim_inventory"),
        },
        "cellpose_model": args.model,
        "software_versions": software_versions,
        "parameters": {
            "segmentation_series": args.seg_series,
            "segmentation_time_index": args.seg_time,
            "segmentation_channel_index": args.seg_channel,
            "segmentation_z_index": args.seg_z,
            "signal_series": args.signal_series,
            "signal_channel_index": args.signal_channel,
            "signal_z_index": args.signal_z,
            "diameter_px": args.diameter,
            "normalize": True,
            "resample": True,
            "cellprob_threshold": args.cellprob_threshold,
            "flow_threshold": args.flow_threshold,
            "minimum_cell_area_px": args.min_area,
            "maximum_cell_area_px": args.max_area,
            "background_ring_width_px": args.background_ring,
        },
        "inputs": {
            "segmentation": _source_record(segmentation_path, seg_axes, seg_data),
            "signal": _source_record(signal_path, signal_axes, signal_data),
        },
        "lif_selection": lif_selection or None,
        "selected_planes": {
            "segmentation_shape_yx": list(seg_plane.shape),
            "signal_shape_yx": list(signal_frames[0].shape),
            "signal_timepoints": len(signal_frames),
            "segmentation_ome_spatial_metadata": seg_metadata,
            "signal_ome_spatial_metadata": signal_metadata,
            "alignment_checks": alignment,
        },
        "mask_qc": {
            "cell_count": len(qc_rows),
            "labels_are_fixed_across_signal_timepoints": True,
            "cells_touching_image_border": sum(
                bool(row["touches_image_border"]) for row in qc_rows
            ),
        },
        "measurement_semantics": (
            "Raw source pixel values are measured without modifying the signal image. "
            "Background-corrected values subtract the local ring median."
        ),
        "outputs": {
            "intensity_csv": str(csv_path.resolve()),
            "mask_qc_csv": str(qc_path.resolve()),
            "segmentation_overlay_png": str(
                (out_dir / "yeast_segmentation_overlay.png").resolve()
            ),
            "label_mask_ome_tiff": str(mask_path.resolve()),
        },
    }
    with (out_dir / "yeast_analysis_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, allow_nan=False)

    return csv_path


def run_yfl_analysis(entry_id: int, run_id: str | None = None) -> str:
    """Django-Q task entry point for one YFL experiment."""
    from Exp_Main.models import YFL
    from Analysis.scripts.Yeast_FLIM_Results import (
        ProgressReporter,
        task_superseded_or_duplicate,
    )

    entry = YFL.objects.get(pk=entry_id)
    skip_reason = task_superseded_or_duplicate(entry, run_id)
    if skip_reason:
        return f"skipped: {skip_reason}"
    progress = ProgressReporter(entry, run_id)
    progress.start()
    entry.Analysis_Status = YFL.AnalysisStatus.RUNNING
    entry.Analysis_Error = ""
    entry.save(update_fields=["Analysis_Status", "Analysis_Error"])

    try:
        from Analysis.scripts.Yeast_FLIM_Results import result_dirs, yeast_data_root

        data_root = yeast_data_root()
        output_dir, processed_dir = result_dirs(entry)
        lif_selection = None
        if entry.LIF_Signal_Index is not None:
            if not entry.Link:
                raise ValueError("This experiment has no linked Leica LIF file.")
            from Analysis.scripts.Yeast_FLIM_LIF import (
                export_lif_candidate,
                resolve_lif_path,
            )

            lif_path = resolve_lif_path(entry.Link, data_root, entry.Device.Path)
            if lif_path.suffix.lower() != ".lif" or not lif_path.is_file():
                raise ValueError(f"Linked Leica LIF file does not exist: {lif_path}")
            reference_path, signal_path, selected_series = export_lif_candidate(
                lif_path,
                int(entry.LIF_Signal_Index),
                processed_dir / "lif_import",
                reference_time=int(entry.Segmentation_Time),
            )
            entry.Segmentation_Image = str(reference_path)
            entry.Signal_Image = str(signal_path)
            entry.save(update_fields=["Segmentation_Image", "Signal_Image"])
            lif_stat = lif_path.stat()
            lif_selection = {
                "source_file": str(lif_path),
                "source_size_bytes": lif_stat.st_size,
                "source_mtime_ns": lif_stat.st_mtime_ns,
                "signal_index": int(selected_series["signal_index"]),
                "signal_name": selected_series["name"],
                "signal_dtype": "float32",
                "reference_index": int(selected_series["reference_index"]),
                "reference_name": selected_series["reference_name"],
                "reference_time_index": int(selected_series["reference_time"]),
                "acquisition": selected_series.get("acquisition"),
            }
        if not entry.Segmentation_Image or not entry.Signal_Image:
            raise ValueError("Choose a Leica LIF time series or set both reference and signal TIFFs.")
        args = Namespace(
            segmentation=entry.Segmentation_Image,
            signal=entry.Signal_Image,
            output=str(output_dir),
            processed_output=str(processed_dir),
            seg_series=0,
            seg_time=entry.Segmentation_Time,
            seg_channel=entry.Segmentation_Channel,
            seg_z=entry.Segmentation_Z,
            signal_series=0,
            signal_channel=entry.Signal_Channel,
            signal_z=entry.Signal_Z,
            model=entry.Cellpose_Model or "cpsam_v2",
            diameter=entry.Cellpose_Diameter,
            cellprob_threshold=0.0,
            flow_threshold=0.4,
            min_area=entry.Min_Cell_Area,
            max_area=entry.Max_Cell_Area,
            background_ring=entry.Background_Ring,
            gpu=False,
            lif_selection=lif_selection,
            progress=progress,
        )
        result = analyze(args)
        entry.Analysis_Result = str(result)
        entry.Analysis_Status = YFL.AnalysisStatus.COMPLETED
        entry.Analysis_Error = ""
        entry.save(update_fields=["Analysis_Result", "Analysis_Status", "Analysis_Error"])
        progress.finish("done")
        return str(result)
    except BaseException as exc:
        entry.Analysis_Status = YFL.AnalysisStatus.FAILED
        entry.Analysis_Error = str(exc) or type(exc).__name__
        entry.save(update_fields=["Analysis_Status", "Analysis_Error"])
        progress.finish("failed", entry.Analysis_Error)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--segmentation", required=True, help="Reference OME-TIFF exported from LAS X")
    parser.add_argument("--signal", required=True, help="Raw FLIM intensity OME-TIFF")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument(
        "--processed-output",
        required=True,
        help="Directory for generated label masks",
    )
    parser.add_argument("--seg-series", type=int, default=0)
    parser.add_argument("--seg-time", type=int, default=0)
    parser.add_argument("--seg-channel", type=int, default=0)
    parser.add_argument("--seg-z", type=int, default=0)
    parser.add_argument("--signal-series", type=int, default=0)
    parser.add_argument("--signal-channel", type=int, default=0)
    parser.add_argument("--signal-z", type=int, default=0)
    parser.add_argument(
        "--model",
        choices=sorted(GENERAL_CELLPOSE_MODELS),
        default="cpsam_v2",
        help="General built-in Cellpose model (custom checkpoints are disabled)",
    )
    parser.add_argument("--diameter", type=float, default=None)
    parser.add_argument("--cellprob-threshold", type=float, default=0.0)
    parser.add_argument("--flow-threshold", type=float, default=0.4)
    parser.add_argument("--min-area", type=int, default=1)
    parser.add_argument("--max-area", type=int, default=None)
    parser.add_argument("--background-ring", type=int, default=3)
    parser.add_argument("--gpu", action="store_true")
    return parser


if __name__ == "__main__":
    cli_args = build_parser().parse_args()
    print(analyze(cli_args))
