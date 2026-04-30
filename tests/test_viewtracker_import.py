from eye_drive_tracker.profiles import ProfileManager, TrackingConfig, import_viewtracker_ini


def test_import_viewtracker_ini_applies_accela_like_defaults(tmp_path) -> None:
    ini = tmp_path / "MINHA.ini"
    ini.write_text(
        "\n".join(
            (
                "[modules]",
                "filter-dll=Accela",
                "protocol-dll=freetrack 2.0 Enhanced",
                "",
                "[spline-yaw]",
                "points=@Variant(dummy)",
            )
        ),
        encoding="utf-8",
    )
    base = TrackingConfig(language="POR", camera_index=2, invert_yaw=False)

    config = import_viewtracker_ini(ini, base)

    assert config.profile_name == "ViewTracker Smooth (MINHA)"
    assert config.language == "POR"
    assert config.camera_index == 2
    assert config.invert_yaw is False
    assert config.head_view_smoothing == 0.08
    assert config.output_smoothing == 0.12
    assert config.output_micro_jitter == 0.10
    assert config.output_max_step == 18.0
    assert config.head_tracking_exponent == 1.08
    assert config.output_mode == "opentrack_udp"


def test_profile_manager_imports_viewtracker_ini(tmp_path) -> None:
    ini = tmp_path / "profile.ini"
    ini.write_text("[modules]\nfilter-dll=Accela\n", encoding="utf-8")

    config = ProfileManager(tmp_path / "profiles").import_viewtracker_ini(ini)

    assert config.profile_name == "ViewTracker Smooth (profile)"
    assert config.head_yaw_sensitivity_cabin == 1.2


def test_import_viewtracker_ini_reads_qt_variant_accela_values(tmp_path) -> None:
    ini = tmp_path / "profile.ini"
    ini.write_text(
        "\n".join(
            (
                "[modules]",
                "filter-dll=Accela",
                "",
                "[accela-sliders]",
                r"rotation-deadzone=@Variant(\\0\\0\\0\\x7f\\0\\0\\0\\x18::options::slider_value\\0?\\x94z\\xe1G\\xae\\x14{\\0\\0\\0\\0\\0\\0\\0\\0?\\xc9\\x99\\x99\\x99\\x99\\x99\\x9a)",
                r"rotation-sensitivity=@Variant(\\0\\0\\0\\x7f\\0\\0\\0\\x18::options::slider_value\\0?\\xf3\\x33\\x33\\x33\\x33\\x33\\x34?\\xa9\\x99\\x99\\x99\\x99\\x99\\x9a@\\x4\\0\\0\\0\\0\\0\\0)",
            )
        ),
        encoding="utf-8",
    )

    config = import_viewtracker_ini(ini)

    assert config.input_deadzone == 0.36
    assert config.head_yaw_sensitivity_cabin == 1.2
