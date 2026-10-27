# Yeast FLIM analysis in the labbook

`YFL` is a separate main-experiment type for yeast FLIM. It does not use the
MFP model, ND2 loader, polymer-sphere tracking, circularity filters, or the
existing MFP analysis database record.

## Setup

1. Install the optional microscopy dependencies in the labbook venv with
   `pip install -r requirements_nd2.txt` (includes Cellpose and Django-Q).
2. Apply migrations with `python manage.py migrate`. This creates the `YFL`
   experiment type and a device entry at
   `01_Experimental/02_Experiments/01_Main_Exp/03_Leica_Microscope/01_Yeast_FLIM/01_Videos`.
   The experiment has the same three-folder layout as MFP: `01_Videos`,
   `02_Analysis_Results`, and `03_Processed_Data`.
3. Keep acquisitions in date-named subfolders such as
   `.../01_Videos/20261023/Project.lif`. The normal **Generate → Main**
   workflow recognizes `.lif` files for `YFL` and stores an experiment entry.
   It uses the date folder for the date and the file modification time for the
   time of day; it does not rename the source acquisition.
4. Start the Django-Q worker (`python manage.py qcluster`) before queuing an
   analysis from the YFL experiment page.

If the data root differs from the default `01_Videos` folder, set
`YEAST_FLIM_DATA_ROOT` in the local Django settings to the chosen directory.

## Run an analysis

Place the `.lif` acquisition in the configured yeast data root, normally in a
date-named subfolder such as `01_Videos/20261023/Project.lif`. The normal
**Generate → Main** workflow creates the YFL experiment entry. Open it and
select **Open yeast FLIM Cellpose analysis**; the labbook reads the linked LIF
file directly and does not require a separate LAS X export.

The importer offers only series whose exact image name ends in
`FLIM Compressed/Intensity`, whose stored bit depth is 32-bit float, and whose
unique same-name-prefix reference has compatible XY dimensions. It exports the
selected FLIM time series as float32 OME-TIFF and exports the matching
reference time series separately. The selected reference time index is used
for segmentation. If multiple usable FLIM series are present, none is
preselected: choose the intended series by its full name. The chosen signal
and reference series and indices are recorded in the analysis manifest.

Fast-FLIM, lifetime, phasor, and other Leica maps are not accepted as raw
intensity input. The Float32 samples are retained as stored; this workflow
does not convert them to photon counts or fit a fluorescence lifetime. LIF
series with multiple channels, z planes, or mosaics are not currently offered
because this form does not provide selectors for those dimensions.

Every signal time plane must have the same YX shape as the reference mask.
The LIF importer requires compatible XY dimensions and matching recorded pixel
scales in the associated reference and intensity series. Leica stage positions
are not currently transferred into the generated OME-TIFFs, so this check
cannot prove registration by itself. The paired LIF series should describe the
same field of view; do not use a reference image with a shift, rotation, flip,
or different crop. When using the command-line workflow with separately
exported OME-TIFFs, available physical pixel sizes and stage positions are
compared and mismatches stop analysis. The alignment checks and missing
metadata are recorded in the run manifest.

The default is Cellpose `cpsam_v2`, a general built-in model with an updated
training fix for low-contrast regions, a useful starting point for yeast
boundaries. `cpsam` and `cpdino` are also available as general built-in models.
Custom checkpoints, including the MFP/Polymersome model, are not accepted.
Choose an optional diameter in pixels based on apparent yeast-cell width in
the reference image; leave it blank to let Cellpose use its default scale
handling. The grayscale reference is explicitly normalized and resampled by
Cellpose. The web workflow uses `cellprob_threshold=0.0` and
`flow_threshold=0.4`. Minimum area defaults to 1 px² and maximum area is
optional; adjust these cleanup bounds to the image resolution and inspect the
QC files rather than treating them as universal yeast sizes. The local
background ring defaults to 3 px.

One mask is generated from the reference plane and reused unchanged for every
signal time point, so changing intensity does not change cell boundaries.
Budding yeast are not removed by circularity or eccentricity filters. The raw
signal array is read-only for measurement; segmentation is run only on the
separate reference image. Measurements preserve the values stored in the
signal TIFF; background-corrected values subtract the median in a local ring
that excludes all cell masks.

For command-line use, provide both output directories and all non-default
indices/parameters explicitly, for example:

```sh
python Analysis/scripts/Yeast_FLIM_Cellpose.py \
  --segmentation /path/to/01_Videos/reference.ome.tif \
  --signal /path/to/01_Videos/raw-intensity.ome.tif \
  --output /path/to/02_Analysis_Results/20261023/YFL_123 \
  --processed-output /path/to/03_Processed_Data/20261023/YFL_123 \
  --model cpsam_v2 --seg-time 0 --seg-channel 0 --seg-z 0 \
  --signal-channel 0 --signal-z 0
```

Analysis results are written under
`.../02_Analysis_Results/<YYYYMMDD>/YFL_<experiment id>/`:

- `yeast_cell_intensity.csv`: per-cell area, mean and integrated raw pixel
  values, local-background median, background-corrected values, and background
  pixel count for each signal time index.
- `yeast_segmentation_overlay.png`: reference image with detected cell borders
  in red for visual review.
- `yeast_mask_qc.csv`: per-mask area, centroid, bounding box, image-area
  fraction, and border contact.
- `yeast_analysis_manifest.json`: input paths, size and modification time,
  OME-TIFF axes/shapes/spatial metadata, alignment checks, model/version,
  parameters, cell count, and output paths.

The fixed label image is written separately under
`.../03_Processed_Data/<YYYYMMDD>/YFL_<experiment id>/yeast_cell_masks.ome.tif`.
It has canonical YX axes and retains physical pixel-size metadata when the
reference OME-TIFF supplies it.

CSV values retain the Float32 pixel values stored in the Leica
`FLIM Compressed/Intensity` series. They are not relabeled as photon counts.
A lifetime map, phasor image, or mean photon-arrival-time image is not a raw
intensity series, and this analysis does not fit a fluorescence lifetime.

## Results page

`/Analysis/Yeast_FLIM/<id>/results/` shows a Plotly/Dash view (`Lab_Dash/dash_apps/YFL_Dashboard.py`):
reference image with Original / transparent Cellpose overlay / stored contour PNG,
per-cell and median time courses (area, raw mean, raw integrated, background-corrected
mean and integrated), KPIs, and downloads of the whitelisted artifacts
(`.../download/<filename>/`). It only reads existing artifacts.

### Completeness
The CSV is written to `yeast_cell_intensity.csv.part` and published only after every
time point and cell was written; the manifest is written last with `"status": "complete"`.
Stale outputs are removed when a run starts. A missing manifest, a missing file, a
CSV with fewer time points than expected, or a stored analysis error is reported on
the results page. Django-Q kills tasks after `Q_CLUSTER['timeout']` (600 s in the
project settings); a killed run therefore appears as incomplete. Optionally set
`YEAST_FLIM_TASK_TIMEOUT` (must be smaller than `Q_CLUSTER['retry']`) for this task only.

### Time axis and registration
Real time stamps from the LIF are used only if their number equals the number of
frames; otherwise the frame index is shown. The LIF stores no per-frame drift data:
the fixed masks assume that the series is spatially registered (same stage position
and pixel size are verified, drift is not), which the manifest states.

### Lifetime / phasor
Not provided. The analysed series is raw intensity. Leica Fast FLIM / Phasor maps in
the LIF are processed 16-bit maps with undocumented scaling and an automatic reference,
and only a global decay histogram is stored. A real lifetime or classic FLIM phasor
needs per-pixel photon arrival-time data (or Leica-calibrated lifetime/phasor maps)
with a measured reference of known lifetime. A spectral phasor is a different method.

## Live status

Settings and results pages show not started / queued / running / completed / failed.
The running task writes `yeast_analysis_progress.json` (in the results folder, no DB
field) with its phase (LIF read, segmentation, quantification, finalizing) and the
processed time points `n of N`; a heartbeat thread refreshes it every 5 s. The pages
poll `/Analysis/Yeast_FLIM/<id>/status/` (JSON) every 2 s while active. If a running
job sends no heartbeat for 90 s (e.g. worker killed by the Django-Q timeout) it is
set to `failed` with an explanatory message and can be restarted. Each start carries
a run id, so a stale queued task or a duplicate delivery of an older run is skipped.
"Completed" is shown only if the database status and the verified artifacts agree.
