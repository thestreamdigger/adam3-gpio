#!/bin/bash
python3 -c "
from src.utils.logger import Logger
log = Logger()
log.debug('Checking service status')
"

SERVICE="adam3-gpio.service"

check_service_status() {
    sudo systemctl is-active --quiet "$1"
    return $?
}

check_service_status "$SERVICE"
SERVICE_STATUS=$?

if [ $SERVICE_STATUS -eq 0 ]; then
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Stopping service')
    "
    sudo systemctl stop "$SERVICE"
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.ok('Service stopped')
    "
else
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Starting service')
    "
    sudo systemctl start "$SERVICE"
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.ok('Service started')
    "
fi
