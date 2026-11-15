# Validation

## Test set

Five H&E images of Reissner's membrane from archival human cochleae, not used in training, stacked as one
Dragonfly volume (image identity = `PosZ`: 0, 0.503, 1.006, 1.509, 2.012). The analysis mask (dilated endolymph
band, kernel 19) was drawn first. Three investigators then point-labelled every epithelial nucleus that overlapped
both the membrane ROI and the dilated endolymph band, following the same rules the model output is filtered by
(one dot per nucleus; nuclei too blurred to identify left unlabelled).

The anonymised coordinates of the model output and of two of the three investigators are in
`examples/validation_annotations/` (semicolon-separated, `PosX`/`PosY` in µm, `PosZ` = image):

| File | Points |
|---|---|
| `model.csv` | 1,272 |
| `rater_B.csv` | 1,071 |
| `rater_C.csv` | 1,119 |

## Method

As described in the paper (Fig. S4F–G): model centroids were matched to each investigator's annotations with a
KD-tree nearest-neighbour search (match radius 15 µm). Matched model points are true positives, unmatched model
points false positives, and annotations without a matching model point false negatives. Accuracy is defined as
TP / (TP + FP + FN).

## Results (as published)

| Investigator | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|
| 1 | 0.97 | 0.89 | 0.93 | 0.87 |
| 2 | 0.95 | 0.94 | 0.95 | 0.90 |
| 3 | 0.96 | 0.93 | 0.94 | 0.89 |
| **Mean ± SD** | **0.96 ± 0.01** | **0.92 ± 0.02** | **0.94 ± 0.01** | **0.89 ± 0.01** |

## Reproduce

```bash
python scripts/validate_against_annotations.py \
    --model examples/validation_annotations/model.csv \
    --reference examples/validation_annotations/rater_B.csv examples/validation_annotations/rater_C.csv
```

This reproduces the values for investigators 2 and 3.

## Validating on your own data

Before applying the model to a new dataset, annotate a few representative images by hand and compare (see
[USER_GUIDE.md](USER_GUIDE.md#8-check-your-results)). The script also has a `--mode per-image` option that matches
points one-to-one within each image at a radius you choose (`--radius`, in µm), and a `--pairwise` option that
compares annotators with each other, so model–human agreement can be judged against human–human agreement.

## Scope of this validation

- Five Reissner's membrane images from cochlear sections; saccular membrane was not part of the test set.
- The test measures the whole pipeline (model plus post-processing) inside the analysis mask.
