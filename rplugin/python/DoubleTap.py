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
        self._dfile.write("KeyInputHandler init: %s %s\n" % (key, key_conf))

    def __str__(self):
        return "KeyInputHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def trigger(self, last_key):

        key = self._key
        # time since epoch in milliseconds
        now = int(time.time() * 1000)

        if self._matching:
            # We're being fed keys while processing a doubleTap event, so ignore them
            self._dfile.write("double_tap_insert already matching key: %s\n" % key)
            return key

        # for the time being, we only handle simple pairs of keys, so pass
        # on anything that doesn't match the last key.
        if key == last_key and now - self._last_key_time < self._key_timeout:
            self._matching = True

            # This is our 'critical section'
            res = self.perform()
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

    def __str__(self):
        return "FinishLineHandler key: %s, key_conf: %s" % (self._key, self._key_conf)

    def perform(self):
        pos = self._vim.current.window.cursor
        self._dfile.write("double_finish_line key: %s\n" % self._key)
        self._dfile.write("double_finish_line : window pos %s\n" % pos)

        buf = self._vim.current.buffer
        ln = pos[0] - 1
        c = pos[1]

        self._dfile.write("double_finish_line : cur line '%s' %s\n" % (buf[ln], len(buf[ln])))
        self._dfile.write("double_finish_line : cur char '%s'\n" % (buf[ln][c],))
        line = buf[ln].rstrip()
        line = line[:(c-1)] + line[(c):]

        if line and line[-1] != self._key:
            line += self._key
        elif not line:
            line = self._key

        c = min(c, (len(line) - 1))
        buf[ln] = line

        self._dfile.write("double_finish_line : new line '%s' %s\n" % (line, len(line)))
        self._dfile.write("double_finish_line : column %s\n" % c)

        pos = self._vim.current.window.cursor = (pos[0], max(0, pos[1] - 1))

        return ''


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

    @neovim.autocmd('BufEnter', pattern='*', eval='expand("<afile>")', sync=True)
    def autocmd_handler(self, filename):
        #  self._vim.current.line = "garbage!!! " + filename
        self._vim.command("echo 'garbage!!! %s'" % filename)

        for k, v in insert_map.items():
            self._insert_key_handlers[k] = InsertHandler(self._vim, k, v, ofd=self._dfile)
            self._dfile.write("autocmd_handler initializing %s : %s \n" % (k, v))

        for f in finishers_map:
            self._finish_key_handlers[f] = FinishLineHandler(self._vim, f, {}, ofd=self._dfile)

    def dispatch(self, args, handlers):
        try:
            key = args[0]
        except KeyError:
            # Ignore and carry on. This would be a very strange scenario
            return

        self._dfile.write("dispatch key: '%s' last_key: '%s' \n" % (key, self._last_key))
        res = key

        handler = handlers.get(key)
        self._dfile.write("dispatch key: %s handler: %s \n" % (key, handler))
        res = handler and handler.trigger(self._last_key) or ''

        self._dfile.write("dispatch key: %s result: '%s' \n" % (key, res))

        self._last_key = key
        return res

    @neovim.function('DoubleTapInsert', sync=True)
    def double_tap_insert(self, args):
        return self.dispatch(args, self._insert_key_handlers)

    @neovim.function('DoubleTapFinishLine', sync=True)
    def double_tap_finish_line(self, args):
        return self.dispatch(args, self._finish_key_handlers)
