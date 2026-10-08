from ultralytics import YOLO
import cv2
model=YOLO('yolov8n.pt')
result=model.predict(source='0',show=True,imgsz=320,conf=0.2,iou=0.5)