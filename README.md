# Smart Resource Monitoring and Auto-Mitigation System

### Project
**Domain:** Systems Programming & Operating System Utilities  
**Target Platforms:** Cross-Platform (Automated detection for Linux 🐧 and Windows 🪟)

---

## 📌 Project Overview
The **Smart Resource Monitoring and Auto-Mitigation System** is an intelligent background utility designed to shift resource management from manual troubleshooting to automated prevention. 

While standard system utilities (like Task Manager or `top`) are purely passive dashboards that display raw numbers, this system acts as an **autonomous control engine**. It continuously evaluates hardware metrics, applies a rule-based heuristic to isolate background "resource hogs," executes non-destructive optimizations or freezes, and records the measurable performance improvements.

### 🎯 Key Highlights
* **Behavior-Based Logic:** Avoids "dumb" threshold triggers; handles transient CPU spikes gracefully while prioritizing long-term idle RAM leaks.
* **Cross-Platform Compatibility:** Features a unified, platform-aware codebase that dynamically leverages low-level Linux signals or Windows Win32 APIs.
* **Measurable Feedback Loop:** Quantifies and logs system resource deltas (Before vs. After) directly into a structured CSV tracking database.

---

## 🧠 System Architecture & Workflow

The system is engineered as a single, modular continuous execution loop divided into three functional phases:

```text
[ 1. Continuous Monitor ] ──► Computes trailing resource loads (CPU & RAM)
                                      │
                               (Threshold Broken?)
                                      ▼
[ 2. Heuristic Engine ]   ──► Runs Weighted Scoring Algorithm on PIDs
                                      │
                               (Isolates Worst Offender)
                                      ▼
[ 3. Platform Mitigator ] ──► Executes Native Trim, Nice, or Suspend Call
                                      │
                               (Measures Delta)
                                      ▼
                           Logs Performance Delta to CSV
```
---
### 1. The Weighted Scoring Heuristic

To avoid deploying resource-intensive Machine Learning models on a lightweight monitoring tool, the system utilizes a **Rule-Based Weighting Coefficient** to calculate an app's inefficiency profile:

$$\text{Score} = (\text{Process CPU} \times 1.5) + (\text{Process RAM} \times 2.5)$$

* **Why RAM is weighted at 2.5:** Physical memory allocation is "sticky." Background applications (such as idle browser tabs) hoard physical RAM long after a user stops interacting with them.
* **Why CPU is weighted at 1.5:** CPU utilization is transient. Brief spikes are normal during active compilation, gaming, or rendering; a lower weight protects active applications from being falsely penalized.

---

### 2. Tiered Optimization Strategies

Unlike the binary "End Task" approach of standard task managers which causes lost user work, this system features context-aware, non-destructive mitigation tiers:

| Optimization Mode | Behavior on Linux 🐧 | Behavior on Windows 🪟 |
| :--- | :--- | :--- |
| **1. Priority Shift** | Adjusts process scheduling priority to max value (`nice 19`), stepping aside for active user tasks. | Invokes native `SetProcessWorkingSetSize` kernel hooks to flush idle pages out of physical RAM. |
| **2. Suspend State** | Dispatches a low-level `SIGSTOP` signal, freezing the process thread to 0% CPU usage without closing windows. | *Optimized for Unix environments (Skipped safely with warning).* |
| **3. Terminate** | Issues a standard platform-agnostic termination sequence. | Issues a standard platform-agnostic termination sequence. |
---
## 📂 Project Directory Structure
```text
smart-resource-monitor/
│
├── data/
│   └── logs.csv               # Shared Database: Records tracking metrics & deltas
│
├── smart_resource_manager.py  # Comprehensive Unified Source Code (Demo Execution File)
├── requirements.txt           # Project Package Dependencies
└── README.md                  # System Documentation
```
---
## 🚀 Getting Started & Installation
## ⚡ Getting Started & Installation

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Install Dependencies
Clone or download this repository, navigate to the project directory in your terminal, and install the required process-mapping utility libraries:

```bash
pip install -r requirements.txt
```
### 3. Execution (Demo Guidelines)
Because the optimization engine interacts with low-level kernel properties (altering priority states, modifying process handles, or transmitting signals), the script must be run with elevated privileges to execute successfully.

#### On Linux:
```Bash
sudo python3 smart_resource_manager.py
```
#### On Windows:
Open PowerShell or Command Prompt as an Administrator, then run:

```PowerShell
python smart_resource_manager.py
```

### 📊 Performance Tracking Log
Every successful optimization generates accountability metrics appended to data/logs.csv. The log tracks the explicit structural performance changes over time:

```Code snippet
Timestamp,App Name,PID,Action Taken,System CPU Before,System CPU After
2026-05-28 11:24:02,brave,255289,Suspended (SIGSTOP),94.4%,41.2%
2026-05-28 11:30:15,chrome,140220,Lowered Priority (Linux Nice),78.1%,52.5%
```