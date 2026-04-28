from eye_drive_tracker.ui.i18n import translate


def test_about_menu_translations() -> None:
    assert translate("ENG", "About") == "About"
    assert translate("POR", "About") == "Sobre"
    assert translate("ESP", "About") == "Acerca de"


def test_game_functions_menu_translations() -> None:
    assert translate("ENG", "Game Functions") == "Game Functions"
    assert translate("POR", "Game Functions") == "Funções no Jogo"
    assert translate("ESP", "Game Functions") == "Funciones en el Juego"
    assert "cabeça" in translate("POR", "game_help_tracking_context")


def test_track_section_translation() -> None:
    assert translate("ENG", "Track") == "Track"
    assert translate("POR", "Track") == "Rastrear"
    assert translate("ESP", "Track") == "Rastrear"


def test_profile_webcam_section_translation() -> None:
    assert translate("ENG", "User Profile/Webcam") == "User Profile/Webcam"
    assert translate("POR", "User Profile/Webcam") == "Perfil de Usuário/Webcam"
    assert translate("ESP", "User Profile/Webcam") == "Perfil de Usuario/Webcam"
