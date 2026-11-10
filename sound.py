import os
import winsound
import threading

# Use high-fidelity, gentle Windows system sounds instead of motherboard buzzer beeps
WINDOWS_MEDIA = r"C:\Windows\Media"

SOUND_MAP = {
    "click": os.path.join(WINDOWS_MEDIA, "notify.wav"),
    "wave": os.path.join(WINDOWS_MEDIA, "ding.wav"),
    "drop": os.path.join(WINDOWS_MEDIA, "chimes.wav"),
    "send": os.path.join(WINDOWS_MEDIA, "Windows Notify System Generic.wav"),
}

class SoundPlayer:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def _play_file_or_alias(self, file_path: str, fallback_alias: str = "SystemAsterisk"):
        if not self.enabled:
            return
        def _target():
            try:
                if os.path.exists(file_path):
                    winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.PlaySound(fallback_alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass
        threading.Thread(target=_target, daemon=True).start()

    def play_click(self):
        """Soft, subtle tick sound on button click."""
        self._play_file_or_alias(SOUND_MAP["click"], "SystemDefault")

    def play_wave(self):
        """Gentle positive chime on voice / mascot greeting."""
        self._play_file_or_alias(SOUND_MAP["wave"], "SystemAsterisk")

    def play_drop(self):
        """Soft landing chime on drag release."""
        self._play_file_or_alias(SOUND_MAP["drop"], "SystemNotification")

    def play_send(self):
        """Crisp message sent chime."""
        self._play_file_or_alias(SOUND_MAP["send"], "SystemAsterisk")
