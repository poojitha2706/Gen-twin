# CV module: steel surface defect detection

Detects six steel surface defects (crazing, inclusion, patches, pitted_surface, rolled-in_scale,
scratches) with YOLOv8n and reports each detection to the backend. One image sends one report,
the most confident detection, unless `--all` is used.

## Setup
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
Create `.env` from `.env.example`:
```
BACKEND_URL=https://gen-twin.onrender.com/anomaly
MACHINE_ID=machine_01
```
Download the trained weights from the team Drive (<PASTE LINK HERE>) and save them as
`models/best.pt`. Weights and datasets are not stored in Git.

## Run
```powershell
python detect.py <image-or-folder> --machine machine_01          # one pass
python detect.py <image-or-folder> --machine machine_01 --loop   # keep cycling (demo mode)
```
Options: `--interval` seconds between images, `--all` send every detection, `--loop` repeat.

## Training
Trained on the NEU-DET dataset converted to YOLOv8 format with Roboflow (1,260 train, 359 valid,
180 test images). Dataset yaml used on Colab:
```yaml
path: /content/machine_02_steel
train: train/images
val: valid/images
test: test/images
nc: 6
names: ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches']
```
Run `python train.py --data <yaml>` on a GPU (50 epochs, 640 px, batch 16, about 17 minutes on a
Colab T4).

## Results (held-out test set, 180 images)
| Class | Precision | Recall | mAP50 |
|---|---|---|---|
| patches | 0.779 | 0.897 | 0.889 |
| pitted_surface | 0.693 | 0.788 | 0.861 |
| scratches | 0.710 | 0.823 | 0.828 |
| inclusion | 0.709 | 0.757 | 0.773 |
| rolled-in_scale | 0.628 | 0.612 | 0.667 |
| crazing | 0.578 | 0.267 | 0.417 |
| **All** | **0.683** | **0.690** | **0.739** |

Inference takes about 6 ms per image. Crazing is the weakest class: it is faint, fine-grained
cracking and the model misses most of it. The test set is small (25 to 40 images per class), so
per-class numbers are noisy.
