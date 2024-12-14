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

import rumps
import sounddevice as sd
import numpy as np
import os
import sys  # Add this import
from datetime import datetime
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

def request_microphone_access():
    AVAudioSession = objc.lookUpClass('AVAudioSession')
    audio_session = AVAudioSession.sharedInstance()
    if audio_session.respondsToSelector_('requestRecordPermission:'):
        audio_session.requestRecordPermission_(lambda allowed: logging.info(f"Microphone access {'granted' if allowed else 'denied'}"))
    else:
        logging.error("This device doesn't support microphone permission requests")

class AdvancedAudioRecorderApp(rumps.App):
    def __init__(self):
        atexit.register(self.cleanup_on_exit)
        
        self.icon_path = resource_path("icon.icns")
        self.icon_recording_path = resource_path("icon_recording.icns")
        
        # Keep only these essential activation settings
        app = AppKit.NSApplication.sharedApplication()
        app.activateIgnoringOtherApps_(False)
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
        
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

    def setup_logging(self):
        app_directory = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(app_directory, 'audio_recorder.log')
        logging.basicConfig(filename=log_file, 
                           level=logging.INFO,  # Changed from ERROR to INFO
                           format='%(asctime)s - %(levelname)s - %(message)s')

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
        self.menu = [
            rumps.MenuItem("Start Recording", callback=self.toggle_recording),
            rumps.MenuItem("Show Last Recording", callback=self.show_last_recording_in_finder),
            None,  # Separator
            rumps.MenuItem("Edit Settings", callback=self.edit_settings),
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
            # Store current devices BEFORE any changes
            self.previous_input_device = self.get_current_input_device()
            self.previous_output_device = self.get_current_output_device()
            logging.info(f"Initial input device: {self.previous_input_device}")
            logging.info(f"Initial output device: {self.previous_output_device}")
            
            # Quick settings reload before recording
            try:
                self.settings = self.load_settings()
            except Exception as e:
                logging.warning(f"Could not reload settings, using existing values: {e}")
                
            self.apply_settings()
            self.channels = 2
            self.audio_data = []
            
            # Set BlackHole 2ch input gain to -1 dB before initializing stream
            self.set_blackhole_gain(-1)
            
            # Initialize stream before device switch
            self.stream = sd.InputStream(samplerate=self.fs, channels=self.channels, 
                                       dtype='int32', device='BlackHole 2ch',
                                       callback=self.audio_callback)
            
            # Switch devices first
            self.switch_devices("BlackHole 2ch", "SoundGrabber")
            
            # Play sound
            self.play_sound('start_recording.wav')
            time.sleep(0.135)  # Wait exactly for the sound duration
            
            # Start recording immediately after sound
            self.recording = True
            self.recording_start_time = time.time()
            self.stream.start()
            
            self.menu["Start Recording"].title = "Stop Recording"
            self.icon = self.icon_recording_path
            
        except Exception as e:
            logging.error(f"Error starting recording: {str(e)}")
            logging.error(traceback.format_exc())

    def stop_recording(self):
        try:
            self.recording = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
            
            if self.audio_data:
                self.save_audio_file()
            
            # Restore previous devices
            if self.previous_input_device:
                self.switch_input_device(self.previous_input_device)
                logging.info(f"Restored input device to: {self.previous_input_device}")
            
            if self.previous_output_device:
                self.switch_to_device(self.previous_output_device)
                logging.info(f"Restored output device to: {self.previous_output_device}")
            
            self.play_sound('stop_recording.wav')
            
            self.menu["Start Recording"].title = "Start Recording"
            self.icon = self.icon_path
            
        except Exception as e:
            logging.error(f"Error stopping recording: {str(e)}")
            logging.error(traceback.format_exc())
        finally:
            self.stream = None
            self.audio_data = []

    def save_audio_file(self):
        try:
            if not self.audio_data:
                logging.warning("No audio data to save")
                return

            start_time = time.time()
            audio_array = np.concatenate(self.audio_data, axis=0)
            logging.info(f"Raw audio array shape: {audio_array.shape}, dtype: {audio_array.dtype}")

            # Check if the audio is too short
            if audio_array.shape[0] < 100:  # Adjust this threshold as needed
                logging.warning("Audio is too short to process")
                return

            # Check for silence/no signal
            rms = np.sqrt(np.mean(audio_array**2))
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
                alert.setMessageText_("Recording Error")
                alert.setInformativeText_("No signal detected. Make sure 'BlackHole 2ch' is enabled in your 'SoundGrabber' Multi-Output Device.")
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
            else:
                logging.info("No fade-out applied as end trimming was performed")

            # Normalize audio to float range [-1, 1]
            audio_array_normalized = final_audio.astype(np.float32) / np.iinfo(np.int32).max

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
            
            os.makedirs(output_folder, exist_ok=True)
            
            logging.info(f"Attempting to save file to: {filepath}")
            sf.write(filepath, audio_array_normalized, self.fs, subtype='FLOAT')
            
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                logging.info(f"File saved successfully. Size: {file_size} bytes")
                self.last_recorded_file = filepath
            else:
                logging.error("File was not created")

            end_time = time.time()
            logging.info(f"Total audio processing and saving time: {end_time - start_time:.2f} seconds")

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

    def audio_callback(self, indata, frames, time, status):
        if status:
            logging.warning(f"Audio callback status: {status}")
        if self.recording:
            self.audio_data.append(indata.copy())
            logging.debug(f"Recorded chunk shape: {indata.shape}, min: {np.min(indata)}, max: {np.max(indata)}")

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
            settings_path = '/Users/ivans/Desktop/app/audio_recorder_settings.txt'
            if not os.path.exists(settings_path):
                self.save_settings()
            
            subprocess.run(['open', settings_path])
        except Exception as e:
            logging.error(f"Error opening settings file: {e}")

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
                self.update_menu_and_icon()
        else:
            if self.stream is not None and self.stream.active:
                logging.warning("Recording flag is False but stream is active. Correcting state.")
                self.recording = True
                self.update_menu_and_icon()

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
            
            # Use GitHub API instead of raw file
            api_url = "https://api.github.com/repos/madebyivans/SoundGrabber/contents/version.txt"
            
            logging.info(f"Checking for updates at URL: {api_url}")
            
            request = urllib.request.Request(
                api_url,
                headers={
                    'User-Agent': 'SoundGrabber',
                    'Accept': 'application/vnd.github.v3.raw'
                }
            )
            
            response = urllib.request.urlopen(request, timeout=10)
            latest_version = response.read().decode('utf-8').strip()
            
            logging.info(f"Latest version from server: {latest_version}")
            
            # Convert version strings to tuples for comparison
            current = tuple(map(int, self.version.split('.')))
            latest = tuple(map(int, latest_version.split('.')))
            logging.info(f"Comparing versions - Current: {current}, Latest: {latest}")
            
            if latest > current:
                # Add update menu item above the separator before "Quit"
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
                
        except Exception as e:
            logging.error(f"Error checking for updates: {str(e)}")
            logging.error(traceback.format_exc())
            if not silent:
                rumps.notification(
                    title="SoundGrabber",
                    subtitle="Update Check Failed",
                    message="Could not check for updates. Please try again later."
                )

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
                AppKit.NSApp.terminate_(None)  # Properly quit the app
        
        except Exception as e:
            logging.error(f"Error during setup wizard: {e}")
            logging.error(traceback.format_exc())
            AppKit.NSApp.terminate_(None)  # Properly quit on error

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

if __name__ == "__main__":
    try:
        app = AdvancedAudioRecorderApp()
        app.check_for_updates(silent=True)  # Silent update check
        app.run()
    except Exception as e:
        error_message = f"SoundGrabber encountered an unexpected error: {str(e)}"
        logging.critical(error_message)
        logging.critical(traceback.format_exc())
        
        # Create a user-friendly error message
        user_message = (
            "SoundGrabber encountered an unexpected error and needs to close.\n\n"
            "Please check the crash log for more details and report this issue (a.ivans@icloud.com).\n"
            f"Error details: {str(e)[:100]}..." if len(str(e)) > 100 else str(e)
        )
        
        # Write to crash log
        crash_log_path = os.path.expanduser('~/Desktop/soundgrabber_crash_log.txt')
        with open(crash_log_path, 'w') as f:
            f.write(f"{error_message}\n\n")
            f.write(traceback.format_exc())
        
        # Display error to user
        rumps.notification(
            title="SoundGrabber Error",
            subtitle="Application Crashed",
            message=user_message
        )
        
        # Ensure the app exits
        sys.exit(1)
