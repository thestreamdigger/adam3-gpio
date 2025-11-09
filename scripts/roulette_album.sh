#!/bin/bash

PROJECT_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.info('Starting album random mode...')
"

mpc consume off

sudo pkill -f ashuffle
mpc clear
ashuffle --group-by album &

python3 -c "
from src.utils.logger import Logger
log = Logger()
log.ok('Album random mode activated')
" 