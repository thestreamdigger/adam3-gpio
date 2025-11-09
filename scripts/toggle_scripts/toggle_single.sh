#!/bin/bash

PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.debug('Checking single state')
"

single_state=$(mpc status | grep -o 'single: on\|single: off')
if [[ $single_state == "single: on" ]]; then
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Disabling single mode')
    "
    mpc single off
else
    python3 -c "
    from src.utils.logger import Logger
    log = Logger()
    log.info('Enabling single mode')
    "
    mpc single on
fi

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.ok('Single state updated')
"
