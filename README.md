# Torvix Tracker

Windows webcam head/eye tracking MVP for ETS2/ATS experimentation.

This MVP is intentionally neutral: it does not ship ETS2/ATS presets or fixed tuning profiles. All runtime shaping values start from neutral defaults and can be changed manually in the UI, then saved as JSON profiles.

## Current MVP

- Webcam preview
- Face/head/eye landmark detection with MediaPipe Face Mesh when installed
- OpenCV Haar fallback if MediaPipe is unavailable
- Real-time yaw, pitch, and roll display
- Start Tracking, Stop Tracking, and Recenter buttons
- Recenter hotkey
- Manual Head Tracking, Gaze Tracking, Extended View, Calibration, and Output panels
- Manual sliders for deadzone, responsiveness, smoothing, cabin/walk sensitivity, exponent, inflection, start/end points, angle scale, gaze strength, and Extended View shaping
- Output stabilization controls for smoothing, micro-jitter threshold, and max step per frame
- Calibration buttons for center, left, right, up, and down
- Top-right language selector with ENG, POR, and ESP
- Save/load custom JSON profiles
- FreeTrack shared-memory output
- TrackIR-compatible shared-memory output mode
- Mouse Look fallback output
- vJoy output placeholder

## Processing Pipeline

The pose pipeline is split into explicit functions:

- `applyDeadzone()`
- `normalizeInput()`
- `applyStartEndPoint()`
- `applyExponentCurve()`
- `applyInflectionCurve()`
- `applyResponsiveness()`
- `applyAxisMultiplier()`
- `applyExtendedView()`
- `combineHeadAndGaze()`
- `sendOutputToGame()`

## ETS2/ATS Output Notes

`FreeTrack` and `TrackIR compatible` now create and update Windows shared-memory mappings used by FreeTrack-style head tracking clients: `FT_SharedMem` and `FreeTrackSharedMem`.

This is not the official NaturalPoint TrackIR driver and does not try to unlock Tobii features in ETS2/ATS. Some games read this memory directly; others expect an NPClient/TrackIR bridge DLL to discover the tracker. If ETS2/ATS does not detect the app in `TrackIR compatible` mode, the next step is adding a legitimate NPClient-compatible bridge DLL or using vJoy/Mouse Look fallback.

## Install

Use Python 3.10+ on Windows. Python 3.10-3.12 is recommended for the classic MediaPipe Face Mesh API. Python 3.13 may install the newer MediaPipe Tasks package, which needs a `face_landmarker.task` model file for landmark tracking.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

If MediaPipe cannot be installed on your Python version, or if a Tasks model is not available, the app still opens with the OpenCV fallback, but head pose quality is much lower.

For MediaPipe Tasks, place `face_landmarker.task` in `models/face_landmarker.task` or set `TORVIX_FACE_LANDMARKER_MODEL` to the model path.
This workspace includes the official MediaPipe Face Landmarker task model at `models/face_landmarker.task`.

## Project Layout

```text
camera/    Webcam capture
tracking/  Face/head/eye detection and raw pose estimation
filters/   Deadzone, smoothing, responsiveness, scaling, and Extended View curve
output/    FreeTrack/TrackIR-compatible shared memory, Mouse Look fallback, vJoy placeholder
profiles/  JSON profile save/load
ui/        Windows desktop UI
```
