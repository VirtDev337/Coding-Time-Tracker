---
name: timetracker
description: >-
  Interact with TimeTracker v2 to query developer time metrics, check active projects,
  inspect coding/AI collaboration hours, and generate customized PDF reports.
---

# TimeTracker v2 Skill for Antigravity

This skill allows Antigravity to interact directly with **TimeTracker v2**, an ambient developer time-tracking system designed by VirtDev and implemented in collaboration with Antigravity.

---

## When to Use This Skill

Activate this skill when the user asks:
* "How much time have I coded today?" or "Show my time tracking status."
* "What projects have I worked on this week?"
* "Generate a PDF report for [project] / this month."
* "How much time did we spend pair programming or in AI collaboration?"
* "Is the TimeTracker daemon running or set to autostart?"

---

## Command Reference

Antigravity can run these commands via `run_command`:

### 1. Check Live Tracking Status & Today's Summary
```bash
timetracker status
```
Returns:
* Active window & categorized application (Coding, AI Collaboration, Research)
* Today's Total Time, Coding Hours, AI Collaboration Hours, and Research Hours.

### 2. View All Tracked Projects
```bash
timetracker projects
```
Returns a tabular view of all projects with:
* Coding time
* AI collaboration (Antigravity) time
* Research time
* Total time & Last active timestamp

### 3. Generate a Customized PDF Report
```bash
# All projects for this month:
timetracker report --month -o monthly_report.pdf

# Specific project with custom hourly rate and theme:
timetracker report -p <ProjectName> --rate 85.0 --theme "#1E40AF" --detailed -o report.pdf

# Today only:
timetracker report --today -o today_report.pdf
```

### 4. Manage Autostart at Login
```bash
timetracker autostart status
timetracker autostart enable
timetracker autostart disable
```
