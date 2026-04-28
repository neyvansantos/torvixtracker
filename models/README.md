# Models

Optional MediaPipe Tasks models can be placed here.

For Python installations where `mediapipe.solutions.face_mesh` is not available, put the Face Landmarker task model at:

```text
models/face_landmarker.task
```

Alternatively set:

```powershell
$env:TOVIX_FACE_LANDMARKER_MODEL = "C:\path\to\face_landmarker.task"
```
