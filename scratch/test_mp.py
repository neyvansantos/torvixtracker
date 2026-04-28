import sys
import os
import time

def test_mediapipe():
    print(f"Python version: {sys.version}")
    print(f"CWD: {os.getcwd()}")
    
    try:
        import mediapipe as mp
        print(f"MediaPipe version: {mp.__version__}")
    except ImportError as e:
        print(f"CRITICAL: MediaPipe not installed! {e}")
        return
    except Exception as e:
        print(f"CRITICAL: Failed to import MediaPipe: {e}")
        return

    try:
        from eye_drive_tracker.tracking.head_pose import HeadPoseTracker
        print("Initializing HeadPoseTracker...")
        tracker = HeadPoseTracker()
        print(f"Backend detected: {tracker.backend_name}")
        if tracker.mediapipe_error:
            print(f"MediaPipe Error: {tracker.mediapipe_error}")
    except Exception as e:
        print(f"Failed to initialize tracker: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mediapipe()
