import os
import ctypes.util

def initialize_portaudio():
    # Set the path where we placed the PortAudio library
    lib_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'Resources', '_sounddevice_data', 'portaudio-binaries', 'libportaudio.2.dylib'
    )
    
    # Override ctypes.util.find_library for PortAudio
    original_find_library = ctypes.util.find_library
    def custom_find_library(name):
        if name == 'portaudio':
            return lib_path
        return original_find_library(name)
    
    ctypes.util.find_library = custom_find_library 