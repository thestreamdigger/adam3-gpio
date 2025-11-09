#!/bin/bash

PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.debug('Checking random state')
"

random_state=$(mpc status | grep -o 'random: on\|random: off')
if [[ $random_state == "random: on" ]]; then
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Disabling random mode')
    "
    mpc random off
else
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Enabling random mode')
    "
    mpc random on
fi

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.ok('Random state updated')
"
