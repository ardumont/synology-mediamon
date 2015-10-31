# /root/mediamon.py
from datetime import datetime

import ConfigParser
import os.path
import pyinotify
import signal
import sys

from datetime import datetime
from subprocess import call

CONFIG_PATH = '/etc/mediamon/mediamon.ini'

CONFIG_DEFAULT = {
    'logfile': '/var/log/mediamon.log',
    'pidfile': '/var/run/mediamon.pid',
    'watched_paths': '/volume1/music /volume1/photo /volume1/video',
    'allowed_exts': 'jpg jpeg png tga gif bmp mp3 flac aac wma ogg ogv '
                    'mp4 avi m4v'
}

def read_configuration(config_path=None):
    # read from file or set the default configuration file
    if config_path and os.path.exists(config_path):
        # Expects an optional config_path configuration file of the form:
        # [main]
        #
        # logging file
        # logfile = /var/log/mediamon.log
        #
        # pid file
        # pidfile = /var/run/mediamon.pid
        #
        # list of space separated paths to watch
        # watched_paths = /volume1/techconf /volume1/musics /volume1/pix
        #
        # list of space separated allowed extensions
        # allowed_exts = jpg png gif bmp mp3 flac aac wma ogg ogv mp4 avi m4v

        confparser = ConfigParser.ConfigParser()
        confparser.read(config_path)
        config = confparser._sections['main']
    else:  # default one based on original code
        config = CONFIG_DEFAULT

    config['watched_paths'] = config['watched_paths'].split(' ')
    config['allowed_exts'] = set(config['allowed_exts'].split(' '))

    return config

config = read_configuration(CONFIG_PATH)

watched_paths = config['watched_paths']
allowed_exts = config['allowed_exts']

log_file = open(config['logfile'], "a")


def log(text):
    dt = datetime.utcnow().isoformat()
    log_file.write(''.join([dt, ' - ', text, '\n']))
    log_file.flush()


def signal_handler(signal, frame):
    log("Exiting")
    sys.exit(0)


log("Starting")

signal.signal(signal.SIGTERM, signal_handler)

wm = pyinotify.WatchManager()
mask = (
    pyinotify.IN_MODIFY |
    pyinotify.IN_CLOSE_WRITE |
    pyinotify.IN_DELETE |
    pyinotify.IN_CREATE |
    pyinotify.IN_MOVED_TO |
    pyinotify.IN_MOVED_FROM
)


class EventHandler(pyinotify.ProcessEvent):
    def __init__(self):
        self.modified_files = set()

    def process_IN_CREATE(self, event):
        self.process_create(event)

    def process_IN_MOVED_TO(self, event):
        self.process_create(event)

    def process_IN_MOVED_FROM(self, event):
        self.process_delete(event)

    def process_IN_DELETE(self, event):
        self.process_delete(event)

    def process_create(self, event):
        arg = ''
        if event.dir:
            arg = "-A"
        else:
            arg = "-a"
        self.do_index_command(event, arg)

    def process_delete(self, event):
        arg = ''
        if event.dir:
            arg = "-D"
        else:
            arg = "-d"
        self.do_index_command(event, arg)

    def process_IN_MODIFY(self, event):
        if self.is_allowed_path(event.pathname, event.dir):
            self.modified_files.add(event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        # ignore close_write unless the file has previously been modified.
        if (event.pathname in self.modified_files):
            self.do_index_command(event, "-a")

    def do_index_command(self, event, index_argument):
        if self.is_allowed_path(event.pathname, event.dir):
            log("synoindex %s %s" % (index_argument, event.pathname))
            call(["synoindex", index_argument, event.pathname])

            self.modified_files.discard(event.pathname)
        else:
            log("%s is not an allowed path" % event.pathname)

    def is_allowed_path(self, filename, is_dir):
        # Don't check the extension for directories
        if not is_dir:
            ext = os.path.splitext(filename)[1][1:].lower()
            if ext not in allowed_exts:
                return False
        return not (filename.find("@eaDir") > 0)

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)
wdd = wm.add_watch(
    watched_paths,
    mask,
    rec=True,
    auto_add=True,
)

try:
    notifier.loop(daemonize=True, pid_file=config['pidfile'])
except pyinotify.NotifierError, err:
    print >> sys.stderr, err
