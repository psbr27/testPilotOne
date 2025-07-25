import time
from datetime import datetime, timezone

# You may want to load the version from a central location or pass it as an argument
APP_VERSION = "1.0.0"  # <-- Change as needed or automate versioning

if __name__ == "__main__":
    epoch = int(time.time())
    date_str = datetime.fromtimestamp(epoch, timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    with open("build_info.py", "w", encoding="utf-8") as f:
        f.write(f'APP_VERSION = "{APP_VERSION}"\n')
        f.write(f"BUILD_EPOCH = {epoch}\n")
        f.write(f'BUILD_DATE = "{date_str}"\n')
    print(
        f"build_info.py updated: VERSION={APP_VERSION}, EPOCH={epoch}, DATE={date_str}"
    )
