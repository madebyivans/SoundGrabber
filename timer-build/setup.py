from setuptools import setup

APP = ['Timer.py']
DATA_FILES = ['icon.png', 'icon.icns']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['rumps', 'PIL', 'pyperclip', 'plyer'],
    'plist': {
        'LSUIElement': True,  # Makes it a menu bar app
        'CFBundleName': 'Timer',
        'CFBundleDisplayName': 'Timer',
        'CFBundleIdentifier': 'com.yourdomain.timer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    },
    'iconfile': 'icon.icns'
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)