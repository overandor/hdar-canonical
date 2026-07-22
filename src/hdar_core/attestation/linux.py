import os


def get_linux_tpm_description() -> str:
    path = "/sys/class/tpm/tpm0/device/description"
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return "tpm-inactive"
