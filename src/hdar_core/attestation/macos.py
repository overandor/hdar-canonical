import subprocess


def get_macos_hardware_uuid() -> str:
    try:
        out = subprocess.check_output([
            "ioreg", "-d2", "-c", "IOPlatformExpertDevice"
        ]).decode('utf-8')
        for line in out.split("\n"):
            if "IOPlatformUUID" in line:
                return line.split("=")[1].replace('"', '').strip()
    except Exception:
        pass
    return "macos-hwid-undetected"
