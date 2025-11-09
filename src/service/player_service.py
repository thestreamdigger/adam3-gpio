import time
import os
from typing import Dict, Any, Optional, Tuple
from src.core.config import Config
from src.core.mpd_client import MPDClient
from src.hardware.led.controller import LEDController
from src.hardware.display.tm1652 import TM1652
from src.hardware.button.controller import ButtonController
from src.utils.logger import Logger
from src.utils.paths import PROJECT_ROOT

log = Logger()

DISPLAY_MODES = {
    'ELAPSED': 'elapsed',
    'REMAINING': 'remaining'
}

class PlayerService:
    def __init__(self, no_wait_mpd: bool = False) -> None:
        log.debug("Initializing player service")
        self.config = Config()
        self.no_wait_mpd = no_wait_mpd

        mpd_config = self.config.get('mpd', {})
        self.mpd = MPDClient(
            host=mpd_config.get('host', 'localhost'),
            port=mpd_config.get('port', 6600)
        )

        log.info("Setting up hardware controllers...")
        self.led_controller = LEDController()

        self.display = TM1652()
        self.display.show_dashes()
        self.button_controller = ButtonController()


        effects_cfg = self.config.get('effects', {})
        self.effects_enabled = effects_cfg.get('enabled', True)
        self.effects_events = effects_cfg.get('events', {})

        self.running = False
        self.last_config_check = 0
        self.last_song_id = None
        self._playlist_cache = {}
        self._playlist_version = None

        log.info("Loading service configurations...")
        self._load_config()
        log.ok("Player service initialized")

    def _load_config(self) -> None:
        log.debug("Loading service configuration")
        self.display_mode = self.config.get('display.mode', DISPLAY_MODES['ELAPSED'])
        self.last_volume = None
        self.volume_display_until = 0
        self.default_update_interval = self.config.get('timing.update_interval', 0.5)
        self.volume_update_interval = self.config.get('timing.volume_update_interval', 0.1)
        self.stop_display_state = 0
        self.stop_state_changed_at = 0
        self.track_display_until = 0
        self._load_display_config()

    def _load_display_config(self) -> None:
        log.debug("Loading display configuration")
        self._load_stop_mode_config()
        self.pause_blink_interval = self.config.get('display.pause_mode.blink_interval', 1)
        track_cfg = self.config.get('display.play_mode.track_number', {})
        self.track_number_time = track_cfg.get('display_time', 2)

    def _load_stop_mode_config(self) -> None:
        self.stop_mode_times = {
            'symbol': self.config.get('display.stop_mode.stop_symbol_time', 2),
            'tracks': self.config.get('display.stop_mode.track_total_time', 2),
            'total': self.config.get('display.stop_mode.playlist_time', 2)
        }

    def _handle_config_update(self) -> None:
        log.info("Processing configuration update")
        
        self.display_mode = self.config.get('display.mode', DISPLAY_MODES['ELAPSED'])
        self._load_display_config()

        
        effects_cfg = self.config.get('effects', {})
        self.effects_enabled = effects_cfg.get('enabled', self.effects_enabled)
        self.effects_events = effects_cfg.get('events', self.effects_events)

        status = self.mpd.get_status()
        if status:
            self._update_display(status)

    def _get_event(self, name: str, defaults: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.effects_enabled:
            return None
        events = self.effects_events if isinstance(self.effects_events, dict) else {}
        value = events.get(name, True)
        if value is False:
            return None
        if value is True:
            return defaults.copy()
        if isinstance(value, dict):
            merged = defaults.copy()
            merged.update({k: v for k, v in value.items() if v is not None})
            return merged
        return None

    def _update_stop_display(self) -> None:
        current_time = time.time()

        current_duration = self.stop_mode_times.get(
            ['symbol', 'tracks', 'total'][self.stop_display_state],
            2
        )

        if current_time - self.stop_state_changed_at >= current_duration:
            self.stop_display_state = (self.stop_display_state + 1) % 3
            self.stop_state_changed_at = current_time
            log.debug(f"Stop display state changed to {self.stop_display_state}")

        status = self.mpd.get_status()
        if status:
            playlist_version = status.get('playlist', '0')

            if playlist_version != self._playlist_version:
                self._playlist_cache = self.mpd.get_playlist_info()
                self._playlist_version = playlist_version
                log.debug("Playlist cache updated")

        playlist_info = self._playlist_cache

        if self.stop_display_state == 0:
            self.display.show_dashes()
        elif self.stop_display_state == 1:
            self.display.show_track_total(playlist_info.get('total_tracks', 0))
        elif self.stop_display_state == 2:
            total_time = sum(
                float(track.get('duration', 0))
                for track in playlist_info.get('tracks', [])
            )
            minutes = int(total_time) // 60
            seconds = int(total_time) % 60
            self.display.show_time(minutes, seconds, True)

    def _check_track_change(self, status: Dict[str, Any]) -> None:
        song_id = status.get('songid', '0')

        track_config = self.config.get('display.play_mode.track_number', {})
        show_number = track_config.get('show_number', True)
        display_time = self.track_number_time

        if show_number and ((song_id and song_id != self.last_song_id) or
                          (not hasattr(self, '_last_state') or self._last_state != 'play')):

            current_song = self.mpd.get_current_song()
            if not current_song:
                return

            self.last_song_id = song_id
            track_number = current_song.get('track', '0')

            if track_number.isdigit():
                track_num = int(track_number)
                if 1 <= track_num <= 99:
                    log.debug(f"Track changed to {track_num}")
                    self.track_display_until = time.time() + display_time
                    self.display.show_track_number(track_num)

                    event = self._get_event(
                        'on_track_change',
                        {
                            "effect": "flash_active",
                            "repeat_count": 2,
                            "on_duration": 0.20,
                            "off_duration": 0.10,
                            "r": 0,
                            "g": 255,
                            "b": 0,
                        },
                    )
                    effect = (event or {}).get('effect')
                    if effect == 'flash_active':
                        self.led_controller.flash_active(
                            event.get('r', 0), event.get('g', 255), event.get('b', 0),
                            times=event.get('repeat_count'),
                            on_ms=int(round(event.get('on_duration') * 1000)),
                            off_ms=int(round(event.get('off_duration') * 1000))
                        )
                    elif effect == 'flash_all':
                        self.led_controller.flash_all(
                            event.get('r', 0), event.get('g', 255), event.get('b', 0),
                            times=event.get('repeat_count'),
                            on_ms=int(round(event.get('on_duration') * 1000)),
                            off_ms=int(round(event.get('off_duration') * 1000))
                        )

    def _convert_time_to_minutes_seconds(self, time_value: float) -> Tuple[Optional[int], Optional[int]]:
        try:
            time_float = float(time_value)
            minutes = int(time_float) // 60
            seconds = int(time_float) % 60
            return minutes, seconds
        except (ValueError, TypeError):
            return None, None

    def _calculate_display_time(self, elapsed_time: str, total_time: str) -> Tuple[Optional[int], Optional[int]]:
        try:
            if self.display_mode == DISPLAY_MODES['REMAINING'] and total_time != 'N/A':
                time_value = float(total_time) - float(elapsed_time)
            else:
                time_value = float(elapsed_time)

            return self._convert_time_to_minutes_seconds(time_value)
        except (ValueError, TypeError):
            return None, None

    def _update_pause_display(self, elapsed_time: str, total_time: str) -> None:
        phase = int(time.time() / self.pause_blink_interval) % 2

        if phase == 0:
            minutes, seconds = self._calculate_display_time(elapsed_time, total_time)
            if minutes is not None:
                self.display.show_time(minutes, seconds, True)
            else:
                self.display.show_dashes()
        else:
            self.display.clear()

    def _update_time_display(self, elapsed_time: str, total_time: str) -> None:
        minutes, seconds = self._calculate_display_time(elapsed_time, total_time)
        if minutes is not None:
            self.display.show_time(minutes, seconds, True)
        else:
            self.display.show_dashes()

    def _update_display(self, status: Dict[str, Any]) -> None:
        current_time = time.time()
        state = status.get('state', 'stop')

        if current_time < self.volume_display_until:
            current_volume = int(status.get('volume', '0'))
            self.display.show_volume(current_volume)
            return

        elapsed_time = status.get('elapsed', '0')
        total_time = status.get('duration', '0')

        if state == 'play':
            self._check_track_change(status)

            if current_time >= self.track_display_until:
                self._update_time_display(elapsed_time, total_time)

        elif state == 'pause':
            self._update_pause_display(elapsed_time, total_time)
        elif state == 'stop':
            if not hasattr(self, '_last_state') or self._last_state != 'stop':
                self.stop_display_state = 0
                self.stop_state_changed_at = current_time
            self._update_stop_display()

        self._last_state = state

    def show_volume(self, status: Dict[str, Any]) -> None:
        try:
            current_volume = int(status.get('volume', '0'))
            log.debug(f"Displaying volume: {current_volume}")
            self.display.show_volume(current_volume)
            duration_seconds = self.config.get('timing.volume_display_duration', 3)
            self.volume_display_until = time.time() + duration_seconds
            
        except (ValueError, TypeError):
            return

    def _check_config_updates(self) -> None:
        current_time = time.time()
        update_config = self.config.get('updates.trigger', {})
        check_interval = update_config.get('check_interval', 2)
        trigger_file = update_config.get('file', '.update_trigger')
        debounce_time = update_config.get('debounce_time', 0.1)

        if (current_time - self.last_config_check) >= check_interval:
            trigger_path = os.path.join(PROJECT_ROOT, 'config', trigger_file)

            try:
                os.stat(trigger_path)

                log.debug("Configuration update triggered")
                time.sleep(debounce_time)

                self.config.load_config()

                new_brightness = self.config.get('display.brightness')
                new_display_mode = self.config.get('display.mode')

                self.led_controller._setup_leds()

                if new_brightness != self.display._brightness:
                    self.display.update_brightness()

                if new_display_mode != self.display_mode:
                    log.debug("Updating display mode")
                    self.display_mode = new_display_mode
                    status = self.mpd.get_status()
                    if status:
                        self._update_display(status)

                os.unlink(trigger_path)
            except FileNotFoundError:
                pass
            except Exception as e:
                log.error(f"Config update check failed: {e}")
            finally:
                self.last_config_check = current_time

    def start(self) -> None:
        log.info("Starting player service")

        if not self.no_wait_mpd:
            if not self.mpd.wait_for_mpd():
                log.error("MPD connection failed")
                return
        else:
            log.info("MPD wait disabled")

        self.running = True
        next_update = time.time()

        try:
            while self.running:
                self._check_config_updates()

                status = self.mpd.get_status()
                if status:
                    self.led_controller.update_from_mpd_status(status)

                    current_volume = status.get('volume', '0')
                    if current_volume != self.last_volume:
                        self.show_volume(status)
                        self.last_volume = current_volume

                    self._update_display(status)

                current_time = time.time()
                update_interval = (self.volume_update_interval
                                 if current_time < self.volume_display_until
                                 else self.default_update_interval)

                next_update += update_interval
                sleep_time = next_update - time.time()

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    next_update = time.time()

        except Exception as e:
            log.error(f"Player service error: {e}")
            self.cleanup()

    def cleanup(self) -> None:
        log.info("Shutting down player service")
        self.running = False
        
        components = [
            ("Status LEDs", self.led_controller),
            ("Display TM1652", self.display),
            ("Button Controller", self.button_controller),
            ("MPD Client", self.mpd)
        ]
        
        for name, component in components:
            try:
                log.debug(f"Shutting down {name}")
                if hasattr(component, 'cleanup'):
                    component.cleanup()
                elif hasattr(component, 'close'):
                    component.close()
                log.debug(f"{name} shutdown complete")
            except Exception as e:
                log.error(f"Error shutting down {name}: {e}")
                continue
        
        time.sleep(0.3)
        
        log.ok("Player service shutdown complete")
