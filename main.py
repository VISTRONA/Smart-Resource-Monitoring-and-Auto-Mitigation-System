#Step -1 Make Montior (With AI)
#Step -2 Make engine to fix (with AI)
#Step -3 Make UI (Useing Tkinter) (Self)
#Step -4 Make it an exxusitable file (Self)

import psutil

import os
import sys 

import time
import csv
from datetime import datetime


CpuThres = 50.0 #Set higher (80%) for actual use, This is for demo
RamThres = 50.0 #Set higher (80%) for actual use, This is for demo

LogFiles = os.path.join("data", "logs.csv")


def log_data(): #Creates file for first time use
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(LogFiles):
        with open(LogFiles, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "App Name", "PID", "Action Taken", "System CPU Before", "System CPU After"])



def system_scanner():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    
    print(f"CPU Usage: {cpu}% | RAM Usage: {ram}%")

    if cpu < CpuThres or ram < RamThres:
        print("Safe!")
        return None, cpu, ram
    
    print("High Resource Usage Detected!") #Else case
    
    worst_app = None #String
    highest_score = -1 


    #To find active apps or processes on CPU and RAM
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            cpu_percent = proc.info['cpu_percent']
            memory_percent = proc.info['memory_percent']

            #Edge case: System processes and this script itself.
            if name in ["System", "Idle", "Registry","init"] or pid == os.getpid():
                print(f"Skipping process: {name} (PID: {pid})")
                continue

            #Rule_Based Scoring: Simple addition of CPU and Memory usage, can be improved with weights or ML models.
            #Source for scoring: Gemini and https://www.researchgate.net/publication/384353674_Resource_Allocation_Based_on_Task_Priority_and_Resource_Consumption_in_Edge_Computing
            #Why 1.5 and 2.5? Because RAM is often a bigger bottleneck than CPU, especially in multitasking environments. This is a simple heuristic and can be adjusted based on specific use cases or further research.
            #Also programs often use more RAM than CPU, so giving it a higher weight can help identify the real culprits in resource hogging scenarios.
            #Plus CPU usage can be more transient, while RAM usage tends to be more consistent, so giving it a higher weight can help identify the real culprits in resource hogging scenarios.
            
            score = cpu_percent * 1.5 + memory_percent * 2.5
            
            if sore > highest_score:
                highest_score = score
                worst_app = {
                    "pid": pid,
                    "name": name,
                    "cpu": round(app_cpu, 1),
                    "ram": round(app_ram, 1),
                    "score": round(score, 2)
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

        return worst_app, cpu, ram

def engine(app,cpu):
    
        

if __name__ == "__main__":
    log_data()



    try:
        while True:
            target_app, sysCpu, sysRam = system_scanner()
            if target_app:
                egine(target_app, sysCpu)
                

