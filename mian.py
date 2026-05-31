import psutil
import os
import sys 
import time
import csv
from datetime import datetime

from tkinter import *
from tkinter import messagebox

# Thresholds
CpuThres = 10.0  
RamThres = 10.0  

LogFiles = os.path.join("data", "logs.csv")

# Smart UI Tracking Dictionaries
active_heavy_widgets = {}
active_idle_widgets = {}

# System Flags
heartbeat_paused = False


def log_data(): 
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(LogFiles):
        with open(LogFiles, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "App Name", "PID(s)", "Action Taken", "System CPU Before", "System CPU After","System RAM Before", "System RAM After"])


def system_scanner():
    cpu = psutil.cpu_percent(interval=None) 
    ram = psutil.virtual_memory().percent
    
    cpu_label.config(text=f"CPU Usage: {cpu}%")
    ram_label.config(text=f"RAM Usage: {ram}%")

    if cpu < CpuThres and ram < RamThres:
        status_label.config(text="SYSTEM STATUS: SAFE", fg="#2ecc71")
        process_text.config(text="System stable. No heavy background resource hogs detected.")
    else:
        status_label.config(text="HIGH RESOURCE USAGE DETECTED!", fg="#e74c3c")
        process_text.config(text="Identified high-resource processes. Act directly on targets below:")

    # 1. GROUP PROCESSES BY NAME TO AVOID CLUTTER (Process Trees)
    current_apps = {}
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            name = proc.info['name']
            pid = proc.info['pid']
            cpu_val = proc.info['cpu_percent'] or 0.0
            ram_val = proc.info['memory_percent'] or 0.0

            # Skip core operating system processes to avoid crashes
            if name in ["System", "Idle", "System Idle Process", "Registry", "init", "taskhostw.exe", "explorer.exe"] or pid == os.getpid():
                continue

            if name not in current_apps:
                current_apps[name] = {
                    "name": name,
                    "pids": [],
                    "cpu": 0.0,
                    "ram": 0.0
                }

            # Aggregate process tree data
            current_apps[name]["pids"].append(pid)
            current_apps[name]["cpu"] += cpu_val
            current_apps[name]["ram"] += ram_val

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # 2. CATEGORIZE GROUPS INTO HEAVY OR IDLE
    heavy_apps = {}
    idle_apps = {}

    for name, data in current_apps.items():
        data["cpu"] = round(data["cpu"], 1)
        data["ram"] = round(data["ram"], 1)

        # CONDITION 1: Heavy Processes (Using noticeable CPU or heavy RAM)
        if data["cpu"] > 1.5 or data["ram"] > 2.0:
            heavy_apps[name] = data

        # CONDITION 2: Idle Processes (Aggregated CPU is basically 0, but holding RAM)
        elif data["cpu"] <= 0.1 and data["ram"] > 0.5:
            idle_apps[name] = data

    # 3. SMART UI UPDATE (Prevents jumping/flickering)
    update_ui_pane(scrollable_frame, active_heavy_widgets, heavy_apps, is_idle_pane=False)
    update_ui_pane(idle_scrollable_frame, active_idle_widgets, idle_apps, is_idle_pane=True)

    heavy_monitor_box.config(text=f" ACTIVE LOADS ({len(heavy_apps)} Detected) ")
    idle_title_lbl.config(text=f" IDLE BACKGROUND TASKS ({len(idle_apps)} Detected) ")
    
    return cpu, ram


def update_ui_pane(target_frame, widget_dict, app_dict, is_idle_pane):
    """Updates rows in-place instead of destroying the whole list to prevent scroll-jumping."""
    # 1. Remove dead applications that are no longer running/heavy
    for name in list(widget_dict.keys()):
        if name not in app_dict:
            widget_dict[name]["frame"].destroy()
            del widget_dict[name]

    # 2. Add new apps or update existing ones
    for name, app in app_dict.items():
        process_count_str = f"({len(app['pids'])} procs)"
        
        if is_idle_pane:
            display_str = f"{name[:12]:<12} {process_count_str:<10} | RAM: {app['ram']}%"
        else:
            display_str = f"{name[:12]:<12} {process_count_str:<10} | C:{app['cpu']}% R:{app['ram']}%"

        # If it already exists on screen, just update the text and button command
        if name in widget_dict:
            widget_dict[name]["label"].config(text=display_str)
            # Rebind command to pass the updated PID list
            action = "Trim" if is_idle_pane else "Purge"
            widget_dict[name]["btn"].config(command=lambda a=app, act=action: implement_mitigation(a, act))
        else:
            # Create a brand new row
            row_frame = Frame(target_frame, bg="#0f0f0f", bd=1, relief="flat")
            row_frame.pack(fill="x", padx=5, pady=4)
            
            lbl = Label(row_frame, text=display_str, font=("Courier", 9), bg="#0f0f0f", fg="#888888" if is_idle_pane else "#ffffff", anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=2)

            if is_idle_pane:
                btn = Button(row_frame, text="RAM", font=("Arial", 7, "bold"), bg="#27ae60", fg="white", bd=0, padx=4, pady=2, command=lambda a=app: implement_mitigation(a, "Trim"))
            else:
                btn = Button(row_frame, text="KILL", font=("Arial", 7, "bold"), bg="#e74c3c", fg="white", bd=0, padx=5, pady=2, command=lambda a=app: implement_mitigation(a, "Purge"))
            
            btn.pack(side="right", padx=2)
            
            # Store in dictionary so we can update it next loop
            widget_dict[name] = {"frame": row_frame, "label": lbl, "btn": btn}


def implement_mitigation(app_group, action_type): 
    """Handles operational mitigation on the ENTIRE process tree."""
    global heartbeat_paused
    heartbeat_paused = True # Freeze background scanning so UI doesn't shift

    confirm = messagebox.askyesno(
        "Confirm Mitigation Strategy", 
        f"Apply '{action_type}' strategy to ALL {len(app_group['pids'])} background processes of {app_group['name']}?"
    )
    
    if not confirm:
        heartbeat_paused = False
        return

    success_count = 0
    action_string = "Skipped"
    
    for pid in app_group['pids']:
        try:
            proc = psutil.Process(pid)
            
            if action_type == "Purge":
                proc.terminate()
                success_count += 1
                action_string = "Terminated Entire Process Tree"
                
            elif action_type == "Trim":
                if sys.platform == "win32":
                    import ctypes
                    handle = ctypes.windll.kernel32.OpenProcess(0x0100, False, pid)
                    if handle:
                        ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
                        ctypes.windll.kernel32.CloseHandle(handle)
                else:
                    proc.nice(19)
                success_count += 1
                action_string = "Idle Working Set Swapped / Trimmed"

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if success_count > 0:
        status_label.config(text="MEASURING POST-ACTION RESOURCE IMPROVEMENTS...", fg="#e67e22")
        window.update()
        # Wait 1.5 seconds, then calculate stats async
        window.after(1500, lambda: finalize_mitigation_stats(app_group, action_type, action_string, saved_cpu, saved_ram, success_count))
    else:
        messagebox.showerror("Error", "Access Denied or Processes vanished unexpectedly.")
        heartbeat_paused = False


def finalize_mitigation_stats(app_group, action_type, action_string, old_cpu, old_ram, success_count):
    """Calculates freed resources completely in the background, then alerts the user."""
    global heartbeat_paused
    new_cpu = psutil.cpu_percent(interval=None)
    new_ram = psutil.virtual_memory().percent
    
    freed_cpu = max(0.0, round(old_cpu - new_cpu, 1))
    freed_ram = max(0.0, round(old_ram - new_ram, 1))
    
    with open(LogFiles, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), app_group['name'], str(app_group['pids']), action_string, f"{old_cpu}%", f"{new_cpu}%", f"{old_ram}%", f"{new_ram}%"])
    
    status_label.config(text="OPTIMIZATION SUCCESS METRICS LOGGED", fg="#2ecc71")
    
    success_msg = (
        f"Successfully applied '{action_type}' to {success_count} processes of {app_group['name']}.\n\n"
        f"📊 Resources Freed:\n"
        f"  • CPU Freed: {freed_cpu}%\n"
        f"  • RAM Freed: {freed_ram}%\n\n"
        f"System metrics have stabilized."
    )
    messagebox.showinfo("Mitigation Success", success_msg)
    
    # Unpause and Force UI scan immediately to refresh the lists
    heartbeat_paused = False
    system_scanner()


def continuous_loop():
    global saved_cpu, saved_ram
    # Only scan if a prompt isn't currently open blocking the user
    if not heartbeat_paused:
        saved_cpu, saved_ram = system_scanner()
        
    window.after(5000, continuous_loop)


if __name__ == "__main__":
    log_data()  
    psutil.cpu_percent(interval=None) 
    
    saved_cpu, saved_ram = 0.0, 0.0

    window = Tk()
    window.title("Smart Resource Monitor and Auto-Mitigation System")
    window.geometry("1000x650") 
    window.configure(bg="#141414")

    tit = Label(window, text="Smart Resource Monitor and Auto-Mitigation System", font=("Arial", 14, "bold"), bg="#141414", fg="white")
    tit.pack(pady=8)

    # Telemetry Dashboard
    dashboard = LabelFrame(window, text=" LIVE HARDWARE METRICS ", font=("Courier", 10, "bold"), bg="#1c1c1c", fg="#2ecc71", bd=2, relief="groove")
    dashboard.pack(fill="x", padx=20, pady=5)
    cpu_label = Label(dashboard, text="CPU Usage: Fetching...", font=("Courier", 12, "bold"), bg="#1c1c1c", fg="white")
    cpu_label.pack(side="left", expand=True, pady=4)
    ram_label = Label(dashboard, text="RAM Usage: Fetching...", font=("Courier", 12, "bold"), bg="#1c1c1c", fg="white")
    ram_label.pack(side="right", expand=True, pady=4)

    # Status Bar Strip
    status_frame = Frame(window, bg="#222222", bd=1, relief="sunken")
    status_frame.pack(fill="x", padx=20, pady=5)
    status_label = Label(status_frame, text="INITIALIZING HEARTBEAT LOOPS...", font=("Courier", 10, "bold"), bg="#222222", fg="yellow")
    status_label.pack(side="left", padx=10)
    
    process_text = Label(status_frame, text="", font=("Courier", 10), bg="#222222", fg="#00ff00")
    process_text.pack(side="right", padx=10)

    # ---------------- MAIN SIDE-BY-SIDE CONTAINER FRAME ----------------
    columns_container = Frame(window, bg="#141414")
    columns_container.pack(fill="both", expand=True, padx=20, pady=5)

    # LEFT COLUMN: HEAVY RESOURCES CONTROLS
    heavy_monitor_box = LabelFrame(columns_container, text=" ACTIVE LOADS ", font=("Courier", 10, "bold"), bg="#1c1c1c", fg="#e67e22", bd=2, relief="groove")
    heavy_monitor_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

    container_frame = Frame(heavy_monitor_box, bg="#0f0f0f")
    container_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    canvas = Canvas(container_frame, bg="#0f0f0f", highlightthickness=0)
    scrollbar = Scrollbar(container_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas, bg="#0f0f0f")
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # RIGHT COLUMN: IDLE BACKGROUND TASK CONTROLS
    idle_monitor_box = LabelFrame(columns_container, text=" IDLE BACKGROUND TASKS ", font=("Courier", 10, "bold"), bg="#1c1c1c", fg="#3498db", bd=2, relief="groove")
    idle_title_lbl = idle_monitor_box 
    idle_monitor_box.pack(side="right", fill="both", expand=True, padx=(10, 0))

    idle_container_frame = Frame(idle_monitor_box, bg="#0f0f0f")
    idle_container_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    idle_canvas = Canvas(idle_container_frame, bg="#0f0f0f", highlightthickness=0)
    idle_scrollbar = Scrollbar(idle_container_frame, orient="vertical", command=idle_canvas.yview)
    idle_scrollable_frame = Frame(idle_canvas, bg="#0f0f0f")
    idle_scrollable_frame.bind("<Configure>", lambda e: idle_canvas.configure(scrollregion=idle_canvas.bbox("all")))
    idle_canvas.create_window((0, 0), window=idle_scrollable_frame, anchor="nw")
    idle_canvas.configure(yscrollcommand=idle_scrollbar.set)
    idle_canvas.pack(side="left", fill="both", expand=True)
    idle_scrollbar.pack(side="right", fill="y")
    # -------------------------------------------------------------------

    btn_exit = Button(window, text="DISCONNECT SYSTEM(EXIT)", font=("Arial", 11, "bold"), bg="#222222", fg="#aaaaaa", height=2, command=window.destroy)
    btn_exit.pack(fill="x", padx=20, pady=15)

    window.after(1000, continuous_loop)
    window.mainloop()