#!/bin/bash

PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.debug('Checking consume state')
"

consume_state=$(mpc status | grep -o 'consume: on\|consume: off')
if [[ $consume_state == "consume: on" ]]; then
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Disabling consume mode')
    "
    mpc consume off
else
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Enabling consume mode')
    "
    mpc consume on
fi

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.ok('Consume state updated')
"
