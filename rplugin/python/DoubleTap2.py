import neovim
import time
import logging

"""Version 2 of the Neovim DoubleTap plugin
TODO:
    * Add auto close without the need for a double tap. This is how most pair plugins work.
        * Make this optional at the per character level. Some auto, some don't
    * Add jump out support back.
"""

# Set up the logger
mod_logger = logging.getLogger(__name__)
# Use a console handler, set it to debug by default
logger_ch = logging.StreamHandler()
mod_logger.setLevel(logging.DEBUG)
mod_logger.addHandler(logger_ch)

LOGGER_DEBUG_FILE = '/tmp/doubletap_debug.log'
logger_fd = logging.FileHandler(LOGGER_DEBUG_FILE)
mod_logger.addHandler(logger_fd)

# future configurable, in MS
# configurable per map will be available
DEFAULT_KEY_TIMEOUT = 750

"""
Default insert map for all file types
"""
INSERT_MAP = {
    "(": {'insert': '()', 'r': ')'},
    "[": {'insert': '[]', 'r': ']'},
    "{": {'insert': '{}', 'r': '}'},
    "<": {'insert': '<>', 'r': '>'},
    "'": {'insert': "''"},
    "`": {'insert': "``"},
}

"""
Default finishers map for all file types
"""
FINISHERS_MAP = {
    ';': ';',
    ',': ',',
}


def dt_imap(func, key):
    # build the imap string for a function and key
    if key == "'":
        imap = "imap <silent> %s <C-R>=%s(\"%s\")<CR>" % (key, func, key)
    else:
        imap = "imap <silent> %s <C-R>=%s('%s')<CR>" % (key, func, key)

    mod_logger.debug('creating imap: %s', imap)
    return imap


def dt_nmap(func, key):
    # build the nmap string for a function and key
    if key == "'":
        nmap = "nmap <silent> %s <ESC>:call %s(\"%s\")<CR>" % (key, func, key)
    else:
        nmap = "nmap <silent> %s <ESC>:call %s('%s')<CR>" % (key, func, key)

    mod_logger.debug('creating nmap: %s', nmap)
    return nmap


@neovim.plugin
class DoubleTap(object):

    def __init__(self, vim):
        self._logger = mod_logger

        self._log("DoubleTap::__init__")
        self._vim = vim
        self._key_tout = DEFAULT_KEY_TIMEOUT
        self._key_stack = []
        self._last_insert = None
        self._finishers_map = {}
        self._insert_map = {}

    @property
    def mode(self):
        return self._vim.eval('mode()').lower()

    def filetype(self):
        return self._vim.eval('&filetype')

    def finishers_map(self):
        # Get the finishers map. Will be built and cached the first access
        ft = self.filetype()
        if self._finishers_map.get(ft):
            return self._finishers_map[ft]

        self._finishers_map[ft] = FINISHERS_MAP.copy()
        self._finishers_map[ft].update(self.ft_var('finishers', {}))
        self._log('finishers_map %s', self._finishers_map[ft])
        return self._finishers_map[ft]

    def insert_map(self):
        # Get the insert map. Will be built and cached the first access
        ft = self.filetype()
        if self._insert_map.get(ft):
            return self._insert_map[ft]

        self._insert_map[ft] = INSERT_MAP.copy()
        self._insert_map[ft].update(self.ft_var('insert', {}))
        self._log('insert_map %s', self._insert_map[ft])
        return self._insert_map[ft]

    def lookup_var(self, vname, defl=None):
        # Lookup a Vim variable from the current instance. Provides
        # the defl value if the variable doesn't exist.
        if self._vim.eval('exists("%s")' % vname):
            return self._vim.eval("%s" % vname)

        return defl

    def ft_var(self, vname, defl=None):
        ft = self.filetype()
        return self.dt_var('%s_%s' % (ft, vname), defl=self.dt_var(vname, defl=defl))

    def dt_var(self, vname, defl=None):
        return self.lookup_var('g:doubletap_%s' % vname, defl=defl)

    def _log(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def _cur_char(self):
        pos = self._vim.current.window.cursor
        line = pos[0] - 1
        char = pos[1]
        return self._vim.current.buffer[line][char]

    def _cut_back(self, r, inline=False, set_pos=False):
        # Return the current line 'cut back' r characters from the current cursor pos
        # Set the current line value to new line if inline is True
        pos = self._vim.current.window.cursor
        line = pos[0] - 1
        char = pos[1]
        buf = self._vim.current.buffer
        buf_line = buf[line]
        self._log("_cut_back orign '%s'", buf_line)

        buf_line_l = buf_line[0: char - r]
        buf_line_r = buf_line[char:]
        new_line = buf_line_l + buf_line_r
        self._log("_cut_back new '%s'", new_line)

        if inline:
            buf[line] = new_line

        if set_pos:
            self._vim.current.window.cursor = (line + 1, char - r)

        return new_line

    def _is_double_tap(self, key):
        self._log("_is_double_tap %s", self._key_stack)

        kdata = {
            'key': key,
            'when': int(time.time() * 1000)  # time since epoch in milliseconds
        }

        if self._key_stack is None:
            self._key_stack = [kdata]
            self._log("_is_double_tap None stack %s", self._key_stack)
            return None

        self._key_stack.append(kdata)

        if len(self._key_stack) < 2:
            self._log("_is_double_tap short stack")
            return None

        if key != self._key_stack[-2]['key']:
            self._log("_is_double_tap stack un-matched stack")
            self._key_stack = [kdata]
            return None

        stack_life = self._key_stack[-1]['when'] - self._key_stack[0]['when']
        if stack_life > self._key_tout:
            self._log("_is_double_tap too old")
            self._key_stack = [kdata]
            return None

        return kdata

    def _process_finish_line_key(self, key):
        self._log("_process_finish_line_key %s", key)

        if not self._is_double_tap(key):
            return key

        pos = self._vim.current.window.cursor
        buf = self._vim.current.buffer
        ln = pos[0] - 1

        line = self.mode == 'i' and self._cut_back(1, set_pos=True) or buf[ln]
        line = line.rstrip()
        fm = self.finishers_map()

        if fm[key] and line[-1] != fm[key]:
            line += fm.get(key, '')

        buf[ln] = line
        return ''

    def _process_rightsert_key(self, key):
        self._log("_process_rightsert_key %s : %s", key, self._key_stack)

        if self._key_stack is None:
            self._log("_process_rightsert_key None stack, cur char: %s", self._cur_char())
            # this is first time we've encountered this key press since the last time we inserted.
            # See if we should 'walk out' of a matching pair
            # if this matches the right char of the last pair insertion, 'walk out'

            self._key_stack = []
            if self._last_insert and self._last_insert.get('r') == self._cur_char():
                pos = self._vim.current.window.cursor
                line = pos[0]
                char = pos[1]
                self._vim.current.window.cursor = (line, char + 1)
                return ''

        return key

    def _process_insert_key(self, key):
        self._log("process_keys %s", self._key_stack)

        if not self._is_double_tap(key):
            return key

        ks_len = len(self._key_stack)
        self._key_stack = None
        #  insert = INSERT_MAP[key]
        insert = self.insert_map()[key]
        self._last_insert = insert

        # erase previous keys, insert our characters and reposition the cursor.
        pos = self._vim.current.window.cursor
        line = pos[0] - 1
        char = pos[1]
        buf = self._vim.current.buffer
        self._log("process_keys, pos %s:%s", line, char)

        buf_line = buf[line]

        self._log("process_keys, orig line: '%s'", buf_line)

        # split the line in half, cutting out the input chars, and rebuild it with our result.
        buf_line_l = buf_line[0: char - ks_len + 1]
        buf_line_r = buf_line[char:]
        new_line = buf_line_l + insert['insert'] + buf_line_r

        self._log("process_keys, new line: '%s'", new_line)
        self._log("process_keys, new pos: %s:%s", pos[0], char - int(insert.get('bs', 0)))
        buf[line] = new_line

        self._vim.current.window.cursor = (pos[0], char - int(insert.get('bs', 0)))
        return ''

    @neovim.autocmd('BufEnter', pattern='*', eval='expand("%:p")', sync=True)
    def autocmd_handler_bufenter(self, filename):
        self._log("autocmd_handler_bufenter initializing %s ", filename)
        self._log('autocmd_handler_bufenter initialize the insert maps')

        self._key_tout = self.ft_var('timeout', DEFAULT_KEY_TIMEOUT)

        self._log('autocmd_handler_bufenter updated finishers %s', self.finishers_map())
        self._log('autocmd_handler_bufenter updated inserters %s', self.insert_map())
        self._log('autocmd_handler_bufenter updated timeout %s', self._key_tout)

        im = self.insert_map()
        for k in im:
            imap = dt_imap('DoubleTapInsert', k)
            self._log('initialize the insert map "%s"', imap)
            self._vim.command(imap)

            if im[k].get('r') and k != im[k]['r']:
                imap = dt_imap('DoubleTapRightsert', im[k]['r'])
                self._log('initialize the rightsert map "%s"', imap)
                self._vim.command(imap)

        for k in self.finishers_map():
            imap = dt_imap('DoubleTapFinishLine', k)
            self._log('initialize the insert map "%s"', imap)
            self._vim.command(imap)

            nmap = dt_nmap('DoubleTapFinishLine', k)
            self._log('initialize the normal map "%s"', nmap)
            self._vim.command(nmap)

    @neovim.function('DoubleTapInsert', sync=True)
    def double_tap_insert(self, args):
        try:
            key = args[0]
        except IndexError:
            return ''

        self._log("double_tap_insert %s ", key)
        return self._process_insert_key(key)

    @neovim.function('DoubleTapRightsert', sync=True)
    def double_tap_rightsert(self, args):
        try:
            key = args[0]
        except IndexError:
            return ''

        self._log("double_tap_righsert %s ", key)
        return self._process_rightsert_key(key)

    @neovim.function('DoubleTapFinishLine', sync=True)
    def double_tap_finish_line(self, args):
        try:
            key = args[0]
        except IndexError:
            return ''

        self._log("double_tap_finish_line %s ", key)
        return self._process_finish_line_key(key)
