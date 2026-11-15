# User guide

This guide follows the workflow used in the paper (Methods, *Deep-learning, semantic segmentation of cell
nuclei*; Fig. S4 H–R). Menu names are from Dragonfly 2024.1; later versions may move items slightly.

## 0. Requirements

- Dragonfly **2024.1 or newer** with the Deep Learning Tool. A free non-commercial licence is available from
  Comet Technologies. Sessions saved in 2024.1 cannot be reopened in 2022.x.
- A CUDA-capable NVIDIA GPU is recommended. CPU inference works but is slow on whole membranes.
- Python ≥ 3.9 with `numpy`, `scipy`, `matplotlib` for the post-processing scripts
  (`pip install -r scripts/requirements.txt`).

## 1. Prepare the images

1. Scan H&E slides at 20× (≈0.5 µm/px). The paper used a Leica Aperio AT2 (0.503 µm/px).
2. For sections that are not flat, scan several focal planes and merge them into one extended-depth-of-field
   image (the paper used 5–11 planes merged with the PMax algorithm in Zerene Stacker).
3. Crop the region with the cochlea (mid-modiolar section) or the saccule (section with its largest extent),
   e.g. in QuPath, and export as a 24-bit RGB TIFF or high-quality JPEG **at full resolution**.

## 2. Import into Dragonfly

1. *Preferences → Default unit → micrometers* (do this before loading anything, so areas and lengths come out
   in µm).
2. *File → Import Image Files → Add*, select the image(s), *Next*.
3. Set *Image Spacing* X = Y = Z = your pixel size (0.503 in the paper). Optionally tick *Invert Y axis*.
4. *Finish*. Dragonfly splits the RGB image into three channels. **Delete the green and blue channels**; the
   model works on the red channel only. Several images can be imported as one stack: each image becomes one
   slice (Z position), which is how the scripts tell images apart later.

## 3. Mark the analysis region

For each membrane segment (e.g. each cochlear half-turn I–V, or the saccule):

1. **Endolymph space ROI** (`s I`, `s II`, …): *Segment → ROI Painter → Point & Click*, Ctrl-click in the
   endolymph space next to the membrane; close gaps with *Morphological operations → Close* (kernel 11) and
   fill the rest with the brush.
2. **Dilate the endolymph ROI**: *Morphological operations*, dimensionality 2D, kernel **19**, *Dilate*. This band
   reaches across the epithelium and defines which nuclei are counted.
3. **Membrane ROI** (`r I`, …): new ROI, paint generously over the whole membrane with a large brush.

## 4. Apply the model

1. *Artificial Intelligence → Deep Learning Tool*.
2. Drag `RM-SM_nuclei_UNet_Dragonfly2024.1.ORSModel` into the model list; it loads as
   *Reissner_1 (+training dataset 2)*.
3. *Apply* → input = the red-channel image → *With Mask* → select the membrane ROI → *OK*.
4. The result is a two-class multi-ROI. Select it, select the background class (*Class 1*) and *Remove*.
5. Right-click the remaining ROI → *Connected Components → New Multi-ROI (6-connected)*; name it `ep I`.
   Delete the intermediate ROI.

## 5. Keep only epithelial nuclei

1. Ctrl-click `ep I` (A) and the dilated endolymph ROI `s I` (B) → *Boolean operations* → destination `ep I` →
   **Keep intersected**. Nuclei not touching the dilated endolymph band are removed.
2. Right-click `ep I` → *Compute Measurements → 2D Measurements* → tick *2D Max Feret* and *Voxel count* →
   *Compute*.
3. Right-click `ep I` → *Connected components → Analysis…*
   - sort by *Voxel count*, select all objects **< 10 voxels** (dust, debris) → *Delete from ROI*;
   - sort by *2D Max Feret*, select all objects **> 10 µm** (flat, elongated mesenchymal nuclei, and merged
     nuclei of tangentially cut epithelium) → *Export to → Multi-ROI* named `me I` → then *Delete from ROI*.

## 6. Export centroids

1. Right-click `ep I` → *Generate Centroids*; right-click the centroids → *Export → Data to file…*.
2. Use a consistent file name, e.g. `<case>_<slide>_ep I.csv`. The file is semicolon-separated with columns
   `Name;Unit;Caption;PosX;PosY;PosZ` in µm.
3. Optionally do the same for `me I`.
4. Repeat for each membrane segment, then *File → Save Session As…* to keep the annotated session.

## 7. Order centroids and measure

```bash
python scripts/order_and_measure.py exports/ --pattern "*_ep*.csv" -o results --plot --start-at max-y
```

For every file and every image (PosZ) the script:

1. orders the centroids into one path along the membrane (nearest-neighbour from every possible start, then
   2-opt refinement);
2. orients the path so that position 0 is at the end chosen with `--start-at` (`max-y`, `min-y`, `left`,
   `right`). In the paper RM ran limbal → strial and SM posterior → anterior; pick whichever image direction
   that is for your sections, and **check the PNGs** (`--plot`) — the start is marked in red;
3. writes `<file>_ordered.csv` (order, coordinates, distance to previous nucleus) and a `summary.csv` with cell
   count, membrane length (sum of internuclear distances), mean ± SD spacing, and nuclei/spacing for 10
   equal-length segments (change with `--segments`).

The per-segment values are what the heat maps in Figs. 2, 3 and S2 show. In the paper each specimen value is the
mean of 2–3 non-consecutive sections.

Try it on the included example:

```bash
python scripts/order_and_measure.py examples/centroids/control_RM_halfturn_IV.csv -o /tmp/demo --plot
# -> n=44, length ≈ 759 µm, mean spacing ≈ 17.7 µm
```

## 8. Check your results

Before analysing a new dataset, validate the model on it:

1. Pick 3–5 representative images. In Dragonfly, have one or more people point-label every epithelial nucleus
   inside the dilated endolymph band (small brush, one dot per nucleus), export as centroids.
2. Run the model pipeline (steps 4–6) on the same images.
3. `python scripts/validate_against_annotations.py --model model.csv --reference rater1.csv rater2.csv`
   (add `--mode per-image --radius 5` to match within each image, one-to-one).
4. With two or more annotators, also run `--pairwise` on the human files, so model–human agreement can be
   compared with human–human agreement. See [VALIDATION.md](VALIDATION.md).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Model will not load | Dragonfly older than 2024.1 |
| Almost nothing segmented | Applied to the green/blue channel or the RGB composite; or wrong pixel spacing (image far from 0.5 µm/px) |
| Background tissue segmented as nuclei | No mask used, or mask painted far beyond the membrane |
| Many merged/elongated objects | Tangential section through the membrane; these are removed by the Feret > 10 µm step |
| Path in PNG jumps across the membrane | Two membrane segments in one file, or a folded membrane; split the ROI and export separately |
