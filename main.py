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
from tkinter import messagebox


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
    cpu = psutil.cpu_percent(interval=None) # Changed to None to prevent Tkinter window lag
    ram = psutil.virtual_memory().percent
    
    # Update our UI metrics dynamically
    cpu_label.config(text=f"CPU Usage: {cpu}%")
    ram_label.config(text=f"RAM Usage: {ram}%")
    print(f"CPU Usage: {cpu}% | RAM Usage: {ram}%")

    if cpu < CpuThres and ram < RamThres:
        print("Safe!")
        status_label.config(text="SYSTEM STATUS: SAFE", fg="#2ecc71")
        process_text.config(text="\n   System metrics are stable.\n   No heavy background resource hogs detected.")
        set_buttons_state("disabled")
        return None, cpu, ram
    
    print("High Resource Usage Detected!") #Else case
    status_label.config(text="HIGH RESOURCE USAGE DETECTED!", fg="#e74c3c")
    
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

    if worst_app:
        display_string = (
            f" Heavy Process Identified:\n\n"
            f"  » Name : {worst_app['name']} (PID: {worst_app['pid']})\n"
            f"  » Load : CPU: {worst_app['cpu']}% | RAM: {worst_app['ram']}%\n"
            f"  » Score: {worst_app['score']}\n\n"
            f" Select an optimization strategy below:"
        )
        process_text.config(text=display_string)
        set_buttons_state("normal")

    return worst_app, cpu, ram

def engine(app,cpu,ram, choice): # Modified to take UI button choices asynchronously
    if not app:
        print("No steps to be taken yet")
        return
    

    print(f"\n Existential process identified: {app['name']} (PID: {app['pid']}) with CPU: {app['cpu']}% and RAM: {app['ram']}% | Score: {app['score']}")

    print("Optimization Strategy: 'Mr. Prsident: '")
    print("1. [Optimize Priority] Lower application's priority (Linux Nice / Windows Set)")
    print("2. [Suspend Process] Freeze the process completely (Linux SIGSTOP)")
    print("3. [Terminate Process] Hard close the application entirely")
    print("4. [Skip Action] Do nothing")

    action_string = "Skipped"

    try:
        proc = psutil.Process(app['pid'])
        if choice == 1:
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
            messagebox.showinfo("Success", f"Optimized priority queue for {app['name']}.")
            
        elif choice == 2:
            if sys.platform != "win32":
                proc.suspend()  # Sends Linux SIGSTOP to freeze the app
                action_string = "Suspended (SIGSTOP)"
                print(f"Frozen {app['name']} successfully. Tabs/Windows remain open but paused.")
                messagebox.showinfo("Success", f"Frozen background threads for {app['name']}.")
            else:
                print("Process suspension is optimized for Linux environments in this version.")
                messagebox.showwarning("Platform Guard", "Process suspension is optimized for Linux environments.")
                return
            
        elif choice == 3:
            proc.terminate()  # Forcefully closes the app
            action_string = "Terminated"
            print(f"Terminated {app['name']} successfully. All tabs/windows will be closed.")
            messagebox.showinfo("Success", f"Closed {app['name']} successfully.")
        else:
            print("Action canceled by user.")
            process_text.config(text="\n\n   Action canceled by user.\n   Resuming background monitoring metrics...")
            set_buttons_state("disabled")
            return

        # Log the action taken along with system CPU before and after the action
        status_label.config(text="SAMPLING POST-ACTION RESOURCE IMPROVEMENTS...", fg="#e67e22")
        window.update()
        
        print("Measuring improv in system resources after action...")
        time.sleep(2)  # 2 sec delay to allow system to stabilize after action
        new_cpu = psutil.cpu_percent(interval=None)
        new_ram = psutil.virtual_memory().percent
        
        with open(LogFiles, mode='a', newline='') as file:
            writer = csv.writer(file)
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
        status_label.config(text="OPTIMIZATION SUCCESS METRICS LOGGED", fg="#2ecc71")

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        print("Process no longer exists. It may have been closed manually or by another system action.")
        messagebox.showerror("Error", "Process vanished or script lacks required user privileges.")

    set_buttons_state("disabled")

# Global variables to handle UI data snapshot transfers
active_target = None
saved_cpu = 0.0
saved_ram = 0.0

def continuous_loop():
    """Tkinter native asynchronous background alarm execution routine replacing while True loops."""
    global active_target, saved_cpu, saved_ram
    
    active_target, saved_cpu, saved_ram = system_scanner()
    
    print("\n-----------------")
    print("5 sec sleep heartbeat")
    print("-----------------")
    
    # Run again automatically in 5000 milliseconds (5 seconds) forever
    window.after(5000, continuous_loop)

def set_buttons_state(state):
    btn_opt.config(state=state)
    btn_susp.config(state=state)
    btn_term.config(state=state)
    btn_skip.config(state=state)


if __name__ == "__main__":
    log_data()  
    psutil.cpu_percent(interval=None) # Prime core performance reading baseline
    
    window = Tk()
    window.title("Smart Resource Monitor and Auto-Mitigation System")
    window.geometry("850x650")
    window.configure(bg="#141414")

    # Banner Title
    tit = Label(window, text="Smart Resource Monitor and Auto-Mitigation System", font=("Arial", 16, "bold"), bg="#141414", fg="white")
    tit.pack(pady=15)

    # Telemetry Dashboard Frames
    dashboard = LabelFrame(window, text=" LIVE HARDWARE METRICS ", font=("Courier", 10, "bold"), bg="#1c1c1c", fg="#2ecc71", bd=2, relief="groove")
    dashboard.pack(fill="x", padx=20, pady=10, ipady=10)
    
    cpu_label = Label(dashboard, text="CPU Usage: Fetching...", font=("Courier", 13, "bold"), bg="#1c1c1c", fg="white")
    cpu_label.pack(pady=5)
    
    ram_label = Label(dashboard, text="RAM Usage: Fetching...", font=("Courier", 13, "bold"), bg="#1c1c1c", fg="white")
    ram_label.pack(pady=5)

    # Status Message Strip
    status_frame = Frame(window, bg="#222222", bd=1, relief="sunken")
    status_frame.pack(fill="x", padx=20, pady=5)
    status_title = Label(status_frame, text="ENGINE PROFILE: ", font=("Courier", 11, "bold"), bg="#222222", fg="#888888")
    status_title.pack(side="left", padx=(10, 2))
    status_label = Label(status_frame, text="RUNNING FOREVER LOOP...", font=("Courier", 11, "bold"), bg="#222222", fg="yellow")
    status_label.pack(side="left")

    # Interactive Console Monitor Display Workspace Box
    monitor_box = LabelFrame(window, text=" PROCESS INTERACTION PANEL ", font=("Courier", 10, "bold"), bg="#1c1c1c", fg="#e67e22", bd=2, relief="groove")
    monitor_box.pack(fill="both", expand=True, padx=20, pady=10)
    
    process_text = Label(
        monitor_box, 
        text="\n\n   Initializing metric sweeps. Scanning for hardware footprint anomalies...", 
        font=("Courier", 11), 
        bg="#0f0f0f", 
        fg="#00ff00", 
        anchor="nw", 
        justify="left",
        relief="solid",
        bd=1
    )
    process_text.pack(fill="both", expand=True, padx=15, pady=15)

    # Symmetrical Interaction Command Button Layout Section Frame
    controls_frame = Frame(window, bg="#141414")
    controls_frame.pack(fill="x", padx=15, pady=15)
    controls_frame.columnconfigure((0, 1, 2, 3), weight=1)

    # Operational Interactive Strategy Mapping Hooks
    btn_opt = Button(controls_frame, text="OPTIMIZE ALLOC", font=("Arial", 10, "bold"), bg="#3498db", fg="white", height=2, command=lambda: engine(active_target, saved_cpu, saved_ram, 1))
    btn_opt.grid(row=0, column=0, padx=5, sticky="ew")

    btn_susp = Button(controls_frame, text="FREEZE THREAD", font=("Arial", 10, "bold"), bg="#e67e22", fg="white", height=2, command=lambda: engine(active_target, saved_cpu, saved_ram, 2))
    btn_susp.grid(row=0, column=1, padx=5, sticky="ew")

    btn_term = Button(controls_frame, text="PURGE TARGET", font=("Arial", 10, "bold"), bg="#e74c3c", fg="white", height=2, command=lambda: engine(active_target, saved_cpu, saved_ram, 3))
    btn_term.grid(row=0, column=2, padx=5, sticky="ew")

    btn_skip = Button(controls_frame, text="BYPASS ALERT", font=("Arial", 10, "bold"), bg="#444444", fg="white", height=2, command=lambda: engine(active_target, saved_cpu, saved_ram, 4))
    btn_skip.grid(row=0, column=3, padx=5, sticky="ew")

    btn_exit = Button(window, text="DISCONNECT SYSTEM", font=("Arial", 11, "bold"), bg="#222222", fg="#aaaaaa", height=2, command=window.destroy)
    btn_exit.pack(fill="x", padx=20, pady=(0, 20))

    set_buttons_state("disabled")

    # KICKSTART: Instruct Tkinter to boot up your infinite background evaluation loop automatically in 1 second!
    window.after(1000, continuous_loop)

    # Hand program pipeline processing tracking over to Tkinter's native graphics engine loops
    window.mainloop()