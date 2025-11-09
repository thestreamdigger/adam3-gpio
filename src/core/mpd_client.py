from mpd import MPDClient as BaseMPDClient
import time
import subprocess
import socket
from typing import Optional, Dict, Any
from src.utils.logger import Logger

log = Logger()

class MPDClient:
    def __init__(self, host: str = 'localhost', port: int = 6600) -> None:
        self.host = host
        self.port = port
        self._client = BaseMPDClient()
        self._connected = False
        self._last_try = 0
        self._retry_interval = 5
        log.debug(f"MPD client initialized for {host}:{port}")

    def connect(self) -> bool:
        current_time = time.time()
        if not self._connected and (current_time - self._last_try) >= self._retry_interval:
            try:
                log.wait("Attempting to connect to MPD...")
                self._client.connect(self.host, self.port)
                self._connected = True
                log.ok(f"Connected to MPD at {self.host}:{self.port}")
                return True
            except Exception:
                self._connected = False
                self._last_try = current_time
                log.error(f"Failed to connect to MPD at {self.host}:{self.port}")
        return self._connected

    def get_status(self) -> Optional[Dict[str, Any]]:
        try:
            if self.connect():
                status = self._client.status()
                log.debug(f"MPD status: {status}")
                return status
        except Exception:
            self._connected = False
            log.error("Failed to get MPD status")
        return None

    def get_current_song(self) -> Optional[Dict[str, Any]]:
        try:
            if self.connect():
                song = self._client.currentsong()
                log.debug(f"Current song: {song}")
                return song
        except Exception:
            self._connected = False
            log.error("Failed to get current song")
        return None

    def wait_for_mpd(self, max_attempts: int = 30, wait_interval: int = 2) -> bool:
        log.wait("Waiting for MPD...")
        
        for attempt in range(max_attempts):
            try:
                result = subprocess.run(['nc', '-z', '-w1', self.host, str(self.port)], 
                                      capture_output=True, timeout=3)
                if result.returncode == 0:
                    log.ok("MPD ready")
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    if sock.connect_ex((self.host, self.port)) == 0:
                        sock.close()
                        log.ok("MPD ready")
                        return True
                    sock.close()
                except Exception:
                    pass
            
            if attempt < max_attempts - 1:
                log.debug(f"MPD not ready, attempt {attempt + 1}/{max_attempts}, waiting {wait_interval}s...")
                time.sleep(wait_interval)
        
        log.error("MPD timeout after 60 seconds")
        return False

    def close(self) -> None:
        if self._connected:
            try:
                log.debug("Closing MPD connection")
                self._client.close()
                self._client.disconnect()
                log.ok("MPD connection closed")
            except Exception:
                log.error("Error closing MPD connection")
            finally:
                self._connected = False

    def get_playlist_info(self) -> Dict[str, Any]:
        try:
            if self.connect():
                status = self._client.status()
                playlist = self._client.playlistinfo()
                log.debug(f"Playlist info retrieved: {len(playlist)} tracks")
                return {
                    'total_tracks': int(status.get('playlistlength', 0)),
                    'tracks': playlist
                }
        except Exception:
            self._connected = False
            log.error("Failed to get playlist info")
        return {'total_tracks': 0, 'tracks': []}

