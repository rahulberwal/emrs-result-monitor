# Timestamp-Based PDF Monitor

Python service for detecting newly published PDF documents in a publicly accessible document repository.

## Overview

The monitor was developed as the backend component of the **EMRS Result Monitor** project.

The basic idea is simple:

```text
Timestamp
    ↓
<timestamp>.pdf
    ↓
HTTP request
    ↓
PDF validation
    ↓
New document detected
    ↓
Save PDF
    ↓
Send FCM notification
```

## Timestamp-Based Detection

During development, I noticed that documents in the target repository followed a timestamp-based filename pattern:

```text
<Unix timestamp>.pdf
```

Instead of repeatedly searching the visible website for changes, the monitor can construct the expected filename from the current Unix timestamp and check whether that document exists.

This made the monitoring process significantly more predictable and allowed unnecessary requests to be reduced.

## Request Optimization

The first implementation was considerably more request-heavy.

After analyzing the naming pattern, the monitoring logic was redesigned to track the last timestamp that had already been checked.

The monitor then checks only newly arrived timestamps instead of repeatedly scanning the same range.

For the same monitoring window, this reduced the number of requests from roughly **1,000 to around 180** during development.

The monitor was also intentionally used during limited periods when a result publication was reasonably expected rather than being operated continuously against the public repository 24/7.

The objective was to detect newly published documents while avoiding unnecessary traffic.

## Duplicate Protection

Detected filenames are stored locally in a state file.

For example:

```text
1789043441.pdf
1788963129.pdf
1788782832.pdf
```

If the same document is encountered again, it is ignored.

This prevents duplicate processing and duplicate notifications.

## PDF Validation

A response is considered a valid document only when:

* the HTTP response indicates success, and
* the response identifies itself as a PDF through its content type or PDF magic bytes.

The monitor therefore does not treat every successful HTTP response as a result document.

## Firebase Cloud Messaging

When a new PDF is detected, the monitor sends a Firebase Cloud Messaging notification to a configured topic.

The Android application subscribes to this topic when installed.

This allows multiple devices to receive the same result notification without the monitoring server maintaining individual device tokens.

## Configuration

The monitor uses environment variables for deployment-specific configuration.

Example:

```text
MONITOR_BASE_URL
FCM_TOPIC
LOOK_BEHIND
MAX_WORKERS
SCAN_INTERVAL
REQUEST_TIMEOUT
DOWNLOAD_FOLDER
STATE_FILE
```

This keeps deployment-specific settings separate from the source code.

## Running

Install dependencies:

```bash
pip install -r requirements.txt
```

Set the required environment configuration and run:

```bash
python monitor.py
```

For long-running Linux deployments, the service can be managed through a process supervisor such as `systemd`.

## Architecture

```text
Public Document Repository
           │
           ▼
    Python Monitor
           │
     Timestamp Logic
           │
           ▼
      PDF Detection
           │
      ┌────┴────┐
      ▼         ▼
   Archive     FCM
                │
                ▼
        Android Application
```

## Responsible Monitoring

This project interacts only with publicly accessible resources.

It does not attempt to bypass authentication, access controls, or restricted resources.

The monitoring logic was specifically optimized to avoid repeatedly checking the same timestamps and was used only during relevant publication windows.

## Part of a Larger Project

This monitor is the backend component of:

**EMRS Result Monitor**

The complete system combines:

* Python
* Google Cloud Compute Engine
* Firebase Cloud Messaging
* Kotlin
* Jetpack Compose
* Linux/systemd
* HTTP-based document detection

See the root project README for the complete architecture.
