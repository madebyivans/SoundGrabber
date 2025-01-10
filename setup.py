"""
SoundGrabber - Audio Recording Utility
Copyright (C) 2025 Ivans Andrejevs

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from setuptools import setup
import subprocess
import os
import time

# Find all dylib files in the libs directory
dylibs = []
libs_dir = 'libs'
if os.path.exists(libs_dir):
    for file in os.listdir(libs_dir):
        if file.endswith('.dylib'):
            dylibs.append(os.path.join(libs_dir, file))

APP = [{
    'script': 'audio_recorder.py',
    'plist': {
        'CFBundleName': 'SoundGrabber',
        'CFBundleDisplayName': 'SoundGrabber',
        'CFBundleIdentifier': 'com.ivans.soundgrabber',
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHumanReadableCopyright': 'Copyright © 2025 Ivans Andrejevs',
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'This app needs access to the microphone to record audio.',
        'LSMinimumSystemVersion': '10.15',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'NSRequiresAquaSystemAppearance': False,
        'LSUIElement': True,
    }
}]
DATA_FILES = [
    ('resources', [
        'resources/icon.icns',
        'resources/icon_recording.icns',
        'resources/SwitchAudioSource',
        'resources/start_recording.wav',
        'resources/stop_recording.wav',
    ]),
    ('resources/setup', [
        'resources/setup/background.png',
        'resources/setup/welcome.png',
        'resources/setup/blackhole_install.png',
        'resources/setup/audio_midi_setup.png',
        'resources/setup/complete.png',
        'resources/setup/guide.mp4'
    ]),
    ('installers', [
        'installers/BlackHole2ch-0.6.0.pkg'
    ]),
    ('_sounddevice_data/portaudio-binaries', [
        '/opt/homebrew/Cellar/portaudio/19.7.0/lib/libportaudio.2.dylib'
    ]),
    ('libs', dylibs)
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'resources/icon.icns',
    'semi_standalone': False,
    'site_packages': True,
    'strip': True,
    'optimize': 2,
    'packages': [
        'PIL',
        'numpy',
        'sounddevice',
        'soundfile',
        'threading',
        'logging',
        'rumps',
        'AppKit',
        'AVFoundation',
        'AVKit',
        'Quartz',
        'objc',
        'tkinter'
    ],
    'includes': [
        'ctypes',
        'ctypes.util',
        'logging.handlers'
    ],
    'frameworks': [
        '/Library/Frameworks/Python.framework/Versions/3.12/Python'
    ],
    'excludes': [
        'PyInstaller',
        'setuptools',
        'pip',
        'wheel',
        'pygments',
        'cffi',
        'test',
        'distutils'
    ],
    'plist': {
        'CFBundleName': 'SoundGrabber',
        'CFBundleDisplayName': 'SoundGrabber',
        'CFBundleIdentifier': 'com.ivans.soundgrabber',
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHumanReadableCopyright': 'Copyright © 2025 Ivans Andrejevs',
        'CFBundleDocumentTypes': [],
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'This app needs access to the microphone to record audio.',
        'LSMinimumSystemVersion': '10.15',
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'NSRequiresAquaSystemAppearance': False,
        'LSUIElement': True,
        'PyRuntimeLocations': [
            '@executable_path/../Frameworks/Python.framework/Versions/3.12/Python',
            '/Library/Frameworks/Python.framework/Versions/3.12/Python'
        ],
        'LSEnvironment': {
            'DYLD_LIBRARY_PATH': '@executable_path/../Resources/_sounddevice_data/portaudio-binaries'
        }
    }
}

# Function to ensure file permissions are correct
def fix_permissions():
    import os
    import stat
    
    # Files that need execution permission
    executables = ['resources/SwitchAudioSource']
    
    # Files that need read permission
    readable = [
        'resources/setup/guide.mp4',
        'resources/setup/background.png',
        'resources/setup/welcome.png',
        'resources/setup/blackhole_install.png',
        'resources/setup/audio_midi_setup.png',
        'resources/setup/complete.png',
        'resources/icon.icns',
        'resources/icon_recording.icns',
        'resources/start_recording.wav',
        'resources/stop_recording.wav',
    ]
    
    # Set executable permissions
    for file in executables:
        if os.path.exists(file):
            os.chmod(file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                          stat.S_IRGRP | stat.S_IXGRP |
                          stat.S_IROTH | stat.S_IXOTH)
    
    # Set readable permissions
    for file in readable:
        if os.path.exists(file):
            os.chmod(file, stat.S_IRUSR | stat.S_IWUSR | 
                          stat.S_IRGRP | stat.S_IROTH)

# Add to end of setup.py
if __name__ == "__main__":
    # Fix permissions before building
    fix_permissions()
    
    setup(
        name="SoundGrabber",
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )
