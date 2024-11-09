import AppKit
import subprocess
import os
import time
from utils import resource_path
import logging
import traceback

class SetupWizard:
    def __init__(self):
        try:
            # Set up the application
            app = AppKit.NSApplication.sharedApplication()
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)  # Show in dock
            
            # Set the dock icon
            icon_path = resource_path("icon.icns")
            if os.path.exists(icon_path):
                icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
                app.setApplicationIconImage_(icon)
            
            # Initialize the rest of the wizard
            self.current_step = 0
            self.steps = [
                {
                    "title": "Welcome to SoundGrabber!",
                    "text": "Let's set up your audio recording environment. This will take about 3 minutes.",
                    "image": "welcome.png",
                    "button": "Start Setup"
                },
                {
                    "title": "Step 1: Install BlackHole",
                    "text": """First, we'll install BlackHole, which allows SoundGrabber to capture system audio.

When the installer appears, follow the prompts and enter your password when asked.""",
                    "image": "blackhole_install.png",
                    "button": "Install BlackHole"
                },
                {
                    "title": "Step 2: Install SwitchAudio",
                    "text": """Now we'll install SwitchAudio, which helps manage your audio devices.

This will be installed automatically when you click the button.""",
                    "image": "switchaudio_install.png",
                    "button": "Install SwitchAudio"
                },
                {
                    "title": "Step 3: Create Multi-Output Device",
                    "text": """Finally, let's set up your audio output:

1. Click the '+' button in the bottom left
2. Select 'Create Multi-Output Device'
3. Name it 'SoundGrabber'
4. Check both 'BlackHole 2ch' and your speakers""",
                    "image": "audio_midi_setup.png",
                    "button": "Open Audio Setup"
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

    def check_switchaudio_installed(self):
        try:
            result = subprocess.run(['which', 'SwitchAudioSource'], 
                                 capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error checking SwitchAudioSource: {e}")
            return False

    def check_multi_output_device(self):
        try:
            result = subprocess.run(['SwitchAudioSource', '-a'], 
                                 capture_output=True, text=True)
            return "SoundGrabber" in result.stdout
        except Exception as e:
            print(f"Error checking Multi-Output device: {e}")
            return False

    def verify_step(self):
        if self.current_step == 1:  # BlackHole
            if not self.check_blackhole_installed():
                self.show_error("BlackHole Installation", 
                              "BlackHole doesn't appear to be installed yet. Please complete the installation.")
                return False
        elif self.current_step == 2:  # SwitchAudio
            if not self.check_switchaudio_installed():
                self.show_error("SwitchAudio Installation", 
                              "SwitchAudio doesn't appear to be installed yet. Please wait for the installation to complete.")
                return False
        elif self.current_step == 3:  # Multi-Output Device
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
            self.install_blackhole()
            # Give time for the installer to appear and complete
            time.sleep(2)  # Wait for installer to open
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Installing BlackHole")
            alert.setInformativeText_("Please complete the BlackHole installation and click OK when finished.")
            alert.addButtonWithTitle_("OK")
            alert.runModal()
            
        elif self.current_step == 2:  # SwitchAudio installation
            self.install_switchaudio()
            time.sleep(2)  # Wait for installation to complete
            
        elif self.current_step == 3:  # Multi-Output setup
            self.setup_audio()
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Setting up Audio Device")
            alert.setInformativeText_("Please create the Multi-Output Device and click OK when finished.")
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        
        # Only verify after user confirms completion
        if not self.verify_step():
            return
            
        self.current_step += 1
        if self.current_step < len(self.steps):
            self.update_content()
        else:
            # Verify all components before finishing
            if (self.check_blackhole_installed() and 
                self.check_switchaudio_installed() and 
                self.check_multi_output_device()):
                self.window.close()
                AppKit.NSApp.terminate_(None)  # Add this line to properly quit
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

    def install_switchaudio(self):
        installer_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            'installers', 
            'SwitchAudioSource'
        )
        try:
            os.chmod(installer_path, 0o755)
            cmd = [
                'osascript', '-e', 
                f'do shell script "cp {installer_path} /usr/local/bin/SwitchAudioSource && chmod 755 /usr/local/bin/SwitchAudioSource" with administrator privileges'
            ]
            subprocess.run(cmd, check=True)
        except Exception as e:
            self.show_error("Installation Error", f"Failed to install SwitchAudioSource: {str(e)}")

    def setup_audio(self):
        subprocess.run(['open', '-a', 'Audio MIDI Setup'])
        
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

if __name__ == "__main__":
    app = AppKit.NSApplication.sharedApplication()
    wizard = SetupWizard()
    wizard.show()
    app.run() 