import logging
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

    def _splice(self, key):
        insert = self.config.inserts[key]

        # erase previous keys, insert our characters and reposition the cursor.
        pos = self.window.cursor
        line = pos[0] - 1
        char = pos[1]
        buf_line = self.buffer[line]

        # split the line in half, cutting out the input chars, and rebuild it with our result.
        #  buf_line_l = buf_line[0: char - ks_len + 1]
        buf_line_l = buf_line[0: char - 1]
        buf_line_r = buf_line[char:]
        new_line = buf_line_l + insert['insert'] + buf_line_r

        # Write the edited line into the buffer
        self.buffer[line] = new_line

        # Re-position the cursor to be inside the pair
        self.nvim.current.window.cursor = (pos[0], char - int(insert.get('bs', 0)))

    def _handle_insert(self, key):
        logger.debug("handle_insert %s", key)
        # get the configuration for the key
        #  k_cfg = self.config.inserts[key]

        #  if not self.key_stack:
        #      self.key_stack.append(key)

        self._splice(key)

        return ''

    @pynvim.function("DoubleTapInsert", sync=True)
    def insert(self, args):
        logger.debug("DoubleTap::insert %s", args)

        try:
            key = args[0]
        except IndexError:
            return ""

        now = time.perf_counter()
        if (key != self.last_key) or ((now - self.last_key_time) > self.config.timeout):
            self.last_key = key
            self.last_key_time = now
            logger.debug("DoubleTap::insert no match or to late")
            return key

        self.last_key = 0
        self.last_key_time = 0
        return self._handle_insert(key)
        #  self._log("double_tap_insert %s ", key)
        #  return self._process_insert_key(key)
