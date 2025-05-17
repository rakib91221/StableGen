"""Install requirements in Blenders interpreter if not already installed."""
import sys
import subprocess
import bpy
import site

def install():
    """     
    Install pip and websocket-client in Blenders interpreter if not already installed.   
    :return: None     
    """
    python = sys.executable
    
    print('Installing websocket-client and websockets in Blender interpreter...')
    print('Python:', python)

    # Get directory for packages
    packages_dir = bpy.utils.user_resource('SCRIPTS', path='modules', create=True)
    if packages_dir not in sys.path:
        sys.path.append(packages_dir)
    site.addsitedir(packages_dir)

    try:
        import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
        import websockets
        import imageio
        import imageio_ffmpeg
        import cv2
    except ImportError or ModuleNotFoundError:
        subprocess.check_call([python, '-m', 'ensurepip'])
        subprocess.check_call([python, '-m', 'pip', 'install', '--upgrade', '--target', packages_dir, 'pip'])
        subprocess.check_call([python, '-m', 'pip', 'install', '--target', packages_dir, 'websocket-client'])
        subprocess.check_call([python, '-m', 'pip', 'install', '--target', packages_dir, 'websockets'])
        subprocess.check_call([python, '-m', 'pip', 'install', '--target', packages_dir, 'imageio'])
        subprocess.check_call([python, '-m', 'pip', 'install', '--target', packages_dir, 'imageio-ffmpeg'])
        subprocess.check_call([python, '-m', 'pip', 'install', '--target', packages_dir, 'opencv-python'])
