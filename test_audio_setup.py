import subprocess
import AppKit
import logging
import time

def test_create_multi_output():
    try:
        # First check if device already exists
        check_cmd = ['SwitchAudioSource', '-a']
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if "SoundGrabber" in result.stdout:
            print("SoundGrabber device already exists!")
            return True
            
        print("Creating new Multi-Output Device...")
        
        # Open Audio MIDI Setup directly
        subprocess.run(['open', '-a', 'Audio MIDI Setup'])
        
        # Wait for Audio MIDI Setup to open
        time.sleep(1)  # Add 1 second delay
        
        # Show instructions
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Audio Setup Required")
        alert.setInformativeText_("""Please follow these steps in Audio MIDI Setup:

1. Click the '+' button in the bottom left
2. Select 'Create Multi-Output Device'
3. Name it 'SoundGrabber'
4. Check both 'BlackHole 2ch' and your Built-in Output
5. Close Audio MIDI Setup when finished""")
        alert.addButtonWithTitle_("OK")
        alert.runModal()
        
        # Wait and verify
        time.sleep(2)
        check_cmd = ['SwitchAudioSource', '-a']
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        if "SoundGrabber" in result.stdout:
            print("Successfully verified device creation!")
            
            # Show success message
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Setup Complete")
            alert.setInformativeText_("Multi-Output Device 'SoundGrabber' has been created successfully!")
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        else:
            print("Warning: Device may not have been created properly")
            
            # Show error message
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Setup Incomplete")
            alert.setInformativeText_("The Multi-Output Device 'SoundGrabber' was not found. Would you like to try again?")
            alert.addButtonWithTitle_("Try Again")
            alert.addButtonWithTitle_("Cancel")
            response = alert.runModal()
            
            if response == AppKit.NSAlertFirstButtonReturn:
                return test_create_multi_output()
            
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Multi-Output Device creation...")
    success = test_create_multi_output()
    print(f"Test {'succeeded' if success else 'failed'}")