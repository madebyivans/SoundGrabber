from setuptools import setup
import sys
from cx_Freeze import setup, Executable

# Dependencies
build_exe_options = {
    "packages": ["rumps", "PIL", "pyperclip", "plyer", "pystray"],
    "include_files": ["icon.png", "icon.ico"],  # Include both icons
}

# Base for Windows (no console)
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="Timer",
    version="1.0",
    description="Timer App",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "Timer.py",
            base=base,
            icon="icon.ico",  # Windows app icon
            target_name="Timer.exe"
        )
    ]
)