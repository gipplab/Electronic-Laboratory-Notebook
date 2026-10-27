"""Locate and validate Yeast-FLIM analysis artifacts (no Cellpose/LIF imports)."""

from __future__ import annotations

import csv
import json
import os
import threading
import time
import uuid
from functools import lru_cache
from pathlib import Path

INTENSITY_CSV = "yeast_cell_intensity.csv"
QC_CSV = "yeast_mask_qc.csv"
OVERLAY_PNG = "yeast_segmentation_overlay.png"
MASK_TIFF = "yeast_cell_masks.ome.tif"
MANIFEST_JSON = "yeast_analysis_manifest.json"
PROGRESS_JSON = "yeast_analysis_progress.json"

# Whitelist for downloads: public file name -> (directory key, content type)
DOWNLOADS = {
    INTENSITY_CSV: ("results", "text/csv"),
    QC_CSV: ("results", "text/csv"),
    MANIFEST_JSON: ("results", "application/json"),
    OVERLAY_PNG: ("results", "image/png"),
    MASK_TIFF: ("processed", "image/tiff"),
}


def yeast_data_root() -> Path:
    from django.conf import settings

    return Path(
        getattr(
            settings,
            "YEAST_FLIM_DATA_ROOT",
            Path.home() / "01_Experimental" / "02_Experiments" / "01_Main_Exp"
            / "03_Leica_Microscope" / "01_Yeast_FLIM" / "01_Videos",
        )
    ).expanduser().resolve()


def result_dirs(entry) -> tuple[Path, Path]:
    """Return (analysis results directory, processed data directory) of an entry."""
    experiment_root = yeast_data_root().parent
    date_folder = entry.Date_time.strftime("%Y%m%d")
    return (
        experiment_root / "02_Analysis_Results" / date_folder / f"YFL_{entry.pk}",
        experiment_root / "03_Processed_Data" / date_folder / f"YFL_{entry.pk}",
    )


def artifact_path(entry, filename: str) -> Path | None:
    spec = DOWNLOADS.get(filename)
    if spec is None:
        return None
    results_dir, processed_dir = result_dirs(entry)
    return (results_dir if spec[0] == "results" else processed_dir) / filename


def read_manifest(results_dir: Path) -> dict | None:
    path = results_dir / MANIFEST_JSON
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _csv_stats(path: Path) -> dict[str, int]:
    times: set[int] = set()
    cells: set[int] = set()
    rows = 0
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                times.add(int(row["time_index"]))
                cells.add(int(row["cell_id"]))
            except (KeyError, TypeError, ValueError):
                continue
            rows += 1
    return {"rows": rows, "timepoints": len(times), "cells": len(cells)}


@lru_cache(maxsize=16)
def _csv_stats_cached(path: str, mtime_ns: int, size: int) -> dict[str, int]:
    return _csv_stats(Path(path))


def inspect_results(entry) -> dict:
    """Summarise which artifacts exist and whether the run is complete.

    state: ``none`` (no artifacts), ``partial`` (artifacts but no verified complete
    run), or ``complete`` (manifest marks completion and the CSV matches it).
    """
    results_dir, processed_dir = result_dirs(entry)
    files = {
        name: artifact_path(entry, name) for name in DOWNLOADS
    }
    present = {name: bool(path and path.is_file()) for name, path in files.items()}
    manifest = read_manifest(results_dir)
    messages: list[tuple[str, str]] = []
    status = getattr(entry, "Analysis_Status", "")
    if getattr(entry, "Analysis_Error", None):
        messages.append(("danger", f"Analyse-Fehler: {entry.Analysis_Error}"))

    stats = None
    csv_file = files[INTENSITY_CSV]
    if present[INTENSITY_CSV]:
        stat = csv_file.stat()
        stats = _csv_stats_cached(str(csv_file), stat.st_mtime_ns, stat.st_size)

    if not any(present.values()):
        state = "none"
        if status == "completed":
            messages.append((
                "danger",
                f"Status „Completed“, aber im Ergebnisordner {results_dir} liegen keine Dateien.",
            ))
        else:
            messages.append(("warning", "Noch keine Analyseergebnisse vorhanden."))
    else:
        completeness = (manifest or {}).get("completeness") or {}
        complete = (
            manifest is not None
            and manifest.get("status") == "complete"
            and stats is not None
            and stats["rows"] == completeness.get("expected_intensity_rows")
            and stats["timepoints"] == completeness.get("signal_timepoints")
            and all(present[name] for name in DOWNLOADS)
        )
        state = "complete" if complete else "partial"
        if not complete:
            missing = [name for name, ok in present.items() if not ok]
            detail = []
            if manifest is None:
                detail.append("Es gibt kein Abschluss-Manifest (yeast_analysis_manifest.json)")
            elif manifest.get("status") != "complete":
                detail.append("Das Manifest ist nicht als abgeschlossen markiert")
            if missing:
                detail.append("fehlende Dateien: " + ", ".join(missing))
            if stats is not None and completeness:
                detail.append(
                    f"CSV enthält {stats['timepoints']} von "
                    f"{completeness.get('signal_timepoints')} Zeitpunkten"
                )
            messages.append((
                "danger",
                "Ergebnisse sind unvollständig und dürfen nicht als Abschluss gewertet "
                "werden. " + "; ".join(detail) + ".",
            ))

    if manifest:
        registration = manifest.get("registration") or {}
        if not registration:
            messages.append((
                "warning",
                "Keine Registrierungs-/Stage-Position-Metadaten im Manifest: Die räumliche "
                "Übereinstimmung von Referenzbild und Zeitserie ist nicht belegt.",
            ))
        else:
            messages.append((
                "info" if registration.get("stage_positions_equal_within_half_pixel") else "warning",
                "Registrierung: " + str(registration.get("status", "nicht angegeben")),
            ))
    return {
        "state": state,
        "files": files,
        "present": present,
        "manifest": manifest,
        "csv_stats": stats,
        "results_dir": results_dir,
        "processed_dir": processed_dir,
        "messages": messages,
    }


# ---------------------------------------------------------------------------
# Live progress reported by the running task (file in the results directory, so
# no database field or migration is needed).
# ---------------------------------------------------------------------------

HEARTBEAT_INTERVAL_S = 5.0
# A live task rewrites its progress file every HEARTBEAT_INTERVAL_S from a helper
# thread; a hard worker kill stops that thread together with the process.
STALE_AFTER_S = 90.0

PHASE_LABELS = {
    "queued": "Eingereiht, wartet auf einen Worker",
    "lif_read": "LIF-Datei lesen und Serie exportieren",
    "segmentation": "Referenzbild segmentieren (Cellpose) und Masken speichern",
    "quantification": "Zeitserie quantifizieren",
    "finalizing": "Ergebnisse prüfen und schreiben",
}
STEP_ORDER = ["lif_read", "segmentation", "quantification", "finalizing"]


def progress_path(entry) -> Path:
    return result_dirs(entry)[0] / PROGRESS_JSON


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, allow_nan=False)
    os.replace(tmp, path)


def read_progress(entry) -> dict | None:
    try:
        with progress_path(entry).open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def new_run_id() -> str:
    return uuid.uuid4().hex


def write_queued(entry, run_id: str) -> None:
    now = time.time()
    _write_json_atomic(progress_path(entry), {
        "run_id": run_id, "phase": "queued", "queued_at": now, "updated_at": now,
        "started_at": None, "done": None, "total": None, "pid": None,
    })


class ProgressReporter:
    """Written by the task itself; ``update`` is called at real processing steps."""

    def __init__(self, entry, run_id: str | None):
        self.path = progress_path(entry)
        self.lock = threading.Lock()
        now = time.time()
        previous = read_progress(entry) or {}
        self.state = {
            "run_id": run_id, "phase": "lif_read", "queued_at": previous.get("queued_at"),
            "started_at": now, "updated_at": now, "done": None, "total": None,
            "pid": os.getpid(),
        }
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._write()

    def _write(self) -> None:
        with self.lock:
            self.state["updated_at"] = time.time()
            try:
                _write_json_atomic(self.path, dict(self.state))
            except (OSError, ValueError):
                pass  # progress is informational and must never break the analysis

    def update(self, phase: str, done: int | None = None, total: int | None = None) -> None:
        with self.lock:
            self.state.update(phase=phase, done=done, total=total)
        self._write()

    def start(self) -> None:
        def beat():
            while not self._stop.wait(HEARTBEAT_INTERVAL_S):
                self._write()
        self._thread = threading.Thread(target=beat, name="yfl-heartbeat", daemon=True)
        self._thread.start()

    def finish(self, phase: str, error: str | None = None) -> None:
        self._stop.set()
        with self.lock:
            self.state.update(phase=phase, error=error)
        self._write()


def task_superseded_or_duplicate(entry, run_id: str | None) -> str | None:
    """Return a reason if this task delivery must not run (newer run or live duplicate)."""
    progress = read_progress(entry)
    if not run_id or not progress or not progress.get("run_id"):
        return None
    if progress["run_id"] != run_id:
        return "Dieser Task wurde durch einen neueren Analyselauf ersetzt."
    if progress.get("phase") not in {"queued", "done", "failed"} and (
        time.time() - float(progress.get("updated_at") or 0) <= STALE_AFTER_S
    ):
        return "Derselbe Lauf wird bereits von einem anderen Worker ausgeführt."
    return None


def _q_settings() -> tuple[float | None, float | None]:
    from django.conf import settings

    q = getattr(settings, "Q_CLUSTER", {}) or {}
    timeout = getattr(settings, "YEAST_FLIM_TASK_TIMEOUT", None) or q.get("timeout")
    retry = q.get("retry")
    return (float(timeout) if timeout else None, float(retry) if retry else None)


def live_status(entry) -> dict:
    """Combine DB status, task heartbeat and artifact check into one JSON-able status.

    state: not_started | queued | running | completed | failed. A run is
    ``completed`` only if the DB says so AND the artifacts verify as complete.
    """
    from Exp_Main.models import YFL

    timeout_s, retry_s = _q_settings()
    now = time.time()
    status = entry.Analysis_Status
    progress = read_progress(entry)
    out = {
        "state": "not_started", "level": "secondary", "label": "Nicht gestartet",
        "phase": None, "step_label": None, "done": None, "total": None,
        "fraction": None, "elapsed_s": None, "heartbeat_age_s": None,
        "message": "", "active": False, "restart_allowed": True,
        "progress_available": progress is not None,
        "steps": [{"key": k, "label": PHASE_LABELS[k]} for k in STEP_ORDER],
        "results_state": None,
    }

    if status == YFL.AnalysisStatus.QUEUED:
        out.update(state="queued", level="info", label="Eingereiht", active=True,
                   step_label=PHASE_LABELS["queued"], restart_allowed=False)
        queued_at = (progress or {}).get("queued_at")
        if queued_at and (progress or {}).get("phase") == "queued":
            age = now - float(queued_at)
            out["elapsed_s"] = age
            if retry_s and age > retry_s:
                out.update(restart_allowed=True, level="warning", message=(
                    f"Der Job wartet seit {int(age // 60)} min auf einen Worker. Läuft "
                    "`manage.py qcluster`? Ein erneuter Start ersetzt den wartenden Job sicher."))
        return out

    if status == YFL.AnalysisStatus.RUNNING:
        out.update(state="running", level="primary", label="Läuft", active=True,
                   restart_allowed=False)
        if progress is None:
            out["message"] = ("Der Lauf meldet keinen Fortschritt (gestartet mit einer älteren "
                              "Programmversion). Es ist nur der Status bekannt.")
            return out
        phase = progress.get("phase")
        updated = float(progress.get("updated_at") or 0)
        started = progress.get("started_at")
        age = now - updated
        out["heartbeat_age_s"] = age
        if started:
            out["elapsed_s"] = now - float(started)
        if phase in PHASE_LABELS:
            out["phase"] = phase
            out["step_label"] = PHASE_LABELS[phase]
        done, total = progress.get("done"), progress.get("total")
        if phase == "quantification" and isinstance(done, int) and isinstance(total, int) and total > 0:
            out.update(done=done, total=total, fraction=done / total)
        if phase in {"done", "failed"} or age > STALE_AFTER_S:
            run_s = (updated - float(started)) if started else None
            hint = ""
            if timeout_s and run_s is not None and abs(run_s - timeout_s) <= 30:
                hint = (f" Die Laufzeit ({int(run_s)} s) entspricht dem Worker-Zeitlimit von "
                        f"{int(timeout_s)} s – der Worker hat den Task vermutlich beendet.")
            text = (f"Analyse abgebrochen: Der Worker hat seit {int(age)} s kein Lebenszeichen "
                    f"mehr gesendet (letzter Schritt: {PHASE_LABELS.get(phase, phase)}"
                    + (f", {done} von {total} Zeitpunkten" if done is not None and total else "")
                    + f").{hint} Es wurden keine vollständigen Ergebnisse erzeugt; ein erneuter Start ist möglich.")
            updated_rows = YFL.objects.filter(
                pk=entry.pk, Analysis_Status=YFL.AnalysisStatus.RUNNING
            ).update(Analysis_Status=YFL.AnalysisStatus.FAILED, Analysis_Error=text)
            if updated_rows:
                entry.Analysis_Status = YFL.AnalysisStatus.FAILED
                entry.Analysis_Error = text
                status = YFL.AnalysisStatus.FAILED
            else:
                return out
        else:
            return out

    results = inspect_results(entry)
    out["results_state"] = results["state"]
    if status == YFL.AnalysisStatus.FAILED:
        out.update(state="failed", level="danger", label="Fehlgeschlagen",
                   message=entry.Analysis_Error or "Die Analyse ist fehlgeschlagen.")
        return out
    if status == YFL.AnalysisStatus.COMPLETED:
        if results["state"] == "complete":
            out.update(state="completed", level="success", label="Abgeschlossen")
        else:
            out.update(state="failed", level="danger", label="Fehlgeschlagen / unvollständig",
                       message="Der Status lautet „abgeschlossen“, die Ergebnisdateien sind aber "
                               "unvollständig oder fehlen. Der Lauf gilt nicht als abgeschlossen.")
        return out
    if results["state"] != "none":
        out["message"] = "Es liegen Dateien eines früheren, nicht verifizierten Laufs vor."
    return out
