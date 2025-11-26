from ultralytics import YOLO

model = YOLO('yolo_coral_training/run_720/weights/best.pt')

# Export specifically for Edge TPU
model.export(
    format='edgetpu',
    imgsz=320,
    data='/home/ryuugami/dev/python/drone/Dumpsite-Detection-1/data.yaml'
)