#!/bin/bash

PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.debug('Checking repeat state')
"

repeat_state=$(mpc status | grep -o 'repeat: on\|repeat: off')
if [[ $repeat_state == "repeat: on" ]]; then
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Disabling repeat mode')
    "
    mpc repeat off
else
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Enabling repeat mode')
    "
    mpc repeat on
fi

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.ok('Repeat state updated')
"
