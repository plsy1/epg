import requests
import os
import time
from utils import get_date_str

def get_epg_from_112114():
    output = f"data/112114/112114-{get_date_str()}.xml"
    url = "https://epg.112114.xyz/pp.xml"

    os.makedirs(os.path.dirname(output), exist_ok=True)

    retries = 3
    delay = 1

    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status() 
            with open(output, "wb") as f:
                f.write(res.content)
            break
        except Exception as e:
            if attempt < retries:
                time.sleep(delay)
