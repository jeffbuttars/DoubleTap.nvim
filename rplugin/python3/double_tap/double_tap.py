import logging
from functools import wraps
import os
import time
from collections import deque

import pynvim

from .config import DTConfig

# Get some config from the env
NEOVIM_DOUBLETAP_LOG_LEVEL = os.environ.get("NEOVIM_DOUBLETAP_LOG_LEVEL", "INFO")
NEOVIM_DOUBLETAP_LOG_FILE = os.environ.get("NEOVIM_DOUBLETAP_LOG_FILE")

# Set up the logger
logger = logging.getLogger(__name__)

if NEOVIM_DOUBLETAP_LOG_LEVEL.lower() == "debug":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


if NEOVIM_DOUBLETAP_LOG_FILE:
    # Use a console handler if NEOVIM_DOUBLETAP_LOG_FILE is '-'
    if NEOVIM_DOUBLETAP_LOG_FILE == "-":
        logger_ch = logging.StreamHandler()
        logger.addHandler(logger_ch)
    else:
        logger_fd = logging.FileHandler(NEOVIM_DOUBLETAP_LOG_FILE)
        logger.addHandler(logger_fd)


def normalize_key(func):
    @wraps(func)
    def wrapper(self, args):
        try:
            key = args[0]
        except IndexError:
            return ""

        if not self._is_double_tap( key):
            return key

        return func(self, key)

    return wrapper


def dt_imap(func, key):
    # build the imap string for a function and key
    # When the key is entered by the user, the function will be called
    if key == "'":
        imap = 'imap <silent> %s <C-R>=%s("%s")<CR>' % (key, func, key)
    else:
        imap = "imap <silent> %s <C-R>=%s('%s')<CR>" % (key, func, key)

    logger.debug("creating imap: %s", imap)
    return imap


def dt_nmap(func, key):
    # build the nmap string for a function and key
    # When the key is entered by the user, the function will be called
    if key == "'":
        nmap = 'nmap <silent> %s <ESC>:call %s("%s")<CR>' % (key, func, key)
    else:
        nmap = "nmap <silent> %s <ESC>:call %s('%s')<CR>" % (key, func, key)

    logger.debug("creating nmap: %s", nmap)
    return nmap


@pynvim.plugin
class DoubleTap:
    def __init__(self, nvim):
        logger.debug("DoubleTap init %s", nvim)
        self.nvim = nvim
        self.config = DTConfig()
        self.key_stack = deque()
        self.last_key = 0
        self.last_key_time = 0.0
        self.window = None
        self.buffer = None

        logger.debug("DoubleTap::init config: %s", self.config)

    @property
    def mode(self):
        return self._vim.eval("mode()").lower()

    def _is_double_tap(self, key):
        now = time.perf_counter()
        if (key != self.last_key) or ((now - self.last_key_time) > self.config.timeout):
            self.last_key = key
            self.last_key_time = now
            #  logger.debug("DoubleTap::_is_double_tap no match or to late")
            return False

        self.last_key = 0
        self.last_key_time = 0
        return True

    @pynvim.autocmd("BufEnter", pattern="*", eval='expand("%:p")', sync=True)
    def on_bufenter(self, filename):
        logger.debug("BufEnter: %s ", filename)
        self.window = self.nvim.current.window
        self.buffer = self.nvim.current.buffer

        # Map the insert characters for imap
        for k, v in self.config.inserts.items():
            if v.get("disabled"):
                continue

            imap = dt_imap("DoubleTapInsert", k)
            logger.debug('initialize the insert map "%s"', imap)
            self.nvim.command(imap)

        for k, v in self.config.finishers.items():
            imap = dt_imap('DoubleTapFinishLine', k)
            self.nvim.command(imap)

            nmap = dt_nmap('DoubleTapFinishLine', k)
            self.nvim.command(nmap)

        for k, v in self.config.jumps.items():
            if v.get("disabled"):
                continue

            imap = dt_imap('DoubleTapJumpOut', k)
            self.nvim.command(imap)

    def _splice(self, key):
        # erase previous keys, insert our characters and reposition the cursor.
        pos = self.window.cursor
        line = pos[0] - 1
        char = pos[1]
        buf_line = self.buffer[line]

        # split the line in half, cutting out the input chars, and rebuild it with our result.
        #  buf_line_l = buf_line[0: char - ks_len + 1]
        buf_line_l = buf_line[0: char - 1]
        buf_line_r = buf_line[char:]
        new_line = buf_line_l + key + buf_line_r

        # Write the edited line into the buffer
        self.buffer[line] = new_line

        # Re-position the cursor to be inside the pair
        #  self.nvim.current.window.cursor = (pos[0], char - int(insert.get('bs', 0)))
        self.nvim.current.window.cursor = (pos[0], char)

    @pynvim.function("DoubleTapJumpOut", sync=True)
    @normalize_key
    def jump_out(self, key):
        logger.debug("DoubleTap::jump_out %s", key)

        # because of how searchpos works we need to back the cursor up by one so we'll match the
        # char if we're on it.
        pos = self.window.cursor
        orig_pos = pos[:]

        # back the cursor up on position on it's current line
        self.window.cursor = (pos[0], pos[1] - 1)

        # Let Neovim do most of the work here. This will do the search and
        # jump for us. We will need to advance the cursor by one if a match is made.
        search = 'searchpos("%s", "Wze", "", %s)' % (
            self.config.jumps[key]['r'],
            self.config.search_timeout
        )
        #  logger.debug("_process_jump_key search %s", search)
        sp = self.nvim.eval(search)

        #  logger.debug("_process_jump_key sp: %s", sp)
        if (sp[0] + sp[1]) == 1:
            logger.debug("DoubleTap::jump_out no match found")
            return key * 2

        logger.debug("DoubleTap::jump_out match found")

        # Advance the cursor past the match by one position
        pos = self.window.cursor
        # forward the cursor up on position on it's current line
        self.window.cursor = (pos[0], pos[1] - 1)

        # Cut out the first key that was inserted from the double tap
        line = self.buffer[orig_pos[0] - 1]
        self.buffer[orig_pos[0] - 1] = line[:orig_pos[1]-1] + line[orig_pos[1]:]

        return ''

    @pynvim.function("DoubleTapInsert", sync=True)
    @normalize_key
    def insert(self, key):
        logger.debug("DoubleTap::insert %s", key)

        r_key = self.config.inserts[key]['insert']
        self._splice(r_key)

        return ''


    @pynvim.function("DoubleTapFinishLine", sync=True)
    @normalize_key
    def finish_line(self, key):
        logger.debug("DoubleTap::finish_line %s", key)
        pos = self.window.cursor
        buf = self.buffer

        ln = pos[0] - 1
        char = pos[1]

        #  line = self.mode == 'i' and self._cut_back(1, set_pos=True, buf_data=buf_data) or self.buffer[ln]
        line = self.buffer[ln].rstrip()

        if line[-1] != key:
            line += self.config.finishers[key]

        self.buffer[ln] = line

        return ''
