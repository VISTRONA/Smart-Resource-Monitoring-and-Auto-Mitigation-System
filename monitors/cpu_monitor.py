import psutil
from datetime import datetime
import json
import time
timestamp  = datetime.now().isoformat()

def get_cpu_useage():

    if psutil.cpu_percent(interval=1)



def get_per_core_usage():
    pass

def per_process():
    process_list = []
    for process in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        if process.info['cpu_percent'] > 5:

            process_list.append(process.info)

    return process_list


# while True:
#     print( get_cpu_useage())


while True:
    data = {
        "timestamp": timestamp,
        "cpu_usage": get_cpu_useage(),
        "processes": [per_process()]
    }
    with open('cpu_monitor.json', 'w') as outfile:
        outfile.write(json.dumps(data))
    time.sleep(5)


