import os
import sys
import json
import time
from datetime import datetime
import psutil


class CPUMonitor:

    def __init__(self, process_cpu_threshold=5.0, interval=5):
        self.process_cpu_threshold = process_cpu_threshold
        self.interval = interval

        # Resolve project root cleanly across Linux and Windows
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.log_dir = os.path.join(base_dir, "storage test files")
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception:
            # Absolute fallback to current directory if paths are unresolvable
            self.log_dir = os.getcwd()

        self.log_file = os.path.join(self.log_dir, "cpu_monitor.json")
        self.max_log_size = 5 * 1024 * 1024  # 5 MB Maximum log size

    def get_cpu_metrics(self):
        """
        Collects overall and per-core CPU usage.
        Returns safe defaults on OS exception.
        """
        try:
            total_cpu = psutil.cpu_percent(interval=0.1)
            per_core = psutil.cpu_percent(interval=None, percpu=True)

            return {
                "total_cpu": total_cpu if total_cpu is not None else 0.0,
                "per_core": per_core if per_core is not None else []
            }
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error reading hardware metrics: {e}", file=sys.stderr)
            return {"total_cpu": 0.0, "per_core": []}

    def get_heavy_processes(self):
        """
        Scans running processes and filters by the specified CPU threshold.
        Optimized one-pass iteration with dict caching to prevent system lag.
        """
        process_list = []
        try:
            for process in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    info = process.info
                    cpu = info.get('cpu_percent')

                    if cpu is not None and cpu > self.process_cpu_threshold:
                        # Isolated block for memory check to keep Windows permissions from breaking the loop
                        try:
                            mem_percent = round(process.memory_percent(), 2)
                        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                            mem_percent = 0.0

                        process_list.append({
                            "pid": info.get('pid', 0),
                            "name": info.get('name') or "Unknown",
                            "cpu_percent": cpu,
                            "memory_percent": mem_percent
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception:
                    continue  # Skip any single corrupted or rapid-cycling process
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error walking process tree: {e}", file=sys.stderr)

        # Sort from highest consumer to lowest
        try:
            process_list.sort(key=lambda x: x["cpu_percent"], reverse=True)
        except Exception:
            pass

        return process_list

    def rotate_logs(self):
        """
        Rotates the active log to cpu_monitor.json.old when it crosses max_log_size.
        Handles Windows/Linux file locks gracefully.
        """
        try:
            if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_log_size:
                backup = self.log_file + ".old"
                if os.path.exists(backup):
                    try:
                        os.remove(backup)
                    except Exception:
                        pass  # Backup file is locked by another reader; append instead of crashing
                os.rename(self.log_file, backup)
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Log rotation bypassed: {e}", file=sys.stderr)

    def log_data(self, payload):
        """Writes telemetric payloads as a single JSON line."""
        try:
            self.rotate_logs()
            with open(self.log_file, "a", encoding="utf-8") as outfile:
                outfile.write(json.dumps(payload) + "\n")
        except Exception as e:
            # Safe boundary print to console if disk space fills up or locks out entirely
            print(f"CRITICAL FILE SYSTEM WRITE FAILURE: {e}", file=sys.stderr)


if __name__ == "__main__":
    monitor = CPUMonitor(process_cpu_threshold=5.0, interval=5)

    print(f"Telemetry collector initialized.\nTarget destination: {monitor.log_file}")

    # Prime the psutil delta tracking system once before looping
    try:
        for p in psutil.process_iter(['cpu_percent']):
            try:
                p.info['cpu_percent']
            except Exception:
                pass
    except Exception:
        pass

    time.sleep(0.5)

    while True:
        try:
            cpu_stats = monitor.get_cpu_metrics()
            heavy_processes = monitor.get_heavy_processes()

            payload = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": cpu_stats["total_cpu"],
                "per_core": cpu_stats["per_core"],
                "processes": heavy_processes
            }

            monitor.log_data(payload)

        except KeyboardInterrupt:
            print("\nCollector gracefully stopped.")
            break
        except Exception as loop_err:
            print(f"[{datetime.now().isoformat()}] Top-level loop anomaly managed: {loop_err}", file=sys.stderr)

        # Fallback interval protector
        try:
            time.sleep(monitor.interval)
        except Exception:
            time.sleep(5)