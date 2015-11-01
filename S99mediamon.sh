#!/bin/sh
# /usr/syno/etc/rc.d/S99mediamon.sh

PIDFILE=/var/run/mediamon.pid

case "$1" in
  start|"")
    #start the monitoring daemon
    python /usr/local/bin/mediamon.py
    ;;
  restart|reload|force-reload)
   echo "Error: argument '$1' not supported" >&2
   exit 3
   ;;
  status)
    [ -f $PIDFILE ] && echo "mediamon is running with pid `cat $PIDFILE`" || echo "mediamon not running."
    exit 0
    ;;
  stop)
    kill `cat $PIDFILE`
    ;;
  *)
    echo "Usage: S99mediamon.sh [start|stop|status]" >&2
    exit 3
    ;;
esac
