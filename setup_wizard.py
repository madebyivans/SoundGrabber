import os
import logging
import subprocess
import AppKit
import Foundation
import AVKit
import time
import traceback
from utils import resource_path
import json
import plistlib
import AVFoundation
import sys
import tempfile
import shutil

class WindowDelegate(AppKit.NSObject):
    def windowShouldClose_(self, sender):
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Quit Setup?")
        alert.setInformativeText_("Are you sure you want to quit the setup?")
        alert.addButtonWithTitle_("Quit")
        alert.addButtonWithTitle_("Cancel")
        
        if alert.runModal() == AppKit.NSAlertFirstButtonReturn:
            AppKit.NSApp.terminate_(None)
            return True
        return False

class SetupWizard:
    def __init__(self):
        try:
            # Set up logging in user's home directory
            home_dir = os.path.expanduser('~')
            log_dir = os.path.join(home_dir, '.soundgrabber')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            log_file = os.path.join(log_dir, 'setup_wizard.log')
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            logging.info("=== Setup Wizard Log Started ===")
            logging.info(f"Log file location: {log_file}")
            logging.info("Starting Setup Wizard...")

            # Define video frame dimensions
            self.video_frame = AppKit.NSMakeRect(40, 100, 720, 405)  # x, y, width, height
            
            # Update resource paths
            self.background_image = resource_path('resources/setup/background.png')
            self.welcome_image = resource_path('resources/setup/welcome.png')
            self.blackhole_install_image = resource_path('resources/setup/blackhole_install.png')
            self.audio_midi_setup_image = resource_path('resources/setup/audio_midi_setup.png')
            self.complete_image = resource_path('resources/setup/complete.png')
            self.guide_video = resource_path('resources/setup/guide.mp4')
            
            # Store path to SwitchAudioSource
            self.switch_audio_source_path = resource_path('resources/SwitchAudioSource')
            
            # Store path to BlackHole installer
            self.blackhole_installer = resource_path('installers/BlackHole2ch-0.6.0.pkg')
            
            # Initialize status flags AFTER switch_audio_source_path is set
            self.blackhole_installed = self.check_blackhole_installed()
            self.soundgrabber_device_setup = self.check_multi_output_device()
            
            # Set up the application
            app = AppKit.NSApplication.sharedApplication()
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            
            # Set the dock icon
            icon_path = resource_path("resources/icon.icns")
            if os.path.exists(icon_path):
                icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
                app.setApplicationIconImage_(icon)
            else:
                logging.error(f"Icon not found at path: {icon_path}")
            
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
                    "text": """Click 'Open Audio Setup', then set up your audio output:

1. Click '+' in bottom left and select 'Create Multi-Output Device'
2. Double click the title of 'Multi-Output Device' (left panel)
3. Rename it to 'SoundGrabber'
4. Tick 'Use' for both BlackHole 2ch and your speakers
5. Close Audio MIDI Setup (Cmd+Q) and press 'Continue'""",
                    "image": "audio_midi_setup.png",
                    "button": "Open Audio Setup" if not self.soundgrabber_device_setup else "Continue"
                },
                {
                    "title": "Setup Complete!",
                    "text": "SoundGrabber is now ready to use. Would you like to watch a quick guide on how to use it?",
                    "image": "complete.png",
                    "button": "Watch Guide",
                    "secondary_button": "Skip Guide"  # Add secondary button
                },
                {
                    "title": "Quick Start Guide",
                    "text": "Watch this short guide to learn how to use SoundGrabber",
                    "video": True,
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
            
            # Add delegate to handle window close button
            self.delegate = WindowDelegate.alloc().init()
            self.window.setDelegate_(self.delegate)
            
        except Exception as e:
            logging.error(f"Failed to initialize setup wizard: {e}")
            logging.error(traceback.format_exc())
            raise
        
    def check_blackhole_installed(self):
        try:
            # First try using switchaudio-source to list devices
            result = subprocess.run([self.switch_audio_source_path, '-a'], 
                                  capture_output=True, text=True)
            
            if 'BlackHole 2ch' in result.stdout:
                logging.info("BlackHole 2ch found in audio devices list")
                return True
            
            logging.info("BlackHole 2ch device not found")
            return False
        except Exception as e:
            logging.error(f"Error checking BlackHole: {e}")
            logging.error(traceback.format_exc())
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
        # Create window with larger dimensions and rounded corners
        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            AppKit.NSMakeRect(0, 0, 800, 600),
            AppKit.NSWindowStyleMaskTitled | 
            AppKit.NSWindowStyleMaskClosable | 
            AppKit.NSWindowStyleMaskMiniaturizable |
            AppKit.NSWindowStyleMaskFullSizeContentView,
            AppKit.NSBackingStoreBuffered,
            False
        )
        
        # Set window properties once
        self.window.setMovableByWindowBackground_(True)
        self.window.setTitlebarAppearsTransparent_(True)
        
        # Create content view
        self.content = AppKit.NSView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 800, 600)
        )
        self.content.setWantsLayer_(True)
        
        # Add background image first
        background_image_path = resource_path(os.path.join("resources", "setup", "background.png"))
        if os.path.exists(background_image_path):
            background_image = AppKit.NSImage.alloc().initWithContentsOfFile_(background_image_path)
            background_imageview = AppKit.NSImageView.alloc().initWithFrame_(
                AppKit.NSMakeRect(0, 0, 800, 600)
            )
            background_imageview.setImage_(background_image)
            background_imageview.setImageScaling_(AppKit.NSImageScaleAxesIndependently)
            self.content.addSubview_(background_imageview)
        
        # Create title label with original position
        self.title_label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 520, 720, 40)  # Back to original height
        )
        self.title_label.setBezeled_(False)
        self.title_label.setDrawsBackground_(False)
        self.title_label.setEditable_(False)
        self.title_label.setFont_(AppKit.NSFont.systemFontOfSize_weight_(24, AppKit.NSFontWeightSemibold))
        self.title_label.setTextColor_(AppKit.NSColor.blackColor())  # Dark text
        
        # Add image view with shadow
        self.image_view = AppKit.NSImageView.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 180, 720, 320)
        )
        self.image_view.setWantsLayer_(True)
        self.image_view.layer().setCornerRadius_(8.0)  # Rounded corners for image
        self.image_view.layer().setShadowColor_(AppKit.NSColor.blackColor().CGColor())
        self.image_view.layer().setShadowOffset_(AppKit.NSMakeSize(0, -2))
        self.image_view.layer().setShadowOpacity_(0.2)
        self.image_view.layer().setShadowRadius_(10.0)
        
        # Add text view with lower position
        self.text_view = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(40, 20, 520, 140)  # Keep at lower position
        )
        self.text_view.setBezeled_(False)
        self.text_view.setDrawsBackground_(False)
        self.text_view.setEditable_(False)

        # Set up the fonts
        bold_font = AppKit.NSFont.boldSystemFontOfSize_(14)
        regular_font = AppKit.NSFont.systemFontOfSize_(14)

        # Create the text with basic styling
        self.text_view.setFont_(regular_font)
        self.text_view.setTextColor_(AppKit.NSColor.blackColor())

        # Configure for multiple lines
        self.text_view.setLineBreakMode_(AppKit.NSLineBreakByWordWrapping)
        text_cell = self.text_view.cell()
        text_cell.setWraps_(True)
        
        # Create button with system default styling (make sure it's on top)
        self.button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(600, 40, 160, 44)  # Keep button position consistent
        )
        
        # Use system default style
        self.button.setBezelStyle_(0)  # NSBezelStyleRounded = 0
        self.button.setButtonType_(AppKit.NSButtonTypeMomentaryPushIn)
        
        # Set button properties
        self.button.setTitle_("Start Setup")
        self.button.setTarget_(self)
        self.button.setAction_("nextStep:")
        
        # Get the button cell and modify its properties
        button_cell = self.button.cell()
        button_cell.setControlSize_(AppKit.NSControlSizeLarge)  # Try to force large size
        
        # Set the button style
        self.button.setWantsLayer_(True)
        self.button.layer().setCornerRadius_(8.0)
        self.button.layer().setBorderWidth_(0)
        
        # Create a lighter blue that matches standard macOS buttons
        mac_button_blue = AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.2,    # Red - keeping low for blue
            0.5,    # Green - moderate for lighter blue
            1.0,    # Blue - full blue
            1.0     # Alpha
        )
        self.button.setBezelColor_(mac_button_blue)
        
        # Ensure button stays visible when window is inactive
        self.button.setShowsBorderOnlyWhileMouseInside_(False)
        button_cell.setBackgroundStyle_(0)
        
        # White text
        attrs = {
            AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_weight_(13, AppKit.NSFontWeightSemibold),
            AppKit.NSForegroundColorAttributeName: AppKit.NSColor.whiteColor()
        }
        title_string = AppKit.NSAttributedString.alloc().initWithString_attributes_("Start Setup", attrs)
        self.button.setAttributedTitle_(title_string)
        
        # Debug: Print actual frame and cell size
        actual_frame = self.button.frame()
        logging.info(f"Button frame: {actual_frame}")
        logging.info(f"Button cell size: {button_cell.controlSize()}")
        
        # Add secondary button (initially hidden)
        self.secondary_button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(420, 40, 160, 44)  # Keep original frame height
        )
        self.secondary_button.setBezelStyle_(0)
        self.secondary_button.setButtonType_(AppKit.NSButtonTypeMomentaryPushIn)
        self.secondary_button.setTitle_("Skip Guide")
        self.secondary_button.setTarget_(self)
        self.secondary_button.setAction_("skipGuide:")
        self.secondary_button.setHidden_(True)
        
        # Match the taller box style of Watch Guide button
        self.secondary_button.setWantsLayer_(True)
        self.secondary_button.layer().setCornerRadius_(22.0)
        self.secondary_button.layer().setBorderWidth_(0)
        
        # Increase the bezel's height to match Watch Guide
        self.secondary_button.cell().setControlSize_(AppKit.NSControlSizeLarge)  # Make the bezel taller
        self.secondary_button.setBezelColor_(AppKit.NSColor.darkGrayColor())
        
        # White text for secondary button
        attrs = {
            AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_weight_(13, AppKit.NSFontWeightSemibold),
            AppKit.NSForegroundColorAttributeName: AppKit.NSColor.whiteColor()
        }
        title_string = AppKit.NSAttributedString.alloc().initWithString_attributes_("Skip Guide", attrs)
        self.secondary_button.setAttributedTitle_(title_string)
        
        # Add views in correct order
        self.content.addSubview_(self.button)
        self.content.addSubview_(self.title_label)
        self.content.addSubview_(self.image_view)
        self.content.addSubview_(self.text_view)
        self.content.addSubview_(self.secondary_button)
        
        self.window.setContentView_(self.content)
        self.update_content()
        
    def update_content(self):
        step = self.steps[self.current_step]
        
        # Show/hide secondary button based on current step
        if hasattr(self, 'secondary_button'):
            self.secondary_button.setHidden_(self.current_step != 3)  # Show only on "Setup Complete" step
        
        # If it's the video step
        if step.get("video", False):
            if hasattr(self, 'image_view'):
                self.image_view.removeFromSuperview()
            
            if not hasattr(self, 'player_view'):
                player = self.setup_video_player()
                player.play()
            
            # Hide text only for video step
            self.text_view.setHidden_(True)
            self.title_label.setHidden_(True)  # Hide the original title
        else:
            # Regular step behavior
            if hasattr(self, 'player_view'):
                self.player_view.removeFromSuperview()
                if hasattr(self, 'title_background'):
                    self.title_background.removeFromSuperview()
            
            self.title_label.setHidden_(False)
            self.title_label.setStringValue_(step["title"])
            self.button.setTitle_(step["button"])
            
            # Show text for non-video steps
            self.text_view.setHidden_(False)
            self.text_view.setStringValue_(step["text"])
            
            image_path = resource_path(os.path.join("resources", "setup", step["image"]))
            if os.path.exists(image_path):
                image = AppKit.NSImage.alloc().initWithContentsOfFile_(image_path)
                self.image_view.setImage_(image)
            else:
                self.image_view.setImage_(None)
        
    def nextStep_(self, sender):
        if self.current_step == 1:  # BlackHole installation
            if not self.blackhole_installed:
                self.install_blackhole()
                time.sleep(5)
        
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
                else:
                    # Success - animate window back to center at top of screen
                    screen = AppKit.NSScreen.mainScreen()
                    screen_frame = screen.visibleFrame()
                    window_frame = self.window.frame()
                    
                    # Calculate center position at top of screen
                    center_x = screen_frame.origin.x + (screen_frame.size.width - window_frame.size.width) / 2
                    center_y = screen_frame.origin.y + screen_frame.size.height - window_frame.size.height - 20  # 20px from top
                    
                    # Animate to center
                    self.window.setFrame_display_animate_(
                        AppKit.NSMakeRect(center_x, center_y, window_frame.size.width, window_frame.size.height),
                        True, True
                    )
        
        self.current_step += 1
        if self.current_step < len(self.steps):
            self.update_content()
        else:
            # Final verification
            blackhole_check = self.check_blackhole_installed()
            multioutput_check = self.check_multi_output_device()
            
            if blackhole_check and multioutput_check:
                self.window.close()
                AppKit.NSApp.terminate_(None)
            else:
                self.show_error("Setup Incomplete", 
                              "Some components are not properly installed. Please complete all steps.")
                self.current_step -= 1
                self.update_content()

    def install_blackhole(self):
        try:
            logging.info(f"Installing BlackHole from: {self.blackhole_installer}")
            if not os.path.exists(self.blackhole_installer):
                logging.error(f"BlackHole installer not found at: {self.blackhole_installer}")
                raise FileNotFoundError("BlackHole installer package not found")
            
            subprocess.run(['open', self.blackhole_installer])
            time.sleep(1)  # Give time for installer to open
        except Exception as e:
            logging.error(f"Failed to install BlackHole: {e}")
            logging.error(traceback.format_exc())
            raise

    def setup_audio(self):
        """Open Audio MIDI Setup and position windows"""
        try:
            # First, position our setup wizard window to the left edge and top
            screen = AppKit.NSScreen.mainScreen()
            screen_frame = screen.visibleFrame()
            
            # Get our window
            our_window = AppKit.NSApp.mainWindow()
            our_frame = our_window.frame()
            
            # Calculate position (left edge and top of screen)
            new_x = screen_frame.origin.x + 20  # 20px padding from left edge
            new_y = screen_frame.origin.y + screen_frame.size.height - our_frame.size.height - 20  # 20px from top
            
            # Move our window
            our_window.setFrame_display_animate_(
                AppKit.NSMakeRect(new_x, new_y, our_frame.size.width, our_frame.size.height),
                True, True
            )
            
            # Simply open Audio MIDI Setup
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

    def close_window(self, sender):
        # Simple direct quit without confirmation
        AppKit.NSApp.terminate_(None)

    def setup_video_player(self):
        # Create AVPlayerView
        self.player_view = AVKit.AVPlayerView.alloc().init()
        
        # Original video dimensions
        original_width = 1728
        original_height = 1080
        
        # Use full window height
        available_height = 600
        
        # Calculate width based on aspect ratio to fill height
        scale = available_height / original_height
        new_width = original_width * scale
        
        # Calculate x offset to center the wider video
        x_offset = (new_width - 800) / 2 * -1
        
        # Position video to fill full height from top to bottom
        self.player_view.setFrame_(AppKit.NSMakeRect(
            x_offset,
            0,              # Start from top
            new_width,
            available_height  # Use exact window height
        ))
        
        self.player_view.setWantsLayer_(True)
        self.player_view.setVideoGravity_(AVFoundation.AVLayerVideoGravityResizeAspectFill)
        # Hide controls
        self.player_view.setControlsStyle_(AVKit.AVPlayerViewControlsStyleNone)
        self.player_view.setShowsFullScreenToggleButton_(False)
        
        # Create background for title with Dynamic Island style
        island_width = 450
        island_height = 40
        
        self.title_background = AppKit.NSVisualEffectView.alloc().initWithFrame_(
            AppKit.NSMakeRect(
                (800 - island_width) / 2,  # Exact center
                600 - island_height,       # Exactly at top
                island_width,
                island_height
            )
        )
        self.title_background.setMaterial_(AppKit.NSVisualEffectMaterialUltraDark)
        self.title_background.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        self.title_background.setState_(AppKit.NSVisualEffectStateActive)
        self.title_background.setWantsLayer_(True)
        
        # Create custom shape for Dynamic Island style
        path = AppKit.NSBezierPath.bezierPath()
        
        # Different radii for top and bottom
        bottom_radius = 20
        
        # Start at top-left with sharp corner
        path.moveToPoint_(AppKit.NSMakePoint(0, island_height))
        
        # Top edge (straight)
        path.lineToPoint_(AppKit.NSMakePoint(island_width, island_height))
        
        # Right edge
        path.lineToPoint_(AppKit.NSMakePoint(island_width, bottom_radius))
        
        # Bottom right corner
        path.appendBezierPathWithArcFromPoint_toPoint_radius_(
            AppKit.NSMakePoint(island_width, 0),
            AppKit.NSMakePoint(0, 0),
            bottom_radius
        )
        
        # Bottom left corner
        path.appendBezierPathWithArcFromPoint_toPoint_radius_(
            AppKit.NSMakePoint(0, 0),
            AppKit.NSMakePoint(0, island_height),
            bottom_radius
        )
        
        path.closePath()
        
        # Apply the mask
        mask = AppKit.CAShapeLayer.layer()
        mask.setPath_(path.CGPath())
        self.title_background.layer().setMask_(mask)
        
        # Create and style title label with exact centering
        self.title = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(
                0,  # No left padding - will center in full width
                5,  # Vertical centering
                island_width, # Use full width of background
                30  # Height
            )
        )
        self.title.setStringValue_("Quick Start Guide")
        self.title.setBezeled_(False)
        self.title.setDrawsBackground_(False)
        self.title.setEditable_(False)
        self.title.setAlignment_(AppKit.NSTextAlignmentCenter)
        self.title.setFont_(AppKit.NSFont.systemFontOfSize_weight_(16, AppKit.NSFontWeightMedium))
        self.title.setTextColor_(AppKit.NSColor.whiteColor())
        
        # Add title to background
        self.title_background.addSubview_(self.title)
        
        # Set up video player
        video_path = resource_path(os.path.join("resources", "setup", "guide.mp4"))
        video_url = AppKit.NSURL.fileURLWithPath_(video_path)
        player = AVFoundation.AVPlayer.playerWithURL_(video_url)
        self.player_view.setPlayer_(player)
        
        # Add observer for video completion using KVO
        self.player_view.player().currentItem().addObserver_forKeyPath_options_context_(
            self,
            'status',
            AVFoundation.NSKeyValueObservingOptionNew,
            None
        )
        
        # Register for end of video notification
        AppKit.NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self,
            'videoDidFinish:',
            AVFoundation.AVPlayerItemDidPlayToEndTimeNotification,
            player.currentItem()
        )
        
        # Add views in correct order
        self.content.addSubview_(self.player_view)
        self.content.addSubview_(self.title_background)
        
        # Hide button initially
        if hasattr(self, 'button'):
            self.button.setHidden_(True)
        
        return player

    def observeValueForKeyPath_ofObject_change_context_(self, keyPath, object, change, context):
        if keyPath == 'status':
            if object.status() == AVFoundation.AVPlayerItemStatusReadyToPlay:
                # Video is ready to play
                self.player_view.player().play()

    def videoDidFinish_(self, notification):
        logging.info("=== Starting App Restart Process ===")
        try:
            # Close current window
            logging.info("Closing setup wizard window...")
            self.window.close()
            
            # Get the bundle path using NSBundle
            bundle = AppKit.NSBundle.mainBundle()
            bundle_path = bundle.bundlePath()
            logging.info(f"Found bundle path: {bundle_path}")
            logging.info(f"Bundle identifier: {bundle.bundleIdentifier()}")
            logging.info(f"Bundle executable path: {bundle.executablePath()}")
            
            if bundle_path.endswith('.app'):
                # We're running from a bundle
                logging.info(f"Running from bundle: {bundle_path}")
                
                # Create a new instance before terminating current one
                launch_cmd = ['open', '-n', bundle_path]
                logging.info(f"Launching new instance with command: {launch_cmd}")
                
                process = subprocess.Popen(launch_cmd, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
                
                stdout, stderr = process.communicate()
                logging.info(f"Launch process return code: {process.returncode}")
                if stdout:
                    logging.info(f"Launch stdout: {stdout.decode()}")
                if stderr:
                    logging.error(f"Launch stderr: {stderr.decode()}")
                
                # Small delay to ensure new instance starts
                logging.info("Waiting for new instance to start...")
                time.sleep(0.5)
                
                # Now terminate current instance
                logging.info("Terminating current instance...")
                AppKit.NSApp.terminate_(None)
            else:
                # Development mode
                script_dir = os.path.dirname(os.path.abspath(__file__))
                main_script = os.path.join(script_dir, 'audio_recorder.py')
                logging.info(f"Development mode, launching: {main_script}")
                logging.info(f"Current executable: {sys.executable}")
                logging.info(f"Current working directory: {os.getcwd()}")
                os.execv(sys.executable, ['python3', main_script])
                
        except Exception as e:
            logging.error(f"Failed to restart app: {e}")
            logging.error(f"Exception type: {type(e)}")
            logging.error(f"Exception details: {str(e)}")
            logging.error("Full traceback:")
            logging.error(traceback.format_exc())
            AppKit.NSApp.terminate_(None)

    def skipGuide_(self, sender):
        """Handler for Skip Guide button"""
        logging.info("Skip Guide button pressed - initiating app restart")
        self.videoDidFinish_(None)  # Reuse the same logic

    def open_audio_midi_setup(self):
        try:
            # First, position our setup wizard window to the left edge
            screen = AppKit.NSScreen.mainScreen()
            screen_frame = screen.visibleFrame()
            
            # Get our window
            our_window = AppKit.NSApp.mainWindow()
            our_frame = our_window.frame()
            
            # Calculate position for our window (left edge, maintaining vertical position)
            new_x = screen_frame.origin.x + 20  # 20px padding from left edge
            new_y = our_frame.origin.y  # Keep current vertical position
            
            # Move our window
            our_window.setFrame_display_animate_(
                AppKit.NSMakeRect(new_x, new_y, our_frame.size.width, our_frame.size.height),
                True, True
            )
            
            # Open Audio MIDI Setup
            subprocess.run(['open', '-a', 'Audio MIDI Setup'])
            
            # Give Audio MIDI Setup a moment to open
            time.sleep(0.5)
            
            # Find Audio MIDI Setup window
            audio_midi_app = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_("com.apple.AudioMIDISetup")[0]
            audio_midi_app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
            
            # Use AppleScript to position the Audio MIDI Setup window
            apple_script = f'''
                tell application "Audio MIDI Setup"
                    activate
                    tell application "System Events"
                        tell process "Audio MIDI Setup"
                            set position of window 1 to {{{our_frame.size.width + new_x + 20}, {new_y}}}
                        end tell
                    end tell
                end tell
            '''
            
            subprocess.run(['osascript', '-e', apple_script])
            
            # Bring our window back to front
            our_window.makeKeyAndOrderFront_(None)
            
        except Exception as e:
            logging.error(f"Error positioning windows: {e}")
            # Fallback to just opening Audio MIDI Setup
            subprocess.run(['open', '-a', 'Audio MIDI Setup'])

    def play_video(self):
        try:
            video_path = resource_path('resources/setup/guide.mp4')
            logging.info(f"Loading video from path: {video_path}")
            
            if not os.path.exists(video_path):
                logging.error(f"Video file not found at path: {video_path}")
                return
                
            # Create a temporary directory with proper permissions
            temp_dir = tempfile.mkdtemp()
            temp_video_path = os.path.join(temp_dir, 'guide.mp4')
            
            try:
                # Copy the video file to temp directory
                shutil.copy2(video_path, temp_video_path)
                # Ensure permissions are correct
                os.chmod(temp_video_path, 0o644)
                logging.info(f"Copied video to temporary location: {temp_video_path}")
            except Exception as e:
                logging.error(f"Failed to copy video to temp location: {e}")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            video_url = Foundation.NSURL.fileURLWithPath_(temp_video_path)
            logging.info(f"Created video URL: {video_url}")
            
            self.player = AVKit.AVPlayer.playerWithURL_(video_url)
            if not self.player:
                logging.error("Failed to create AVPlayer")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            # Store temp directory path for cleanup
            self.temp_video_dir = temp_dir
            
            # Create the player view with the same frame as the container
            self.player_view = AVKit.AVPlayerView.alloc().initWithFrame_(
                self.video_container.frame()
            )
            if not self.player_view:
                logging.error("Failed to create AVPlayerView")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            self.player_view.setPlayer_(self.player)
            
            # Remove any existing subviews from the container
            for subview in self.video_container.subviews():
                subview.removeFromSuperview()
                
            # Add player view to the container
            self.video_container.addSubview_(self.player_view)
            
            # Add observer for playback status
            self.player.addObserver_forKeyPath_options_context_(
                self, "status", Foundation.NSKeyValueObservingOptionNew, None)
            
            # Play the video
            self.player.play()
            logging.info("Video playback started")
            
        except Exception as e:
            logging.error(f"Error playing video: {e}")
            logging.error(traceback.format_exc())
            if hasattr(self, 'temp_video_dir'):
                shutil.rmtree(self.temp_video_dir, ignore_errors=True)

    def observeValueForKeyPath_ofObject_change_context_(self, keyPath, obj, change, context):
        if keyPath == "status":
            status = obj.status()
            if status == AVFoundation.AVPlayerStatusFailed:
                error = obj.error()
                logging.error(f"Player failed with error: {error}")
            elif status == AVFoundation.AVPlayerStatusReadyToPlay:
                logging.info("Player is ready to play")
            elif status == AVFoundation.AVPlayerStatusUnknown:
                logging.info("Player status is unknown")

    def create_window(self):
        try:
            # Create the window
            self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                AppKit.NSMakeRect(0, 0, 800, 600),
                AppKit.NSWindowStyleMaskTitled |
                AppKit.NSWindowStyleMaskClosable |
                AppKit.NSWindowStyleMaskMiniaturizable,
                AppKit.NSBackingStoreBuffered,
                False
            )
            
            self.window.setTitle_("SoundGrabber Setup")
            
            # Store content view for later use
            self.content_view = self.window.contentView()
            
            # Create video container view
            self.video_container = AppKit.NSView.alloc().initWithFrame_(
                AppKit.NSMakeRect(40, 100, 720, 405)
            )
            self.content_view.addSubview_(self.video_container)
            
            # Center window on screen
            self.window.center()
            
            # Set up the window delegate
            self.delegate = WindowDelegate.alloc().init()
            self.window.setDelegate_(self.delegate)
            
            logging.info("Setup wizard window created successfully")
            
        except Exception as e:
            logging.error(f"Error creating window: {e}")
            logging.error(traceback.format_exc())

    def dealloc(self):
        # Remove observer when the window is closed
        if hasattr(self, 'player'):
            self.player.removeObserver_forKeyPath_(self, "status")
        # Clean up temporary directory
        if hasattr(self, 'temp_video_dir'):
            shutil.rmtree(self.temp_video_dir, ignore_errors=True)
        super().dealloc()

if __name__ == "__main__":
    app = AppKit.NSApplication.sharedApplication()
    wizard = SetupWizard()
    wizard.show()
    app.run() 