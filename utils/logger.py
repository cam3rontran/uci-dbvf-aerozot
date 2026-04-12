# Prints information about what the system is doing
import datetime

def _get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(message):
    print(f"[{_get_time()}][LOG] {message}")

def info(message):
    print(f"[{_get_time()}][INFO] {message}")

def warning(message):
    print(f"[{_get_time()}][WARNING] {message}")

def error(message):
    print(f"[{_get_time()}][ERROR] {message}")
    