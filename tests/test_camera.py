"""
test_camera.py - Test de capture d'une webcam
Usage: python3 test_camera.py [index_camera]
"""
import cv2
import sys

index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
print(f"Test camera index {index}...")

cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
if not cap.isOpened():
    print(f"ERREUR: Camera {index} non disponible")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

ret, frame = cap.read()
if ret:
    cv2.imwrite("test_photo.jpg", frame)
    print(f"Photo sauvegardee: test_photo.jpg ({frame.shape})")
else:
    print("ERREUR: Impossible de lire une frame")

cap.release()
