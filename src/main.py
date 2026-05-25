# src/main.py

import os
import sys
import json
import csv
import time
from datetime import datetime
import psutil

# Path alignments
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "system_state.json")
LOG_FILE = os.path.join(DATA_DIR, "mitigation_history.csv")

# Threshold configurations
CPU_THRESHOLD = 70.0
RAM_THRESHOLD = 75.0


def load_system_state():
    """Reads historical metrics data collected by the monitor."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("❌ State file not found or corrupted. Make sure resource_monitor.py is running.")
        return None


def log_mitigation_result(action, app_name, before_cpu, after_cpu, before_ram, after_ram):
    """Saves structural performance results to a CSV log."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["Timestamp", "Action", "App Name", "Before CPU %", "After CPU %", "Before RAM %", "After RAM %"])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action,
            app_name,
            before_cpu,
            after_cpu,
            before_ram,
            after_ram
        ])
    print(f"📈 Logged performance change to {LOG_FILE}")


def analyze_and_score(state):
    """Applies rule-based calculations to locate idle resource hogs."""
    cpu_hist = state["system"]["cpu_history"]
    ram_hist = state["system"]["ram_history"]

    if not cpu_hist or not ram_hist:
        print("⚠️ Not enough history collected yet. Waiting for monitor data...")
        return []

    avg_sys_cpu = sum(cpu_hist) / len(cpu_hist)
    avg_sys_ram = sum(ram_hist) / len(ram_hist)

    print(f"📊 Current Burden -> Avg CPU: {avg_sys_cpu:.1f}%, Avg RAM: {avg_sys_ram:.1f}%")

    if avg_sys_cpu < CPU_THRESHOLD and avg_sys_ram < RAM_THRESHOLD:
        print("✅ System resources are stable. No mitigation needed.")
        return []

    offenders = []

    for proc_key, metrics in state["processes"].items():
        if not metrics["cpu_samples"] or not metrics["ram_samples"]:
            continue

        avg_p_cpu = sum(metrics["cpu_samples"]) / len(metrics["cpu_samples"])
        avg_p_ram = sum(metrics["ram_samples"]) / len(metrics["ram_samples"])
        idle_ticks = metrics["accumulated_idle_intervals"]

        cpu_weight = avg_p_cpu * 1.5
        ram_weight = avg_p_ram * 2.5

        idle_factor = min(1.0 + (idle_ticks * 0.1), 4.0)
        inefficiency_score = (cpu_weight + ram_weight) * idle_factor

        if idle_ticks >= 5 and (avg_p_cpu > 1.0 or avg_p_ram > 0.5):
            offenders.append({
                "pid": metrics["pid"],
                "name": metrics["name"],
                "score": round(inefficiency_score, 2),
                "avg_cpu": round(avg_p_cpu, 1),
                "avg_ram": round(avg_p_ram, 1),
                "idle_duration_cycles": idle_ticks
            })

    return sorted(offenders, key=lambda x: x['score'], reverse=True)


def execute_mitigation(target, mode="suggest"):
    """Applies optimizations, suspensions, or closures cleanly across platforms."""
    pid = target["pid"]
    name = target["name"]

    try:
        proc = psutil.Process(pid)

        before_cpu = psutil.cpu_percent()
        before_ram = psutil.virtual_memory().percent

        if mode == "suggest":
            print(f"\n🚨 ALERT: '{name}' (PID: {pid}) has been idle for {target['idle_duration_cycles']} cycles!")
            print(
                f"   Resource Waste -> Avg CPU: {target['avg_cpu']}%, Avg RAM: {target['avg_ram']}% (Score: {target['score']})")
            decision = input(f"👉 Choose action (optimize/terminate/suspend/skip): ").strip().lower()

            if decision not in ['optimize', 'terminate', 'suspend']:
                print("Skipping action.")
                return
        else:
            decision = "optimize"

        action_taken = ""

        # --- OPTIMIZE STRATEGY ---
        if decision == "optimize":
            if sys.platform == 'win32':
                import ctypes
                PROCESS_SET_QUOTA = 0x0100
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SET_QUOTA, False, pid)
                if handle:
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, -1, -1)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    action_taken = "Memory Optimized (Windows)"
            else:
                # Linux Strategy: Lower scheduling priority to max nice value (19)
                # Gives CPU scheduling preference away to active foreground user apps
                proc.nice(19)
                action_taken = "Priority Lowered (Linux Nice)"
                print(f"📉 Set CPU priority for {name} to lowest background priority.")

        # --- SUSPEND STRATEGY (Linux Native Tab Freezing) ---
        elif decision == "suspend":
            if sys.platform != 'win32':
                proc.suspend()  # Issues SIGSTOP under the hood
                action_taken = "Process Suspended (SIGSTOP)"
                print(f"⏸️ Suspended {name}. Process is frozen; it won't consume CPU cycles until resumed.")
            else:
                print("❌ Suspend mode not natively optimized for Windows targets in this version.")
                return

        # --- TERMINATE STRATEGY ---
        elif decision == "terminate":
            proc.terminate()
            action_taken = "Terminated"
            print(f"💀 Forcefully terminated: {name}")

        time.sleep(2)
        after_cpu = psutil.cpu_percent()
        after_ram = psutil.virtual_memory().percent

        log_mitigation_result(action_taken, name, before_cpu, after_cpu, before_ram, after_ram)

    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"❌ Action failed: Process closed unexpectedly or script lacks permissions.")


if __name__ == "__main__":
    print("🧠 System Decision Engine Running...")
    RUN_MODE = "suggest"

    state = load_system_state()
    if state:
        targets = analyze_and_score(state)
        if targets:
            print(f"⚠️ Detected {len(targets)} resource-inefficient processes.")
            execute_mitigation(targets[0], mode=RUN_MODE)
        else:
            print("Everything looks pristine right now.")