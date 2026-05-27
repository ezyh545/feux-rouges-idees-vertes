"""
test_gpio.py - Test sequentiel des LEDs (Rouge/Jaune/Vert)
Usage: python3 test_gpio.py [NORD|SUD|EST|OUEST]
"""
import time
import sys

DIRECTION = sys.argv[1].upper() if len(sys.argv) > 1 else "NORD"
PINS = {
    'NORD':  {'rouge': 17, 'jaune': 27, 'vert': 22},
    'SUD':   {'rouge': 23, 'jaune': 24, 'vert': 25},
    'EST':   {'rouge': 5,  'jaune': 6,  'vert': 13},
    'OUEST': {'rouge': 19, 'jaune': 26, 'vert': 16},
}

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    pins = PINS[DIRECTION]
    for couleur, pin in pins.items():
        GPIO.setup(pin, GPIO.OUT)

    print(f"Test LEDs {DIRECTION}: R={pins['rouge']}, J={pins['jaune']}, V={pins['vert']}")
    for couleur in ['rouge', 'jaune', 'vert']:
        print(f"  {couleur.upper()} allume...")
        GPIO.output(pins[couleur], GPIO.HIGH)
        time.sleep(2)
        GPIO.output(pins[couleur], GPIO.LOW)
    print("Test termine.")
    GPIO.cleanup()
except ImportError:
    print("Pas sur RPi - simulation")
    for couleur in ['rouge', 'jaune', 'vert']:
        print(f"  [SIM] {DIRECTION} {couleur.upper()} allume (2s)")
        time.sleep(1)
