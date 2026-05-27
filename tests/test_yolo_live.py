"""
test_yolo_live.py - Detection YOLO en direct avec bounding boxes
Usage: python3 test_yolo_live.py [index_camera]
Controles: Q=quitter, S=screenshot, +/-=ajuster seuil confiance
"""
import cv2
import sys
import time

index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
seuil = 0.40

from ultralytics import YOLO
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
if not cap.isOpened():
    print(f"ERREUR: Camera {index}")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
cv2.namedWindow("YOLO Live", cv2.WINDOW_NORMAL)
cv2.resizeWindow("YOLO Live", 800, 600)

print(f"YOLO Live camera {index}. Seuil={seuil}")
print("Q=quitter, S=screenshot, +/-=seuil")

# Warmup
time.sleep(2)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, conf=seuil, verbose=False)
    annotated = results[0].plot()

    cv2.putText(annotated, f"Seuil: {seuil:.2f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("YOLO Live", annotated)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        cv2.imwrite(f"yolo_capture_{int(time.time())}.jpg", annotated)
        print("Screenshot sauvegarde!")
    elif key == ord('+') or key == ord('='):
        seuil = min(0.95, seuil + 0.05)
        print(f"Seuil: {seuil:.2f}")
    elif key == ord('-'):
        seuil = max(0.05, seuil - 0.05)
        print(f"Seuil: {seuil:.2f}")

cap.release()
cv2.destroyAllWindows()
