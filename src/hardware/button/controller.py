import os
import time
import subprocess
import signal

from gpiozero import Button
from src.core.config import Config
from src.utils.logger import Logger
from src.utils.paths import PROJECT_ROOT

log = Logger()

class ButtonController:
    def __init__(self) -> None:
        self.config = Config()
        self.last_command_time = 0
        self.press_start_time = None
        
        self.command_cooldown = self.config.get('timing.command_cooldown', 0.5)
        self.long_press_time = self.config.get('timing.long_press_time', 2)
        
        button_pin = self.config.get('gpio.button', 20)
        self.button = Button(button_pin, pull_up=True, bounce_time=0.1)
        self.button.when_pressed = self._on_press
        self.button.when_released = self._on_release
        
        log.ok("Button initialized")

    def _on_press(self) -> None:
        self.press_start_time = time.time()

    def _on_release(self) -> None:
        if self.press_start_time is None:
            return

        press_duration = time.time() - self.press_start_time
        self.press_start_time = None
        
        current_time = time.time()
        if (current_time - self.last_command_time) < self.command_cooldown:
            return
        
        if press_duration >= self.long_press_time:
            self._execute_long_press()
        else:
            self._execute_short_press()

    def _execute_short_press(self) -> None:
        self.last_command_time = time.time()
        script_path = self.config.get('paths.roulette', 'scripts/roulette.sh')
        full_script_path = os.path.join(PROJECT_ROOT, script_path)
        
        if os.path.exists(full_script_path):
            subprocess.run(['sudo', full_script_path], check=True)

    def _execute_long_press(self) -> None:
        self.last_command_time = time.time()
        os.kill(os.getpid(), signal.SIGINT)

    def cleanup(self) -> None:
        if self.button:
            self.button.close()
            self.button = None
