import psutil
import os
import csv
import time
from datetime import datetime

from tkinter import *
from tkinter import messagebox

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
CPU_THRESHOLD = 10.0   # % — kept low for demo/testing
RAM_THRESHOLD = 10.0   # %

# Score weights: CPU impact weighted less than RAM since RAM pressure is stickier
CPU_WEIGHT = 1.5
RAM_WEIGHT = 2.5

LOG_DIR  = "data"
LOG_FILE = os.path.join(LOG_DIR, "logs.csv")

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

def init_log():
    """Create log directory + CSV with headers if they don't exist yet."""
    os.makedirs(LOG_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "App Name", "PID", "Action Taken",
                "System CPU Before", "System CPU After",
                "System RAM Before", "System RAM After"
            ])


def write_log(name, pid, action, cpu_before, cpu_after, ram_before, ram_after):
    """Append one row to the CSV log. Silently handles I/O errors."""
    try:
        with open(LOG_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name, pid, action,
                f"{cpu_before}%", f"{cpu_after}%",
                f"{ram_before}%", f"{ram_after}%"
            ])
    except OSError as e:
        print(f"[LOG ERROR] Could not write to log file: {e}")

# ---------------------------------------------------------------------------
# CORE SCANNER
# ---------------------------------------------------------------------------

def system_scanner():
    """
    Sample live CPU + RAM, refresh the UI, and build the process rows.
    Returns (cpu, ram) as floats.
    
    NOTE: cpu_percent(interval=None) returns the value since the last call.
    The warm-up call in __main__ ensures the first reading is valid.
    """
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent

    cpu_label.config(text=f"CPU Usage: {cpu:.1f}%")
    ram_label.config(text=f"RAM Usage: {ram:.1f}%")

    # Clear previous process rows
    for widget in scrollable_frame.winfo_children():
        widget.destroy()

    if cpu < CPU_THRESHOLD and ram < RAM_THRESHOLD:
        status_label.config(text="SYSTEM STATUS: SAFE", fg="#2ecc71")
        process_text.config(
            text="\n   System metrics are stable.\n   No heavy background resource hogs detected."
        )
        return cpu, ram

    status_label.config(text="HIGH RESOURCE USAGE DETECTED!", fg="#e74c3c")

    # Collect heavy processes
    heavy = []
    own_pid = os.getpid()

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pid  = proc.info['pid']
            name = proc.info['name']
            cpu_pct = proc.info['cpu_percent'] or 0.0
            ram_pct = proc.info['memory_percent'] or 0.0

            # Skip kernel/idle processes and ourselves
            if pid == own_pid:
                continue
            if name in {"System", "Idle", "System Idle Process", "Registry", "init", "kthreadd"}:
                continue

            # Only show processes that meaningfully contribute
            if cpu_pct > 1.5 or ram_pct > 1.5:
                score = cpu_pct * CPU_WEIGHT + ram_pct * RAM_WEIGHT
                heavy.append({
                    "pid":   pid,
                    "name":  name,
                    "cpu":   round(cpu_pct, 1),
                    "ram":   round(ram_pct, 1),
                    "score": round(score, 2)
                })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Sort heaviest first so the worst offenders are immediately visible
    heavy.sort(key=lambda x: x["score"], reverse=True)

    for idx, app in enumerate(heavy):
        create_process_row(idx, app)

    if heavy:
        process_text.config(
            text=f" Identified {len(heavy)} heavy processes. Act directly on targets below:"
        )
    else:
        process_text.config(
            text=(
                "\n   High system load detected, but individual user applications are low.\n"
                "   Likely transient kernel or OS micro-bursting."
            )
        )

    return cpu, ram

# ---------------------------------------------------------------------------
# UI ROW BUILDER
# ---------------------------------------------------------------------------

def create_process_row(row_index: int, app: dict):
    """Render one process row with its label and PURGE button."""
    row_frame = Frame(scrollable_frame, bg="#0f0f0f", bd=1, relief="flat")
    row_frame.pack(fill="x", padx=5, pady=4)

    display_str = (
        f"PID: {app['pid']:<6} | "
        f"{app['name'][:22]:<22} | "
        f"CPU: {app['cpu']}% | "
        f"RAM: {app['ram']}% | "
        f"Score: {app['score']}"
    )
    lbl = Label(
        row_frame, text=display_str,
        font=("Courier", 10), bg="#0f0f0f", fg="#ffffff", anchor="w"
    )
    lbl.pack(side="left", fill="x", expand=True, padx=5)

    btn_purge = Button(
        row_frame,
        text="PURGE",
        font=("Arial", 8, "bold"),
        bg="#e74c3c", fg="white",
        bd=0, padx=10,
        command=lambda a=app: direct_purge_engine(a)   # FIX: default-arg capture avoids late-binding bug
    )
    btn_purge.pack(side="right", padx=5)

# ---------------------------------------------------------------------------
# PURGE ENGINE
# ---------------------------------------------------------------------------

def direct_purge_engine(app: dict):
    """
    Terminate the target process + all its children, wait for exit, then
    re-sample metrics and write a log entry — without blocking the UI thread.

    Why children matter: apps like Spotify, Chrome, Electron spawn multiple
    child processes. Killing only the PID shown leaves orphaned children
    running and the app appears to stay alive.
    """
    confirm = messagebox.askyesno(
        "Confirm Action",
        f"Are you sure you want to completely PURGE/TERMINATE\n"
        f"{app['name']} (PID: {app['pid']})?"
    )
    if not confirm:
        return

    cpu_before = saved_cpu
    ram_before = saved_ram

    try:
        proc = psutil.Process(app['pid'])

        # Collect children BEFORE sending any signal (they may vanish after)
        try:
            children = proc.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            children = []

        # --- Phase 1: SIGTERM (graceful) ---
        procs_to_kill = [proc] + children
        for p in procs_to_kill:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Wait up to 3 s for graceful shutdown
        _, still_alive = psutil.wait_procs(procs_to_kill, timeout=3)

        # --- Phase 2: SIGKILL for anything still running ---
        for p in still_alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        # Final wait — confirm they're all gone
        psutil.wait_procs(still_alive, timeout=2)

        killed_count = len(procs_to_kill)
        action_string = f"Terminated via Direct UI Grid Button ({killed_count} process(es) killed)"

        if killed_count > 1:
            messagebox.showinfo(
                "Success",
                f"Closed {app['name']} and {killed_count - 1} child process(es) successfully."
            )
        else:
            messagebox.showinfo("Success", f"Closed {app['name']} successfully.")

    except psutil.NoSuchProcess:
        messagebox.showwarning("Already Gone", f"{app['name']} (PID: {app['pid']}) was already terminated.")
        system_scanner()
        return
    except psutil.AccessDenied:
        messagebox.showerror(
            "Access Denied",
            "This script lacks the privileges to terminate that process.\n"
            "Try running as administrator/root:\n\n  sudo python resource_monitor.py"
        )
        return
    except psutil.ZombieProcess:
        messagebox.showwarning("Zombie Process", f"{app['name']} is a zombie process and cannot be killed directly.")
        return

    # Post-action: use window.after so Tkinter doesn't freeze during the wait
    status_label.config(text="SAMPLING POST-ACTION RESOURCE IMPROVEMENTS...", fg="#e67e22")
    window.update_idletasks()

    def _post_sample():
        new_cpu = psutil.cpu_percent(interval=None)
        new_ram = psutil.virtual_memory().percent

        write_log(
            app['name'], app['pid'], action_string,
            cpu_before, new_cpu,
            ram_before, new_ram
        )
        status_label.config(text="OPTIMIZATION SUCCESS METRICS LOGGED", fg="#2ecc71")
        system_scanner()

    # 1.2 s delay via event loop — does NOT block the UI thread
    window.after(1200, _post_sample)

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

def continuous_loop():
    global saved_cpu, saved_ram
    saved_cpu, saved_ram = system_scanner()
    window.after(5000, continuous_loop)

# ---------------------------------------------------------------------------
# MOUSE SCROLL HELPER
# ---------------------------------------------------------------------------

def _on_mousewheel(event):
    """Cross-platform mouse-wheel scrolling for the process canvas."""
    # Windows/macOS send event.delta; Linux sends Button-4/5
    if event.num == 4:
        canvas.yview_scroll(-1, "units")
    elif event.num == 5:
        canvas.yview_scroll(1, "units")
    else:
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_log()

    # Warm-up call: the first cpu_percent(interval=None) always returns 0.0
    # because there is no prior sample to diff against. Calling it once with
    # a blocking interval seeds the internal counter correctly.
    psutil.cpu_percent(interval=0.1)

    saved_cpu = 0.0
    saved_ram = 0.0

    # ---- WINDOW ----
    window = Tk()
    window.title("Smart Resource Monitor and Auto-Mitigation System")
    window.geometry("900x700")
    window.configure(bg="#141414")

    # ---- TITLE ----
    tit = Label(
        window,
        text="Smart Resource Monitor and Auto-Mitigation System",
        font=("Arial", 16, "bold"), bg="#141414", fg="white"
    )
    tit.pack(pady=10)

    # ---- LIVE HARDWARE METRICS ----
    dashboard = LabelFrame(
        window,
        text=" LIVE HARDWARE METRICS ",
        font=("Courier", 10, "bold"),
        bg="#1c1c1c", fg="#2ecc71", bd=2, relief="groove"
    )
    dashboard.pack(fill="x", padx=20, pady=5, ipady=5)

    cpu_label = Label(
        dashboard, text="CPU Usage: Fetching...",
        font=("Courier", 13, "bold"), bg="#1c1c1c", fg="white"
    )
    cpu_label.pack(side="left", expand=True, pady=5)

    ram_label = Label(
        dashboard, text="RAM Usage: Fetching...",
        font=("Courier", 13, "bold"), bg="#1c1c1c", fg="white"
    )
    ram_label.pack(side="right", expand=True, pady=5)

    # ---- STATUS STRIP ----
    status_frame = Frame(window, bg="#222222", bd=1, relief="sunken")
    status_frame.pack(fill="x", padx=20, pady=5)

    status_title = Label(
        status_frame, text="ENGINE PROFILE: ",
        font=("Courier", 11, "bold"), bg="#222222", fg="#888888"
    )
    status_title.pack(side="left", padx=(10, 2))

    status_label = Label(
        status_frame, text="RUNNING FOREVER LOOP...",
        font=("Courier", 11, "bold"), bg="#222222", fg="yellow"
    )
    status_label.pack(side="left")

    # ---- PROCESS PANEL ----
    monitor_box = LabelFrame(
        window,
        text=" PROCESS INTERACTION PANEL ",
        font=("Courier", 10, "bold"),
        bg="#1c1c1c", fg="#e67e22", bd=2, relief="groove"
    )
    monitor_box.pack(fill="both", expand=True, padx=20, pady=10)

    process_text = Label(
        monitor_box,
        text="Initializing metric sweeps. Scanning for hardware footprint anomalies...",
        font=("Courier", 10), bg="#0f0f0f", fg="#00ff00",
        anchor="nw", justify="left"
    )
    process_text.pack(fill="x", padx=15, pady=5)

    # ---- SCROLLABLE CANVAS ----
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

    # Bind mouse-wheel scroll (works on Windows, macOS, Linux)
    canvas.bind("<MouseWheel>", _on_mousewheel)   # Windows / macOS
    canvas.bind("<Button-4>",   _on_mousewheel)   # Linux scroll up
    canvas.bind("<Button-5>",   _on_mousewheel)   # Linux scroll down

    # ---- EXIT BUTTON ----
    btn_exit = Button(
        window,
        text="DISCONNECT SYSTEM (EXIT)",
        font=("Arial", 11, "bold"),
        bg="#222222", fg="#aaaaaa",
        height=2,
        command=window.destroy
    )
    btn_exit.pack(fill="x", padx=20, pady=(0, 15))

    # Kick off the monitoring loop after 1 s
    window.after(1000, continuous_loop)
    window.mainloop()