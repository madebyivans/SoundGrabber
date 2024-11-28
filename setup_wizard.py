import AppKit
import subprocess
import os
import time
from utils import resource_path
import logging
import traceback
import json
import plistlib

class SetupWizard:
    def __init__(self):
        try:
            # Set up logging first
            app_dir = os.path.dirname(os.path.abspath(__file__))
            log_file = os.path.join(app_dir, 'setup_wizard.log')
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            logging.info("Starting Setup Wizard...")

            # Set up the switch_audio_source_path FIRST
            self.switch_audio_source_path = os.path.join(app_dir, 'resources', 'SwitchAudioSource')
            logging.info(f"SwitchAudioSource path: {self.switch_audio_source_path}")
            
            if not os.path.exists(self.switch_audio_source_path):
                logging.error(f"SwitchAudioSource not found at {self.switch_audio_source_path}")
            else:
                logging.info("SwitchAudioSource found")

            # Initialize status flags AFTER switch_audio_source_path is set
            self.blackhole_installed = self.check_blackhole_installed()
            self.soundgrabber_device_setup = self.check_multi_output_device()
            
            # Set up the application
            app = AppKit.NSApplication.sharedApplication()
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            
            # Set the dock icon
            icon_path = resource_path("icon.icns")
            if os.path.exists(icon_path):
                icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
                app.setApplicationIconImage_(icon)
            
            # Initialize the rest of the wizard
            self.current_step = 0
            
            # Modify steps to be dynamic based on what's already installed
            self.steps = [
                {
                    "title": "Welcome to SoundGrabber!",
                    "text": "Let's set up your audio recording environment. This will take about 2 minutes.",
                    "image": "welcome.png",
                    "button": "Start Setup"
                },
                {
                    "title": "Step 1: Install BlackHole",
                    "text": """First, we'll install BlackHole, which allows SoundGrabber to capture system audio.

When the installer appears, follow the prompts and enter your password when asked.""" if not self.blackhole_installed else "BlackHole is already installed!",
                    "image": "blackhole_install.png",
                    "button": "Continue" if self.blackhole_installed else "Install BlackHole"
                },
                {
                    "title": "Step 2: Create Multi-Output Device",
                    "text": """Please set up your audio output:

1. Click '+' in bottom left
2. Select 'Create Multi-Output Device'
3. Name it 'SoundGrabber'
4. ✓ Check both 'BlackHole 2ch' and your speakers
5. Make sure BlackHole 2ch is checked!

Click 'Continue' when done.""",
                    "image": "audio_midi_setup.png",
                    "button": "Open Audio Setup" if not self.soundgrabber_device_setup else "Continue"
                },
                {
                    "title": "Setup Complete!",
                    "text": "SoundGrabber is now ready to use. Click the menu bar icon to start recording!",
                    "image": "complete.png",
                    "button": "Finish"
                }
            ]
            
            # Add Quit menu item
            menubar = AppKit.NSMenu.alloc().init()
            app_menu_item = AppKit.NSMenuItem.alloc().init()
            menubar.addItem_(app_menu_item)
            
            app_menu = AppKit.NSMenu.alloc().init()
            quit_title = "Quit SoundGrabber Setup"
            quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                quit_title, "terminate:", "q"
            )
            app_menu.addItem_(quit_item)
            app_menu_item.setSubmenu_(app_menu)
            
            app.setMainMenu_(menubar)
            
            logging.info("Setup wizard initialized, creating window...")
            self.setup_window()
            logging.info("Setup wizard window created successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize setup wizard: {e}")
            logging.error(traceback.format_exc())
            raise
        
    def check_blackhole_installed(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            return any('BlackHole 2ch' in str(device['name']) for device in devices)
        except Exception as e:
            print(f"Error checking BlackHole: {e}")
            return False

    def check_multi_output_device(self):
        try:
            # Check if SoundGrabber exists
            result = subprocess.run([self.switch_audio_source_path, '-a'], 
                                 capture_output=True, text=True)
            
            logging.info(f"Available audio devices:\n{result.stdout}")
            
            # Exact match check for "SoundGrabber"
            if "SoundGrabber" not in result.stdout.split('\n'):
                logging.info("SoundGrabber device not found in audio devices list")
                return False
            
            logging.info("Found SoundGrabber device")
            return True
                
        except Exception as e:
            logging.error(f"Error checking Multi-Output device: {e}")
            logging.error(traceback.format_exc())
            return False

    def verify_step(self):
        if self.current_step == 1:  # BlackHole
            if not self.check_blackhole_installed():
                self.show_error("BlackHole Installation", 
                              "BlackHole doesn't appear to be installed yet. Please complete the installation.")
                return False
        elif self.current_step == 2:  # Multi-Output Device
            if not self.check_multi_output_device():
                self.show_error("Audio Setup", 
                              "The 'SoundGrabber' Multi-Output Device hasn't been created yet. Please complete the setup.")
                return False
        return True

    def show_error(self, title, message):
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        alert.runModal()
        
    def setup_window(self):
        # Create window with larger dimensions
        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            AppKit.NSMakeRect(0, 0, 800, 600),
            AppKit.NSWindowStyleMaskTitled | 
            AppKit.NSWindowStyleMaskClosable | 
            AppKit.NSWindowStyleMaskMiniaturizable,
            AppKit.NSBackingStoreBuffered,
            False
        )
        
        # Set window to terminate app when closed
        self.window.setReleasedWhenClosed_(True)
        
        # Add window delegate to handle closing
        class WindowDelegate(AppKit.NSObject):
            def windowWillClose_(self, notification):
                AppKit.NSApp.terminate_(None)
        
        self.window_delegate = WindowDelegate.alloc().init()
        self.window.setDelegate_(self.window_delegate)
        
        # Create content view
        self.content = AppKit.NSView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 800, 600)
        )
        
        # Add title label
        self.title_label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 520, 720, 40)  # Adjusted position
        )
        self.title_label.setBezeled_(False)
        self.title_label.setDrawsBackground_(False)
        self.title_label.setEditable_(False)
        self.title_label.setFont_(AppKit.NSFont.boldSystemFontOfSize_(24))  # Larger font
        
        # Add image view with larger dimensions
        self.image_view = AppKit.NSImageView.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 180, 720, 320)  # Larger image area
        )
        self.image_view.setWantsLayer_(True)
        self.image_view.layer().setBackgroundColor_(AppKit.NSColor.lightGrayColor().CGColor())
        
        # Add text view
        self.text_view = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 100, 720, 60)  # Adjusted position
        )
        self.text_view.setBezeled_(False)
        self.text_view.setDrawsBackground_(False)
        self.text_view.setEditable_(False)
        self.text_view.setFont_(AppKit.NSFont.systemFontOfSize_(14))
        
        # Add button
        self.button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(640, 40, 120, 32)  # Adjusted position
        )
        self.button.setBezelStyle_(AppKit.NSBezelStyleRounded)
        self.button.setTarget_(self)
        self.button.setAction_("nextStep:")
        
        # Add all views to content
        self.content.addSubview_(self.title_label)
        self.content.addSubview_(self.image_view)
        self.content.addSubview_(self.text_view)
        self.content.addSubview_(self.button)
        
        self.window.setContentView_(self.content)
        self.update_content()
        
    def update_content(self):
        step = self.steps[self.current_step]
        
        self.title_label.setStringValue_(step["title"])
        self.text_view.setStringValue_(step["text"])
        self.button.setTitle_(step["button"])
        
        # Image would be loaded here, but for now we'll show a placeholder
        self.image_view.setImage_(None)
        
    def nextStep_(self, sender):
        if self.current_step == 1:  # BlackHole installation
            if not self.blackhole_installed:
                self.install_blackhole()
                # Give time for the installer to appear
                time.sleep(2)
            
        elif self.current_step == 2:  # Multi-Output setup
            if sender.title() == "Open Audio Setup":
                self.setup_audio()
                sender.setTitle_("Continue")
                return
            else:  # Button says "Continue"
                if not self.check_multi_output_device():
                    self.show_error_and_reopen_audio_setup(
                        "Audio Setup Incomplete", 
                        """Please ensure:

1. A Multi-Output Device named exactly 'SoundGrabber' exists
2. Both BlackHole 2ch and your speakers are checked
3. BlackHole 2ch is enabled (checked) in the device

Need help? Check the image above for reference."""
                    )
                    return
        
        self.current_step += 1
        if self.current_step < len(self.steps):
            self.update_content()
        else:
            # Final verification
            if (self.check_blackhole_installed() and 
                self.check_multi_output_device()):
                self.window.close()
                AppKit.NSApp.terminate_(None)
            else:
                self.show_error("Setup Incomplete", 
                              "Some components are not properly installed. Please complete all steps.")
                self.current_step -= 1
                self.update_content()

    def install_blackhole(self):
        installer_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            'installers', 
            'BlackHole2ch-0.6.0.pkg'
        )
        subprocess.run(['open', installer_path])
        time.sleep(1)  # Give time for installer to open

    def setup_audio(self):
        """Open Audio MIDI Setup and bring it to front"""
        try:
            # Simple open and activate
            subprocess.run(['open', '-a', 'Audio MIDI Setup'])
            time.sleep(0.5)  # Give time for app to launch
            
            script = """
            tell application "Audio MIDI Setup"
                activate
            end tell
            """
            subprocess.run(['osascript', '-e', script])
            
        except Exception as e:
            logging.error(f"Failed to open Audio MIDI Setup: {e}")
            logging.error(traceback.format_exc())

    def show(self):
        try:
            logging.info("Showing setup wizard window...")
            self.window.center()
            self.window.makeKeyAndOrderFront_(None)
            AppKit.NSApp.activateIgnoringOtherApps_(True)
            logging.info("Setup wizard window shown successfully")
        except Exception as e:
            logging.error(f"Failed to show setup wizard: {e}")
            logging.error(traceback.format_exc())
            raise

    def show_error_and_reopen_audio_setup(self, title, message):
        """Shows error dialog and reopens Audio MIDI Setup"""
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_("""Please ensure:

1. A Multi-Output Device named exactly 'SoundGrabber' exists
2. Both BlackHole 2ch and your preferred listening device are checked

Need help? Check the image above for reference or send an email to a.ivans@icloud.com""")
        alert.addButtonWithTitle_("OK")
        alert.runModal()
        
        # Reopen/bring to front Audio MIDI Setup
        self.setup_audio()

if __name__ == "__main__":
    app = AppKit.NSApplication.sharedApplication()
    wizard = SetupWizard()
    wizard.show()
    app.run() 