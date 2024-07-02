import sys
from machine import Pin, Timer
import time
import urequests
import keys
import random
import select

# Define pins
vibration_sensor = Pin(28, Pin.IN)
piezo_speaker = Pin(26, Pin.OUT)
led_armed = Pin(13, Pin.OUT)
led_disarmed = Pin(18, Pin.OUT)

# Initial state
system_armed = False
alarm_on = False

# Timer for alarm duration
alarm_timer = Timer()

# Debounce variables
debounce_delay = 100  # in milliseconds
last_vibration_time = 0
last_user_input_time = 0
last_ubidots_update_time = 0
ubidots_request_interval = 2  # seconds (adjust as needed)

# Function to sound the piezo speaker briefly
def sound_piezo():
    piezo_speaker.on()
    time.sleep(0.2)
    piezo_speaker.off()

# Function to sound the alarm
def sound_alarm(timer):
    global alarm_on
    alarm_on = False
    piezo_speaker.off()

# Function to arm the system
def arm_system():
    global system_armed
    if not system_armed:
        system_armed = True
        led_armed.on()
        led_disarmed.off()
        print("System armed")
        send_telegram_message(keys.TELEGRAM_BOT_TOKEN, keys.TELEGRAM_CHAT_ID, "System armed")

# Function to disarm the system
def disarm_system():
    global system_armed, alarm_on
    if system_armed:
        system_armed = False
        alarm_on = False
        piezo_speaker.off()
        led_armed.off()
        led_disarmed.on()
        print("System disarmed")
        send_telegram_message(keys.TELEGRAM_BOT_TOKEN, keys.TELEGRAM_CHAT_ID, "System disarmed")

# Function to send a Telegram message
def send_telegram_message(token, chat_id, message):
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': message
    }
    try:
        response = urequests.post(url, json=data)
        response_data = response.json()
        if response_data.get('ok'):
            print("Notification sent:", response_data)
        else:
            print("Failed to send notification:", response_data.get('description'))
    except Exception as e:
        print("Failed to send notification:", e)

# Function to send data to Ubidots with rate limiting
def send_data_to_ubidots(variable, value):
    global last_ubidots_update_time
    
    # Implement rate limiting
    current_time = time.time()
    if current_time - last_ubidots_update_time < ubidots_request_interval:
        time.sleep(ubidots_request_interval - (current_time - last_ubidots_update_time))
    
    # Update last request time
    last_ubidots_update_time = time.time()
    
    # Send data to Ubidots
    url = f'https://industrial.api.ubidots.com/api/v1.6/devices/{keys.UBIDOTS_DEVICE_LABEL}/{variable}/values'
    headers = {"X-Auth-Token": keys.UBIDOTS_TOKEN, "Content-Type": "application/json"}
    data = {"value": value}
    try:
        response = urequests.post(url, json=data, headers=headers)
        print(f"Data sent to Ubidots: {response.text}")
        return response
    except Exception as e:
        print(f"Failed to send data to Ubidots: {e}")
        return None

# Function to send alarm status to Ubidots
def send_alarm_status_to_ubidots(status):
    value = 1 if status else 0
    send_data_to_ubidots(keys.ALARM_VARIABLE, value)

# Function to send vibration data to Ubidots
def send_vibration_data_to_ubidots(value):
    send_data_to_ubidots(keys.VIBRATION_SENSOR_VARIABLE, value)

# Function to check vibration sensor when armed
def check_vibration():
    global alarm_on, last_vibration_time, last_user_input_time, last_ubidots_update_time
    while system_armed:
        # Read sensor value
        current_time = time.ticks_ms()
        sensor_value = vibration_sensor.value()
        print("Sensor value:", sensor_value)  # Debug print for sensor value
        
        # Debounce logic
        if sensor_value == 0 and current_time - last_vibration_time > debounce_delay:
            last_vibration_time = current_time
            if not alarm_on:
                alarm_on = True
                piezo_speaker.on()
                print("Vibration detected! Alarm sounding.")
                send_telegram_message(keys.TELEGRAM_BOT_TOKEN, keys.TELEGRAM_CHAT_ID, "Vibration detected! Alarm sounding.")
                alarm_timer.init(period=1000, mode=Timer.ONE_SHOT, callback=sound_alarm)
        
        # Send data to Ubidots every 5 minutes
        if time.time() - last_ubidots_update_time > 300:  # 300 seconds = 5 minutes
            value = random_integer()  # Generate random value for vibration
            send_vibration_data_to_ubidots(value)
            last_ubidots_update_time = time.time()
        
        # Wait for 10 seconds before checking vibration again
        time.sleep(10)
        
        # Wait for user input for 7 seconds
        user_input = non_blocking_input(7)  # Wait up to 7 seconds for input
        if user_input:
            handle_user_input(user_input)
            last_user_input_time = time.ticks_ms()
        else:
            print("No user input within 7 seconds. Continuing armed mode.")
            last_user_input_time = time.ticks_ms()  # Reset last input time

# Function to handle user input
def handle_user_input(user_input):
    if user_input.lower() == 'arm' and not system_armed:
        arm_system()
    elif user_input.lower() == 'disarm' and system_armed:
        disarm_system()

# Function to generate random integer between 0 and 100
def random_integer():
    return random.randint(0, 100)

# Non-blocking input function
def non_blocking_input(timeout=None):
    start_time = time.time()
    input_buffer = ''
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            char = sys.stdin.read(1)
            if char == '\n':  # End of input
                break
            input_buffer += char
        else:
            break
    return input_buffer.strip()

# Main loop for user interaction via terminal
try:
    print("System started")
    while True:
        if system_armed:
            check_vibration()
        else:
            user_input = input("Enter 'arm' to arm the system or 'disarm' to disarm the system: ")
            handle_user_input(user_input)

except KeyboardInterrupt:
    # Clean up on keyboard interrupt
    piezo_speaker.off()
    led_armed.off()
    led_disarmed.off()
    print("System shutdown")
