import neovim
import time

insert_map = {
        "(": {"l": "(", "r": ")"},
        '"': {"l": '"', "r": '"'},
        "'": {'l': "'", 'r': "'"},
        "{": {'l': "{", 'r': "}"},
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
DEFAULT_KEY_TIMEOUT = 750


class KeyInputHandler(object):

    def __init__(self, vim, key, key_conf, key_timeout=None, ofd=None):
        self._key = key
        self._key_conf = key_conf
        self._vim = vim

        self._last_key_time = 0
        self._key_timeout = key_timeout or DEFAULT_KEY_TIMEOUT
        self._matching = False

        self._dfile = ofd
        self._dfile.write("KeyInputHandler init: %s %s, timer: %s\n" % (
            key, key_conf, self._key_timeout))

    def __str__(self):
        return "KeyInputHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def _patch_line(self, line, pos, mode=None):
        """Returns a new line without the unwanted input character
        as the result of a double tap.
        """
        self._dfile.write("TapOut original line: '%s', pos: %s\n" % (line, pos))

        self._dfile.write("KeyInputHandler patch o-line: '%s', pos: %s, mode: %s\n" % (
            line, pos, mode))

        if mode:
            m = self._vim.eval('mode()').lower()
            if mode != m:
                self._dfile.write("KeyInputHandler mode mismatch %s:%s\n" % (mode, m))
                return line

            if mode == 'i':
                self._vim.current.window.cursor = (pos[0], max(0, pos[1] - 1))

        col = pos[1]
        if len(line) >= col:
            line = line[:(col - 1)] + line[col:]

        self._dfile.write("KeyInputHandler patched line: '%s'\n" % (line,))
        return line

    def trigger(self, last_key):

        key = self._key
        # time since epoch in milliseconds
        now = int(time.time() * 1000)

        if self._matching:
            # We're being fed keys while processing a doubleTap event, so ignore them
            self._dfile.write("trigger already matching key: %s\n" % key)
            return key

        # for the time being, we only handle simple pairs of keys, so pass
        # on anything that doesn't match the last key.
        if key == last_key and now - self._last_key_time < self._key_timeout:
            self._matching = True

            # This is our 'critical section'
            try:
                res = self.perform()
            finally:
                # reset our state, let the exception be handled further up
                self._matching = False
                self._last_key_time = 0

            self._dfile.write("trigger perform result: '%s'\n" % res)

            self._matching = False
            self._last_key_time = 0
            return res

        self._dfile.write("trigger BOTTOM key: %s\n" % key)
        self._last_key_time = now
        return key

    def perform(self):
        """
        This is where the 'critical section' work is performed.
        Do the workin in `perform()` that will change the buffer when a 
        doubleTap event has occurred.
        Whatever `perform` returns will be written in the current buffer and the current position
        """
        raise NotImplementedError("perform() must be overriden")


class InsertHandler(KeyInputHandler):
    def __init__(self, vim, key, key_conf, key_timeout=None, ofd=None):
        super(InsertHandler, self).__init__(vim, key, key_conf, key_timeout=key_timeout, ofd=ofd)

        # XXX(jeffbuttars) Big fat hack for now for the '"' case.
        if key == '"':
            imap = "imap <silent> %s <C-R>=DoubleTapInsert('%s')<CR>" % (key, key)
        else:
            imap = "imap <silent> %s <C-R>=DoubleTapInsert(\"%s\")<CR>" % (key, key)

        self._dfile.write(imap + "\n")
        self._vim.command(imap)

    def __str__(self):
        return "InsertHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def perform(self):
        pos = self._vim.current.window.cursor
        self._dfile.write("double_tap_insert key: %s\n" % self._key)
        self._dfile.write("double_tap_insert : window pos %s\n" % pos)

        buf = self._vim.current.buffer
        ln = pos[0] - 1
        line = buf[ln]
        lp = pos[1]
        bl = line[:lp - 1]
        el = line[lp:]
        self._dfile.write("double_tap_insert : line %s\n" % ln)
        buf[ln] = bl + self._key_conf['r'] + el
        self._vim.current.window.cursor = (pos[0], lp - 1)

        return self._key_conf['l']


class FinishLineHandler(KeyInputHandler):
    def __init__(self, vim, key, key_conf, key_timeout=None, ofd=None):
        super(FinishLineHandler, self).__init__(
                vim, key, key_conf, key_timeout=key_timeout, ofd=ofd)

        imap = "imap <silent> %s <C-R>=DoubleTapFinishLine('%s')<CR>" % (key, key)
        self._dfile.write(imap + "\n")
        self._vim.command(imap)

        imap = "nmap <silent> %s <ESC>:call DoubleTapFinishLineNormal('%s')<CR>" % (key, key)
        self._dfile.write(imap + "\n")
        self._vim.command(imap)

    def __str__(self):
        return "FinishLineHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def perform(self):
        pos = self._vim.current.window.cursor

        self._dfile.write("double_finish_line key: %s\n" % self._key)
        self._dfile.write("double_finish_line : window pos %s\n" % pos)
        #  self._dfile.write("double_finish_line : mode %s\n" % mode)

        buf = self._vim.current.buffer
        ln = pos[0] - 1
        c = pos[1]

        self._dfile.write("double_finish_line : cur line '%s' %s\n" % (buf[ln], len(buf[ln])))
        if buf[ln]:
            self._dfile.write("double_finish_line : cur char '%s'\n" % (buf[ln][c - 1],))

        line = buf[ln].rstrip()

        if line and (line[-1] != self._key):
            line += self._key
        elif not line:
            line = self._key

        line = self._patch_line(line, pos, mode='i')

        buf[ln] = line

        self._dfile.write("double_finish_line : new line '%s' %s\n" % (line, len(line)))
        self._dfile.write("double_finish_line : column %s\n" % c)

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

        self._dfile.write(imap + "\n")
        self._vim.command(imap)

    def __str__(self):
        return "TapOutHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def perform(self):
        pos = self._vim.current.window.cursor
        buf = self._vim.current.buffer
        ln = pos[0] - 1
        line = buf[ln]

        line = self._patch_line(line, pos, mode='i')

        # If we're sigging on the left char of the match, move over one
        # We have be carefull about the first and last chars
        c = max(0, min(pos[1] - 1, len(line) - 1))

        self._dfile.write("checking line: '%s', c: %s, len: %s \n" % (line, c, len(line)))

        if line[c] == self._lkey:
            self._vim.current.window.cursor = (pos[0], (pos[1] + 1))
            pos = self._vim.current.window.cursor

        buf[ln] = line
        c = max(0, min(pos[1] - 1, len(line) - 1))
        self._dfile.write("checking line: '%s', c: %s, len: %s \n" % (line, c, len(line)))

        # If we're sitting on the char, just move over one!
        if line[c] == self._rkey:
            self._vim.current.window.cursor = (pos[0], (pos[1] + 1))
            return ""

        # Vim has some built funcs to help us with this. If we're in a matching
        # pair, witch is likely, it will do the jump for us!
        sres = int(self._vim.eval("searchpair('%s', '', '%s', 'W')" % (self._lkey, self._rkey)))
        if sres > 0:
            self._dfile.write("TapOut patched Vim jump! %s\n" % sres)
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
        print("__init__")
        self._vim = vim
        self._last_key = ''

        #  self._buf = self._vim.current.buffer
        self._dfile = open('/tmp/dtout.text', "a")
        #  self._dfile.write("%s\n" % (dir(vim),))
        self._dfile.write("Instatiating...\n")

        self._insert_key_handlers = {}
        self._finish_key_handlers = {}
        self._jump_key_handlers = {}

        self._insert_timer = 0
        #  self._insert_timer = int(self.lookup_var("g:DoubleTapInsertTimer", DEFAULT_KEY_TIMEOUT))

        self._insert_timer = self._insert_timer or DEFAULT_KEY_TIMEOUT
        self._dfile.write("Instatiating... timer %s\n" % self._insert_timer)

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
                    key_timeout=self._insert_timer, ofd=self._dfile)
            self._dfile.write("autocmd_handler initializing %s : %s \n" % (k, v))

        for f in finishers_map:
            self._finish_key_handlers[f] = FinishLineHandler(
                    self._vim, f, {},
                    key_timeout=self._insert_timer, ofd=self._dfile)

        for k, v in jump_map.items():
            self._jump_key_handlers[k] = TapOutHandler(
                    self._vim, k, v,
                    key_timeout=self._insert_timer, ofd=self._dfile)

    def dispatch(self, args, handlers):
        try:
            key = args[0]
        except KeyError:
            # Ignore and carry on. This would be a very strange scenario
            return

        self._dfile.write("dispatch args: %s, key: '%s' last_key: '%s' \n" % (args, key, self._last_key))
        res = key

        handler = handlers.get(key)
        self._dfile.write("dispatch key: %s handler: %s \n" % (key, handler))

        if not handler:
            return key

        try:
            res = handler.trigger(self._last_key)
        except Exception:
            import traceback
            self._dfile.write("EXECPTION\n%s\n" % (traceback.format_exc(),))
            return key

        self._dfile.write("dispatch key: %s result: '%s' \n" % (key, res))

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
