# Smart Resource Monitoring and Auto-Mitigation System

An intelligent, behavior-aware Python system designed to continuously monitor system performance, detect inefficient process behavior, and automatically mitigate resource hogs to optimize system health.

---

## 🎯 The Core Idea

Most resource monitors simply tell you when your system is lagging. This system **understands why** it's lagging by tracking application usage behavior over time. It identifies heavy applications that are running in the background completely unused and takes automated or user-approved actions to restore performance.

## ✨ Key Features

*   **Real-Time System Monitoring:** Continuous telemetry tracking of CPU (with RAM and Disk scaling in development).
*   **Behavior-Based Scoring:** Decisions aren't based on sudden spikes; they are based on an application's resource consumption vs. idle duration.
*   **Automated Optimization:** Dynamically kills processes or lowers their system priority.
*   **Dual Operating Modes:** Swap seamlessly between hands-off **Auto Mode** and interactive **User Suggestion Mode**.
*   **Measurable Impact Logging:** Tracks exact system load immediately before and after mitigation to quantify performance wins.

---

## WORK IN PROGRESS 
