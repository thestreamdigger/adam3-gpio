import sys
import os
import argparse

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

os.chdir(PROJECT_ROOT)

from service.player_service import PlayerService
from core.signal_handler import SignalHandler
from utils.logger import Logger
from src.__version__ import __version__, __copyright__

log = Logger()

def print_banner() -> str:
    banner = f"""
 █████╗ ██████╗  █████╗ ███╗   ███╗██████╗ 
██╔══██╗██╔══██╗██╔══██╗████╗ ████║╚════██╗
███████║██║  ██║███████║██╔████╔██║ █████╔╝
██╔══██║██║  ██║██╔══██║██║╚██╔╝██║ ╚═══██╗
██║  ██║██████╔╝██║  ██║██║ ╚═╝ ██║██████╔╝
╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═════╝ 
                                                                       
ADAM3-GPIO
Version {__version__}
{__copyright__}
"""
    return banner

def main() -> None:
    parser = argparse.ArgumentParser(description='ADAM3-GPIO - GPIO controller service')
    parser.add_argument('--version', '-v', action='version', version=f'ADAM3-GPIO {__version__}')
    parser.add_argument('--no-wait-mpd', action='store_true',
                       help='Do not wait for MPD to be available (start immediately)')
    args = parser.parse_args()
    
    print(print_banner())
    
    player_service = None
    signal_handler = SignalHandler()
    
    try:
        log.wait("Initializing player service")
        player_service = PlayerService(no_wait_mpd=args.no_wait_mpd)
        signal_handler.register_cleanup(player_service.cleanup)
        log.ok("Player service is ready")
        player_service.start()
    except Exception as e:
        log.error(f"Service failed: {e}")
        if player_service:
            player_service.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
