# Import from libraries
import time
from machine import Pin

pin_input = Pin(27, Pin.IN)

# Runs Forever
while True:
    value = pin_input.value()
    if value == 1:
        print("No vibration detected...")
    else:
        print("Vibration detected...")
    time.sleep_ms(100)
