from typing import Dict, Any

class Logger:
    LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "WAIT": 21, "OK": 22}
    _instance = None

    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.enabled = True
            cls._instance.level = "INFO"
            cls._instance.format = "[{level}] {message}"
        return cls._instance

    def configure(self, settings: Dict[str, Any]) -> None:
        log_cfg = settings.get('logging', {})
        self.enabled = log_cfg.get('enable', True)
        self.level = log_cfg.get('level', 'INFO').upper()
        self.format = log_cfg.get('format', '[{level}] {message}')

    def _log(self, level: str, message: str) -> None:
        if self.enabled and self.LEVELS[self.level] <= self.LEVELS[level]:
            print(self.format.format(level=level, message=message))

    def debug(self, message: str) -> None: self._log("DEBUG", message)
    def info(self, message: str) -> None: self._log("INFO", message)
    def wait(self, message: str) -> None: self._log("WAIT", message)
    def ok(self, message: str) -> None: self._log("OK", message)
    def warning(self, message: str) -> None: self._log("WARNING", message)
    def error(self, message: str) -> None: self._log("ERROR", message)

