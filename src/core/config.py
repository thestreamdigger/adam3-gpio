import json
import os
from typing import Any, Optional
from src.utils.logger import Logger

log = Logger()

class Config:
    _instance = None

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self.initialized:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.config_path = os.path.join(base_path, 'config', 'settings.json')
            self.load_config()
            log.configure(self.config)
            self.initialized = True

    def load_config(self) -> None:
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            log.error(f"Config load failed: {e}")
            self.config = {}

    def get(self, key: str, default: Any = None) -> Any:
        value = self.config
        for k in key.split('.'):
            value = value.get(k) if isinstance(value, dict) else None
            if value is None:
                return default
        return value

