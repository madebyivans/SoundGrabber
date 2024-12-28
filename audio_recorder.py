"""
SoundGrabber - Audio Recording Utility
Version 1.0.0
Copyright (C) 2024 Ivans Andrejevs

Website: www.madebyivans.info
Repository: https://github.com/madebyivans/SoundGrabber
Contact: a.ivans@icloud.com

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

import sys
import os
import ctypes.util

# Initialize PortAudio path
lib_path = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])),
    '..', 'Resources', '_sounddevice_data', 'portaudio-binaries', 'libportaudio.2.dylib'
)

# Override ctypes.util.find_library for PortAudio
original_find_library = ctypes.util.find_library
def custom_find_library(name):
    if name == 'portaudio':
        return lib_path
    return original_find_library(name)
ctypes.util.find_library = custom_find_library

import sounddevice as sd
import numpy as np
import rumps
import logging
import subprocess
import time
import soundfile as sf
import AVFoundation
import objc
import traceback  # Add this import
import urllib.request
import webbrowser
import AppKit
import ssl
from setup_wizard import SetupWizard
from utils import resource_path  # Import from utils instead of defining it here
import atexit
import tkinter as tk
from tkinter import ttk
import logging.handlers
import errno
import socket  # Add this with the other imports
import json
import tempfile
from datetime import datetime

ICON_PATH = "icon.icns"
ICON_RECORDING_PATH = "icon_recording.icns"

def request_microphone_access():
    AVAudioSession = objc.lookUpClass('AVAudioSession')
    audio_session = AVAudioSession.sharedInstance()
    if audio_session.respondsToSelector_('requestRecordPermission:'):
        audio_session.requestRecordPermission_(lambda allowed: logging.info(f"Microphone access {'granted' if allowed else 'denied'}"))
    else:
        logging.error("This device doesn't support microphone permission requests")

class AdvancedAudioRecorderApp(rumps.App):
    def __init__(self):
        try:
            # Initialize basic attributes first
            self.recording = False
            self.version = "1.0.0"
            self.audio_data = []
            self.fs = 48000
            self.channels = 2
            self.stream = None
            
            # Set up logging before any other operations
            self.setup_logging()
            
            logging.info("=== SoundGrabber Starting ===")
            logging.info(f"Version: {self.version}")
            
            # Initialize version
            self.version = "1.0.0"  # Current version
            self.update_url = "https://raw.githubusercontent.com/madebyivans/SoundGrabber/main/version.txt"
            self.download_url = "https://github.com/madebyivans/SoundGrabber/releases"
            
            logging.info("=== Starting Version Check ===")
            logging.info(f"Current app version: {self.version}")
            
            # Try to check online version first
            try:
                # Bypass SSL verification
                import ssl
                ssl._create_default_https_context = ssl._create_unverified_context
                
                api_url = "https://api.github.com/repos/madebyivans/SoundGrabber/contents/version.txt"
                logging.info(f"Checking online version at: {api_url}")
                
                request = urllib.request.Request(
                    api_url,
                    headers={
                        'User-Agent': 'SoundGrabber',
                        'Accept': 'application/vnd.github.v3.raw'
                    }
                )
                
                response = urllib.request.urlopen(request, timeout=5)
                latest_version = response.read().decode('utf-8').strip()
                logging.info(f"Server version: {latest_version}")
                
                # Store the latest version from server
                self.store_version_requirement(latest_version)
                
            except Exception as e:
                logging.warning(f"Could not check online version: {e}")
                
            # Now check stored version requirement
            requirement_exists = self.check_stored_version_requirement()
            logging.info(f"Version requirement check result: {requirement_exists}")
            
            if requirement_exists:
                logging.critical("Version requirement not met. Exiting application.")
                self.show_update_required_message()
                AppKit.NSApp.terminate_(None)
                return

            logging.info("=== Version Check Complete ===")
            
            # Get the actual app path using sys.executable
            app_dir = os.path.abspath(sys.executable)
            logging.info(f"Running from: {app_dir}")

            # Only show installation prompt if we're not already in Applications
            if '/Applications/SoundGrabber.app' not in app_dir:
                logging.info("Not running from Applications, initiating installation...")
                
                # Check if there's an existing installation
                existing_app = '/Applications/SoundGrabber.app'
                is_update = os.path.exists(existing_app)
                
                # Temporarily change activation policy and bring app to front
                app = AppKit.NSApplication.sharedApplication()
                logging.info("Setting activation policy...")
                app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
                app.activateIgnoringOtherApps_(True)  # Force activation
                
                # Create alert with appropriate messaging
                logging.info("Creating installation alert...")
                alert = AppKit.NSAlert.alloc().init()
                if is_update:
                    alert.setMessageText_("Update SoundGrabber")
                    alert.setInformativeText_("Would you like to update the existing SoundGrabber installation?")
                    alert.addButtonWithTitle_("Update")
                else:
                    alert.setMessageText_("Install SoundGrabber")
                    alert.setInformativeText_("Would you like to install SoundGrabber to your Applications folder?")
                    alert.addButtonWithTitle_("Install")
                alert.addButtonWithTitle_("Cancel")
                
                # Force the alert window to front and center it
                alert_window = alert.window()
                screen = AppKit.NSScreen.mainScreen()
                screen_frame = screen.visibleFrame()
                window_frame = alert_window.frame()
                
                # Calculate center position
                center_x = screen_frame.origin.x + (screen_frame.size.width - window_frame.size.width) / 2
                center_y = screen_frame.origin.y + (screen_frame.size.height - window_frame.size.height) / 2
                
                # Set window position and bring to front
                alert_window.setFrame_display_(
                    AppKit.NSMakeRect(center_x, center_y, window_frame.size.width, window_frame.size.height),
                    True
                )
                alert_window.makeKeyAndOrderFront_(None)
                alert_window.orderFrontRegardless()
                
                logging.info("Showing alert...")
                response = alert.runModal()
                logging.info(f"Alert response: {response}")
                
                if response == AppKit.NSAlertSecondButtonReturn:  # "Cancel" clicked
                    logging.info("User cancelled installation, exiting...")
                    sys.exit(0)  # Exit cleanly
                
                # Return to accessory app status
                app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
                
                if response == AppKit.NSAlertFirstButtonReturn:  # "Install/Update" clicked
                    try:
                        # If updating, quit any running instances first
                        if is_update:
                            logging.info("Attempting to close existing SoundGrabber instance...")
                            try:
                                subprocess.run(['pkill', '-f', 'SoundGrabber'], check=False)
                                # Give it a moment to close
                                time.sleep(1)
                            except Exception as e:
                                logging.warning(f"Error while trying to close existing instance: {e}")
                        
                        # Get source and destination paths
                        current_file = os.path.abspath(sys.executable)
                        logging.info(f"Current executable: {current_file}")
                        
                        # Look for .app in parent directories
                        check_path = current_file
                        for _ in range(5):  # Check up to 5 levels up
                            check_path = os.path.dirname(check_path)
                            logging.info(f"Checking path: {check_path}")
                            if check_path.endswith('.app'):
                                source_path = check_path
                                logging.info(f"Found .app at: {source_path}")
                                break
                        else:
                            raise Exception("Could not locate SoundGrabber.app")
                        
                        dest_path = '/Applications/SoundGrabber.app'
                        
                        logging.info(f"Found source path: {source_path}")
                        logging.info(f"Destination path: {dest_path}")
                        
                        # Create an AppleScript that uses the security system dialog
                        logging.info("Creating installation script...")
                        action = "update" if is_update else "install"
                        script = f'''
                            tell application "Finder"
                                try
                                    do shell script "rm -rf '{dest_path}'" with prompt "SoundGrabber needs permission to {action}" with administrator privileges
                                    do shell script "cp -R '{source_path}' '{dest_path}'" with administrator privileges
                                    return "success"
                                on error errMsg
                                    return "error: " & errMsg
                                end try
                            end tell
                        '''
                        
                        # Run the AppleScript
                        logging.info(f"Running {action} script...")
                        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
                        logging.info(f"Installation script output: {result.stdout}")
                        
                        if result.returncode != 0:
                            logging.error(f"Installation script error: {result.stderr}")
                            raise Exception(f"{action.capitalize()} failed: {result.stderr}")
                        
                        # Verify installation
                        logging.info("Verifying installation...")
                        if os.path.exists(dest_path):
                            logging.info(f"{action.capitalize()} successful")
                            
                            # Launch the installed version
                            logging.info("Launching installed version...")
                            subprocess.Popen(['open', dest_path])
                            
                            # Quit current instance
                            logging.info("Quitting current instance...")
                            sys.exit(0)
                            return
                        else:
                            logging.error(f"{action.capitalize()} failed - destination not found")
                            raise Exception(f"{action.capitalize()} failed")
                            
                    except Exception as e:
                        logging.error(f"Installation error: {e}")
                        logging.error(traceback.format_exc())
                        
                        # Show error to user
                        error_alert = AppKit.NSAlert.alloc().init()
                        error_alert.setMessageText_("Installation Failed")
                        error_alert.setInformativeText_(f"Could not install SoundGrabber: {str(e)}")
                        error_alert.runModal()
                        
                        # Return to accessory app status
                        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
                else:
                    logging.info("User cancelled installation")
            
            # Continue with normal initialization
            atexit.register(self.cleanup_on_exit)
            
            self.icon_path = resource_path("resources/icon.icns")
            self.recording_icon_path = resource_path("resources/icon_recording.icns")
            self.start_sound_path = resource_path("resources/start_recording.wav")
            self.stop_sound_path = resource_path("resources/stop_recording.wav")
            
            # Keep only these essential activation settings
            app = AppKit.NSApplication.sharedApplication()
            app.activateIgnoringOtherApps_(False)
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
            
            # Request microphone access before setting up audio
            AVAudioSession = objc.lookUpClass('AVAudioSession')
            audio_session = AVAudioSession.sharedInstance()
            if audio_session.respondsToSelector_('requestRecordPermission:'):
                permission_granted = False
                def permission_callback(allowed):
                    nonlocal permission_granted
                    permission_granted = allowed
                    logging.info(f"Microphone access {'granted' if allowed else 'denied'}")
                
                audio_session.requestRecordPermission_(permission_callback)
                # Small delay to allow the permission prompt to show
                time.sleep(0.5)
                
                if not permission_granted:
                    logging.warning("Microphone permission not granted")
            
            super().__init__("SoundGrabber", icon=self.icon_path, quit_button=None)
            self.setup_logging()
            
            # Initialize switch_audio_source_path FIRST
            self.switch_audio_source_path = self.find_switch_audio_source()
            
            # Check if setup is needed
            setup_needed = self.needs_setup()
            if setup_needed:
                logging.info("First-time setup needed...")
                self.run_setup_wizard()
            else:
                logging.info("All requirements met, starting main app...")
                # Continue with normal app initialization
                self.settings = self.load_settings()
                self.recording = False
                self.audio_data = []
                self.fs = 48000
                self.channels = 2
                self.stream = None
                self.previous_output_device = None
                self.last_recorded_file = None
                self.setup_menu()
                request_microphone_access()
                self.previous_input_device = None
                rumps.Timer(self.check_recording_state, 5).start()
            
            # Update these URLs
            self.version = "1.0.0"  # Current version
            self.update_url = "https://raw.githubusercontent.com/madebyivans/SoundGrabber/main/version.txt"
            self.download_url = "https://github.com/madebyivans/SoundGrabber/releases"  # Updated to GitHub releases

        except Exception as e:
            logging.error(f"Error during setup: {e}")
            logging.error(traceback.format_exc())
            sys.exit(1)

    def setup_logging(self):
        if hasattr(self, '_logging_setup'):
            return
        
        try:
            # Get the user's home directory and create a hidden app directory
            home = os.path.expanduser('~')
            app_dir = os.path.join(home, '.soundgrabber')
            os.makedirs(app_dir, exist_ok=True)
            
            # Set up the log file path
            log_file = os.path.join(app_dir, 'soundgrabber.log')
            
            # Create a detailed formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            
            # Set up file handler with rotation
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3
            )
            file_handler.setFormatter(formatter)
            
            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)  # Changed to INFO level
            
            # Remove any existing handlers
            root_logger.handlers = []
            
            # Add our handler
            root_logger.addHandler(file_handler)
            
            self._logging_setup = True
            
        except Exception as e:
            print(f"Failed to setup logging: {str(e)}")
            logging.basicConfig(
                level=logging.INFO,  # Changed to INFO level
                format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )

    def handle_error(self, error, context="", show_to_user=True):
        """
        Centralized error handling method
        
        Args:
            error: The exception object
            context: String describing where/when the error occurred
            show_to_user: Boolean indicating if error should be shown to user
        """
        try:
            # Log the full error with context
            logging.error(f"Error in {context}: {str(error)}")
            logging.error(traceback.format_exc())
            
            if show_to_user:
                # Temporarily change activation policy to make alert visible
                app = AppKit.NSApplication.sharedApplication()
                previous_policy = app.activationPolicy()
                app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
                
                # Create and configure alert
                alert = AppKit.NSAlert.alloc().init()
                alert.setMessageText_("SoundGrabber Error")
                
                # Create a more user-friendly error message
                user_message = str(error)
                if isinstance(error, OSError):
                    if error.errno == errno.ENOSPC:
                        user_message = "Not enough disk space available."
                    elif error.errno == errno.EACCES:
                        user_message = "Permission denied. Please check your system settings."
                
                alert.setInformativeText_(f"{context}\n\n{user_message}")
                alert.addButtonWithTitle_("OK")
                
                # Add "Show Log" button for technical users
                alert.addButtonWithTitle_("Show Log")
                
                # Show the alert
                response = alert.runModal()
                
                # Handle "Show Log" button
                if response == AppKit.NSAlertSecondButtonReturn:
                    log_dir = os.path.dirname(logging.getLoggerClass().root.handlers[0].baseFilename)
                    subprocess.run(['open', log_dir])
                
                # Restore previous activation policy
                app.setActivationPolicy_(previous_policy)
                
        except Exception as e:
            # If error handling fails, at least try to log it
            logging.critical(f"Error handler failed: {e}")
            logging.critical(traceback.format_exc())

    def load_settings(self):
        settings_path = '/Users/ivans/Desktop/app/audio_recorder_settings.txt'
        settings = {
            'output_folder': os.path.expanduser('~/Desktop'),
            'recording_name': 'recording'
        }
        try:
            with open(settings_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key, value = parts
                            settings[key.strip()] = value.strip()
        except FileNotFoundError:
            logging.warning(f"Settings file not found at {settings_path}. Using default settings.")
            self.save_settings(settings)
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            logging.error(traceback.format_exc())
        return settings

    def save_settings(self, settings=None):
        if settings is None:
            settings = self.settings
        settings_path = '/Users/ivans/Desktop/app/audio_recorder_settings.txt'
        with open(settings_path, 'w') as f:
            for key, value in settings.items():
                f.write(f"{key}={value}\n")

    def setup_menu(self):
        # Create Settings submenu
        settings_submenu = rumps.MenuItem("Edit Settings", callback=self.open_settings_file)  # Main item gets a callback
        settings_submenu.add(rumps.MenuItem("Choose Output Folder", callback=self.edit_settings))
        settings_submenu.add(rumps.MenuItem("Set Recording Name", callback=self.edit_recording_name))
        
        self.menu = [
            rumps.MenuItem("Start Recording", callback=self.toggle_recording),
            rumps.MenuItem("Show Last Recording", callback=self.show_last_recording_in_finder),
            None,  # Separator
            settings_submenu,  # Submenu with its own callback
            rumps.MenuItem("Audio MIDI Setup", callback=self.open_audio_midi_setup),
            None,  # Separator
            rumps.MenuItem("Check for Updates", callback=self.check_for_updates),
            None,  # Separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

    def toggle_recording(self, _):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        try:
            logging.info("=== Starting Recording Process ===")
            # Quick settings reload and output folder validation
            try:
                self.settings = self.load_settings()
                output_folder = self.settings['output_folder']
                logging.info(f"Output folder: {output_folder}")
                
                if not os.path.exists(output_folder):
                    logging.warning(f"Output folder not found: {output_folder}")
                    # Temporarily change activation policy to make alert visible
                    app = AppKit.NSApplication.sharedApplication()
                    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
                    
                    # Create and configure alert
                    alert = AppKit.NSAlert.alloc().init()
                    alert.setMessageText_("Output Folder Not Found")
                    alert.setInformativeText_(f"The folder '{output_folder}' doesn't exist. Would you like to create it or edit settings?")
                    alert.addButtonWithTitle_("Create Folder")
                    alert.addButtonWithTitle_("Edit Settings")
                    alert.addButtonWithTitle_("Cancel")
                    
                    # Make sure the alert window comes to front
                    AppKit.NSApp.activateIgnoringOtherApps_(True)
                    
                    response = alert.runModal()
                    
                    # Return to accessory app status
                    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
                    
                    if response == AppKit.NSAlertFirstButtonReturn:  # "Create Folder"
                        try:
                            os.makedirs(output_folder, exist_ok=True)
                            logging.info(f"Created output folder: {output_folder}")
                        except Exception as e:
                            logging.error(f"Failed to create output folder: {e}")
                            return
                    elif response == AppKit.NSAlertSecondButtonReturn:  # "Edit Settings"
                        self.edit_settings(None)
                        return
                    else:  # "Cancel"
                        logging.info("Recording cancelled - no output folder")
                        return
                
            except Exception as e:
                logging.warning(f"Could not reload settings or validate output folder: {e}")
                return
                
            # Store current devices BEFORE any changes
            self.previous_input_device = self.get_current_input_device()
            self.previous_output_device = self.get_current_output_device()
            logging.info(f"Initial input device: {self.previous_input_device}")
            logging.info(f"Initial output device: {self.previous_output_device}")
            
            # Clear audio data before starting new recording
            self.audio_data = []
            self.channels = 2
            
            logging.info("Setting up audio devices...")
            # Set BlackHole 2ch input gain to -1 dB before initializing stream
            self.set_blackhole_gain(-1)
            
            # Switch devices first
            self.switch_devices("BlackHole 2ch", "SoundGrabber")
            
            logging.info("Initializing audio stream...")
            self.stream = sd.InputStream(samplerate=self.fs, channels=self.channels, 
                                       dtype='int32', device='BlackHole 2ch',
                                       callback=self.audio_callback)
            
            # Start stream and verify it's active
            self.stream.start()
            if not self.stream.active:
                raise RuntimeError("Stream failed to start")
            
            # Verify stream is receiving data
            self.last_callback_time = 0
            test_start = time.time()
            while time.time() - test_start < 0.1:  # 100ms timeout
                if self.last_callback_time > test_start:
                    break
            else:
                logging.warning("Stream may not be receiving data")
            
            # Now that stream is confirmed ready, play start sound
            logging.info("Playing start sound...")
            self.play_sound('start_recording.wav')
            time.sleep(0.135)  # Exact duration of start_recording.wav
            
            # Start recording immediately after sound
            self.recording = True
            self.recording_start_time = time.time()
            logging.info("Recording started successfully")
            
            self.menu["Start Recording"].title = "Stop Recording"
            self.icon = self.recording_icon_path

        except Exception as e:
            logging.error(f"Error starting recording: {str(e)}")
            logging.error(traceback.format_exc())

    def stop_recording(self):
        try:
            logging.info("=== Stopping Recording Process ===")
            self.recording = False
            
            if self.stream:
                logging.info("Closing audio stream...")
                self.stream.stop()
                self.stream.close()
            
            if self.audio_data:
                logging.info("Saving recorded audio...")
                self.save_audio_file()
            
            # Clear audio data after saving
            self.audio_data = []
            
            # Restore previous devices
            if self.previous_input_device:
                logging.info(f"Restoring input device to: {self.previous_input_device}")
                self.switch_input_device(self.previous_input_device)
            
            if self.previous_output_device:
                logging.info(f"Restoring output device to: {self.previous_output_device}")
                self.switch_to_device(self.previous_output_device)
            
            logging.info("Playing stop sound...")
            self.play_sound('stop_recording.wav')
            
            self.menu["Start Recording"].title = "Start Recording"
            self.icon = self.icon_path
            
            logging.info("Recording stopped successfully")
            
        except Exception as e:
            logging.error(f"Error stopping recording: {str(e)}")
            logging.error(traceback.format_exc())
        finally:
            # Ensure we always try to restore devices
            try:
                if hasattr(self, 'previous_input_device') and self.previous_input_device:
                    self.switch_input_device(self.previous_input_device)
                if hasattr(self, 'previous_output_device') and self.previous_output_device:
                    self.switch_to_device(self.previous_output_device)
            except Exception as e:
                logging.error(f"Error in device restoration: {str(e)}")
            self.stream = None
            self.audio_data = []

    def save_audio_file(self):
        try:
            if not self.audio_data:
                logging.warning("No audio data to save")
                return

            logging.info("=== Starting Audio Save Process ===")
            start_time = time.time()
            audio_array = np.concatenate(self.audio_data, axis=0)
            logging.info(f"Raw audio array shape: {audio_array.shape}, dtype: {audio_array.dtype}")

            # Check signal levels
            rms = np.sqrt(np.mean(audio_array**2))
            logging.info(f"Audio RMS level: {rms}")
            
            if rms < 1e-6:  # Adjust threshold as needed
                logging.error("No signal detected in recording")
                
                # Stop recording first
                self.menu["Start Recording"].title = "Start Recording"
                self.icon = self.icon_path
                self.recording = False
                
                # Temporarily change activation policy to make app visible
                app = AppKit.NSApplication.sharedApplication()
                app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
                
                # Create and configure NSAlert
                alert = AppKit.NSAlert.alloc().init()
                alert.setMessageText_("No Signal Recorded")
                alert.setInformativeText_("If there is a problem with the recording, make sure 'BlackHole 2ch' is enabled in your 'SoundGrabber' Multi-Output Device.")
                alert.addButtonWithTitle_("OK")
                alert.addButtonWithTitle_("Open Audio MIDI Setup")
                
                # Make sure the alert window comes to front
                AppKit.NSApp.activateIgnoringOtherApps_(True)
                
                response = alert.runModal()
                
                # Return to accessory app status after alert is closed
                app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
                
                if response == AppKit.NSAlertSecondButtonReturn:  # "Open Audio MIDI Setup" clicked
                    self.open_audio_midi_setup(None)
                return

            # Trim silence from start and end
            logging.info("Trimming silence from start and end")
            trimmed_audio, start_trim, end_trim = self.trim_silence_int32(audio_array)
            logging.info(f"Trimmed {start_trim} samples from start, {end_trim} samples from end")

            # Find the first transient in the trimmed audio
            transient_start = self.find_first_transient(trimmed_audio)
            logging.info(f"First transient found at sample: {transient_start}")

            # Further trim the audio to start at the first transient
            final_audio = trimmed_audio[transient_start:]
            logging.info(f"Final audio shape after transient trimming: {final_audio.shape}")

            # Apply initial fade if no trimming occurred (audio was already playing)
            if start_trim == 0 and transient_start == 0:
                logging.info("Applying initial fade for already playing audio")
                fade_duration = int(0.02 * self.fs)  # 20ms fade
                fade_in = np.linspace(0, 1, fade_duration)
                fade_in = np.tile(fade_in[:, np.newaxis], (1, final_audio.shape[1]))
                final_audio[:fade_duration] = (final_audio[:fade_duration] * fade_in).astype(np.int32)
            else:
                logging.info("No initial fade applied as audio was trimmed or transient was found")

            # Apply fade-out only if end trimming was not applied
            if end_trim == audio_array.shape[0]:
                fade_out_duration = int(0.04 * self.fs)  # 40ms fade-out
                final_audio = self.apply_fade_int32(final_audio, fade_out_duration, fade_in=False)
                logging.info("Applied fade-out to audio end")
            else:
                logging.info("No fade-out applied as end trimming was performed")

            # Normalize audio to float range [-1, 1]
            audio_array_normalized = final_audio.astype(np.float32) / np.iinfo(np.int32).max
            logging.info("Audio normalized to float range")

            # Get list of existing files with same name
            recording_name = self.settings['recording_name']
            output_folder = self.settings['output_folder']
            
            # Get all files that match the pattern name_XX.wav
            existing_files = [f for f in os.listdir(output_folder) 
                             if f.startswith(recording_name) and f.endswith('.wav') 
                             and f[len(recording_name):].startswith('_')]
            
            # Extract existing numbers
            used_numbers = set()
            for filename in existing_files:
                try:
                    # Extract number between name_ and .wav
                    num_str = filename[len(recording_name)+1:-4]  # remove name_, .wav
                    if num_str.isdigit():
                        used_numbers.add(int(num_str))
                except:
                    continue
            
            # Find the first available number
            number = 1
            while number in used_numbers:
                number += 1
            
            # Create filename with padded number
            filename = f"{recording_name}_{number:02d}.wav"
            filepath = os.path.join(output_folder, filename)
            
            logging.info(f"Saving audio to: {filepath}")
            sf.write(filepath, audio_array_normalized, self.fs, subtype='FLOAT')
            
            # Verify file was saved
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                processing_time = time.time() - start_time
                logging.info(f"File saved successfully. Size: {file_size} bytes, Processing time: {processing_time:.2f}s")
                self.last_recorded_file = filepath
            else:
                logging.error("File was not created")
            
        except Exception as e:
            logging.error(f"Error saving audio file: {e}")
            logging.error(traceback.format_exc())

    def find_first_transient(self, audio, threshold_db=-20, window_size=1024):
        threshold_linear = 10 ** (threshold_db / 20) * np.iinfo(np.int32).max
        
        # Calculate local energy more efficiently
        energy = np.sum(audio[:, 0]**2)  # Use first channel for mono compatibility
        
        # Find where energy exceeds the threshold
        transients = np.flatnonzero(energy > threshold_linear**2)
        
        return transients[0] if transients.size > 0 else 0

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            logging.warning(f"Audio callback status: {status}")
        self.last_callback_time = time.time()
        
        if self.recording:
            self.audio_data.append(indata.copy())
            # Add occasional audio data logging
            if len(self.audio_data) % 100 == 0:
                logging.info(f"Audio stats: shape={indata.shape}, max_value={np.max(np.abs(indata))}")
                logging.info(f"Total chunks recorded: {len(self.audio_data)}")

    def find_switch_audio_source(self):
        """Look for SwitchAudioSource in multiple locations"""
        try:
            # First check in our resources directory
            app_dir = os.path.dirname(os.path.abspath(__file__))
            local_path = os.path.join(app_dir, 'resources', 'SwitchAudioSource')
            if os.path.exists(local_path) and os.access(local_path, os.X_OK):
                return local_path

            # Fallback to system path
            result = subprocess.run(['which', 'SwitchAudioSource'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
                
            return None
        except Exception as e:
            logging.error(f"Error finding SwitchAudioSource: {e}")
            return None

    def get_current_output_device(self):
        if self.switch_audio_source_path:
            try:
                result = subprocess.run([self.switch_audio_source_path, "-c"], capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except subprocess.CalledProcessError:
                logging.error("Failed to get current output device")
        return None

    def switch_to_device(self, device):
        if not self.switch_audio_source_path or not device:
            logging.warning(f"Cannot switch output device to {device}. SwitchAudioSource not available or device is None.")
            return
        try:
            subprocess.run([self.switch_audio_source_path, "-s", device, "-t", "output"], check=True)
            logging.info(f"Switched output to {device}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to switch output to {device}: {e}")

    def switch_to_multi_output_device(self):
        self.switch_to_device("SoundGrabber")

    def quit_app(self, _):
        try:
            # Run cleanup before quitting
            self.cleanup_on_exit()
            
            # Then quit the application
            rumps.quit_application()
        except Exception as e:
            logging.error(f"Error during quit: {e}")
            logging.error(traceback.format_exc())
            # Still try to quit even if cleanup fails
            rumps.quit_application()

    def trim_silence_int32(self, audio_array, threshold_db=-60, min_silence_ms=2):
        threshold_linear = int(10 ** (threshold_db / 20) * np.iinfo(np.int32).max)
        min_silence_samples = int(min_silence_ms * self.fs / 1000)

        # Use vectorized operations for faster processing
        is_silent = np.all(np.abs(audio_array) < threshold_linear, axis=1)
        
        # Find the first non-silent sample
        start_trim = np.argmax(~is_silent)
        if start_trim == 0 and is_silent[0]:
            start_trim = len(is_silent)  # All silent

        # Find the last non-silent sample
        end_trim = len(is_silent) - np.argmax(~is_silent[::-1])
        end_trim = min(end_trim + min_silence_samples, len(is_silent))

        logging.info(f"Trim analysis: start_trim={start_trim}, end_trim={end_trim}, total_samples={audio_array.shape[0]}")
        
        # Check if the entire track is below the threshold
        if start_trim >= end_trim:
            logging.warning("The entire audio track is below the threshold. Returning original array.")
            return audio_array, 0, audio_array.shape[0]

        trimmed_audio = audio_array[start_trim:end_trim]
        
        logging.debug(f"Trimmed {start_trim} samples from start and {audio_array.shape[0] - end_trim} samples from end")
        
        return trimmed_audio, start_trim, end_trim

    def apply_fade_int32(self, audio, fade_length, fade_in=True):
        audio_length = audio.shape[0]
        
        # If audio is shorter than fade_length, adjust fade_length
        if audio_length < fade_length:
            fade_length = audio_length
        
        if fade_in:
            fade = np.linspace(0, 1, fade_length)
        else:
            fade = np.sqrt(np.linspace(1, 0, fade_length))  # Square root for a smoother fade-out
        
        fade = np.tile(fade, (audio.shape[1], 1)).T.astype(np.float32)
        
        # Create a copy of the audio array to avoid modifying the original
        faded_audio = audio.copy()
        
        if fade_in:
            faded_segment = faded_audio[:fade_length].astype(np.float32)
            faded_segment *= fade[:fade_length]
            faded_audio[:fade_length] = faded_segment.astype(np.int32)
        else:
            faded_segment = faded_audio[-fade_length:].astype(np.float32)
            faded_segment *= fade[-fade_length:]
            faded_audio[-fade_length:] = faded_segment.astype(np.int32)
        
        return faded_audio

    def show_last_recording_in_finder(self, _):
        output_folder = self.settings['output_folder']
        prefix = self.settings['recording_name']
        
        if not os.path.exists(output_folder):
            logging.error("Recording folder not found")
            return

        # Get all files in the output folder that start with the prefix and end with .wav
        recordings = [f for f in os.listdir(output_folder) if f.startswith(prefix) and f.endswith('.wav')]
        
        # Sort recordings by modification time, newest first
        recordings.sort(key=lambda x: os.path.getmtime(os.path.join(output_folder, x)), reverse=True)
        
        if recordings:
            # Find the first existing file
            for recording in recordings:
                file_path = os.path.join(output_folder, recording)
                if os.path.exists(file_path):
                    subprocess.run(['open', '-R', file_path])
                    logging.info(f"Showed recording in Finder: {file_path}")
                    return
        
        # If no recordings found or all were deleted, show the output folder
        subprocess.run(['open', output_folder])
        logging.info(f"No recordings found. Showed output folder in Finder: {output_folder}")

    def edit_settings(self, _):
        try:
            current_name = self.settings.get('recording_name', 'recording')
            
            # Create AppleScript command with basic styling and proper window positioning
            apple_script = f'''
            tell application "System Events"
                activate
                set folderSelection to choose folder with prompt "Select Output Folder" default location path to desktop
                set folderPath to POSIX path of folderSelection
                return folderPath
            end tell
            '''
            
            # Run AppleScript and get result
            result = subprocess.run(['osascript', '-e', apple_script], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                new_folder = result.stdout.strip()
                if new_folder:
                    self.settings['output_folder'] = new_folder
                    self.save_settings()
                    logging.info(f"Updated output folder to: {new_folder}")
                
        except Exception as e:
            logging.error(f"Error editing settings: {e}")
            logging.error(traceback.format_exc())

    def reload_settings(self, _):
        try:
            self.settings = self.load_settings()
        except Exception as e:
            logging.error(f"Error reloading settings: {e}")

    def apply_settings(self):
        try:
            # Test if audio device is available
            sd.check_output_settings(samplerate=48000)
        except sd.PortAudioError as e:
            logging.error(f"Error with audio settings: {e}")

    def get_current_input_device(self):
        if self.switch_audio_source_path:
            try:
                result = subprocess.run([self.switch_audio_source_path, "-c", "-t", "input"], capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except subprocess.CalledProcessError:
                logging.error("Failed to get current input device")
        return None

    def switch_input_device(self, device):
        if not self.switch_audio_source_path or not device:
            logging.warning(f"Cannot switch input device to {device}. SwitchAudioSource not available or device is None.")
            return
        try:
            subprocess.run([self.switch_audio_source_path, "-s", device, "-t", "input"], check=True)
            logging.info(f"Switched input to {device}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to switch input to {device}: {e}")

    def play_sound(self, sound_name):
        sound_path = os.path.join(os.path.dirname(__file__), 'resources', sound_name)
        logging.info(f"Attempting to play sound: {sound_path}")
        if not os.path.exists(sound_path):
            logging.error(f"Sound file not found: {sound_path}")
            return
        try:
            os.system(f"afplay {sound_path}")
            logging.info(f"Sound played successfully: {sound_name}")
        except Exception as e:
            logging.error(f"Failed to play sound {sound_name}: {e}")

    def check_recording_state(self, _):
        if self.recording:
            if self.stream is None or not self.stream.active:
                logging.error("Recording flag is True but stream is not active. Correcting state.")
                self.recording = False
                self.menu["Start Recording"].title = "Start Recording"
                self.icon = self.icon_path
        else:
            if self.stream is not None and self.stream.active:
                logging.warning("Recording flag is False but stream is active. Correcting state.")
                self.recording = True
                self.menu["Start Recording"].title = "Stop Recording"
                self.icon = self.recording_icon_path

    def log_app_state(self):
        logging.info(f"Current app state: recording={self.recording}, stream active={self.stream is not None and self.stream.active if self.stream else False}")

    def switch_devices(self, input_device, output_device):
        if not self.switch_audio_source_path:
            logging.warning("SwitchAudioSource not available. Skipping device switch.")
            return

        if input_device and self.get_current_input_device() != input_device:
            self.switch_input_device(input_device)

        if output_device and self.get_current_output_device() != output_device:
            self.switch_to_device(output_device)

        time.sleep(0.1)  # Reduced delay from 0.5 to 0.1 seconds

    def periodic_check(self, _):
        logging.info("Periodic check: Application is still running")

    def check_for_updates(self, sender=None, silent=False):
        try:
            # Remove existing update menu item if it exists
            for item in list(self.menu):
                if isinstance(item, rumps.MenuItem) and item.title.startswith("Update Available"):
                    self.menu.remove(item)
        
            # Bypass SSL verification
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            
            # Use GitHub API
            api_url = "https://api.github.com/repos/madebyivans/SoundGrabber/contents/version.txt"
            
            logging.info(f"Checking for updates at URL: {api_url}")
            
            request = urllib.request.Request(
                api_url,
                headers={
                    'User-Agent': 'SoundGrabber',
                    'Accept': 'application/vnd.github.v3.raw'
                }
            )
            
            response = urllib.request.urlopen(request, timeout=5)
            latest_version = response.read().decode('utf-8').strip()
            
            logging.info(f"Latest version from server: {latest_version}")
            
            # Store or clear version requirement based on server version
            self.store_version_requirement(latest_version)
            
            # Check if major version update is available
            current_major = int(self.version.split('.')[0])
            latest_major = int(latest_version.split('.')[0])
            
            if latest_major > current_major:
                logging.warning("Major version update required")
                self.show_update_required_message()
                AppKit.NSApp.terminate_(None)
                return
            
            # For non-major updates, continue with normal update notification
            elif latest_version > self.version:
                self.menu.insert_before(
                    "Check for Updates",
                    rumps.MenuItem(
                        f"Update Available ({latest_version})",
                        callback=self.download_update
                    )
                )
                
                if not silent:
                    rumps.notification(
                        title="SoundGrabber Update Available",
                        subtitle=f"Version {latest_version} is available",
                        message="Click 'Update Available' in the menu to download."
                    )
            elif not silent:
                rumps.notification(
                    title="SoundGrabber",
                    subtitle="No Updates Available",
                    message=f"You're running the latest version ({self.version})"
                )
            
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout) as e:
            # Handle connection errors
            logging.warning(f"Could not check for updates (connection error): {e}")
            # When offline, fall back to stored version requirement
            if self.check_stored_version_requirement():
                self.show_update_required_message()
                AppKit.NSApp.terminate_(None)
                return
            
            if not silent:
                rumps.notification(
                    title="SoundGrabber",
                    subtitle="Update Check Failed",
                    message="Could not check for updates. Will continue with current version."
                )
            return
            
        except Exception as e:
            logging.error(f"Error checking for updates: {str(e)}")
            logging.error(traceback.format_exc())

    def download_update(self, sender=None):
        try:
            webbrowser.open(self.download_url)
        except Exception as e:
            logging.error(f"Error opening download page: {e}")

    def check_blackhole_installed(self):
        try:
            devices = sd.query_devices()
            blackhole_exists = any('BlackHole 2ch' in str(device['name']) for device in devices)
            
            if not blackhole_exists:
                installer_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), 
                    'installers', 
                    'BlackHole2ch-0.6.0.pkg'
                )
                
                # Replace tkinter dialog with NSAlert
                alert = AppKit.NSAlert.alloc().init()
                alert.setMessageText_("BlackHole Not Found")
                alert.setInformativeText_("SoundGrabber requires BlackHole 2ch to function. Would you like to install it now?")
                alert.addButtonWithTitle_("Install")
                alert.addButtonWithTitle_("Cancel")
                
                response = alert.runModal()
                
                if response == AppKit.NSAlertFirstButtonReturn:  # "Install" clicked
                    subprocess.run(['open', installer_path])
                    return False
                return False
            return True
        except Exception as e:
            logging.error(f"Error checking BlackHole installation: {e}")
            return False

    def check_switchaudio_installed(self):
        try:
            if self.find_switch_audio_source():
                return True
                
            logging.error("SwitchAudioSource not found in resources or system path")
            return False
                
        except Exception as e:
            logging.error(f"Error checking SwitchAudioSource installation: {e}")
            return False

    def check_dependencies(self):
        # First check BlackHole
        blackhole_ok = self.check_blackhole_installed()
        if not blackhole_ok:
            logging.info("Waiting for BlackHole installation...")
            time.sleep(5)  # Give some time for the installer to start
            return False

        # Then check SwitchAudioSource
        switchaudio_ok = self.check_switchaudio_installed()
        if not switchaudio_ok:
            logging.info("Waiting for SwitchAudioSource installation...")
            time.sleep(2)  # Give some time for the installer to start
            return False

        return True

    def needs_setup(self):
        """Check if any components need to be set up"""
        try:
            # Check BlackHole
            devices = sd.query_devices()
            blackhole_exists = any('BlackHole 2ch' in str(device['name']) for device in devices)
            if not blackhole_exists:
                return True
                
            # Check Multi-Output Device
            result = subprocess.run([self.switch_audio_source_path, '-a'], 
                                 capture_output=True, text=True)
            if "SoundGrabber" not in result.stdout:
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Error checking setup requirements: {e}")
            return True

    def run_setup_wizard(self):
        """Run the setup wizard"""
        try:
            logging.info("Starting setup wizard...")
            wizard = SetupWizard()
            wizard.show()
            
            # Run the wizard's event loop
            AppKit.NSApp.run()
            
            # After wizard completes, verify everything is set up
            if self.needs_setup():
                logging.error("Setup incomplete")
                rumps.notification(
                    title="SoundGrabber",
                    subtitle="Setup Required",
                    message="Please complete the setup process before using SoundGrabber."
                )
                AppKit.NSApp.terminate_(None)
            else:
                # Restart the app properly
                self.__init__()  # Reinitialize the app
                self.run()
        
        except Exception as e:
            logging.error(f"Error during setup wizard: {e}")
            logging.error(traceback.format_exc())
            AppKit.NSApp.terminate_(None)

    def set_blackhole_gain(self, gain_db):
        try:
            # Switch to BlackHole first
            subprocess.run([self.switch_audio_source_path, "-t", "input", "-s", "BlackHole 2ch"], check=True)
            
            # Convert dB to a percentage (assuming -1 dB is approximately 89% volume)
            gain_percent = max(0, min(100, 100 + gain_db))  # Ensure the value is between 0 and 100
            
            # Use AppleScript to set the input volume
            apple_script = f'''
            tell application "System Events"
                set volume input volume {gain_percent}
            end tell
            '''
            
            # Get volume before change
            before_vol = subprocess.run(['osascript', '-e', 'get volume settings'], 
                                      capture_output=True, text=True).stdout.strip()
            
            # Set the volume
            subprocess.run(['osascript', '-e', apple_script], check=True)
            
            # Get volume after change
            after_vol = subprocess.run(['osascript', '-e', 'get volume settings'], 
                                     capture_output=True, text=True).stdout.strip()
            
            logging.info(f"BlackHole 2ch volume adjustment - Before: {before_vol}, After: {after_vol}")
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Error setting BlackHole gain: {e}")
            logging.error(f"Command output: {e.output if hasattr(e, 'output') else 'No output'}")
        except Exception as e:
            logging.error(f"Unexpected error setting BlackHole gain: {e}")
            logging.error(traceback.format_exc())

    def cleanup_on_exit(self):
        """Ensure proper cleanup when app exits"""
        try:
            logging.info("=== Starting Cleanup ===")
            if hasattr(self, 'recording') and self.recording:
                logging.info("Stopping active recording")
                self.stop_recording()
            
            if hasattr(self, 'stream') and self.stream:
                logging.info("Closing audio stream")
                self.stream.close()
            
            # Restore audio devices if needed
            if hasattr(self, 'previous_input_device') and self.previous_input_device:
                logging.info(f"Restoring input device to: {self.previous_input_device}")
                self.switch_input_device(self.previous_input_device)
            
            if hasattr(self, 'previous_output_device') and self.previous_output_device:
                logging.info(f"Restoring output device to: {self.previous_output_device}")
                self.switch_to_device(self.previous_output_device)
            
            logging.info("Cleanup completed successfully")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            logging.error(traceback.format_exc())

    def terminate_(self, sender):
        try:
            if self.recording:
                logging.info("Application exiting while recording, restoring audio devices...")
                if hasattr(self, 'previous_input_device') and self.previous_input_device:
                    self.switch_input_device(self.previous_input_device)
                    logging.info(f"Restored input device to: {self.previous_input_device}")
                
                if hasattr(self, 'previous_output_device') and self.previous_output_device:
                    self.switch_to_device(self.previous_output_device)
                    logging.info(f"Restored output device to: {self.previous_output_device}")
        except Exception as e:
            logging.error(f"Error during terminate: {e}")
            logging.error(traceback.format_exc())
        finally:
            super().terminate_(sender)

    def open_audio_midi_setup(self, _):
        try:
            subprocess.run(['open', '-a', 'Audio MIDI Setup'])
        except Exception as e:
            logging.error(f"Error opening Audio MIDI Setup: {e}")

    def edit_recording_name(self, _):
        try:
            current_name = self.settings.get('recording_name', 'recording')
            
            # Create AppleScript command with basic styling
            apple_script = f'''
            tell application "System Events"
                display dialog "Enter the base name for your recordings:" ¬
                    default answer "{current_name}" ¬
                    with title "Set Recording Name" ¬
                    buttons {{"Cancel", "Save"}} ¬
                    default button "Save"
            end tell
            '''
            
            # Run AppleScript and get result
            result = subprocess.run(['osascript', '-e', apple_script], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:  # User clicked Save
                # Parse the result to get the text
                new_name = result.stdout.strip()
                if new_name and "text returned:" in new_name:
                    new_name = new_name.split("text returned:")[1].strip()
                    self.settings['recording_name'] = new_name
                    self.save_settings()
                    logging.info(f"Updated recording name to: {new_name}")
            
        except Exception as e:
            logging.error(f"Error editing recording name: {e}")
            logging.error(traceback.format_exc())

    def open_settings_file(self, _):
        try:
            settings_path = '/Users/ivans/Desktop/app/audio_recorder_settings.txt'
            subprocess.run(['open', '-t', settings_path])  # Opens with default text editor
        except Exception as e:
            logging.error(f"Error opening settings file: {e}")
            logging.error(traceback.format_exc())

    def check_stored_version_requirement(self):
        """Check if there's a stored version requirement that hasn't been met"""
        try:
            requirement_file = os.path.join(tempfile.gettempdir(), 'soundgrabber_version_requirement.json')
            if os.path.exists(requirement_file):
                with open(requirement_file, 'r') as f:
                    data = json.load(f)
                    required_version = data.get('required_version')
                    if required_version:
                        current_major = int(self.version.split('.')[0])
                        required_major = int(required_version.split('.')[0])
                        return required_major > current_major
            return False
        except Exception as e:
            logging.error("Version check error")
            return False

    def store_version_requirement(self, required_version):
        """Store the version requirement persistently"""
        try:
            requirement_file = os.path.join(tempfile.gettempdir(), 'soundgrabber_version_requirement.json')
            
            # Always remove existing file first
            if os.path.exists(requirement_file):
                os.remove(requirement_file)
            
            # Parse versions
            required_major = int(required_version.split('.')[0])
            current_major = int(self.version.split('.')[0])
            
            # If server version is 1.x.x or lower than current, don't store anything
            if required_major <= 1 or required_major <= current_major:
                return
            
            # Only store if it's a higher major version
            if required_major > current_major:
                with open(requirement_file, 'w') as f:
                    json.dump({'required_version': required_version}, f)
        
        except Exception:
            pass  # Silently fail

    def show_update_required_message(self):
        """Show the update required message and exit"""
        try:
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Critical Update Required")
            alert.setInformativeText_(
                f"Your version ({self.version}) is outdated and no longer supported. "
                "Please update to continue using SoundGrabber."
            )
            alert.addButtonWithTitle_("Update Now")
            alert.addButtonWithTitle_("Exit")
            
            response = self.show_centered_alert(alert)
            
            if response == AppKit.NSAlertFirstButtonReturn:  # "Update Now"
                webbrowser.open("https://madebyivans.gumroad.com/l/soundgrabber")
            
        except Exception as e:
            logging.error(f"Error showing update message: {e}")

    def show_centered_alert(self, alert):
        """Helper method to show an alert centered and in front"""
        try:
            # Temporarily change activation policy and bring app to front
            app = AppKit.NSApplication.sharedApplication()
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            app.activateIgnoringOtherApps_(True)
            
            # Center and show alert
            alert_window = alert.window()
            screen = AppKit.NSScreen.mainScreen()
            screen_frame = screen.visibleFrame()
            window_frame = alert_window.frame()
            
            # Calculate center position
            center_x = screen_frame.origin.x + (screen_frame.size.width - window_frame.size.width) / 2
            center_y = screen_frame.origin.y + (screen_frame.size.height - window_frame.size.height) / 2
            
            # Set window position and bring to front
            alert_window.setFrame_display_(
                AppKit.NSMakeRect(center_x, center_y, window_frame.size.width, window_frame.size.height),
                True
            )
            alert_window.makeKeyAndOrderFront_(None)
            alert_window.orderFrontRegardless()
            
            # Show alert
            response = alert.runModal()
            
            # Return to accessory app status
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
            
            return response
            
        except Exception as e:
            logging.error(f"Error showing centered alert: {e}")
            return alert.runModal()  # Fallback to normal alert

if __name__ == "__main__":
    try:
        app = AdvancedAudioRecorderApp()
        app.check_for_updates(silent=True)
        
        # Add cleanup handler
        atexit.register(app.cleanup_on_exit)
        
        logging.info("Starting main application loop")
        app.run()
        
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
        logging.critical(traceback.format_exc())
        
        # Move crash log to app directory instead of Desktop
        crash_log_path = os.path.expanduser('~/.soundgrabber/crash.log')
        with open(crash_log_path, 'w') as f:
            f.write(f"SoundGrabber Crash Report\n")
            f.write(f"Version: {app.version if 'app' in locals() else 'Unknown'}\n")
            f.write(f"Time: {datetime.now()}\n\n")
            f.write(traceback.format_exc())
