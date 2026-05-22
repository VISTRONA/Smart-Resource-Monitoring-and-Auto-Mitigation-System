"""
CPU Monitor Module
==================
Tracks total CPU usage, per-core metrics, and high-consumption processes.
Logs data locally in JSON Lines format and handles automatic high-usage alerting.

Project Structure Context:
.
├── engine
├── main.py
├── monitors
│   ├── cpu_monitor.py  <- This file
│   └── disk_monitor.py
└── storage test files  <- Target logging directory
"""

import os
import sys
import json
import time
from datetime import datetime
import psutil


class CPUMonitor:
    """Handles CPU metrics collection, process tracking, and alerting logic."""

    def __init__(self, alert_threshold=85.0, consecutive_triggers=4):
        self.alert_threshold = alert_threshold
        self.consecutive_triggers = consecutive_triggers
        self.high_use_counter = 0

        # Cross-platform path resolution relative to this file's location
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(base_dir, "storage test files")
        self.log_file = os.path.join(self.log_dir, "cpu_monitor.json")

        # Ensure target storage directory exists
        os.makedirs(self.log_dir, exist_ok=True)

    def get_cpu_metrics(self):
        """
        Gathers overall and per-core CPU usage safely.
        Using interval=0.1 prevents heavy blocking while allowing psutil to sample accurately.
        """
        # Collect overall and per-cpu simultaneously using a single blocking sample period
        total_cpu = psutil.cpu_percent(interval=0.1)
        per_core = psutil.cpu_percent(percpu=True)

        # Evaluate alerting logic based on the collected reading
        self._check_alerts(total_cpu)

        return {
            "total_cpu": total_cpu,
            "per_core": per_core
        }

    def get_heavy_processes(self, cpu_threshold=5.0):
        """
        Scans running processes and returns those exceeding the CPU threshold.
        Includes robust exception handling for ephemeral and OS-protected processes.
        """
        process_list = []
        # Fetching process metrics can throw errors mid-iteration if a process terminates
        for process in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                # Note: psutil's 'cpu_percent' here evaluates since the last process_iter call
                info = process.info
                if info['cpu_percent'] and info['cpu_percent'] > cpu_threshold:
                    process_list.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return process_list

    def _check_alerts(self, current_usage):
        """Internal tracker for persistent high CPU spikes."""
        if current_usage > self.alert_threshold:
            self.high_use_counter += 1
            if self.high_use_counter >= self.consecutive_triggers:
                self._trigger_alert(f"HIGH_USE (Sustained at {current_usage}%)")
        else:
            self.high_use_counter = 0  # Reset if usage dips below threshold

    def _trigger_alert(self, error_msg):
        """Dispatches alerts. Expand this method to connect to Webhooks, email, etc."""
        print(f"[{datetime.now().isoformat()}] ALERT: {error_msg}", file=sys.stderr)


if __name__ == "__main__":
    monitor = CPUMonitor(alert_threshold=85.0, consecutive_triggers=4)
    print(f"Starting CPU Monitor. Logging data to: {monitor.log_file}")

    while True:
        try:
            # 1. Gather all system data point components
            cpu_stats = monitor.get_cpu_metrics()
            heavy_procs = monitor.get_heavy_processes(cpu_threshold=5.0)

            # 2. Package data with an active, fresh timestamp
            payload = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": cpu_stats["total_cpu"],
                "per_core": cpu_stats["per_core"],
                "processes": heavy_procs
            }

            # 3. Write securely using proper file encoding configuration
            with open(monitor.log_file, 'a', encoding='utf-8') as outfile:
                outfile.write(json.dumps(payload) + "\n")

            # 4. Wait out the interval loop cycle
            time.sleep(5)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            break