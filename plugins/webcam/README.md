# Webcam Driver Plugin

Webcam driver plugin for ModLink Studio. Captures video streams from built-in or USB cameras.

## Features

- Auto-detects available cameras
- RGB video streaming at 30 FPS
- Configurable resolution (default: 640x480)
- Threaded capture for non-blocking operation

## Supported Providers

- `video`: Searches and connects to available video capture devices

## Dependencies

- opencv-python >= 4.11.0
- numpy >= 2.3.3
- modlink-sdk
