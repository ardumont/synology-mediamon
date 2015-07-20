#!/usr/bin/env bash

set -x
HOST=${1-"syno"}

rexec="ssh $HOST"
rcp="scp -r"

$rexec mkdir -p /etc/mediamon /usr/local/bin
$rcp mediamon.py $HOST:/usr/local/bin/
$rcp S99mediamon.sh $HOST:/usr/syno/etc/rc.d/
$rcp .config/mediamon/mediamon.ini $HOST:/etc/mediamon/
