
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import requests
from config import *

def get_system_status():
    resp = requests.get(f"{SCH_SERVICE_NAME}/api/status")
    print(resp.status_code)
    if resp.status_code < 300:
        return resp.json()
    
    return []


if __name__ == "__main__":
    get_system_status()