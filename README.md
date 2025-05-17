# Trackers in OpenCV

**Overview**  
Tracker_opencv is a PyQt5-based tool for comparing four OpenCV trackers (CSRT, KCF, Boosting, MIL) on video sequences. The GUI allows you to load a video, draw a bounding box (ROI) around an object, and run all four trackers simultaneously. Each tracker overlays a color-coded bounding box, providing a side-by-side visualization to evaluate their performance under various conditions.

---

## Installation

1. Ensure Python 3.7 or higher is installed.
2. Install the required packages:

```bash
pip install -r requirements.txt
```

---

## Usage

### Download Videos
Use `download_videos.py` to fetch sample videos from Google Drive:

```bash
python download_videos.py
```

This will download predefined video files for testing.

### Run Tracker Comparison GUI
Launch the PyQt application:

```bash
python tracker_opencv.new.py
```

In the GUI:
- Click **“Load Video”** to select a video file.
- Draw a bounding box around the object you want to track.
- The four trackers (CSRT, KCF, Boosting, MIL) will run in real time, displaying their bounding boxes with distinct colors.

---

## Limitations & Interpretation

- **Contrast Dependency:** All four trackers perform best with strong object/background contrast. They are reliable when the object is clearly distinguishable.
- **KCF Behavior:** KCF tends to drift or lose the target faster under challenging conditions like fast motion or occlusion.
- **MIL Issues:** MIL may produce false positives or switch between similar objects, leading to unreliable bounding boxes.
- **Boosting and CSRT Stability:** These trackers generally stay stable longer but can still fail if the object is occluded or changes appearance significantly without an external detection step.
- **General Insight:** Simple tracking has inherent limits. For production systems, combining tracking with object detection or re-initialization strategies is recommended.

---
