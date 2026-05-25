# Script 1: Continuous, lightweight logger (CPU/RAM)


import os
import time
import json
from datetime import datetime
import psutil

# Ensure paths align with our project structure
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
STATE_FILE = os.path.join(DATA_DIR, "system_state.json")


def initialize_storage():
    """Creates the data directory and state file if they don't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(STATE_FILE):# src/resource_monitor.py
        blank_state = {
            "system": {"cpu_history": [], "ram_history": []},
            "processes": {}
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(blank_state, f, indent=2)


def collect_metrics():
    """Gathers global and per-process resource statistics."""
    current_state = {}

    # 1. Global Metrics
    system_cpu = psutil.cpu_percent()
    system_ram = psutil.virtual_memory().percent

    # 2. Per-Process Metrics
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            p_name = pinfo['name']
            pid = pinfo['pid']

            # Skip safe/system vital processes and this monitor itself
            if p_name in ['Idle', 'System', 'Registry'] or pid == os.getpid():
                continue

            cpu_usage = pinfo['cpu_percent']
            ram_usage = pinfo['memory_percent']  # % of total system RAM

            # Simple rule: if it's using CPU, it's considered "actively used" right now
            is_active = cpu_usage > 1.5

            # Unique key combining name and PID (e.g., "chrome.exe_1402")
            proc_key = f"{p_name}_{pid}"

            current_state[proc_key] = {
                "pid": pid,
                "name": p_name,
                "cpu": cpu_usage,
                "ram_percent": round(ram_usage, 2),
                "is_active": is_active
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Safe ignore if process closes mid-execution or requires admin privileges
            continue

    return system_cpu, system_ram, current_state


def update_historical_data(system_cpu, system_ram, current_state):
    """Updates the JSON file with rolling historical timelines."""
    with open(STATE_FILE, 'r') as f:
        history = json.load(f)

    # Maintain global system averages (keep trailing 20 records)
    history["system"]["cpu_history"].append(system_cpu)
    history["system"]["ram_history"].append(system_ram)
    history["system"]["cpu_history"] = history["system"]["cpu_history"][-20:]
    history["system"]["ram_history"] = history["system"]["ram_history"][-20:]

    # Process and blend current readings into history entries
    for proc_key, data in current_state.items():
        if proc_key not in history["processes"]:
            history["processes"][proc_key] = {
                "pid": data["pid"],
                "name": data["name"],
                "accumulated_idle_intervals": 0,
                "cpu_samples": [],
                "ram_samples": [],
                "last_active": datetime.now().isoformat()
            }

        p_hist = history["processes"][proc_key]
        p_hist["cpu_samples"].append(data["cpu"])
        p_hist["ram_samples"].append(data["ram_percent"])

        # Keep process rolling window locked to last 20 frames
        p_hist["cpu_samples"] = p_hist["cpu_samples"][-20:]
        p_hist["ram_samples"] = p_hist["ram_samples"][-20:]

        if data["is_active"]:
            p_hist["last_active"] = datetime.now().isoformat()
            p_hist["accumulated_idle_intervals"] = 0
        else:
            # Increment how long this app has been sitting completely idle
            p_hist["accumulated_idle_intervals"] += 1

    # Cleanup dead processes so the JSON doesn't grow forever
    tracked_keys = list(history["processes"].keys())
    for key in tracked_keys:
        if key not in current_state:
            del history["processes"][key]

    # Write state back safely
    with open(STATE_FILE, 'w') as f:
        json.dump(history, f, indent=2)


if __name__ == "__main__":
    initialize_storage()
    print("Resource Monitor running successfully...")
    print(f"Tracking logs writing to: {STATE_FILE}")
    print("Press Ctrl+C to terminate.")

    try:
        while True:
            sys_cpu, sys_ram, proc_state = collect_metrics()
            update_historical_data(sys_cpu, sys_ram, proc_state)
            time.sleep(3)  # Sample system behavior every 3 seconds
    except KeyboardInterrupt:
        print("\nStopping Resource Monitor. Goodbye!")