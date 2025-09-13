import undetected_chromedriver as uc
import time
import pathlib
import os
import sys
import stat
import traceback
from selenium.common.exceptions import WebDriverException

STDIN = None
STDOUT = None
STDERR = None

# --- Configuration for Yolks Environment ---
# The path for the Chrome user profile. In a containerized environment,
# it's best to use a relative path to ensure data is stored within the
# container's accessible directory. The 'yolks' environment typically
# mounts the home directory, so this path is safe.
USER_PROFILE_PATH = pathlib.Path("./chrome_profile/")

# The URL you want to connect to.
TARGET_URL = ""

# Idle time in seconds after the page loads.
IDLE_TIME_SECONDS = 60

# Set the path to your Chrome browser executable.
# This is a common path for portable Chrome installations.
CHROME_BINARY_PATH = "./chrome/chrome"

# Set the LD_LIBRARY_PATH once, outside the main loop.
# This prevents the path from being appended repeatedly.
# Include both the chrome directory and the libs directory
chrome_lib_path = os.path.join(os.getcwd(), 'chrome')
libs_path = os.path.join(os.getcwd(), 'libs')
current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
if STDIN != None:
    sys.stdin = open(STDIN, "r")
if STDOUT != None:
    sys.stdout = open(STDOUT, "w")
if STDERR != None:
    sys.stderr = open(STDERR, "w")

# Build the new LD_LIBRARY_PATH with both directories
if current_ld_path:
    os.environ['LD_LIBRARY_PATH'] = f"{libs_path}:{chrome_lib_path}:{current_ld_path}"
else:
    os.environ['LD_LIBRARY_PATH'] = f"{libs_path}:{chrome_lib_path}"

def run_session(is_headless: bool):
    """
    Runs a single browser session, navigating to a URL and idling.
    
    Args:
        is_headless (bool): If True, the browser will run in headless mode.
    """
    # Convert to absolute path to avoid issues with undetected_chromedriver
    chrome_binary_abs = os.path.abspath(CHROME_BINARY_PATH)
    
    # Verify the Chrome binary path exists
    if not os.path.exists(chrome_binary_abs):
        print(f"Error: Chrome binary not found at '{chrome_binary_abs}'. Please ensure the path is correct.", file=sys.stderr)
        return

    # Make the Chrome binary executable if it's not already.
    try:
        os.chmod(chrome_binary_abs, os.stat(chrome_binary_abs).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError as e:
        print(f"Warning: Could not set executable permissions: {e}", file=sys.stderr)

    options = uc.ChromeOptions()
    
    # Set the binary location in ChromeOptions (this is crucial)
    options.binary_location = chrome_binary_abs
    
    # Essential options for containerized environments
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-background-networking")
    
    # Use absolute path for the user data directory
    user_data_abs = os.path.abspath(USER_PROFILE_PATH)
    options.add_argument(f"--user-data-dir={user_data_abs}")

    # Set the headless state for the current session
    if is_headless:
        options.add_argument("--headless=new")  # Use new headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--single-process')  # This can help with resource constraints

    driver = None
    try:
        print(f"Starting browser session (headless: {is_headless})...")
        print(f"Using Chrome binary: {chrome_binary_abs}")
        
        # Try to create the driver with explicit version management disabled
        # This can help avoid version conflicts
        driver = uc.Chrome(
            options=options,
            version_main=None,  # Let it auto-detect
            driver_executable_path=None  # Let it auto-download/find chromedriver
        )
        
        print(f"Browser started successfully")
        print(f"Navigating to: {TARGET_URL}")
        driver.get(TARGET_URL)
        print(f"Connected to '{TARGET_URL}' and idling for {IDLE_TIME_SECONDS} seconds...")
        
        # Wait for the specified idle time before closing.
        time.sleep(IDLE_TIME_SECONDS)
        
        print("Idling complete.")
    
    except WebDriverException as e:
        print(f"WebDriver error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
    finally:
        if driver:
            try:
                print("Closing the browser.")
                driver.quit()
            except Exception as e:
                print(f"Error closing driver: {e}", file=sys.stderr)

def verify_chrome_installation():
    """Verify that Chrome is properly installed and accessible."""
    chrome_binary_abs = os.path.abspath(CHROME_BINARY_PATH)
    libs_abs = os.path.abspath('./libs')
    
    # Check if Chrome binary exists
    if not os.path.exists(chrome_binary_abs):
        print(f"Chrome binary not found at: {chrome_binary_abs}")
        return False
    
    # Check if libs directory exists
    if not os.path.exists(libs_abs):
        print(f"Libs directory not found at: {libs_abs}")
        return False
    
    # Check if Chrome binary is executable
    if not os.access(chrome_binary_abs, os.X_OK):
        print(f"Chrome binary is not executable: {chrome_binary_abs}")
        return False
    
    print(f"Chrome binary found at: {chrome_binary_abs}")
    print(f"Libs directory found at: {libs_abs}")
    print(f"Current LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'Not set')}")
    
    # Test if Chrome can actually run
    try:
        import subprocess
        
        # Set up environment for subprocess
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH']
        
        result = subprocess.run([chrome_binary_abs, '--version'], 
                              capture_output=True, text=True, timeout=10, env=env)
        if result.returncode == 0:
            print(f"Chrome version: {result.stdout.strip()}")
            print(f"Chrome binary verified successfully!")
            return True
        else:
            print(f"Chrome failed to run. Return code: {result.returncode}")
            print(f"Error output: {result.stderr}")
            
            # Try to get more detailed error info
            if result.stderr:
                if "error while loading shared libraries" in result.stderr:
                    print("Missing shared libraries detected. Checking dependencies...")
                    # Try ldd to see what's missing
                    try:
                        ldd_result = subprocess.run(['ldd', chrome_binary_abs], 
                                                  capture_output=True, text=True, timeout=5, env=env)
                        if ldd_result.returncode == 0:
                            print("Dependencies check:")
                            for line in ldd_result.stdout.splitlines():
                                if "not found" in line:
                                    print(f"MISSING: {line}")
                                elif "=>" in line:
                                    print(f"OK: {line}")
                    except Exception as e:
                        print(f"Could not run ldd: {e}")
            return False
    except subprocess.TimeoutExpired:
        print("Chrome version check timed out")
        return False
    except FileNotFoundError:
        print("Chrome binary not found when trying to execute")
        return False
    except Exception as e:
        print(f"Error testing Chrome binary: {e}")
        return False

if __name__ == "__main__":
    print("=== Chrome Automation Script Starting ===")
    print(f"Working directory: {os.getcwd()}")
    print(f"Chrome binary path: {os.path.abspath(CHROME_BINARY_PATH)}")
    print(f"Libs directory: {os.path.abspath('./libs')}")
    print(f"LD_LIBRARY_PATH set to: {os.environ['LD_LIBRARY_PATH']}")
    print()
    
    # Verify Chrome installation before starting
    if not verify_chrome_installation():
        print("Chrome installation verification failed. Exiting.", file=sys.stderr)
        print("\nTroubleshooting tips:", file=sys.stderr)
        print("1. Check if Chrome binary exists: ls -la ./chrome/chrome", file=sys.stderr)
        print("2. Check if libs directory exists: ls -la ./libs", file=sys.stderr)
        print("3. Check dependencies: ldd ./chrome/chrome", file=sys.stderr)
        print("4. Try running Chrome directly: LD_LIBRARY_PATH=./libs:./chrome:$LD_LIBRARY_PATH ./chrome/chrome --version", file=sys.stderr)
        print("5. Make sure all .so files are in ./libs directory", file=sys.stderr)
        sys.exit(1)
    
    # Ensure the user profile directory exists before starting.
    # This prevents the script from failing on the first run.
    if not USER_PROFILE_PATH.exists():
        USER_PROFILE_PATH.mkdir(parents=True)
        print(f"Created directory: {USER_PROFILE_PATH}")
    
    print("All checks passed. Starting automation script...")

    # The main loop for continuous operation.
    try:
        while True:
            run_session(is_headless=True)
            
            print("\n--- Cycle complete. Waiting 10 seconds before next cycle. ---")
            time.sleep(10)
            print("\n--- Starting next cycle ---")
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error in main loop: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)