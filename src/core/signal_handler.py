from src.utils.logger import Logger
from typing import Callable
import signal
import sys
import time
import subprocess

log = Logger()

class SignalHandler:
    _instance = None
    
    def __new__(cls) -> 'SignalHandler':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cleanup_callbacks = []
            cls._instance._initialized = False
            cls._instance._shutdown_in_progress = False
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._setup_signals()
            self._initialized = True

    def _setup_signals(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        log.debug("Signal handlers initialized")

    def register_cleanup(self, callback: Callable) -> None:
        if callback not in self._cleanup_callbacks:
            self._cleanup_callbacks.append(callback)
            log.debug(f"Registered cleanup: {callback.__name__}")

    def _handle_shutdown(self, signum: int, frame) -> None:
        if self._shutdown_in_progress:
            return
        
        self._shutdown_in_progress = True
        signal_name = signal.Signals(signum).name
        log.info(f"Received signal: {signal_name}")
        
        try:
            log.info("Stopping audio playback...")
            subprocess.run(["mpc", "stop"], check=True, timeout=2)
            time.sleep(1.0)
        except Exception as e:
            log.error(f"Error stopping audio: {e}")
        
        for i, callback in enumerate(reversed(self._cleanup_callbacks)):
            try:
                log.debug(f"Executing cleanup {i+1}/{len(self._cleanup_callbacks)}: {callback.__name__}")
                callback()
                log.debug(f"Cleanup {callback.__name__} completed")
            except Exception as e:
                log.error(f"Cleanup error in {callback.__name__}: {e}")
                continue
        
        log.debug("Waiting for hardware shutdown...")
        time.sleep(0.5)
        
        if signum == signal.SIGINT:
            log.ok("Cleanup complete. Powering off system.")
            try:
                log.info("Initiating system poweroff...")
                subprocess.run(["poweroff"], check=True)
            except Exception as e:
                log.error(f"Failed to power off system: {e}")
                sys.exit(1)
            sys.exit(0)
        else:
            log.ok("Cleanup complete. Exiting service without poweroff.")
            sys.exit(0)