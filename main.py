import psutil
import os
import sys 
import time
import csv
from datetime import datetime

from tkinter import *
from tkinter import messagebox
from tkinter import ttk  # Imported for notebook/tabs framework

# Thresholds
CpuThres = 10.0  
RamThres = 10.0  

LogFiles = os.path.join("data", "logs.csv")

CRITICAL_OS_PROCESSES = {
    "csrss.exe", "lsass.exe", "wininit.exe", "smss.exe", "services.exe", 
    "winlogon.exe", "svchost.exe", "explorer.exe", "taskhostw.exe", 
    "spoolsv.exe", "init", "systemd", "Registry", "System", "Idle", "System Idle Process"
}

PROTECTED_SYSTEM_USERS = {"nt authority\\system", "nt authority\\local service", "nt authority\\network service", "root"}

def log_data(): 
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(LogFiles):
        with open(LogFiles, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "App Name", "PID", "Action Taken", "System CPU Before", "System CPU After","System RAM Before", "System RAM After"])


def system_scanner():
    try:
        cpu = psutil.cpu_percent(interval=None) 
        ram = psutil.virtual_memory().percent
        
        cpu_label.config(text=f"CPU: {cpu}%")
        ram_label.config(text=f"RAM: {ram}%")

        # Clear active views
        for widget in active_scroll_frame.winfo_children():
            widget.destroy()
        for widget in idle_scroll_frame.winfo_children():
            widget.destroy()

        if cpu < CpuThres and ram < RamThres:
            status_label.config(text="SYSTEM STATUS: STABLE", fg="#2ecc71")
        else:
            status_label.config(text="HIGH RESOURCE ALERT", fg="#e74c3c")

        heavy_count = 0
        idle_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                cpu_percent = proc.info['cpu_percent']
                memory_percent = proc.info['memory_percent']
                status = proc.info['status']

                if pid == os.getpid():
                    continue

                is_protected = False
                if name in CRITICAL_OS_PROCESSES:
                    is_protected = True
                else:
                    try:
                        username = proc.username().lower()
                        if username in PROTECTED_SYSTEM_USERS:
                            is_protected = True
                    except (psutil.AccessDenied, Exception):
                        is_protected = True

                app_details = {
                    "pid": pid,
                    "name": name,
                    "cpu": round(cpu_percent, 1),
                    "ram": round(memory_percent, 1),
                    "score": round((cpu_percent * 1.5 + memory_percent * 2.5), 2),
                    "status": status,
                    "is_protected": is_protected
                }

                # CONDITION 1: Heavy Processes
                if cpu_percent > 1.5 or memory_percent > 1.5:
                    create_process_row(active_scroll_frame, app_details, is_idle_pane=False)
                    heavy_count += 1

                # CONDITION 2: Idle Processes
                elif cpu_percent == 0.0 and memory_percent > 0.1:
                    if proc.memory_info().rss > 15 * 1024 * 1024: 
                        create_process_row(idle_scroll_frame, app_details, is_idle_pane=True)
                        idle_count += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Dynamic Tab Title Updates
        notebook.tab(0, text=f" Active Hogs ({heavy_count}) ")
        notebook.tab(1, text=f" Idle Applications ({idle_count}) ")
        return cpu, ram
    except Exception as e:
        print(f"Scanner error: {e}")
        return 0.0, 0.0


def create_process_row(target_frame, app, is_idle_pane):
    # Modern card styling for process entries
    row_card = Frame(target_frame, bg="#1e1e1e", bd=0, padx=10, pady=8)
    row_card.pack(fill="x", padx=10, pady=4)
    
    if app['is_protected']:
        text_color = "#666666"
        badge_text = f"[SYSTEM] {app['name']}"
    else:
        text_color = "#ffffff" if not is_idle_pane else "#aaaaaa"
        badge_text = app['name']

    # Beautifully aligned, spacious string layout
    if is_idle_pane:
        display_str = f"PID: {app['pid']:<8} |  {badge_text:<30} |  Memory Footprint: {app['ram']}%"
    else:
        display_str = f"PID: {app['pid']:<8} |  {badge_text:<30} |  CPU: {app['cpu']}%   RAM: {app['ram']}%   (Score: {app['score']})"
        
    lbl = Label(row_card, text=display_str, font=("Consolas", 10), bg="#1e1e1e", fg=text_color, anchor="w")
    lbl.pack(side="left", fill="x", expand=True)

    # Contextual Button Actions
    if app['is_protected']:
        lbl_lock = Label(row_card, text="PROTECTED", font=("Arial", 8, "bold"), bg="#2a2a2a", fg="#666666", width=12, pady=3)
        lbl_lock.pack(side="right", padx=5)
    else:
        btn_purge = Button(row_card, text="TERMINATE TASK", font=("Arial", 8, "bold"), bg="#c0392b", fg="white", activebackground="#e74c3c", activeforeground="white", bd=0, padx=12, pady=4, command=lambda: implement_mitigation(app, "Purge"))
        btn_purge.pack(side="right", padx=5)
        
        if is_idle_pane:
            btn_trim = Button(row_card, text="OPTIMIZE RAM", font=("Arial", 8, "bold"), bg="#27ae60", fg="white", activebackground="#2ecc71", activeforeground="white", bd=0, padx=12, pady=4, command=lambda: implement_mitigation(app, "Trim"))
            btn_trim.pack(side="right", padx=5)


def implement_mitigation(app, action_type): 
    if app.get('is_protected', False):
        messagebox.showerror("Security Block", "This action is restricted on OS tasks.")
        return

    confirm = messagebox.askyesno("Action Confirmation", f"Are you sure you want to run '{action_type}' optimization on {app['name']}?")
    if not confirm:
        return

    action_string = "Skipped"
    try:
        proc = psutil.Process(app['pid'])
        
        if action_type == "Purge":
            proc.kill() 
            action_string = "Force Killed via Dashboard UI"
            messagebox.showinfo("Success", f"Terminated {app['name']} instantly.")
            
        elif action_type == "Trim":
            if sys.platform == "win32":
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x0100, False, app['pid'])
                if handle:
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    action_string = "RAM Optimized via WorkingSet Trimming"
                    messagebox.showinfo("Success", f"Reclaimed memory frames from {app['name']}.")
            else:
                proc.nice(19)
                action_string = "Linux Nice Deprioritization"
                messagebox.showinfo("Success", f"Adjusted scheduling priority for {app['name']}.")

        status_label.config(text="RE-SAMPLING METRICS...", fg="#e67e22")
        window.after(1200, lambda: log_post_action_metrics(app, action_string))

    except psutil.AccessDenied:
        messagebox.showerror("Access Denied", "Action rejected. Run code as Administrator to manage this app.")
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        messagebox.showerror("Error", "Process missing or changed state.")


def log_post_action_metrics(app, action_string):
    new_cpu = psutil.cpu_percent(interval=None)
    new_ram = psutil.virtual_memory().percent
    
    try:
        with open(LogFiles, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), app['name'], app['pid'], action_string, f"{saved_cpu}%", f"{new_cpu}%", f"{saved_ram}%", f"{new_ram}%"])
    except Exception as e:
        print(f"Logging error: {e}")
        
    system_scanner()


def load_logs_to_viewer():
    """Reads the local CSV file and updates the logs terminal tab view."""
    logs_text.config(state="normal")
    logs_text.delete("1.0", END)
    if os.path.exists(LogFiles):
        with open(LogFiles, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                logs_text.insert(END, " | ".join(row) + "\n")
    else:
        logs_text.insert(END, "No recorded events logged yet.")
    logs_text.config(state="disabled")


def continuous_loop():
    global saved_cpu, saved_ram
    saved_cpu, saved_ram = system_scanner()
    window.after(5000, continuous_loop)


if __name__ == "__main__":
    log_data()  
    psutil.cpu_percent(interval=None) 
    
    saved_cpu, saved_ram = 0.0, 0.0

    window = Tk()
    window.title("Smart Resource Monitor")
    window.geometry("900x680")
    window.configure(bg="#121212")

    # Custom styling for standard Tkinter Notebook elements to match Dark Mode Theme
    style = ttk.Style()
    style.theme_use('default')
    style.configure('TNotebook', background='#121212', borderwidth=0)
    style.configure('TNotebook.Tab', background='#252525', foreground='#ffffff', font=('Arial', 10, 'bold'), padding=[15, 6])
    style.map('TNotebook.Tab', background=[('selected', '#1a73e8')], foreground=[('selected', '#ffffff')])

    # --- TOP CONTROL BAR WIDGET ---
    top_bar = Frame(window, bg="#1a1a1a", height=60)
    top_bar.pack(fill="x", padx=15, pady=(15, 5))

    status_label = Label(top_bar, text="SYSTEM MONITOR CONNECTED", font=("Arial", 11, "bold"), bg="#1a1a1a", fg="#2ecc71")
    status_label.pack(side="left", padx=15, pady=15)

    ram_label = Label(top_bar, text="RAM: --", font=("Consolas", 12, "bold"), bg="#252525", fg="#3498db", padx=12, pady=4)
    ram_label.pack(side="right", padx=15)

    cpu_label = Label(top_bar, text="CPU: --", font=("Consolas", 12, "bold"), bg="#252525", fg="#e67e22", padx=12, pady=4)
    cpu_label.pack(side="right")

    # --- MAIN NOTEBOOK (TABBED WRAPPER PANEL) ---
    notebook = ttk.Notebook(window)
    notebook.pack(fill="both", expand=True, padx=15, pady=5)

    # TAB 1: ACTIVE LOADS
    tab_active = Frame(notebook, bg="#121212")
    notebook.add(tab_active, text=" Active Hogs ")
    
    active_canvas = Canvas(tab_active, bg="#121212", highlightthickness=0)
    active_scroll = Scrollbar(tab_active, orient="vertical", command=active_canvas.yview)
    active_scroll_frame = Frame(active_canvas, bg="#121212")
    active_scroll_frame.bind("<Configure>", lambda e: active_canvas.configure(scrollregion=active_canvas.bbox("all")))
    active_canvas.create_window((0, 0), window=active_scroll_frame, anchor="nw", width=860)
    active_canvas.configure(yscrollcommand=active_scroll.set)
    active_canvas.pack(side="left", fill="both", expand=True, pady=5)
    active_scroll.pack(side="right", fill="y")

    # TAB 2: IDLE BACKGROUND APPLICATIONS
    tab_idle = Frame(notebook, bg="#121212")
    notebook.add(tab_idle, text=" Idle Applications ")

    idle_canvas = Canvas(tab_idle, bg="#121212", highlightthickness=0)
    idle_scroll = Scrollbar(tab_idle, orient="vertical", command=idle_canvas.yview)
    idle_scroll_frame = Frame(idle_canvas, bg="#121212")
    idle_scroll_frame.bind("<Configure>", lambda e: idle_canvas.configure(scrollregion=idle_canvas.bbox("all")))
    idle_canvas.create_window((0, 0), window=idle_scroll_frame, anchor="nw", width=860)
    idle_canvas.configure(yscrollcommand=idle_scroll.set)
    idle_canvas.pack(side="left", fill="both", expand=True, pady=5)
    idle_scroll.pack(side="right", fill="y")

    # NEW FEATURE - TAB 3: SYSTEM HISTORIC LOGS VIEWER
    tab_logs = Frame(notebook, bg="#121212")
    notebook.add(tab_logs, text=" Historic Action Logs ")
    notebook.bind("<<NotebookTabChanged>>", lambda e: load_logs_to_viewer() if notebook.index("current") == 2 else None)

    logs_text = Text(tab_logs, font=("Consolas", 9), bg="#0f0f0f", fg="#888888", wrap="none", padx=10, pady=10)
    logs_text.pack(fill="both", expand=True, padx=10, pady=10)

    # --- BOTTOM SYSTEM EXIT AREA ---
    btn_exit = Button(window, text="CLOSE MONITOR SYSTEM", font=("Arial", 10, "bold"), bg="#2c3e50", fg="#bdc3c7", activebackground="#34495e", activeforeground="white", bd=0, height=2, command=window.destroy)
    btn_exit.pack(fill="x", padx=15, pady=15)

    window.after(1000, continuous_loop)
    window.mainloop()