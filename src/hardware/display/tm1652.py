import serial
import time
from typing import Union, List
from src.core.config import Config
from src.utils.logger import Logger

log = Logger()

class TM1652:
    CMD_WRITE_DATA = 0x08
    CMD_SET_BRIGHTNESS = 0x18
    CMD_BRIGHTNESS_BASE = 0x10
    
    CHAR_MAP = {
        '0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F, '4': 0x66,
        '5': 0x6D, '6': 0x7D, '7': 0x07, '8': 0x7F, '9': 0x6F,
        '-': 0x40, ' ': 0x00
    }
    
    COLON_BIT = 0x80
    
    def __init__(self) -> None:
        self.config = Config()
        self.ser = None
        self._connection_retry_count = 0
        self._max_retries = 3
        self._retry_delay = 0.5
        self._last_retry_time = 0
        
        display_config = self.config.get('gpio.display', {})
        self.serial_port = display_config.get('serial_port', '/dev/ttyAMA0')
        self.baudrate = display_config.get('baudrate', 19200)
        
        self._connect_serial()
        self._brightness = self.config.get('display.brightness', 4)
        self._set_brightness_internal(self._brightness)
        log.ok("TM1652 initialized")

    def _connect_serial(self) -> bool:
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                
            current_time = time.time()
            if current_time - self._last_retry_time < self._retry_delay:
                time.sleep(self._retry_delay - (current_time - self._last_retry_time))
            
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=8,
                parity=serial.PARITY_ODD,
                stopbits=1,
                timeout=0.1
            )
            
            self.ser.flush()
            time.sleep(0.1)
            
            log.ok(f"Connected to serial port {self.serial_port}")
            self._connection_retry_count = 0
            return True
            
        except Exception as e:
            self._connection_retry_count += 1
            self._last_retry_time = time.time()
            log.error(f"Failed to connect to serial port {self.serial_port} (attempt {self._connection_retry_count}): {e}")
            
            if self._connection_retry_count >= self._max_retries:
                log.error("Max connection retries reached. Display may not function correctly.")
                return False
            return False

    def _reverse_4_bits(self, n: int) -> int:
        bits = f"{n:04b}"
        return int(bits[::-1], 2)

    def _write_command(self, data: bytearray) -> None:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if not self.ser or not self.ser.is_open:
                    if not self._connect_serial():
                        return

                self.ser.write(data)
                self.ser.flush()
                time.sleep(0.002)
                return

            except Exception as e:
                log.error(f"Failed to write to serial port (attempt {attempt + 1}): {e}")

                if attempt < max_attempts - 1:
                    self._connect_serial()
                    time.sleep(0.05)
                else:
                    log.error("Failed to write after all attempts")

    def _set_brightness_internal(self, brightness: int) -> None:
        try:
            brightness = max(1, min(8, brightness))
            send = bytearray([
                self.CMD_SET_BRIGHTNESS,
                self.CMD_BRIGHTNESS_BASE | (self._reverse_4_bits(brightness - 1) & 0x0F)
            ])
            self._write_command(send)
        except Exception as e:
            log.error(f"Display brightness internal set failed: {e}")

    def update_brightness(self) -> None:
        try:
            new_brightness = self.config.get('display.brightness', 4)
            if new_brightness != self._brightness:
                self._brightness = new_brightness
                self._set_brightness_internal(self._brightness)
        except Exception as e:
            log.error(f"Display brightness update failed: {e}")

    def _write_segments(self, segments: List[int], colon: bool = False) -> None:
        try:
            send = bytearray([self.CMD_WRITE_DATA])
            for i, seg in enumerate(segments[:4]):
                if colon and i == 1:
                    seg |= self.COLON_BIT
                send.append(seg)
            self._write_command(send)
        except Exception as e:
            log.error(f"Display segments write failed: {e}")

    def show_number(self, number: Union[int, float], colon: bool = False) -> None:
        try:
            number = max(-999, min(9999, int(number)))
            digits = f"{abs(number):04d}"
            segments = []
            
            if number < 0:
                segments.append(self.CHAR_MAP['-'])
                digits = digits[1:]
            
            segments.extend(self.CHAR_MAP[d] for d in digits)
            self._write_segments(segments, colon)
        except Exception as e:
            log.error(f"Display show_number failed: {e}")

    def show_time(self, minutes: int, seconds: int, colon: bool = True) -> None:
        try:
            minutes = max(0, min(99, int(minutes)))
            seconds = max(0, min(59, int(seconds)))
            segments = [
                self.CHAR_MAP[str(minutes // 10)],
                self.CHAR_MAP[str(minutes % 10)],
                self.CHAR_MAP[str(seconds // 10)],
                self.CHAR_MAP[str(seconds % 10)]
            ]
            self._write_segments(segments, colon)
        except Exception as e:
            log.error(f"Display show_time failed: {e}")

    def show_track_number(self, number: int) -> None:
        try:
            number = max(1, min(99, int(number)))
            num_str = f"{number:02d}"
            segments = [
                self.CHAR_MAP['-'],
                self.CHAR_MAP[num_str[0]],
                self.CHAR_MAP[num_str[1]],
                self.CHAR_MAP['-']
            ]
            self._write_segments(segments, False)
        except Exception as e:
            log.error(f"Display show_track_number failed: {e}")

    def show_track_total(self, count: int) -> None:
        try:
            count = max(0, min(99, int(count)))
            segments = [
                self.CHAR_MAP[str(count // 10)],
                self.CHAR_MAP[str(count % 10)],
                self.CHAR_MAP['-'],
                self.CHAR_MAP['-']
            ]
            self._write_segments(segments, False)
        except Exception as e:
            log.error(f"Display show_track_total failed: {e}")

    def show_volume(self, number: Union[int, str]) -> None:
        try:
            number = max(0, min(100, int(number)))
            if number == 100:
                segments = [
                    self.CHAR_MAP['-'],
                    self.CHAR_MAP['1'],
                    self.CHAR_MAP['0'],
                    self.CHAR_MAP['0']
                ]
            else:
                num_str = f"{number:02d}"
                segments = [
                    self.CHAR_MAP['-'],
                    self.CHAR_MAP['-'],
                    self.CHAR_MAP[num_str[0]],
                    self.CHAR_MAP[num_str[1]]
                ]
            self._write_segments(segments, False)
        except Exception as e:
            log.error(f"Display show_volume failed: {e}")

    def show_dashes(self) -> None:
        try:
            self._write_segments([self.CHAR_MAP['-']] * 4, False)
        except Exception as e:
            log.error(f"Display show_dashes failed: {e}")

    def clear(self) -> None:
        try:
            self._write_segments([0, 0, 0, 0], False)
        except Exception as e:
            log.error(f"Display clear failed: {e}")
    
    def force_off(self) -> None:
        try:
            if self.ser and self.ser.is_open:
                self._set_brightness_internal(1)
                time.sleep(0.1)
                for _ in range(3):
                    self.clear()
                    time.sleep(0.05)
                self.ser.flush()
        except Exception as e:
            log.error(f"Display force_off failed: {e}")

    def cleanup(self) -> None:
        try:
            self.force_off()
            time.sleep(0.2)
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = None
        except Exception as e:
            log.error(f"Display cleanup failed: {e}")
