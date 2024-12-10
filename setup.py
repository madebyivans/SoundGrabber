"""
SoundGrabber - Audio Recording Utility
Copyright (C) 2024 Ivans Andrejevs

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

APP = ['audio_recorder.py']
DATA_FILES = [
    'icon.icns',
    'icon_recording.icns',
    ('resources', [
        'resources/start_recording.wav',
        'resources/stop_recording.wav',
        'resources/version.txt'
    ]),
    ('resources/setup', [
        'resources/setup/welcome.png',
        'resources/setup/blackhole_install.png',
        'resources/setup/audio_midi_setup.png',
        'resources/setup/complete.png'
    ]),
    ('installers', [
        'installers/BlackHole2ch-0.6.0.pkg',
        'installers/SwitchAudioSource'
    ]),
    ('licenses', [
        'licenses/switchaudio-osx-LICENSE',
        'licenses/blackhole-LICENSE'
    ]),
    'LICENSE',
    'ATTRIBUTION.md',
    'setup_wizard.py',
    'utils.py',
]
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True,
        'NSMicrophoneUsageDescription': 'SoundGrabber needs microphone access to record audio.',
        'CFBundleIdentifier': 'com.yourdomain.soundgrabber',
        'CFBundleName': 'SoundGrabber',
        'CFBundleDisplayName': 'SoundGrabber',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSRequiresAquaSystemAppearance': False,
    },
    'iconfile': 'icon.icns',
    'packages': [
        'rumps', 
        'sounddevice', 
        'numpy', 
        'soundfile', 
        'cffi',
        'AppKit',
        'Cocoa',
    ],
    'includes': [
        'objc', 
        'Foundation', 
        '_cffi_backend',
        'subprocess',
        'os',
        'sys',
        'time',
        'logging',
    ],
    'resources': DATA_FILES,
    'frameworks': [
        'CoreAudio', 
        'AVFoundation', 
        'ApplicationServices', 
        'Foundation'
    ],
    'semi_standalone': False,
    'site_packages': True,
}

setup(
    name='SoundGrabber',  # Add name
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
