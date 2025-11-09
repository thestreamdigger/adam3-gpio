#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import Logger
from src.core.config import Config

log = Logger()
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config', 'settings.json')

def toggle_brightness() -> None:
    try:
        config = Config()
        
        log.debug("Reading current brightness configuration")
        if not os.path.exists(CONFIG_FILE):
            raise FileNotFoundError("Configuration file not found")
            
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            
        display_config = data.get('display', {})
        current_display_brightness = display_config.get('brightness', 6)
        
        brightness_levels = display_config.get('brightness_levels', {})
        display_levels = brightness_levels.get('display', [3, 6, 8])
        led_levels = brightness_levels.get('led', [8, 16, 32])
        
        try:
            current_index = display_levels.index(current_display_brightness)
        except ValueError:
            current_index = 0
        
        next_index = (current_index + 1) % len(display_levels)
        
        new_display_brightness = display_levels[next_index]
        new_led_brightness = led_levels[next_index]
        
        if 'display' not in data:
            data['display'] = {}
        data['display']['brightness'] = new_display_brightness
        
        if 'gpio' not in data:
            data['gpio'] = {}
        if 'status_leds' not in data['gpio']:
            data['gpio']['status_leds'] = {}
        data['gpio']['status_leds']['brightness'] = new_led_brightness
        
        temp_file = Path(CONFIG_FILE).with_suffix('.json.tmp')
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        os.replace(temp_file, CONFIG_FILE)
        
        trigger_file = os.path.join(PROJECT_ROOT, 'config', '.update_trigger')
        Path(trigger_file).touch()
        
        log.ok(f"Brightness set to level {next_index + 1} (Display: {new_display_brightness}, LEDs: {new_led_brightness})")
            
    except Exception as e:
        log.error(f"Failed to toggle brightness: {e}")
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        sys.exit(1)

if __name__ == "__main__":
    toggle_brightness()
