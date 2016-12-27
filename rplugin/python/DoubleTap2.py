import neovim
import time
import logging

"""Version 2 of the Neovim DoubleTap plugin
TODO:
    * Add auto close without the need for a double tap. This is how most pair plugins work.
        * Make this optional at the per character level. Some auto, some don't
    * Add jump out support back.
    * Support 'disable' flag
    * Bring in surround taps
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

SYN_STRINGS = [
    'string', 'quotes', 'heredoc', 'doctestvalue',
    'doctest', 'doctest2', 'bytesescape',
]

# future configurable, in MS
# configurable per map will be available
DEFAULT_KEY_TIMEOUT = 750
INSERT_IN_STRING = 0

"""
Default insert map for all file types
"""
INSERT_MAP = {
    "(": {'insert': '()', 'r': ')'},
    "[": {'insert': '[]', 'r': ']'},
    "{": {'insert': '{}', 'r': '}'},
    "<": {'insert': '<>', 'r': '>'},
    "'": {'insert': "''"},
    '"': {'insert': '""'},
    "`": {'insert': "``"},
}

"""
Default finishers map for all file types
"""
FINISHERS_MAP = {
    ';': ';',
    ',': ',',
}

"""
Default jump map values
"""
JUMP_MAP = {
    ")": {'l': '(', 'm': '', 'r': ')'},
    "]": {'l': '[', 'm': '', 'r': ']'},
    "}": {'l': '{', 'm': '', 'r': '}'},
    ">": {'l': '<', 'm': '', 'r': '>'},
    #  "'": {'l': "'", 'm': '', 'r':  "'"},
    #  '"': {'l': '"', 'm': '', 'r': '"'},
    #  "`": {'l': '`', 'm': '', 'r': '`'},
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

class VimLog(object):
    def __init__(self, vim):
        self._logger = mod_logger
        self._vim = vim

    def _log(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)


class DTConfig(VimLog):
    def __init__(self, vim):
        super(DTConfig, self).__init__(vim)
        #  self._log("DTConfig::__init__")

        self.dt_globals = {
            'finishers': FINISHERS_MAP.copy(),
            'insert': INSERT_MAP.copy(),
            'jump': JUMP_MAP.copy(),
            'timeout': DEFAULT_KEY_TIMEOUT,
            'insert_in_string': INSERT_IN_STRING,
        }

        self.dt_ft = {}

    def __getattr__(self, name):
        #  self._log("DTConfig::__getattr__ %s", name)
        if name in self.dt_globals:
            #  self._log("DTConfig::__getattr__ vim var %s : %s",
                      #  name,
                      #  self.dt_ft.get(self.filetype(), {}).get(name, self.dt_globals.get(name)))
            return self.dt_ft.get(self.filetype(), {}).get(name, self.dt_globals.get(name))

        return self.__getattribute__(name)

    def filetype(self):
        return self._vim.eval('&filetype')

    def lookup_var(self, vname, defl=None):
        # Lookup a Vim variable from the current instance. Provides
        # the defl value if the variable doesn't exist.
        if self._vim.eval('exists("%s")' % vname):
            return self._vim.eval("%s" % vname)

        return defl

    def ft_var(self, vname, defl=None):
        # Lookup variables at the filetype scope, fallback to global scope if ft scope
        # value is not found, otherwise return defl or None
        ft = self.filetype()
        return self.dt_var('%s_%s' % (ft, vname), defl=self.dt_var(vname, defl=defl))

    def dt_var(self, vname, defl=None):
        # Lookup variables at the g:doubletap global scope
        # if value is not found return defl or None
        return self.lookup_var('g:doubletap_%s' % vname, defl=defl)

    def update_ft(self):
        ft = self.filetype()
        self._log('update_ft %s', ft)

        if self.dt_ft.get(ft):
            self._log('update_ft %s cache exists', ft)
            return

        self._log('update_ft %s building cache ...', ft)
        cache = {}
        for k, v in self.dt_globals.items():
            self._log('update_ft %s building cache %s : %s', ft, k, v)
            if type(v) is dict:
                cache[k] = v.copy()
                cv = self.ft_var(k, cache[k])
                cache[k].update(cv)
            else:
                cache[k] = self.ft_var(k, v)

            self.dt_ft[ft] = cache
            self._log('update_ft %s built cache value %s : %s', ft, k, self.dt_ft[ft])


@neovim.plugin
class DoubleTap(VimLog):

    def __init__(self, vim):
        super(DoubleTap, self).__init__(vim)
        self._log("DoubleTap::__init__")
        self._key_stack = []
        self._last_insert = None
        self._config = DTConfig(vim)

    @property
    def mode(self):
        return self._vim.eval('mode()').lower()

    def in_string(self, pos=None):
        try:
            line = pos and pos[0] or 'line(".")'
            col = pos and pos[1] or 'col(".")'
        except IndexError as e:
            self._log.error(e)
            line = 'line(".")'
            col = 'col(".")'

        syn = self._vim.eval(
            'synIDattr(synID(%s, %s, 1), "name")' % (line, col)
        ).lower()

        self._log('in_string syn: "%s"', syn)

        if syn:
            for symbol in SYN_STRINGS:
                if symbol in syn:
                    return True

        return False

    def _cur_char(self):
        pos = self._vim.current.window.cursor
        line = pos[0] - 1
        char = pos[1]
        return self._vim.current.buffer[line][char]

    def _buf_data(self):
        window = self._vim.current.window
        pos = self._vim.current.window.cursor
        buf = self._vim.current.buffer
        line = pos[0] - 1
        char = pos[1]

        return {
            'window': window,
            'buffer': buf,
            'pos': pos,
            'line': line,
            'char': char,
            'buf_line': buf[line],
            'buf_char': buf[line][char - 1],
        }

    def _cut_back(self, r, inline=False, set_pos=False):
        # Return the current line 'cut back' r characters from the current cursor pos
        # Set the current line value to new line if inline is True
        buf_data = self._buf_data()
        char = buf_data['char']
        line = buf_data['line']
        buf_line = buf_data['buf_line']
        self._log("_cut_back orign '%s'", buf_line)

        buf_line_l = buf_line[0: char - r]
        buf_line_r = buf_line[char:]
        new_line = buf_line_l + buf_line_r
        self._log("_cut_back new '%s'", new_line)

        if inline:
            buf_data['buffer'][line] = new_line

        if set_pos:
            self._vim.current.window.cursor = (line + 1, char - r)

        return new_line

    def _is_double_tap(self, key, buf_data=None):
        #  self._log("_is_double_tap %s", self._key_stack)
        #  self._log("_is_double_tap in string? %s", self.in_string())

        # If we're in string, check if we allow double tap
        if self.in_string() and not self._config.insert_in_string:
            #  self._log("_is_double_tap in string, ignoring key")
            return None

        kdata = {
            'key': key,
            'when': int(time.time() * 1000)  # time since epoch in milliseconds
        }

        if self._key_stack is None:
            self._key_stack = [kdata]
            #  self._log("_is_double_tap None stack %s", self._key_stack)
            return None

        self._key_stack.append(kdata)

        if len(self._key_stack) < 2:
            #  self._log("_is_double_tap short stack")
            return None

        if key != self._key_stack[-2]['key']:
            self._log("_is_double_tap stack un-matched stack")
            self._key_stack = [kdata]
            return None

        stack_life = self._key_stack[-1]['when'] - self._key_stack[0]['when']
        if stack_life > self._config.timeout:
            self._log("_is_double_tap too old")
            self._key_stack = [kdata]
            return None

        # enforce the last char in the buffer is the same as the double tap key
        buf_data = buf_data or self._buf_data()
        #  self._log("_is_double_tap buf_data %s", buf_data)
        if self.mode == 'i' and key != buf_data['buf_char']:
            #  self._log("_is_double_tap cur buf char %s does not match key", buf_data['buf_char'])
            self._key_stack = []
            return None

        self._log("_is_double_tap good")
        return kdata

    def _process_finish_line_key(self, key):
        self._log("_process_finish_line_key %s", key)

        buf_data = self._buf_data()
        if not self._is_double_tap(key, buf_data):
            return key

        buf = buf_data['buffer']
        ln = buf_data['line']

        line = self.mode == 'i' and self._cut_back(1, set_pos=True) or buf[ln]
        line = line.rstrip()
        fm = self._config.finishers

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

    def _process_jump(self, key):
        self._log("_process_jump %s", self._key_stack)

        if not self._is_double_tap(key):
            return key

        kconf = self._config.jump[key]
        self._log("_process_jump config %s : %s", key, kconf)
        self._vim.eval('searchpair("%s", "%s", "%s")' % (
            kconf.get('l', ''), kconf.get('m', ''), kconf.get('r', ''))
        )

        return key

    def _process_insert_key(self, key):
        self._log("process_keys %s", self._key_stack)

        buf_data = self._buf_data()
        if not self._is_double_tap(key, buf_data):
            return key

        ks_len = len(self._key_stack)
        self._key_stack = None
        insert = self._config.insert[key]
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
        #  self._log("autocmd_handler_bufenter initializing %s ", filename)
        #  self._log('autocmd_handler_bufenter initialize the insert maps')

        self._config.update_ft()

        #  self._log('autocmd_handler_bufenter updated finishers %s', self._config.finishers)
        #  self._log('autocmd_handler_bufenter updated inserters %s', self._config.insert)
        #  self._log('autocmd_handler_bufenter updated timeout %s', self._config.timeout)

        im = self._config.insert
        for k, v in im.items():
            if v.get('disabled'):
                continue

            imap = dt_imap('DoubleTapInsert', k)
            #  self._log('initialize the insert map "%s"', imap)
            self._vim.command(imap)

            if im[k].get('r') and k != im[k]['r']:
                imap = dt_imap('DoubleTapRightsert', im[k]['r'])
                #  self._log('initialize the rightsert map "%s"', imap)
                self._vim.command(imap)

        for k, v in self._config.finishers.items():
            if v == 'disabled':
                continue

            imap = dt_imap('DoubleTapFinishLine', k)
            #  self._log('initialize the insert map "%s"', imap)
            self._vim.command(imap)

            nmap = dt_nmap('DoubleTapFinishLine', k)
            #  self._log('initialize the normal map "%s"', nmap)
            self._vim.command(nmap)

        for k, v in self._config.jump.items():
            if v == 'disabled':
                continue

            imap = dt_imap('DoubleTapJump', k)
            self._log('initialize the jump map "%s"', imap)
            self._vim.command(imap)

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

    @neovim.function('DoubleTapJump', sync=True)
    def double_tap_jump(self, args):
        try:
            key = args[0]
        except IndexError:
            return ''

        self._log("double_tap_jump %s ", key)
        return self._process_jump(key)
