from datetime import datetime

import ConfigParser
import os.path
import pyinotify
import re
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
                    'mp4 avi m4v',
    'exclude_dir_patterns': '@eaDir .sync'
}

def read_configuration(config_path=None):
    """Read from file or set the default configuration file.

    Args:
        config_path: a path to a configuration file.

    Returns:
        A dictionary that represents the configuration with the keys:
        - watched_paths: paths to watch
        - allowed_exts: extensions allowed
        - exclude_dir_patterns: folder to avoid watching even on watched_paths
        - logfile: where to log event
        - pidfile: where to store the pid

    """
    def compute(entry):
        """Compute entry as list of words.
        Words are stripped.
        Args:
            entry: string of space separated words

        Returns:
            List of entries.

        """
        if entry:
            return map(lambda x: x.strip(), entry.split(' '))
        return []

    def compute_exclude_pattern(exclude_pattern):
        """Compute exclusion patterns from simple words.
        Those words represents generic folder name (e.g. @eaDir,
        .sync, .stfolder)

        Args:
            exclude_pattern: string of words

        Returns:
            List of regexp patterns.

        """
        if exclude_pattern:
            folder_patterns = exclude_pattern.split(' ')
            return list(
                map(lambda x: '.*/' + x.strip().replace('.', '\.') + '.*',
                    folder_patterns))
        return []

    if config_path and os.path.exists(config_path):
        confparser = ConfigParser.ConfigParser()
        confparser.read(config_path)
        config = confparser._sections['main']
    else:  # default one based on original code
        config = CONFIG_DEFAULT

    config['watched_paths'] = compute(config.get('watched_paths'))
    config['allowed_exts'] = set(compute(config.get('allowed_exts')))

    config['exclude_dir_patterns'] = compute_exclude_pattern(
        config.get('exclude_dir_patterns'))

    return config

config = read_configuration(CONFIG_PATH)

watched_paths = config['watched_paths']
allowed_exts = config['allowed_exts']
exclude_dir_patterns = config['exclude_dir_patterns']

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
            return ext in allowed_exts
        return True

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)

excl_pattern = pyinotify.ExcludeFilter(config['exclude_dir_patterns'])

wdd = wm.add_watch(
    watched_paths,
    mask,
    rec=True,
    auto_add=True,
    exclude_filter=excl_pattern)

try:
    notifier.loop(daemonize=True, pid_file=config['pidfile'])
except pyinotify.NotifierError, err:
    print >> sys.stderr, err
