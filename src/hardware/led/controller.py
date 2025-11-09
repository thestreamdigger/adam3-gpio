from rpi_ws281x import PixelStrip, Color
import threading
import time
from typing import Dict, Any
from src.core.config import Config
from src.utils.logger import Logger

log = Logger()

class LEDController:
    def __init__(self) -> None:
        self.config = Config()
        
        status_leds_config = self.config.get('gpio.status_leds', {})
        pin = status_leds_config.get('pin', 21)
        count = status_leds_config.get('count', 4)
        color_order = status_leds_config.get('order', 'GRB')
        
        import rpi_ws281x as ws
        color_order_map = {
            'RGB': ws.WS2811_STRIP_RGB,
            'GRB': ws.WS2811_STRIP_GRB,
            'BGR': ws.WS2811_STRIP_BGR,
            'BRG': ws.WS2811_STRIP_BRG,
            'GBR': ws.WS2811_STRIP_GBR,
            'RBG': ws.WS2811_STRIP_RBG
        }
        
        self.strip = PixelStrip(count, pin, strip_type=color_order_map.get(color_order, ws.WS2811_STRIP_GRB))
        self.strip.begin()
        
        self.led_map = {
            'repeat': 0,
            'random': 1,
            'single': 2,
            'consume': 3
        }
        
        self.brightness = max(0, min(255, int(status_leds_config.get('brightness', 32))))
        self._last_status = {}
        self._animation_lock = threading.Lock()

        self.all_off()
        log.ok("Status LEDs initialized")

    def _setup_leds(self) -> None:
        try:
            old_brightness = self.brightness
            configured_brightness = int(self.config.get('gpio.status_leds.brightness', self.brightness))
            self.brightness = max(0, min(255, configured_brightness))
            log.debug(f"Status LEDs brightness set to {self.brightness}/255")

            if old_brightness != self.brightness:
                self._update_leds(self._last_status)

        except Exception as e:
            log.error(f"Status LEDs setup failed: {e}")
            self.brightness = 32

    def _update_leds(self, state_map: Dict[str, bool]) -> None:
        try:
            for led_name, is_on in state_map.items():
                led_index = self.led_map[led_name]
                color = Color(0, 0, self.brightness) if is_on else Color(0, 0, 0)
                self.strip.setPixelColor(led_index, color)
            self.strip.show()
        except Exception as e:
            log.error(f"LED update failed: {e}")

    def update_from_mpd_status(self, status: Dict[str, Any]) -> None:
        if not status:
            return

        try:
            state_map = {
                'repeat': status.get('repeat', '0') == '1',
                'random': status.get('random', '0') == '1',
                'single': status.get('single', '0') == '1',
                'consume': status.get('consume', '0') == '1'
            }

            if state_map != self._last_status:
                self._last_status = state_map
                self._update_leds(state_map)
        except Exception as e:
            log.error(f"MPD status update failed: {e}")

    def all_off(self) -> None:
        try:
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()
            self._last_status = {}
        except Exception as e:
            log.error(f"LED all_off failed: {e}")

    def cleanup(self) -> None:
        try:
            self.all_off()
            self.strip = None
        except Exception as e:
            log.error(f"LED cleanup failed: {e}")
  
    def _run_one_shot(self, effect_fn) -> None:
        if not self._animation_lock.acquire(blocking=False):
            return

        def _worker() -> None:
            try:
                effect_fn()
            finally:
                self._update_leds(self._last_status)
                self._animation_lock.release()

        threading.Thread(target=_worker, daemon=True).start()

    def _rgb(self, r: int, g: int, b: int) -> Color:
        scale = max(0, min(255, self.brightness)) / 255.0 if self.brightness else 0.0
        sr = int(max(0, min(255, r)) * scale)
        sg = int(max(0, min(255, g)) * scale)
        sb = int(max(0, min(255, b)) * scale)
        return Color(sr, sg, sb)

    def flash_all(self, r: int, g: int, b: int, times: int = 1, on_ms: int = 150, off_ms: int = 120) -> None:
        def run() -> None:
            for _ in range(max(1, times)):
                for i in range(self.strip.numPixels()):
                    self.strip.setPixelColor(i, self._rgb(r, g, b))
                self.strip.show()
                time.sleep(max(0, on_ms) / 1000.0)

                for i in range(self.strip.numPixels()):
                    self.strip.setPixelColor(i, self._rgb(0, 0, 0))
                self.strip.show()
                time.sleep(max(0, off_ms) / 1000.0)

        self._run_one_shot(run)

    def flash_active(self, r: int, g: int, b: int, times: int = 1, on_ms: int = 150, off_ms: int = 120) -> None:
        def run() -> None:
            active_indices = [self.led_map[name] for name, is_on in self._last_status.items() if is_on]
            base_on_color = Color(0, 0, self.brightness)

            if not active_indices:
                first = 0
                for _ in range(max(1, times)):
                    self.strip.setPixelColor(first, self._rgb(r, g, b))
                    self.strip.show()
                    time.sleep(max(0, on_ms) / 1000.0)

                    self.strip.setPixelColor(first, self._rgb(0, 0, 0))
                    self.strip.show()
                    time.sleep(max(0, off_ms) / 1000.0)
                return

            for _ in range(max(1, times)):
                for i in active_indices:
                    self.strip.setPixelColor(i, self._rgb(r, g, b))
                self.strip.show()
                time.sleep(max(0, on_ms) / 1000.0)

                for i in active_indices:
                    self.strip.setPixelColor(i, base_on_color)
                self.strip.show()
                time.sleep(max(0, off_ms) / 1000.0)

        self._run_one_shot(run)

    

