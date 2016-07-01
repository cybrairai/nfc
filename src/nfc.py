#!/bin/python3
import sys
import time
import configparser
import RPi.GPIO as GPIO

import nfc
from api import CybApi
from lcd import LcdDisplay

# Input pins
cancel_button = 37
enter_button = 35
pluss_button = 33
minus_button = 31
# The i2c bus id
bus_id = 1
# Host address of the LCD display
bar_lcd = LcdDisplay(0x28, bus_id) # Large display
customer_lcd = LcdDisplay(0x27,bus_id) # Small display
# API for internsystem
api = None


class Customer:
    def __init__(self, username="", name="", vouchers=0, coffee_vouchers=0):
        self.username = username
        self.name = name
        self.vouchers = vouchers
        self.coffee_vouchers = coffee_vouchers


def setup():
    # Get the config
    config = configparser.ConfigParser()
    config.read(sys.argv[1])

    # Get the API ready
    global api
    api_config = config._sections["api"]
    api = CybApi(
            api_config["username"], api_config["password"],
            api_config["client_id"], api_config["client_secret"]
    )

    # Get the LCD screen ready
    for lcd in bar_lcd, customer_lcd:
        lcd.clean()
        lcd.tick_off()
        lcd.write("Laster systemet...")

    # Get the bong amount inputs ready
    GPIO.setmode(GPIO.BOARD)
    for pin in cancel_button, enter_button, pluss_button, minus_button:
        GPIO.setup(pin, GPIO.IN)

    # Initialize the NFC reader
    nfc.open()


def get_card_id():
    bar_lcd.clean()
    bar_lcd.write("Venter pa kort")
    customer_lcd.clean()
    customer_lcd.write("Venter pa kort")

    return nfc.getid()


def get_customer(card_id):
    username, name = api.get_card_owner(card_id)

    vouchers = 0
    # A NFC card might only be used as a coffee card.
    if username:
        vouchers = api.get_voucher_balance(username)
    coffee_vouchers = api.get_coffee_voucher_balance(card_id)

    return Customer(username, name, vouchers, coffee_vouchers)


def display_info(customer):
    customer_output = "Du har %2d bonger" % customer.vouchers
    if customer.coffee != 0:
        customer_output += " og %2d kaffer" % customer.coffee

    customer_lcd.clean()
    customer_lcd.write(customer_output)

    bar_lcd.clean()
    bar_lcd.write("Navn: %s" % customer.name)
    bar_lcd.set_pointer(0, 1)
    bar_lcd.write("Bonger: %s" % customer.vouchers)
    bar_lcd.set_pointer(0, 2)
    bar_lcd.write("Kaffe: %s" % customer.coffee)


def get_amount():
    amount = 0
    active_button = None # To avoid adding/removing multiple bong in one press.

    while not GPIO.input(enter_button):
        bar_lcd.set_pointer(0, 3)
        bar_lcd.write("Antall bonger: %2d" % amount)
        
        if GPIO.input(cancel_button):
            return 0
        elif GPIO.input(pluss_button) and active_button is not pluss_button:
            amount += 1
            active_button = pluss_button
        elif GPIO.input(minus_button) and active_button is not minus_button and amount > 0:
            amount -= 1
            active_button = minus_button
        else:
            active_button = None
        
    return amount


def register_use(customer, amount):
    # TODO: Registrer bonger
    customer_lcd.clean()
    customer_lcd.write("%2d bonger trukket" % amount)


def countdown(seconds):
    for i in reversed(range(1, seconds+1)):
        customer_lcd.set_pointer(14, 1)
        customer_lcd.write("%2d" % i)
        bar_lcd.set_pointer(18, 0)
        bar_lcd.write("%2d" % i)
        time.sleep(1)

if __name__ == "__main__":
    setup()

    while True:
        # Get customer info
        customer = get_customer(get_card_id())
        if customer is None:
            continue

        # Display info about the customer
        display_info(customer)
        
        # Get amount of bongs to remove
        amount = get_amount()
        if amount is 0:
            continue

        # Remove x amount of bongs from customer
        register_use(customer, amount)

        # Give people some time to read
        countdown(5)
