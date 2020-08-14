"""
This script is used with Heroku scheduler.
It intends to call a wakeup function in the main.py (if necessary, restart the main web dyno)
"""
import os
import requests


SECRET = os.getenv('SECRET', 'mfrw7qy4as-]e0qs-ads;lkfua')

if __name__ == '__main__':
    requests.get(f"https://the-watchman-bot.herokuapp.com/{SECRET}/wakeup/")
