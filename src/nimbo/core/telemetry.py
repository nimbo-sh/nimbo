import json
from datetime import datetime

import requests

from nimbo import CONFIG


# noinspection PyBroadException
def record_event(cmd):
    if not CONFIG.telemetry:
        return
    else:
        if not CONFIG.user_id:
            raise ValueError("CONFIG.user_id is undefined.")

    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d-%H-%M-%S")

    data = {
        "user_id": CONFIG.user_id,
        "user_arn": CONFIG.user_arn,
        "cmd": cmd,
        "date": date_time,
    }
    try:
        requests.post(CONFIG.telemetry_url, data=json.dumps(data), timeout=2)
    except BaseException:
        pass
