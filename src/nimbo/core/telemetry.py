import json
from datetime import datetime

import requests

from nimbo.core.globals import CONFIG


# noinspection PyBroadException
def record_event(cmd):
    if not CONFIG.telemetry:
        return

    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d-%H-%M-%S")

    data = {"user_id": CONFIG.user_id, "cmd": cmd, "date": date_time}
    try:
        requests.post(CONFIG.telemetry_url, data=json.dumps(data), timeout=2)
    except BaseException:
        pass
