# AUV Pipe-Following & Defect Detection (Simulation)

A proof-of-concept simulating an autonomous underwater vehicle (AUV) that
autonomously follows a pipeline and flags surface defects. Built in a
Minecraft environment as a visual testbed for the perception-to-control loop.

## What it does

The system combines two independently built components into one loop:

- **Navigation (classical CV, hand-coded):** Uses HSV masking, contour
  detection with minimum-area-rectangle angle estimation, and Hough-line
  alignment to perform visual servoing. The agent continuously corrects its
  heading and walks the pipe on its own — no hardcoded path.
- **Defect detection (YOLO):** A YOLO model trained on a custom-built dataset
  detects "defects" (differently-textured blocks) along the route.

The core idea: make perception and control talk to each other in real time,
which is the same problem real inspection robots solve.

## Tech

Python · OpenCV · YOLO · NumPy · PyAutoGUI

## Files

## Files

- `navigation.py` — main perception + control loop: screen capture, CV processing (HSV mask, contour angle detection, Hough lines), heading correction, and movement control.

## How it works

1. Captures a screen region as the agent's "camera" feed
2. Masks and finds the pipe contour, computes its angle
3. Corrects heading via visual servoing until aligned
4. Walks forward along the pipe while scanning for defects

## Note

This is a simulation / proof-of-concept — the environment is Minecraft and
"defects" are re-textured blocks. The focus is the CV navigation and
detection pipeline, not a physical robotics deployment.
