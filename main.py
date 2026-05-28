#Step -1 Make Montior (With AI) (Done)
#Step -2 Make engine to fix (with AI) (Done)
#Step -3 Make UI (Useing Tkinter) (Self) (Work in progress, will be added in next commit)
#Step -4 Make it an executable file (Self) 

import psutil

import os
import sys 

import time
import csv
from datetime import datetime

from tkinter import *


CpuThres = 50.0 #Set higher (80%) for actual use, This is for demo
RamThres = 40.0 #Set higher (80%) for actual use, This is for demo

LogFiles = os.path.join("data", "logs.csv")



screen = Tk()
screen.title("Smart Resource Monitor and Auto-Mitigation System")
screen.geometry("800x600")


CpuThres = 50.0 #Set higher (80%) for actual use, This is for demo
RamThres = 40.0 #Set higher (80%) for actual use, This is for demo

LogFiles = os.path.join("data", "logs.csv")


def log_data(): #Creates file for first time use
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(LogFiles):
        with open(LogFiles, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "App Name", "PID", "Action Taken", "System CPU Before", "System CPU After","System RAM Before", "System RAM After"])



def system_scanner():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    
    print(f"CPU Usage: {cpu}% | RAM Usage: {ram}%")

    if cpu < CpuThres and ram < RamThres:
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
            if name in ["System", "Idle", "System Idle Process", "Registry", "init"] or pid == os.getpid():
                print(f"Skipping process: {name} (PID: {pid})")
                continue

            #Rule_Based Scoring: Simple addition of CPU and Memory usage, can be improved with weights or ML models.
            #Source for scoring: Gemini and https://www.researchgate.net/publication/384353674_Resource_Allocation_Based_on_Task_Priority_and_Resource_Consumption_in_Edge_Computing
            #Why 1.5 and 2.5? Because RAM is often a bigger bottleneck than CPU, especially in multitasking environments. This is a simple heuristic and can be adjusted based on specific use cases or further research.
            #Also programs often use more RAM than CPU, so giving it a higher weight can help identify the real culprits in resource hogging scenarios.
            #Plus CPU usage can be more transient, while RAM usage tends to be more consistent, so giving it a higher weight can help identify the real culprits in resource hogging scenarios.
            
            score = cpu_percent * 1.5 + memory_percent * 2.5
            
            if score > highest_score:
                highest_score = score
                worst_app = {
                    "pid": pid,
                    "name": name,
                    "cpu": round(cpu_percent, 1),
                    "ram": round(memory_percent, 1),
                    "score": round(score, 2)
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return worst_app, cpu, ram

def engine(app,cpu,ram): #Difficult one
    if not app:
        print("No steps to be taken yet")
        return
    

    print(f"\n Existential process identified: {app['name']} (PID: {app['pid']}) with CPU: {app['cpu']}% and RAM: {app['ram']}% | Score: {app['score']}")

    print("Optimization Strategy: 'Mr. Prsident: '")
    print("1. [Optimize Priority] Lower application's priority (Linux Nice / Windows Set)")
    print("2. [Suspend Process] Freeze the process completely (Linux SIGSTOP)")
    print("3. [Terminate Process] Hard close the application entirely")
    print("4. [Skip Action] Do nothing")

    choice = input("Enter your choice (1-4): ").strip()
    action_string = "Skipped"

    try:
        proc = psutil.Process(app['pid'])
        if choice == '1':
            if sys.platform == "win32":
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x0100, False, app['pid'])
                if handle:
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1) # BELOW_NORMAL_PRIORITY_CLASS
                    ctypes.windll.kernel32.CloseHandle(handle)
                    action_string = "Optimed Memory (Windows Trimming)"
            else:
                # Linux Nice priority adjustment (Values range from -20 to 19. 19 is lowest priority)
                proc.nice(19) # Lower priority
                action_string = "Lowered Priority (Linux Nice)"
            print(f"Action taken: {action_string} to {app['name']} (PID: {app['pid']})")
        elif choice == '2':
            if sys.platform != "win32":
                proc.suspend()  # Sends Linux SIGSTOP to freeze the app
                action_string = "Suspended (SIGSTOP)"
                print(f"Frozen {app['name']} successfully. Tabs/Windows remain open but paused.")
            else:
                print("Process suspension is optimized for Linux environments in this version.")
                return
            
        elif choice == '3':
            proc.terminate()  # Forcefully closes the app
            action_string = "Terminated"
            print(f"Terminated {app['name']} successfully. All tabs/windows will be closed.")
        else:
            print("Action canceled by user.")
            return

             # Log the action taken along with system CPU before and after the action
          
        print("Measuring improv in system resources after action...")
        time.sleep(2)  # 2 sec delay to allow system to stabilize after action
        new_cpu = psutil.cpu_percent(interval=0.5)
        new_ram = psutil.virtual_memory().percent

        with open(LogFiles, mode='a', newline='') as file:
            writer = csv.writer(file)
            # writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), app['name'], app['pid'], action_string, cpu, new_cpu])
            writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            app['name'],
            app['pid'],
            action_string,
            f"{cpu}%",
            f"{new_cpu}%",
            f"{ram}%",
            f"{new_ram}%"

        ])
        print(f"Logged action to {LogFiles}")


    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        print("Process no longer exists. It may have been closed manually or by another system action.")

if __name__ == "__main__":
    log_data()  



    try:
        while True:
            target_app, sysCpu, sysRam = system_scanner()
            if target_app:
                engine(target_app, sysCpu,sysRam)

            print("\n"+ "-----------------")
            print("5 sec sleep")
            print("-----------------")      
            time.sleep(5)          

    except KeyboardInterrupt:
        print("\n Exiting Program!")
    
    screen.mainloop()