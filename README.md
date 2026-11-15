# Reissner's & saccular membrane nucleus segmentation (Dragonfly U-Net)

[![Paper](https://img.shields.io/badge/Sci%20Rep-10.1038%2Fs41598--025--24549--9-1f77b4)](https://doi.org/10.1038/s41598-025-24549-9)
[![Licence: CC BY-NC 4.0](https://img.shields.io/badge/model-CC%20BY--NC%204.0-lightgrey)](LICENSE-MODEL)
[![PubMed](https://img.shields.io/badge/PMID-41257965-326599)](https://pubmed.ncbi.nlm.nih.gov/41257965/)

**Model and analysis code for Bryton, Correa et al., *Scientific Reports* 15, 40801 (2025).**

A trained 2D U-Net for [Dragonfly](https://www.theobjects.com/dragonfly/) (Comet Technologies) that segments
cell nuclei in Reissner's membrane (RM) and the saccular membrane (SM) of H&E-stained human temporal bone
sections. This is the exact model used to produce the cell counts and cell-spacing data in:

> Bryton C\*, Correa DM\*, Bächinger D, Fankhauser V, Kamber NC, Zhu MY, O'Malley JT, Hickman TT,
> Robles-Bolivar P, Rauch SD, Eckhard AH. **Hyperplastic growth, not hydrostatic distension, in endolymphatic
> hydrops in humans challenges the classic view of Meniere's disease.** *Scientific Reports* 15, 40801 (2025).
> https://doi.org/10.1038/s41598-025-24549-9 · PMID [41257965](https://pubmed.ncbi.nlm.nih.gov/41257965/) ·
> PMCID [PMC12630622](https://pmc.ncbi.nlm.nih.gov/articles/PMC12630622/) (open access)  (\*equal contribution)

The repository also contains the post-processing scripts used to turn the segmented nuclei into cell counts and
cell spacing along the membrane, and the script and nucleus coordinates used to validate the model against
human annotators.

---

## Contents

| Path | What it is |
|---|---|
| `model/RM-SM_nuclei_UNet_Dragonfly2024.1.ORSModel` | The trained model (88 MB). Load it in Dragonfly 2024.1 or newer. |
| `model/training_logs/` | Dragonfly training parameters (`.json`) and per-epoch logs (`.csv`) for both training stages. |
| `model/SHA256SUMS.txt` | Checksum to verify the download. |
| `MODEL_CARD.md` | What the model does, how it was trained and validated, and its limits. **Read before use.** |
| `docs/USER_GUIDE.md` | Step-by-step manual: image preparation, applying the model in Dragonfly, filtering, export. |
| `docs/TRAINING.md` | Full training record (data, hyperparameters, learning curves). |
| `docs/VALIDATION.md` | Validation against three annotators, and how to repeat it. |
| `scripts/order_and_measure.py` | Orders exported nucleus centroids along the membrane; computes counts, length, spacing, per-segment heat-map values. |
| `scripts/validate_against_annotations.py` | Precision / recall / F1 of model centroids against manual point annotations. |
| `examples/` | Example centroid export and the anonymised validation annotations. |

## Quick start

1. **Get Dragonfly 2024.1 or newer** (free non-commercial licence available from Comet Technologies).
   The model was trained in Dragonfly 2024.1.0.1579 and cannot be opened in Dragonfly 2022.
2. **Download the model**: clone the repository, or open `model/RM-SM_nuclei_UNet_Dragonfly2024.1.ORSModel`
   on GitHub and click *Download raw file*. Check it with `cd model && shasum -a 256 -c SHA256SUMS.txt`.
3. **Prepare your image** so it matches the training data (details in the [user guide](docs/USER_GUIDE.md)):
   - H&E-stained section, brightfield, **0.5 µm/pixel** (20× objective; Aperio AT2 at 0.503 µm/px in the paper);
   - import the RGB image into Dragonfly, set pixel spacing in micrometres, and **keep only the red channel**
     (delete green and blue). The model takes one 8-bit channel.
4. **Paint an ROI over the membrane** you want to analyse, then
   *Artificial Intelligence → Deep Learning Tool*, drag the `.ORSModel` file into the model list,
   *Apply → input = red channel → With Mask → your ROI*.
5. **Clean up** the output exactly as in the paper: keep nuclei touching the dilated endolymph space
   (19 × 19 px kernel), delete objects < 10 px, move objects with 2D max Feret > 10 µm (mesenchymal/flat nuclei)
   to a separate ROI.
6. **Export centroids** and run
   ```bash
   pip install -r scripts/requirements.txt
   python scripts/order_and_measure.py path/to/centroid_csvs -o results --plot
   ```

## Performance

On an independent set of 5 RM images, with manual annotations by three investigators as ground truth
(paper, Fig. S4F–G):

| Precision | Recall | F1 | Accuracy |
|---|---|---|---|
| 0.96 ± 0.01 | 0.92 ± 0.02 | 0.94 ± 0.01 | 0.89 ± 0.01 |

See [docs/VALIDATION.md](docs/VALIDATION.md) for the method and how to reproduce it.

## Data availability

The training and test images are of human donor tissue and are not distributed. The repository contains the
trained model, its training parameters and logs, and nucleus coordinates (no images) for the validation set.

## Intended use and limits (short version)

- Built for **H&E-stained, celloidin-embedded, 20 µm human temporal bone sections**, digitised at 0.5 µm/px.
  Other species, stains, embedding media or resolutions need re-validation and probably fine-tuning.
- Segments **all** nuclei in the masked region (epithelial and mesenchymal). Separating the epithelial layer is
  done by the post-processing steps, not by the model.
- Accuracy drops where hydropic membranes touch or fold against other tissue; nuclei can be missed there, which
  inflates spacing (discussed in the paper's Supplementary Information).
- Research use only. Not a diagnostic device.

Full details: [MODEL_CARD.md](MODEL_CARD.md).

## Citation

If you use the model or scripts, please cite the paper above. A `CITATION.cff` is included, so GitHub's
"Cite this repository" button gives the reference in BibTeX/APA.

```bibtex
@article{Bryton2025hydrops,
  author  = {Bryton, Corey and Correa, Diana M. and B{\"a}chinger, David and Fankhauser, Valentin and
             Kamber, Nicole C. and Zhu, Meng Yu and O'Malley, Jennifer T. and Hickman, Tyler T. and
             Robles-Bolivar, Paula and Rauch, Steven D. and Eckhard, Andreas H.},
  title   = {Hyperplastic growth, not hydrostatic distension, in endolymphatic hydrops in humans
             challenges the classic view of {Meniere's} disease},
  journal = {Scientific Reports},
  volume  = {15},
  pages   = {40801},
  year    = {2025},
  doi     = {10.1038/s41598-025-24549-9},
  pmid    = {41257965},
  pmcid   = {PMC12630622}
}
```

## Licence

- Model weights and documentation: [CC BY-NC 4.0](LICENSE-MODEL)
- Scripts: [MIT](LICENSE)

## Contact

Otopathology Laboratory / Eckhard Lab, Mass Eye and Ear, Harvard Medical School, Boston, MA.
Correspondence: Andreas H. Eckhard — andreas_eckhard@meei.harvard.edu. Questions about the model are welcome as
GitHub issues.

## Funding

NIDCD U24-DC020849 and U24-DC013983; Zürcher Stiftung für das Hören; SNSF MD-PhD scholarship #183978 (D.B.).
