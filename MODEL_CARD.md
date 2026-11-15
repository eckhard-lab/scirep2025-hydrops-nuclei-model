# Model card — RM/SM nucleus U-Net (Dragonfly 2024.1)

## Identity

| | |
|---|---|
| File | `model/RM-SM_nuclei_UNet_Dragonfly2024.1.ORSModel` |
| SHA-256 | `00a93ead37a3e919dbfe36cb24f79a001e86cdce18abb7f3dde1bcc4acbb74ad` |
| Name inside Dragonfly | `Reissner_1 (+training dataset 2)` (lab file name: *Reissner_1_trained with training dataset 1+2*) |
| Model UUID | `84b7e072f6bb11ee859bb04f13109d43` |
| Saved | 2024-04-10 07:41 (weights from stage-2 checkpoint, epoch 29) |
| Software | Dragonfly 2024.1.0.1579, Deep Learning Tool (TensorFlow/Keras back end) |
| Version | 1.0.0 — the model used for all counts in Bryton, Correa et al., *Sci Rep* 2025 |

## Architecture

- 2D U-Net, depth 5, 64 initial filters, 21,958,050 trainable parameters.
- Input: one channel, 64 × 64 px patches, intensity range 0–255 mapped linearly to 0–1.
- Output: 2 classes, softmax, same size as input. In Dragonfly the classes are called *Class 1* and
  *Class 2*; **Class 1 = background, Class 2 = nucleus**.

## Input requirements

| Property | Training data | Notes |
|---|---|---|
| Stain | Hematoxylin & eosin | 40+ years of archival staining, including faded and yellowed slides |
| Tissue | Human temporal bone, formalin-fixed, EDTA-decalcified, celloidin-embedded, 20 µm sections | Mass Eye and Ear archive |
| Scanner | Leica Aperio AT2, 20× Plan-Apo | Uneven ("wavy") sections: 5–11 focal planes merged by PMax (Zerene Stacker) |
| Pixel size | 0.503 µm | Rescale other data to ~0.5 µm/px |
| Channel | **Red channel of the RGB image only** | Green and blue deleted on import |
| Region | RM and SM, masked by a hand-painted ROI | The model was never shown whole sections |

## Training data

- Manually painted nuclei in RM and SM from archival human specimens; the paper reports 2,342 annotated nuclei
  from 20 specimens.
- Two datasets, trained in sequence (details in [docs/TRAINING.md](docs/TRAINING.md)):
  1. *Dataset 1* — more recent sections.
  2. *Dataset 2* — older, artefact-prone sections (fading H&E, yellowed mounting medium), added so the model
     learns to ignore these artefacts.
- Validation during training: 20 % random split of the labelled pixels (Dragonfly "voxel validation").
  The independent test set is described under Evaluation.
- **The training images are not distributed**: they are images of human donor tissue. The model file contains
  only network weights and training metadata.

## Training procedure

| | Stage 1 | Stage 2 (fine-tune, saved model) |
|---|---|---|
| Data | Dataset 1 | Datasets 1 + 2 |
| Patch / batch | 64 × 64 / 32 | 64 × 64 / 32 |
| Augmentation | ×10: flips, rotation ±180°, shear 45°, zoom 0.9–1.1, brightness 0.6–1.4 | ×5, same transforms |
| Loss / optimiser | categorical cross-entropy / Adam, lr 1e-3, β₁ 0.99 | same |
| LR schedule | reduce on plateau ×0.75, patience 20 | same |
| Epochs run | 218 (stopped manually) | 68 (stopped manually) |
| Weights kept | — | best `val_loss`, epoch 29 |

## Evaluation

Independent test set: 5 RM images not used for training, with nuclei point-annotated by three investigators as
ground truth. Annotators labelled the nuclei that fall inside the dilated-endolymph analysis mask, so the test
covers the model together with its post-processing. Model centroids were matched to each investigator's
annotations by nearest-neighbour search (Fig. S4F–G).

| | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|
| Mean ± SD over 3 investigators | 0.96 ± 0.01 | 0.92 ± 0.02 | 0.94 ± 0.01 | 0.89 ± 0.01 |

Details and how to reproduce: [docs/VALIDATION.md](docs/VALIDATION.md).

## Intended use

Counting and spacing of epithelial nuclei along RM and SM in H&E-stained human temporal bone sections, within a
hand-drawn ROI, for research.

## Out-of-scope / known limitations

- **Not validated on** other stains (IHC, toluidine blue), other species (mouse, guinea pig), plastic-embedded or
  paraffin sections, or pixel sizes far from 0.5 µm. Re-validate before use; fine-tune if needed.
- **Validated on RM only.** SM nuclei were included in training and analysed in the paper, but the independent
  test set contained only RM images.
- **Severe hydrops.** Where RM/SM folds or touches other tissue, nuclei are harder to separate and some are missed,
  which inflates spacing. The paper discusses this as the likely cause of the weak spacing–length correlation.
- **Touching nuclei** may be merged into one object; tangentially cut membranes show several nuclear rows. The
  post-processing (dilated endolymph mask, Feret > 10 µm exclusion) limits counting to one row.
- **The model does not distinguish epithelial from mesenchymal nuclei.** That is done by the post-processing.
- Results depend on the scanner, focus merging, and the red-channel conversion. Keep these constant within a study.

## Ethical considerations

Training images came from archival post-mortem human temporal bones collected with informed consent (Mass Eye
and Ear IRB #2021P001593 and #2019P003755). The model file contains only network weights and training metadata;
it contains no images or donor information.

## Citation

Bryton C, Correa DM, et al. *Sci Rep* 15, 40801 (2025). https://doi.org/10.1038/s41598-025-24549-9 · PMID 41257965 · PMCID PMC12630622
