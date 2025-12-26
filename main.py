from app_launcher import FixedAppLauncher
import sys
if __name__ == '__main__':
    launcher = FixedAppLauncher()
    sys.exit(launcher.launch())