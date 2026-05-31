import psutil
import os
import sys 
import time
import csv
from datetime import datetime

from tkinter import *
from tkinter import messagebox
from tkinter import ttk  # Added for the History Data Table

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

    current_apps = {}
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            name = proc.info['name']
            pid = proc.info['pid']
            cpu_val = proc.info['cpu_percent'] or 0.0
            ram_val = proc.info['memory_percent'] or 0.0

            if name in ["System", "Idle", "System Idle Process", "Registry", "init", "taskhostw.exe", "explorer.exe"] or pid == os.getpid():
                continue

            if name not in current_apps:
                current_apps[name] = {
                    "name": name,
                    "pids": [],
                    "cpu": 0.0,
                    "ram": 0.0
                }

            current_apps[name]["pids"].append(pid)
            current_apps[name]["cpu"] += cpu_val
            current_apps[name]["ram"] += ram_val

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    heavy_apps = {}
    idle_apps = {}

    for name, data in current_apps.items():
        data["cpu"] = round(data["cpu"], 1)
        data["ram"] = round(data["ram"], 1)

        if data["cpu"] > 1.5 or data["ram"] > 2.0:
            heavy_apps[name] = data
        elif data["cpu"] <= 0.1 and data["ram"] > 0.5:
            idle_apps[name] = data

    update_ui_pane(scrollable_frame, active_heavy_widgets, heavy_apps, is_idle_pane=False)
    update_ui_pane(idle_scrollable_frame, active_idle_widgets, idle_apps, is_idle_pane=True)

    heavy_monitor_box.config(text=f" ACTIVE LOADS ({len(heavy_apps)} Detected) ")
    idle_title_lbl.config(text=f" IDLE BACKGROUND TASKS ({len(idle_apps)} Detected) ")
    
    return cpu, ram


def update_ui_pane(target_frame, widget_dict, app_dict, is_idle_pane):
    for name in list(widget_dict.keys()):
        if name not in app_dict:
            widget_dict[name]["frame"].destroy()
            del widget_dict[name]

    for name, app in app_dict.items():
        process_count_str = f"({len(app['pids'])} procs)"
        
        if is_idle_pane:
            display_str = f"{name[:12]:<12} {process_count_str:<10} | RAM: {app['ram']}%"
        else:
            display_str = f"{name[:12]:<12} {process_count_str:<10} | C:{app['cpu']}% R:{app['ram']}%"

        if name in widget_dict:
            widget_dict[name]["label"].config(text=display_str)
            action = "Trim" if is_idle_pane else "Purge"
            widget_dict[name]["btn"].config(command=lambda a=app, act=action: implement_mitigation(a, act))
        else:
            row_frame = Frame(target_frame, bg="#0f0f0f", bd=1, relief="flat")
            row_frame.pack(fill="x", padx=5, pady=4)
            
            lbl = Label(row_frame, text=display_str, font=("Courier", 9), bg="#0f0f0f", fg="#888888" if is_idle_pane else "#ffffff", anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=2)

            if is_idle_pane:
                btn = Button(row_frame, text="RAM", font=("Arial", 7, "bold"), bg="#27ae60", fg="white", bd=0, padx=4, pady=2, command=lambda a=app: implement_mitigation(a, "Trim"))
            else:
                btn = Button(row_frame, text="KILL", font=("Arial", 7, "bold"), bg="#e74c3c", fg="white", bd=0, padx=5, pady=2, command=lambda a=app: implement_mitigation(a, "Purge"))
            
            btn.pack(side="right", padx=2)
            widget_dict[name] = {"frame": row_frame, "label": lbl, "btn": btn}


def implement_mitigation(app_group, action_type): 
    global heartbeat_paused
    heartbeat_paused = True

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
        window.after(1500, lambda: finalize_mitigation_stats(app_group, action_type, action_string, saved_cpu, saved_ram, success_count))
    else:
        messagebox.showerror("Error", "Access Denied or Processes vanished unexpectedly.")
        heartbeat_paused = False


def finalize_mitigation_stats(app_group, action_type, action_string, old_cpu, old_ram, success_count):
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
    
    heartbeat_paused = False
    system_scanner()


# --- NEW: History Window UI ---
def open_history_window():
    """Opens a new window displaying past actions logged in the CSV file."""
    history_win = Toplevel(window)
    history_win.title("Optimization History Log")
    history_win.geometry("900x450")
    history_win.configure(bg="#141414")

    lbl = Label(history_win, text="SYSTEM OPTIMIZATION HISTORY", font=("Arial", 12, "bold"), bg="#141414", fg="white")
    lbl.pack(pady=10)

    # Styling the Treeview to match the Dark Theme
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview", background="#1c1c1c", foreground="white", rowheight=25, fieldbackground="#1c1c1c", borderwidth=0)
    style.map("Treeview", background=[("selected", "#3498db")])
    style.configure("Treeview.Heading", background="#222222", foreground="white", font=("Courier", 9, "bold"), relief="flat")

    tree_frame = Frame(history_win, bg="#141414")
    tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # Define columns based on what the user actually cares about
    columns = ("Timestamp", "App Name", "Action Taken", "CPU Freed", "RAM Freed")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="none")

    # Format column headers
    tree.heading("Timestamp", text="TIME")
    tree.column("Timestamp", width=150, anchor="center")
    
    tree.heading("App Name", text="APPLICATION")
    tree.column("App Name", width=150, anchor="w")
    
    tree.heading("Action Taken", text="ACTION")
    tree.column("Action Taken", width=250, anchor="w")
    
    tree.heading("CPU Freed", text="CPU FREED")
    tree.column("CPU Freed", width=100, anchor="center")
    
    tree.heading("RAM Freed", text="RAM FREED")
    tree.column("RAM Freed", width=100, anchor="center")

    # Add a scrollbar to the table
    scrollbar = Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    # Read the CSV and populate the table
    try:
        with open(LogFiles, mode='r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header row
            
            records = list(reader)
            # Reverse list so newest entries show at the top
            for row in reversed(records):
                if len(row) >= 8:
                    try:
                        # Safely parse old and new usage to calculate exactly what was freed
                        old_cpu, new_cpu = float(row[4].replace('%', '')), float(row[5].replace('%', ''))
                        old_ram, new_ram = float(row[6].replace('%', '')), float(row[7].replace('%', ''))
                        
                        freed_cpu = f"{max(0.0, round(old_cpu - new_cpu, 1))}%"
                        freed_ram = f"{max(0.0, round(old_ram - new_ram, 1))}%"
                    except ValueError:
                        freed_cpu, freed_ram = "N/A", "N/A"

                    tree.insert("", "end", values=(row[0], row[1], row[3], freed_cpu, freed_ram))
    except FileNotFoundError:
        tree.insert("", "end", values=("No logs found", "-", "-", "-", "-"))


def continuous_loop():
    global saved_cpu, saved_ram
    if not heartbeat_paused:
        saved_cpu, saved_ram = system_scanner()
    window.after(5000, continuous_loop)


if __name__ == "__main__":
    log_data()  
    psutil.cpu_percent(interval=None) 
    
    saved_cpu, saved_ram = 0.0, 0.0

    window = Tk()
    window.title("Smart Resource Monitor and Auto-Mitigation System")
    window.geometry("1000x700") 
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

    # Controls at the bottom
    bottom_controls = Frame(window, bg="#141414")
    bottom_controls.pack(fill="x", padx=20, pady=10)

    btn_history = Button(bottom_controls, text="VIEW OPTIMIZATION HISTORY", font=("Arial", 10, "bold"), bg="#8e44ad", fg="white", height=2, command=open_history_window)
    btn_history.pack(side="left", fill="x", expand=True, padx=(0, 5))

    btn_exit = Button(bottom_controls, text="DISCONNECT SYSTEM", font=("Arial", 10, "bold"), bg="#222222", fg="#aaaaaa", height=2, command=window.destroy)
    btn_exit.pack(side="right", fill="x", expand=True, padx=(5, 0))

    window.after(1000, continuous_loop)
    window.mainloop()