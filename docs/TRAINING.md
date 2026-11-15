# Training record

All values are taken from the Dragonfly training files in `../model/training_logs/` and from the metadata embedded
in the `.ORSModel` file.

## History

| Date | Model | Notes |
|---|---|---|
| 2024-01-29 | earlier pilot in Dragonfly 2022.2 (144 × 144 px patches, 132 training patches) | superseded, not released |
| 2024-04-09 09:56 – 17:39 | **Stage 1** `Reissner_1`, Dataset 1 | 218 epochs, ~7.7 h |
| 2024-04-09 17:58 – 04-10 06:53 | **Stage 2** `Reissner_1 (+training dataset 2)`, Datasets 1 + 2 | 68 epochs, ~12.9 h; best checkpoint (epoch 29) saved |
| 2024-04-10 07:41 | Released model saved | used for all data in the paper |

Both stages ran on one workstation (Dragonfly 2024.1.0.1579). Stage 2 continued from the stage-1 weights.

## Data

| | Stage 1 | Stage 2 |
|---|---|---|
| Total pixels in training images | 807,559,890 | 1,083,692,148 |
| Labelled pixels used | 8,067,217 (1.0 %) | 116,070,783 (10.7 %) |
| Class 1, background | 7,922,131 (98.2 %) | 115,924,756 (99.87 %) |
| Class 2, nucleus | 145,086 (1.8 %) | 146,027 (0.13 %) |
| Training / validation patches (after augmentation) | 39,589 / 3,558 | 194,490 / 32,350 |

Validation = 20 % random split of labelled pixels from the same images (`SPLIT_RANDOM_SEED 0`).

## Hyperparameters

```
architecture       U-Net, 2D, depth 5, 64 initial filters, 21,958,050 parameters
input              64 x 64 x 1 patches, stride ratio 1.0, intensity 0-255 -> 0-1
loss               categorical cross-entropy, uniform class weights
optimiser          Adam, lr 0.001, beta1 0.99, beta2 0.999, epsilon 1e-7
batch size         32
epochs (max)       10,000 (both runs stopped manually)
callbacks          ReduceLROnPlateau(val_loss, factor 0.75, patience 20)
                   EarlyStopping(val_loss, patience 1000, restore_best_weights)
                   ModelCheckpoint(val_loss, save_best_only)
augmentation       stage 1 x10, stage 2 x5; flips H+V, rotation +/-180 deg, shear 45 deg,
                   zoom 0.9-1.1, brightness 0.6-1.4 (no noise, elastic, or jitter)
```

## Learning curves (summary)

| | Stage 1 | Stage 2 |
|---|---|---|
| Best val loss (epoch) | 0.00099 (214) | 0.00026 (28; checkpoint e0029) |
| Dice at best epoch, train / val | 0.66 / 0.70 | 0.62 / 0.60 |

The Dice values are Dragonfly's `ORS_dice_coefficient` on 64 × 64 patches; they are not comparable between
stages (stage 2 has 14× more background) and are not the per-nucleus metrics reported in the paper.

In stage 2 the training loss jumped about tenfold after epoch ~50 and validation metrics then stayed constant,
which suggests the run diverged. Training was stopped and the checkpoint with the lowest validation loss
(epoch 29, well before this point) was kept, so the released weights are not affected.
