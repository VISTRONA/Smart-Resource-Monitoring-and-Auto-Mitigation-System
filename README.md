# Smart Resource Monitor & Auto-Mitigation System

A lightweight, automated system utility built in Python utilizing **Tkinter** and **psutil**. This tool continuously tracks real-time hardware telemetry and categorizes tasks into **Active Resource Hogs** and **Idle Background Tasks**, offering targeted mitigation strategies (like force-killing or advanced RAM trimming) while dynamically safe-guarding critical system processes.

## 🚀 Key Features

* **Dual-Category Processing (Side-by-Side Analysis):** Discovers and segments background applications automatically based on their structural resource footprint.
    * **Active Loads:** High-stress apps triggering significant processor or memory spikes.
    * **Idle Applications:** Programs lingering silently in the background, drawing $0.0\%$ CPU while unnecessarily leaking RAM.
* **Advanced Mitigation Strategies:**
    * **Terminate Task (All OS platforms):** Force-kills processes instantly at the kernel level (`proc.kill()`) to bypass stubborn app hangs.
    * **Optimize RAM (Windows Exclusive):** Uses native Win32 API bindings (`SetProcessWorkingSetSize`) to flush dormant memory pages straight into the system standby pool, instantly recovering RAM without closing the application.
* **System Task Protection Layer:** Prevents critical Windows services (e.g., `svchost.exe`, `explorer.exe`, `csrss.exe`) and root accounts from being managed or terminated, rendering them completely unclickable in the UI to protect against accidental system crashes (BSOD).
* **Modern Tabbed UI Design:** A sleek, non-blocking dark mode interface built using asynchronous Tkinter loops to maintain structural stability and completely eliminate "Not Responding" application locks.
* **Historic Audit Logging:** Automatically saves structural metric improvements (snapshots of CPU/RAM before and after actions are performed) into an append-only `data/logs.csv` ledger file.

---

## 🛠️ System Prerequisites

### Core Operating Systems
* **Windows 10 / 11** (Optimized for full features including RAM reclamation)
* **Linux / macOS** (Supported with fallback priority adjustments)

### Software Requirements
* **Python 3.10** or higher
* **psutil** library


   
