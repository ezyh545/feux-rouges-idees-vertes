"""
test_video.py - Flux video brut (sans YOLO)
Usage: python3 test_video.py [index_camera]
Controles: Q = quitter
"""
import cv2
import sys

index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(index, cv2.CAP_V4L2)

if not cap.isOpened():
    print(f"ERREUR: Camera {index} non disponible")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
cv2.namedWindow("Video brut", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Video brut", 800, 600)

print(f"Flux video camera {index}. Q pour quitter.")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("Video brut", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
