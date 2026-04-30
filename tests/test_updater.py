from pathlib import Path

from eye_drive_tracker.updater import update_installer_path


def test_update_installer_path_uses_temp_updates_folder() -> None:
    path = update_installer_path(
        "https://github.com/NeyvanSantos/TorvixTracker/releases/download/v0.2.0/TorvixTracker_Setup.exe",
        "0.2.0",
    )

    assert path.name == "TorvixTracker_Setup_0.2.0.exe"
    assert path.parent.name == "TorvixTrackerUpdates"


def test_update_installer_path_sanitizes_version_and_forces_exe_suffix() -> None:
    path = update_installer_path("https://example.com/download", "v 2/beta")

    assert path.name == "TorvixTracker_Setup_v_2_beta.exe"
    assert Path(path).suffix == ".exe"
