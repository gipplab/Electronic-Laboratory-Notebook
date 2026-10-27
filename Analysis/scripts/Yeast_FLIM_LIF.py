"""Read raw FLIM intensity time series and matching reference planes from Leica LIF files."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import tifffile
from readlif.reader import LifFile


INTENSITY_SUFFIX = "/FLIM Compressed/Intensity"


def resolve_lif_path(
    link: str | Path,
    data_root: str | Path,
    logical_data_path: str | Path,
) -> Path:
    """Resolve the labbook's stored experiment-relative link inside its data root."""
    data_root = Path(data_root).expanduser().resolve()
    link_path = Path(link).expanduser()
    if link_path.is_absolute():
        lif_path = link_path.resolve()
    else:
        try:
            relative_path = link_path.relative_to(Path(logical_data_path))
        except ValueError:
            relative_path = link_path
        lif_path = (data_root / relative_path).resolve()
    if not lif_path.is_relative_to(data_root):
        raise ValueError("The original LIF file is outside the configured yeast data folder.")
    return lif_path


def _series_record(index: int, image) -> dict[str, object]:
    dims = image.dims
    return {
        "signal_index": index,
        "name": image.name,
        "x": int(dims.x),
        "y": int(dims.y),
        "z": int(dims.z),
        "t": int(dims.t),
        "channels": int(image.channels),
        "mosaic": int(dims.m),
        "bit_depth": int(image.bit_depth[0]),
        "scale_x_um": float(image.scale[0]) if image.scale[0] else None,
        "scale_y_um": float(image.scale[1]) if image.scale[1] else None,
    }


def list_lif_candidates(path: str | Path) -> list[dict[str, object]]:
    """Return supported 32-bit FLIM Intensity series and their unique references."""
    path = Path(path)
    lif = LifFile(str(path))
    images = list(lif.get_iter_image())
    by_name: dict[str, list[int]] = {}
    for index, image in enumerate(images):
        by_name.setdefault(image.name, []).append(index)

    candidates = []
    for index, image in enumerate(images):
        if not image.name.endswith(INTENSITY_SUFFIX):
            continue
        ref_name = image.name[: -len(INTENSITY_SUFFIX)]
        reference_indices = by_name.get(ref_name, [])
        if len(reference_indices) > 1:
            raise ValueError(
                f"FLIM intensity series {image.name!r} has multiple matching "
                f"reference images named {ref_name!r}."
            )
        if not reference_indices:
            continue

        ref_index = reference_indices[0]
        dims = image.dims
        if (
            int(image.bit_depth[0]) != 32
            or image.display_dims != (1, 2)
            or int(dims.x) < 32
            or int(dims.y) < 32
            or int(dims.t) < 2
            or int(image.offsets[1]) == 0
        ):
            continue
        if int(dims.z) != 1 or int(image.channels) != 1 or int(dims.m) != 1:
            continue

        reference = images[ref_index]
        reference_dims = reference.dims
        if (
            reference.display_dims != (1, 2)
            or int(reference_dims.x) != int(dims.x)
            or int(reference_dims.y) != int(dims.y)
            or int(reference_dims.z) != 1
            or int(reference.channels) != 1
            or int(reference_dims.m) != 1
            or int(reference_dims.t) < 1
            or int(reference.offsets[1]) == 0
        ):
            continue
        if any(
            (bool(image.scale[axis]) != bool(reference.scale[axis]))
            or (
                image.scale[axis]
                and reference.scale[axis]
                and not math.isclose(
                    float(image.scale[axis]),
                    float(reference.scale[axis]),
                    rel_tol=1e-6,
                    abs_tol=1e-12,
                )
            )
            for axis in (0, 1)
        ):
            continue

        record = _series_record(index, image)
        record.update({
            "reference_index": ref_index,
            "reference_name": reference.name,
            "reference_timepoints": int(reference_dims.t),
            "reference_bit_depth": int(reference.bit_depth[0]),
            "label": (
                f"{image.name} — {dims.t} FLIM frames, "
                f"{dims.x}×{dims.y}; reference: {reference.name} "
                f"({reference_dims.t} frame(s))"
            ),
        })
        candidates.append(record)
    return candidates


_FILETIME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


def _element_index(lif: LifFile) -> dict[str, ET.Element]:
    """Map image names (path below the project root) to their LIF XML elements."""
    index: dict[str, ET.Element] = {}

    def walk(element: ET.Element, parts: list[str]) -> None:
        for child in element:
            if child.tag == "Children":
                walk(child, parts)
            elif child.tag == "Element" and child.get("Name") is not None:
                child_parts = parts + [child.get("Name")]
                if len(child_parts) > 1:
                    index["/".join(child_parts[1:])] = child
                walk(child, child_parts)

    walk(lif.xml_root, [])
    return index


def _data_subtree(element: ET.Element) -> ET.Element | None:
    return element.find("Data")


def _nearest(index: dict[str, ET.Element], name: str, tag: str):
    """Find the first <tag> in the element's own data, then in its ancestors' data."""
    parts = name.split("/")
    while parts:
        element = index.get("/".join(parts))
        data = _data_subtree(element) if element is not None else None
        if data is not None:
            found = next(data.iter(tag), None)
            if found is not None:
                return "/".join(parts), found
        parts.pop()
    return None, None


def acquisition_metadata(
    lif: LifFile,
    images: list,
    signal_index: int,
    reference_index: int,
) -> dict[str, object]:
    """Collect stored timing, stage position, and FLIM-data inventory for one series.

    Only values stored in the LIF are reported. Nothing here is a lifetime or phasor
    value; the inventory documents which Leica FLIM products exist next to the
    intensity series.
    """
    index = _element_index(lif)
    signal = images[signal_index]
    reference = images[reference_index]
    frame_count = int(signal.nt)

    ts_path, ts_element = _nearest(index, signal.name, "TimeStamps")
    timestamps_s: list[float] = []
    if ts_element is not None and ts_element.text:
        timestamps_s = [float(value) for value in ts_element.text.split()]
    timestamp_info: dict[str, object] = {
        "source_element": ts_path,
        "stored_timestamp_count": len(timestamps_s),
        "frame_count": frame_count,
        "frame_timestamps_utc": None,
        "frame_elapsed_s": None,
    }
    if timestamps_s and len(timestamps_s) == frame_count:
        timestamp_info["frame_timestamps_utc"] = [
            (_FILETIME_EPOCH + timedelta(seconds=value)).isoformat()
            for value in timestamps_s
        ]
        timestamp_info["frame_elapsed_s"] = [value - timestamps_s[0] for value in timestamps_s]
    elif timestamps_s:
        timestamp_info["note"] = (
            f"LIF stores {len(timestamps_s)} time stamps for {frame_count} frames; "
            "they cannot be assigned unambiguously, so frame indices are used."
        )

    def stage(name: str):
        path, element = _nearest(index, name, "StagePositions")
        if element is None:
            return path, None
        try:
            return path, {
                "x_m": float(element.findtext("X")),
                "y_m": float(element.findtext("Y")),
            }
        except (TypeError, ValueError):
            return path, None

    signal_stage_path, signal_stage = stage(signal.name)
    reference_stage_path, reference_stage = stage(reference.name)
    pixel_um = signal.scale[0] if signal.scale and signal.scale[0] else None
    registration: dict[str, object] = {
        "reference_stage_element": reference_stage_path,
        "signal_stage_element": signal_stage_path,
        "reference_stage_xy_m": reference_stage,
        "signal_stage_xy_m": signal_stage,
        "per_frame_registration_verified": False,
    }
    if reference_stage and signal_stage and pixel_um:
        half_pixel_m = float(pixel_um) * 1e-6 / 2
        offsets = [
            abs(reference_stage[key] - signal_stage[key]) for key in ("x_m", "y_m")
        ]
        registration["stage_offset_xy_m"] = offsets
        if max(offsets) > half_pixel_m:
            raise ValueError(
                "The LIF stage positions of the reference and FLIM series differ by more "
                "than half a pixel; the cell masks cannot be applied without registration."
            )
        registration["stage_positions_equal_within_half_pixel"] = True
        registration["status"] = (
            "Reference and FLIM series report the same stage position and pixel size; "
            "drift between time points is not measured or corrected."
        )
    else:
        registration["status"] = (
            "Stage positions are not stored for both series; registration is not verified."
        )

    parent_name = signal.name[: -len(INTENSITY_SUFFIX)] + "/FLIM Compressed"
    siblings = [
        {"name": image.name[len(parent_name) + 1:], "bit_depth": int(image.bit_depth[0])}
        for image in images
        if image.name.startswith(parent_name + "/")
    ]
    sibling_names = {row["name"] for row in siblings}
    parent_element = index.get(parent_name)
    parent_data = _data_subtree(parent_element) if parent_element is not None else None

    def parent_text(tag: str):
        if parent_data is None:
            return None
        found = next(parent_data.iter(tag), None)
        return found.text if found is not None else None

    laser_hz = parent_text("LaserPulseFrequency")
    reference_phase = parent_text("PhasorPhase")
    flim = {
        "stored_series": siblings,
        "has_fast_flim_map": "Fast Flim" in sibling_names,
        "has_phasor_real_imaginary_maps": {"Phasor Real", "Phasor Imaginary"} <= sibling_names,
        "has_global_decay_histogram_in_xml": (
            parent_data is not None and next(parent_data.iter("RawDataFrequency"), None) is not None
        ),
        "laser_pulse_frequency_hz": float(laser_hz) if laser_hz else None,
        "phasor_automatic_reference": (
            (parent_text("PhasorAutomaticReference") or "").strip().lower() == "true"
            if parent_text("PhasorAutomaticReference") is not None else None
        ),
        "phasor_reference_phase_s": float(reference_phase) if reference_phase else None,
    }
    return {"timestamps": timestamp_info, "registration": registration, "flim_inventory": flim}


def _frame_array(path: Path, image, *, t: int, z: int = 0, c: int = 0, m: int = 0) -> np.ndarray:
    """Decode a single planar frame, including Leica's 32-bit float intensity maps."""
    if image.display_dims != (1, 2):
        raise ValueError(f"Unsupported non-XY LIF plane layout in {image.name!r}.")
    if not (0 <= t < int(image.nt) and 0 <= z < int(image.nz)
            and 0 <= c < int(image.channels) and 0 <= m < int(image.n_mosaic)):
        raise ValueError("Requested LIF frame index is outside the image dimensions.")

    channels = int(image.channels)
    z_count = int(image.nz)
    t_count = int(image.nt)
    if image.channel_as_second_dim:
        item = t * channels * z_count + c * z_count + z
    else:
        item = t * channels * z_count + z * channels + c
    item += m * channels * z_count * t_count

    item_count = channels * image._get_len_nondisplay_dims()
    bytes_per_pixel = int(image.bit_depth[0]) // 8
    frame_bytes = int(image.dims.x) * int(image.dims.y) * bytes_per_pixel
    if image.offsets[1] == 0:
        raw = bytes(frame_bytes)
    else:
        image_bytes = int(image.offsets[1])
        if image_bytes % item_count or image_bytes // item_count != frame_bytes:
            actual_frame_bytes = image_bytes // item_count
            raise ValueError(
                f"Unexpected frame size in {image.name!r}: {actual_frame_bytes} bytes; "
                f"expected {frame_bytes}."
            )
        with path.open("rb") as stream:
            stream.seek(int(image.offsets[0]) + frame_bytes * item)
            raw = stream.read(frame_bytes)
        if len(raw) != frame_bytes:
            raise ValueError(f"Truncated image plane in {image.name!r}.")

    bit_depth = int(image.bit_depth[0])
    dtype = {8: "u1", 16: "<u2", 32: "<f4"}.get(bit_depth)
    if dtype is None:
        raise ValueError(f"Unsupported {bit_depth}-bit LIF data in {image.name!r}.")
    return np.frombuffer(raw, dtype=dtype).reshape(int(image.dims.y), int(image.dims.x)).copy()


def export_lif_candidate(
    lif_path: str | Path,
    signal_index: int,
    output_dir: str | Path,
    *,
    reference_time: int = 0,
) -> tuple[Path, Path, dict[str, object]]:
    """Export a matched reference series and raw intensity time stack as OME-TIFF."""
    lif_path = Path(lif_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    lif = LifFile(str(lif_path))
    images = list(lif.get_iter_image())
    candidates = {int(row["signal_index"]): row for row in list_lif_candidates(lif_path)}
    if signal_index not in candidates:
        raise ValueError(f"LIF intensity series {signal_index} has no matching reference plane.")
    candidate = candidates[signal_index]
    signal = images[signal_index]
    reference = images[int(candidate["reference_index"])]
    reference_timepoints = int(candidate["reference_timepoints"])
    if not 0 <= reference_time < reference_timepoints:
        raise ValueError(
            f"Reference time {reference_time} is outside the available range "
            f"0..{reference_timepoints - 1}."
        )
    frame_count = int(signal.nt)
    candidate["acquisition"] = acquisition_metadata(
        lif, images, signal_index, int(candidate["reference_index"])
    )
    x_size, y_size = int(signal.dims.x), int(signal.dims.y)

    signal_stack = np.empty((frame_count, y_size, x_size), dtype=np.float32)
    for time_index in range(frame_count):
        signal_stack[time_index] = _frame_array(lif_path, signal, t=time_index)
    first_reference_frame = _frame_array(lif_path, reference, t=0)
    reference_stack = np.empty(
        (reference_timepoints, y_size, x_size), dtype=first_reference_frame.dtype
    )
    reference_stack[0] = first_reference_frame
    for time_index in range(1, reference_timepoints):
        reference_stack[time_index] = _frame_array(
            lif_path, reference, t=time_index
        )
    if reference_stack.shape[1:] != signal_stack.shape[1:]:
        raise ValueError("Matched LIF reference and signal planes have different XY dimensions.")

    physical = {}
    if candidate["scale_x_um"]:
        physical.update(PhysicalSizeX=candidate["scale_x_um"], PhysicalSizeXUnit="µm")
    if candidate["scale_y_um"]:
        physical.update(PhysicalSizeY=candidate["scale_y_um"], PhysicalSizeYUnit="µm")

    safe_index = f"series_{signal_index:04d}"
    signal_path = output_dir / f"{lif_path.stem}_{safe_index}_raw_intensity.ome.tif"
    reference_path = output_dir / (
        f"{lif_path.stem}_{safe_index}_reference_t{reference_time:04d}.ome.tif"
    )
    tifffile.imwrite(
        signal_path,
        signal_stack,
        ome=True,
        photometric="minisblack",
        metadata={"axes": "TYX", **physical},
    )
    tifffile.imwrite(
        reference_path,
        reference_stack[0] if reference_timepoints == 1 else reference_stack,
        ome=True,
        photometric="minisblack",
        metadata={
            "axes": "YX" if reference_timepoints == 1 else "TYX",
            **physical,
        },
    )
    candidate["reference_time"] = reference_time
    return reference_path, signal_path, candidate
