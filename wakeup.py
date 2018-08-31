"""
This script is used with Heroku scheduler.
It intends to call a wakeup function in the main.py (if necessary, restart the main web dyno)
"""
import requests

if __name__ == '__main__':
    requests.get("https://the-watchman-bot.herokuapp.com/wakeup/")
