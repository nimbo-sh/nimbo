import os
import json
import requests
from datetime import datetime


def record_event(cmd, config):
    user_id = config["user_id"]

    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d-%H-%M-%S")

    url = f"https://nimbotelemetry-8ef4c-default-rtdb.firebaseio.com/events.json"
    data = {"user_id": user_id, "cmd": "run", "date": date_time}
    try:
        r = requests.post(url, data=json.dumps(data), timeout=2)
    except:
        pass
