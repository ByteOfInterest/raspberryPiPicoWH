from machine import Pin
import time

pin_input = Pin(27, Pin.IN)

while True:
    value = pin_input.value()
    if value == 1:
        print("No vibration detected...")
    else:
        print("Vibration detected...")
    time.sleep_ms(100)