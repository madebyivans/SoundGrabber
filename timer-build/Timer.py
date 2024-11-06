import datetime
import time
from datetime import timedelta
import pyperclip
import platform
import threading
from plyer import notification
import ctypes
import os
import sys

# Determine the operating system
IS_MACOS = platform.system() == "Darwin"

if IS_MACOS:
    import rumps
else:
    import pystray
    from PIL import Image, ImageDraw
    import tkinter as tk
    from tkinter import simpledialog, messagebox
    import winsound
    from winotify import Notification

    try:
        # Enable modern Windows styles
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        # Use dark mode for system dialogs
        ctypes.windll.uxtheme.SetThemeAppProperties(1)
    except:
        pass

    if not IS_MACOS:
        import winsound

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class TimerApp:
    def __init__(self):
        self.mode = None
        self.activity = None
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.is_running = False
        self.root = None
        
        # Use resource_path for icons
        self.icon_path = resource_path("icon.png")
        self.icon_ico_path = resource_path("icon.ico")
        
        if IS_MACOS:
            self.setup_macos()
        else:
            self.setup_windows()

    def setup_macos(self):
        self.app = rumps.App("⏱️", icon=None, quit_button=None)
        self.timer_button = rumps.MenuItem("Start Timer", callback=self.start_timer)
        self.stopwatch_button = rumps.MenuItem("Start Stopwatch", callback=self.start_stopwatch)
        self.stop_button = rumps.MenuItem("Stop", callback=self.stop)
        self.resume_button = rumps.MenuItem("Resume", callback=self.resume)
        self.copy_button = rumps.MenuItem("Copy to Clipboard", callback=self.copy_format)
        
        self.resume_button.hidden = True
        
        self.app.menu = [
            self.timer_button,
            self.stopwatch_button,
            None,
            self.stop_button,
            self.resume_button,
            self.copy_button,
            None,
            rumps.MenuItem("Quit", callback=self.stop_app)
        ]

    def setup_windows(self):
        self.icon = self.create_icon()
        
        # Initialize notification system
        try:
            self.notification = Notification
        except Exception as e:
            print(f"Notification setup error: {e}")
            self.notification = None
        
        def create_menu():
            return pystray.Menu(
                pystray.MenuItem("Start Timer", self.start_timer),
                pystray.MenuItem("Start Stopwatch", self.start_stopwatch),
                pystray.MenuItem("Stop", self.stop),
                pystray.MenuItem("Resume", self.resume),
                pystray.MenuItem("Copy to Clipboard", self.copy_format),
                pystray.MenuItem("Quit", self.stop_app)
            )
        
        self.tray_icon = pystray.Icon(
            "timer",
            self.icon,
            "Timer",
            menu=create_menu()
        )
        
        # Create and configure root window
        self.root = tk.Tk()
        self.root.withdraw()
        # Make it handle focus properly
        self.root.attributes('-topmost', True)

    def create_icon(self, size=32):
        if not IS_MACOS:
            # Use resource_path for icon
            image = Image.open(self.icon_path)
            image = image.convert('RGBA')
            image = image.resize((32, 32), Image.Resampling.LANCZOS)
            return image
        
        # Fallback for macOS
        image = Image.new('RGBA', (size, size), color=(0,0,0,0))
        dc = ImageDraw.Draw(image)
        dc.ellipse([2, 2, size-2, size-2], outline='black', width=2)
        dc.line([size//2, size//2, size//2, size//4], fill='black', width=2)
        return image

    def update_icon_title(self, text):
        if IS_MACOS:
            self.app.title = f"⏱️ {text}"
        else:
            self.tray_icon.title = f"Timer: {text}"
            # Ensure menu stays accessible
            self.tray_icon.update_menu()

    def show_notification(self, title, message, play_sound=False):
        if IS_MACOS:
            os.system("""
                osascript -e 'display notification "{}" with title "{}" sound name "Glass"'
            """.format(message, title))
        else:
            try:
                toast = self.notification(
                    app_id="Timer App",
                    title=title,
                    msg=message,
                    icon=self.icon_ico_path,
                    duration="short"
                )
                toast.show()
                
                if play_sound:
                    sound_path = resource_path("notification.wav")
                    winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Notification error: {e}")
                # Fallback to basic Windows message
                self.root.deiconify()
                messagebox.showinfo(title, message)
                self.root.withdraw()

    def get_user_input(self, prompt, default=""):
        if IS_MACOS:
            response = rumps.Window(prompt, "Input", default_text=default).run()
            return response.text if response.clicked else None
        else:
            if not self.root:
                self.root = tk.Tk()
            self.root.withdraw()
            
            # Force focus before showing dialog
            self.root.lift()
            self.root.attributes('-topmost', True)
            
            # Get user input
            result = simpledialog.askstring(
                "Input",
                prompt,
                initialvalue=default,
                parent=self.root
            )
            
            # Force focus after dialog appears
            self.root.after(100, self._force_dialog_focus)
            
            return result

    def _force_dialog_focus(self):
        # Find and focus the dialog
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel):
                widget.focus_force()
                # Find and focus the entry
                for child in widget.winfo_children():
                    if isinstance(child, tk.Entry):
                        child.focus_set()
                        child.select_range(0, tk.END)
                break

    def start_timer(self, _=None):
        if not self.is_running:
            # Reset previous session data
            self.reset_session()
            
            minutes = self.get_user_input("Enter duration (minutes):", "25")
            if minutes:
                try:
                    self.duration = timedelta(minutes=int(minutes))
                    activity = self.get_user_input("Enter activity name:", "Web Design")
                    if activity:
                        self.activity = activity
                        self.start_time = datetime.datetime.now()
                        self.end_time = self.start_time + self.duration
                        self.is_running = True
                        self.mode = 'timer'
                        self.paused_time = None
                        threading.Thread(target=self.update_timer, daemon=True).start()
                except ValueError:
                    self.show_notification("Error", "Please enter a valid number")

    def start_stopwatch(self, _=None):
        if not self.is_running:
            # Reset previous session data
            self.reset_session()
            
            activity = self.get_user_input("Enter activity name:", "Web Design")
            if activity:
                self.activity = activity
                self.start_time = datetime.datetime.now()
                self.is_running = True
                self.mode = 'stopwatch'
                self.paused_time = None
                threading.Thread(target=self.update_stopwatch, daemon=True).start()

    def reset_session(self):
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.paused_time = None
        self.elapsed_time = timedelta()
        if IS_MACOS:
            self.resume_button.hidden = True

    def stop(self, _=None):
        if self.is_running:
            self.is_running = False
            self.paused_time = datetime.datetime.now()
            self.update_icon_title("Paused")
            if IS_MACOS:
                self.resume_button.hidden = False
            self.show_notification(
                "Timer Paused",
                "Click 'Resume' to continue or 'Copy to Clipboard' to save current time",
                play_sound=False
            )

    def resume(self, _=None):
        if not self.is_running and self.paused_time:
            time_paused = datetime.datetime.now() - self.paused_time
            if self.mode == 'timer':
                # Check if timer was completed
                if self.end_time <= self.paused_time:
                    self.show_notification(
                        "Timer Complete",
                        "Cannot resume completed timer. Start a new session."
                    )
                    return
                # Adjust end time for remaining duration
                self.end_time += time_paused
            
            self.is_running = True
            if IS_MACOS:
                self.resume_button.hidden = True
            threading.Thread(target=self.update_timer if self.mode == 'timer' else self.update_stopwatch, daemon=True).start()

    def update_timer(self):
        while self.is_running and self.mode == 'timer':
            remaining = self.end_time - datetime.datetime.now()
            if remaining.total_seconds() <= 0:
                self.update_icon_title("00:00:00")
                self.is_running = False
                
                # Custom completion notification with sound
                title = "⌛ Timer Complete!"
                message = f"Your {self.activity} timer has ended! Great job!"
                
                self.show_notification(title, message, play_sound=True)
                break
            
            self.update_icon_title(str(remaining).split('.')[0])
            time.sleep(1)

    def update_stopwatch(self):
        while self.is_running and self.mode == 'stopwatch':
            elapsed = datetime.datetime.now() - self.start_time
            self.update_icon_title(str(elapsed).split('.')[0])
            time.sleep(1)

    def copy_format(self, _=None):
        if self.start_time:
            # Use current time if timer is still running
            end_time = self.paused_time if self.paused_time else datetime.datetime.now()
            
            # Calculate duration based on mode and status
            if self.mode == 'timer':
                if end_time - self.start_time >= self.duration:
                    duration = self.duration
                else:
                    duration = end_time - self.start_time
            else:
                duration = end_time - self.start_time
            
            # Format duration as HH:MM:SS
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Format start and end times
            start_time_str = self.start_time.strftime("%H:%M")
            end_time_str = end_time.strftime("%H:%M")
            
            formatted_text = f"{self.activity}:: {duration_str} | {start_time_str}-{end_time_str} | "
            pyperclip.copy(formatted_text)
            self.show_notification(
                "Copied!",
                "Time entry copied to clipboard",
                play_sound=False
            )

    def stop_app(self, _=None):
        self.is_running = False
        if not IS_MACOS:
            self.tray_icon.stop()
        else:
            rumps.quit_application()

    def run(self):
        if IS_MACOS:
            self.app.run()
        else:
            self.tray_icon.run()

if __name__ == "__main__":
    TimerApp().run()
