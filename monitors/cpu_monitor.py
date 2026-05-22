#Also start documentation

import psutil
from datetime import datetime
import json
import time
timestamp  = datetime.now().isoformat()



class CPUMonitor:

    def get_cpu_useage(self):
        cpu_data = {
            "timestamp": datetime.now().isoformat(),
            "total_cpu": psutil.cpu_percent(interval=1),
            "per_core": psutil.cpu_percent(interval=1, percpu=True),
            "processes": []
        }

        for process in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                info = process.info
                if info["cpu_percent"] > 5:
                    cpu_data["processes"].append(info)
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied):
                pass

        return cpu_data


# def get_cpu_useage():
#
#     cpu_percent = psutil.cpu_percent(interval=1)
#     cons_reading = 0
#     if cpu_percent > 85:
#         cons_reading += 1
#         if cons_reading > 4:
#             alerts("HIGH_USE")



def get_per_core_usage():
    pass

def per_process():
    process_list = []
    for process in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        if process.info['cpu_percent'] > 5:

            process_list.append(process.info)

    return process_list


def alerts(error_det):  #Add args for data what is more or fucked
    if error_det == "HIGH_USE":
        print("HIGH CPU USEAGE")

# while True:
#     print( get_cpu_useage())


while True:
    data = {
        "timestamp": timestamp,
        "cpu_usage": get_cpu_useage(),
        "processes": [per_process()]
    }
    with open('../storage test files/cpu_monitor.json', 'a') as outfile:
        outfile.write(json.dumps(data)+"\n")
    time.sleep(5)


