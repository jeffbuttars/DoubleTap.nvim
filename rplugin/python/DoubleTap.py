import neovim
import time

import logging

# Set up the logger
mod_logger = logging.getLogger(__name__)
# Use a console handler, set it to debug by default
logger_ch = logging.StreamHandler()
mod_logger.setLevel(logging.DEBUG)
#  log_formatter = logging.Formatter(('%(levelname)s: %(asctime)s %(processName)s:%(process)d'
#                                     ' %(filename)s:%(lineno)s %(module)s::%(funcName)s()'
#                                     ' -- %(message)s'))
#  logger_ch.setFormatter(log_formatter)
mod_logger.addHandler(logger_ch)

LOGGER_DEBUG_FILE = '/tmp/doubletap_debug.log'
logger_fd = logging.FileHandler(LOGGER_DEBUG_FILE)
mod_logger.addHandler(logger_fd)


insert_map = {
        "(": {"l": "(", "r": ")"},
        '"': {"l": '"', "r": '"'},
        "'": {'l': "'", 'r': "'"},
        "{": {'l': "{", 'r': "}",
              'mode': 'triggered', 'filler': ['', '']
              },
        "[": {'l': "[", 'r': "]"},
        "<": {'l': "<", 'r': ">"},
        }

jump_map = {
        ")": {"l": "(", "r": ")"},
        "}": {'l': "{", 'r': "}"},
        "]": {'l': "[", 'r': "]"},
        ">": {'l': "<", 'r': ">"},
        #  '"': {"l": '"', "r": '"', 'sym': True},  # Symetric : True
        #  "'": {'l': "'", 'r': "'", 'sym': True},
        }


finishers_map = (';', ',')

# future configurable, in MS
# configurable per map will be available
DEFAULT_KEY_TIMEOUT = 750

# Future configurable input modes for insert
# configurable per map will be available
# Generally, stream mode is good for single line inserts and
# triggered is good for multiline inserts, ie: {}
INPUT_MODES = ('stream', 'triggered')
INPUT_MODE = INPUT_MODES[1]


class KeyInputHandler(object):

    def __init__(self, vim, key, key_conf, key_timeout=None, ofd=None, logger=None):
        self._logger = logger or mod_logger
        self._key = key
        self._key_conf = key_conf
        self._vim = vim

        self._last_key_time = 0
        self._key_timeout = key_timeout or DEFAULT_KEY_TIMEOUT
        self._matching = False

        self._log("KeyInputHandler init: %s %s, timer: %s",
                  key, key_conf, self._key_timeout)

        self.event_proc = self.stream

    def __str__(self):
        return "KeyInputHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def _log(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def _patch_line(self, line, pos, mode=None):
        """Returns a new line without the unwanted input character
        as the result of a double tap.
        """

        self._log("TapOut original line: '%s', pos: %s", line, pos)

        self._log("KeyInputHandler patch o-line: '%s', pos: %s, mode: %s",
                  line, pos, mode)

        if mode:
            m = self._vim.eval('mode()').lower()
            if mode != m:
                self._log("KeyInputHandler mode mismatch %s:%s", mode, m)
                return line

            if mode == 'i':
                self._vim.current.window.cursor = (pos[0], max(0, pos[1] - 1))

        col = pos[1]
        if len(line) >= col:
            line = line[:(col - 1)] + line[col:]

        self._log("KeyInputHandler patched line: '%s'", line)
        return line

    #  def _set_lines(self, line, pos, lc, m=None, rc=''):
    #      """todo: Docstring for _set_lines

    #      :param line: arg description
    #      :type line: type description
    #      :param pos: arg description
    #      :type pos: type description
    #      :param lc: arg description
    #      :type lc: type description
    #      :param m: arg description
    #      :type m: type description
    #      :param rc: arg description
    #      :type rc: type description
    #      :return:
    #      :rtype:
    #      """

    #      if m:

    #      input_list = []

    def _in_str(self, char, pos=None):
        """
        Param: thechar the quote character that's been double tapped.
        See if the cursor is inside a string according the current syntax definition

        This will often contain whether we are in a single or double quote
        string. How that is represented seems syntax specific, not standard.
        We still leverage that knowledge if we can.
        """

        synstr = self._vim.eval('synIDattr(synID(line("."), col("."), 0), "name" )')
        self._log("synstr %s", synstr)

        in_string = 'string' in synstr.lower()
        self._log("In string %s", in_string)

        return in_string

    def stream(self, last_key):

        key = self._key

        if self._in_str(key):
            return key

        # time since epoch in milliseconds
        now = int(time.time() * 1000)

        if self._matching:
            # We're being fed keys while processing a doubleTap event, so ignore them
            self._log("stream already matching key: %s", key)
            return key

        # for the time being, we only handle simple pairs of keys, so pass
        # on anything that doesn't match the last key.
        if key == last_key and now - self._last_key_time < self._key_timeout:
            self._matching = True

            # This is our 'critical section'
            try:
                res = self.stream_perform()
            finally:
                # reset our state, let the exception be handled further up
                self._matching = False
                self._last_key_time = 0

            self._log("stream perform result: '%s'", res)

            self._matching = False
            self._last_key_time = 0
            return res

        self._log("stream BOTTOM key: %s", key)
        self._last_key_time = now
        return key

    def stream_perform(self):
        """
        This is where the 'critical section' work is performed.
        Do the workin in `stream_perform()` that will change the buffer when a
        doubleTap event has occurred.
        Whatever `stream_perform` returns will be written in the current
        buffer and the current position
        """
        raise NotImplementedError("stream_perform() must be overriden")


class InsertHandler(KeyInputHandler):
    def __init__(self, vim, key, key_conf, key_timeout=None, ofd=None):
        super(InsertHandler, self).__init__(vim, key, key_conf, key_timeout=key_timeout, ofd=ofd)

        # XXX(jeffbuttars) Big fat hack for now for the '"' case.
        if key == '"':
            imap = "imap <silent> %s <C-R>=DoubleTapInsert('%s')<CR>" % (key, key)
        else:
            imap = "imap <silent> %s <C-R>=DoubleTapInsert(\"%s\")<CR>" % (key, key)

        self._log(imap)
        self._vim.command(imap)

    def __str__(self):
        return "InsertHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def stream_perform(self):
        pos = self._vim.current.window.cursor
        self._log("double_tap_insert key: %s", self._key)
        self._log("double_tap_insert : window pos %s", pos)

        buf = self._vim.current.buffer
        ln = pos[0] - 1
        line = buf[ln]
        lp = pos[1]
        bl = line[:lp - 1]
        el = line[lp:]
        self._log("double_tap_insert : line %s", ln)
        buf[ln] = bl + self._key_conf['r'] + el
        self._vim.current.window.cursor = (pos[0], lp - 1)

        return self._key_conf['l']


class FinishLineHandler(KeyInputHandler):
    def __init__(self, vim, key, key_conf, key_timeout=None, ofd=None):
        super(FinishLineHandler, self).__init__(
                vim, key, key_conf, key_timeout=key_timeout, ofd=ofd)

        imap = "imap <silent> %s <C-R>=DoubleTapFinishLine('%s')<CR>" % (key, key)
        self._log(imap)
        self._vim.command(imap)

        imap = "nmap <silent> %s <ESC>:call DoubleTapFinishLineNormal('%s')<CR>" % (key, key)
        self._log(imap)
        self._vim.command(imap)

    def __str__(self):
        return "FinishLineHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def stream_perform(self):
        pos = self._vim.current.window.cursor

        self._log("double_finish_line key: %s", self._key)
        self._log("double_finish_line : window pos %s", pos)

        buf = self._vim.current.buffer
        ln = pos[0] - 1
        c = pos[1]

        self._log("double_finish_line : cur line '%s' %s", buf[ln], len(buf[ln]))
        if buf[ln]:
            self._log("double_finish_line : cur char '%s'", buf[ln][c - 1])

        line = buf[ln].rstrip()

        if line and (line[-1] != self._key):
            line += self._key
        elif not line:
            line = self._key

        line = self._patch_line(line, pos, mode='i')

        buf[ln] = line

        self._log("double_finish_line : new line '%s' %s", line, len(line))
        self._log("double_finish_line : column %s", c)

        #  if mode == 'i':
        #      self._vim.current.window.cursor = (pos[0], max(0, pos[1] - 1))

        return ''


class TapOutHandler(KeyInputHandler):
    def __init__(self, vim, key, key_conf, key_timeout=None, ofd=None):
        super(TapOutHandler, self).__init__(
                vim, key, key_conf, key_timeout=key_timeout, ofd=ofd)

        self._lkey = key_conf.get('l')
        self._rkey = key_conf.get('r')
        self._is_sym = key_conf.get('sym', False)

        if key == '"':
            imap = "imap <silent> %s <C-R>=DoubleTapOut('%s')<CR>" % (
                    self._key, self._key)
        else:
            imap = "imap <silent> %s <C-R>=DoubleTapOut(\"%s\")<CR>" % (
                    self._key, self._key)

        self._log(imap)
        self._vim.command(imap)

    def __str__(self):
        return "TapOutHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def stream_perform(self):
        pos = self._vim.current.window.cursor
        buf = self._vim.current.buffer
        ln = pos[0] - 1
        line = buf[ln]

        line = self._patch_line(line, pos, mode='i')

        # If we're sigging on the left char of the match, move over one
        # We have be carefull about the first and last chars
        c = max(0, min(pos[1] - 1, len(line) - 1))

        self._log("checking line: '%s', c: %s, len: %s ", line, c, len(line))

        if line[c] == self._lkey:
            self._vim.current.window.cursor = (pos[0], (pos[1] + 1))
            pos = self._vim.current.window.cursor

        buf[ln] = line
        c = max(0, min(pos[1] - 1, len(line) - 1))
        self._log("checking line: '%s', c: %s, len: %s ", line, c, len(line))

        # If we're sitting on the char, just move over one!
        if line[c] == self._rkey:
            self._vim.current.window.cursor = (pos[0], (pos[1] + 1))
            return ""

        # Vim has some built funcs to help us with this. If we're in a matching
        # pair, witch is likely, it will do the jump for us!
        sres = int(self._vim.eval("searchpair('%s', '', '%s', 'W')" % (self._lkey, self._rkey)))
        if sres > 0:
            self._log("TapOut patched Vim jump! %s", sres)
            # We jumped.
            #  call s:advCursorAndMatch( 1, [ [ l:cpos[1], l:cpos[2]-1 ] ] )
            pos = self._vim.current.window.cursor
            self._vim.current.window.cursor = (pos[0], (pos[1] + 1))
            return ""

        return self._key


@neovim.plugin
class DoubleTap(object):
    """Docstring for DoubleTap """

    def __init__(self, vim):
        self._logger = mod_logger

        self._log("DoubleTap::__init__")

        self._vim = vim
        self._last_key = ''

        self._insert_key_handlers = {}
        self._finish_key_handlers = {}
        self._jump_key_handlers = {}

        self._insert_timer = 0
        #  self._insert_timer = int(self.lookup_var("g:DoubleTapInsertTimer", DEFAULT_KEY_TIMEOUT))

        self._insert_timer = self._insert_timer or DEFAULT_KEY_TIMEOUT
        self._log("Instatiating... timer %s", self._insert_timer)

    def _log(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def lookup_var(self, vname, *args):
        defa = None
        if args:
            defa = args[0]

        exists = self._vim.eval('exists("%s")' % vname)
        if exists:
            return self._vim.eval("%s" % vname)

        return defa

    @neovim.autocmd('BufEnter', pattern='*', eval='expand("<afile>")', sync=True)
    def autocmd_handler(self, filename):
        #  self._vim.current.line = "garbage!!! " + filename
        self._vim.command("echo 'garbage!!! %s'" % filename)

        for k, v in insert_map.items():
            self._insert_key_handlers[k] = InsertHandler(
                    self._vim, k, v,
                    key_timeout=self._insert_timer)
            self._log("autocmd_handler initializing %s : %s ", k, v)

        for f in finishers_map:
            self._finish_key_handlers[f] = FinishLineHandler(
                    self._vim, f, {},
                    key_timeout=self._insert_timer)

        for k, v in jump_map.items():
            self._jump_key_handlers[k] = TapOutHandler(
                    self._vim, k, v,
                    key_timeout=self._insert_timer)

    def dispatch(self, args, handlers):
        """
        Handle the key input of the mapped trigger keys.
        The event is dispatched to the proper handler which is passed in.

        There are two input modes, stream and triggerd.

        In stream mode the keys are inserted as they're typed. If a double tap event
        occurs, then the line is retroactively edited to reflect the pair input.

        In triggerd mode, when the first trigger input is received, it's buffered until it's
        determined that a double tap event won't happen, or of course the double tap event
        occurs. When the state is resolved, the insert will happen.
        """
        try:
            key = args[0]
        except KeyError:
            # Ignore and carry on. This would be a very strange scenario
            return

        self._log("dispatch args: %s, key: '%s' last_key: '%s' ",
                  args, key, self._last_key)
        res = key

        handler = handlers.get(key)
        self._log("dispatch key: %s handler: %s ", key, handler)

        if not handler:
            return key

        try:
            res = handler.event_proc(self._last_key)
        except Exception:
            import traceback
            self._log("EXECPTION\n%s", traceback.format_exc())
            return key

        self._log("dispatch key: %s result: '%s' ", key, res)

        self._last_key = key
        return res

    @neovim.function('DoubleTapInsert', sync=True)
    def double_tap_insert(self, args):
        return self.dispatch(args, self._insert_key_handlers)

    @neovim.function('DoubleTapOut', sync=True)
    def double_tap_out(self, args):
        return self.dispatch(args, self._jump_key_handlers)

    @neovim.function('DoubleTapFinishLine', sync=True)
    def double_tap_finish_line(self, args):
        return self.dispatch(args, self._finish_key_handlers)

    @neovim.function('DoubleTapFinishLineNormal', sync=True)
    def double_tap_finish_line_normal(self, args):
        return self.dispatch(args, self._finish_key_handlers)
