# MLP Training & Deployment Troubleshooting

> Load this when: training diverges, metrics look wrong, or a deployed model misbehaves in MD.

| Symptom | Likely cause | Fix |
|---|---|---|
| Loss becomes NaN early in training | learning rate too high, or corrupted frames (energy spikes from unconverged DFT) | filter the dataset for outlier energies/forces first; then lower start_lr |
| Held-out metrics look good but MD explodes | training/test distributions are too narrow or deployment mapping/units are wrong | verify engine mapping and units; add representative perturbed/state-point frames; revalidate physics and dynamics |
| Energy RMSE fine, force RMSE terrible | label noise (loose EDIFF in labeling DFT) or loss prefactors skewed | relabel with EDIFF ≤ 1e-6; check force-loss weighting |
| Per-system constant energy offset in parity plot | inconsistent DFT settings across dataset chunks, or E0/bias handling | verify all labels share one method fingerprint; fix E0s (MACE) |
| MACE fine-tune degrades on general structures | catastrophic forgetting from too-aggressive fine-tuning | lower LR, fewer epochs, early-stop on a validation set that includes general structures |
| GPU OOM during training | batch size / model size / r_max too large | reduce batch size first; then model channels; r_max last (physics) |
| Validation loss plateaus far above training loss | overfitting (small dataset) | more data > regularization; foundation-model fine-tune instead of from-scratch |

When the cause is data (it usually is): fix the dataset and retrain — do not paper over label problems with longer training.

For DeePMD-specific symptoms (`dp train`, `type_map`, frozen/compressed models, or
model deviation), use `tools/deepmd/references/errors.md`.
