"""Train the YOLOv8 defect detector on the NEU-DET dataset (YOLO format).

Run it on a GPU machine such as Google Colab. Example:
    python train.py --data /content/machine_02_steel/data_colab.yaml

The best weights are written to runs/gentwin/steel/weights/best.pt, and the model is then
evaluated on the held-out test split.
"""
import argparse

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="path to the dataset yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--project", default="runs/gentwin")
    parser.add_argument("--name", default="steel")
    args = parser.parse_args()

    model = YOLO("yolov8n.pt")  # nano model: small and fast enough for real-time use
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=args.project,
        name=args.name,
        exist_ok=True,
    )

    best = YOLO(f"{args.project}/{args.name}/weights/best.pt")
    best.val(data=args.data, split="test")


if __name__ == "__main__":
    main()
