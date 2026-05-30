import psutil
import os
import sys 
import time
import csv
from datetime import datetime

from tkinter import *
from tkinter import messagebox

# Thresholds - Kept low for testing/demo purposes
CpuThres = 10.0  
RamThres = 10.0  

LogFiles = os.path.join("data", "logs.csv")

def log_data(): 
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(LogFiles):
        with open(LogFiles, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "App Name", "PID", "Action Taken", "System CPU Before", "System CPU After","System RAM Before", "System RAM After"])


def system_scanner():
    cpu = psutil.cpu_percent(interval=None) 
    ram = psutil.virtual_memory().percent
    
    cpu_label.config(text=f"CPU Usage: {cpu}%")
    ram_label.config(text=f"RAM Usage: {ram}%")
    print(f"CPU Usage: {cpu}% | RAM Usage: {ram}%")

    # Clear out the previous rows in our scrollable frame
    for widget in scrollable_frame.winfo_children():
        widget.destroy()

    if cpu < CpuThres and ram < RamThres:
        print("Safe!")
        status_label.config(text="SYSTEM STATUS: SAFE", fg="#2ecc71")
        process_text.config(text="\n   System metrics are stable.\n   No heavy background resource hogs detected.")
        return cpu, ram
    
    print("High Resource Usage Detected!") 
    status_label.config(text="HIGH RESOURCE USAGE DETECTED!", fg="#e74c3c")
    
    heavy_count = 0
    
    # Scan for heavy processes
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            cpu_percent = proc.info['cpu_percent']
            memory_percent = proc.info['memory_percent']

            if name in ["System", "Idle", "System Idle Process", "Registry", "init"] or pid == os.getpid():
                continue

            score = cpu_percent * 1.5 + memory_percent * 2.5
            
            # Filter criteria for displaying a process in the UI list
            if cpu_percent > 1.5 or memory_percent > 1.5:
                app_details = {
                    "pid": pid,
                    "name": name,
                    "cpu": round(cpu_percent, 1),
                    "ram": round(memory_percent, 1),
                    "score": round(score, 2)
                }
                
                # Render a row dynamically for this process
                create_process_row(heavy_count, app_details)
                heavy_count += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if heavy_count > 0:
        process_text.config(text=f" Identified {heavy_count} heavy processes. Act directly on targets below:")
    else:
        process_text.config(text="\n   High system load detected, but individual user applications are low.\n   Likely transient kernel or OS micro-bursting.")

    return cpu, ram


def create_process_row(row_index, app):
    """Creates a dedicated text descriptor and functional delete button for a specific process row."""
    row_frame = Frame(scrollable_frame, bg="#0f0f0f", bd=1, relief="flat")
    row_frame.pack(fill="x", padx=5, pady=4)
    
    # Formatted clean metrics label
    display_str = f"PID: {app['pid']:<6} | {app['name'][:22]:<22} | CPU: {app['cpu']}% | RAM: {app['ram']}% | Score: {app['score']}"
    lbl = Label(row_frame, text=display_str, font=("Courier", 10), bg="#0f0f0f", fg="#ffffff", anchor="w")
    lbl.pack(side="left", fill="x", expand=True, padx=5)
    
    # DIRECT PURGE (DELETE) BUTTON bound uniquely to this app configuration payload
    btn_purge = Button(
        row_frame, 
        text="PURGE", 
        font=("Arial", 8, "bold"), 
        bg="#e74c3c", 
        fg="white", 
        bd=0,
        padx=10,
        command=lambda: direct_purge_engine(app)
    )
    btn_purge.pack(side="right", padx=5)


def direct_purge_engine(app): 
    """Triggers instantly when a dedicated row button is clicked"""
    confirm = messagebox.askyesno("Confirm Action", f"Are you sure you want to completely PURGE/TERMINATE {app['name']} (PID: {app['pid']})?")
    if not confirm:
        return

    try:
        proc = psutil.Process(app['pid'])
        proc.terminate()  # Forcefully closes the app
        action_string = "Terminated via Direct UI Grid Button"
        messagebox.showinfo("Success", f"Closed {app['name']} successfully.")

        # Log system changes
        status_label.config(text="SAMPLING POST-ACTION RESOURCE IMPROVEMENTS...", fg="#e67e22")
        window.update()
        
        time.sleep(1.2)  
        new_cpu = psutil.cpu_percent(interval=None)
        new_ram = psutil.virtual_memory().percent
        
        with open(LogFiles, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                app['name'],
                app['pid'],
                action_string,
                f"{saved_cpu}%",
                f"{new_cpu}%",
                f"{saved_ram}%",
                f"{new_ram}%"
            ])
        status_label.config(text="OPTIMIZATION SUCCESS METRICS LOGGED", fg="#2ecc71")

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        messagebox.showerror("Error", "Process vanished or script lacks administrative privileges.")

    # Refresh the hardware metrics loop immediately to re-sync active states
    system_scanner()


def continuous_loop():
    global saved_cpu, saved_ram
    saved_cpu, saved_ram = system_scanner()
    
    print("-----------------")
    print("5 sec sleep heartbeat")
    print("-----------------")
    
    window.after(5000, continuous_loop)


if __name__ == "__main__":
    log_data()  
    psutil.cpu_percent(interval=None) 
    
    saved_cpu = 0.0
    saved_ram = 0.0

    window = Tk()
    window.title("Smart Resource Monitor and Auto-Mitigation System")
    window.geometry("900x700")
    window.configure(bg="#141414")

    # Title
    tit = Label(window, text="Smart Resource Monitor and Auto-Mitigation System", font=("Arial", 16, "bold"), bg="#141414", fg="white")
    tit.pack(pady=10)

    # Telemetry Dashboard Frames
    dashboard = LabelFrame(window, text=" LIVE HARDWARE METRICS ", font=("Courier", 10, "bold"), bg="#1c1c1c", fg="#2ecc71", bd=2, relief="groove")
    dashboard.pack(fill="x", padx=20, pady=5, ipady=5)
    
    cpu_label = Label(dashboard, text="CPU Usage: Fetching...", font=("Courier", 13, "bold"), bg="#1c1c1c", fg="white")
    cpu_label.pack(side="left", expand=True, pady=5)
    
    ram_label = Label(dashboard, text="RAM Usage: Fetching...", font=("Courier", 13, "bold"), bg="#1c1c1c", fg="white")
    ram_label.pack(side="right", expand=True, pady=5)

    # Status Message Strip
    status_frame = Frame(window, bg="#222222", bd=1, relief="sunken")
    status_frame.pack(fill="x", padx=20, pady=5)
    status_title = Label(status_frame, text="ENGINE PROFILE: ", font=("Courier", 11, "bold"), bg="#222222", fg="#888888")
    status_title.pack(side="left", padx=(10, 2))
    status_label = Label(status_frame, text="RUNNING FOREVER LOOP...", font=("Courier", 11, "bold"), bg="#222222", fg="yellow")
    status_label.pack(side="left")

    # Interactive Console Monitor Box
    monitor_box = LabelFrame(window, text=" PROCESS INTERACTION PANEL ", font=("Courier", 10, "bold"), bg="#1c1c1c", fg="#e67e22", bd=2, relief="groove")
    monitor_box.pack(fill="both", expand=True, padx=20, pady=10)
    
    process_text = Label(
        monitor_box, 
        text="Initializing metric sweeps. Scanning for hardware footprint anomalies...", 
        font=("Courier", 10), 
        bg="#0f0f0f", 
        fg="#00ff00", 
        anchor="nw", 
        justify="left"
    )
    process_text.pack(fill="x", padx=15, pady=5)

    # ---- SCROLLABLE CANVAS CONTAINER FOR INDIVIDUAL ELEMENT BUTTON ROWS ----
    container_frame = Frame(monitor_box, bg="#0f0f0f")
    container_frame.pack(fill="both", expand=True, padx=15, pady=5)

    canvas = Canvas(container_frame, bg="#0f0f0f", highlightthickness=0)
    scrollbar = Scrollbar(container_frame, orient="vertical", command=canvas.yview)
    
    scrollable_frame = Frame(canvas, bg="#0f0f0f")
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    # ------------------------------------------------------------------------

    btn_exit = Button(window, text="DISCONNECT SYSTEM(EXIT)", font=("Arial", 11, "bold"), bg="#222222", fg="#aaaaaa", height=2, command=window.destroy)
    btn_exit.pack(fill="x", padx=20, pady=(0, 15))

    window.after(1000, continuous_loop)
    window.mainloop()