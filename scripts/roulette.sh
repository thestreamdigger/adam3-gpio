#!/bin/bash

PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.info('Starting random mode...')
"

mpc repeat off
mpc single off
mpc random off
mpc consume on

sudo pkill -f ashuffle
mpc clear
ashuffle &

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.ok('Random mode activated')
"
