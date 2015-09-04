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
DEFAULT_KEY_TIMEOUT = 500


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

    def trigger(self):

        key = self._key
        if self._matching:
            # We're being fed keys while processing a double tapped situation, so ignore them
            self._dfile.write("double_tap_insert already matching key: %s\n" % key)
            return key

        # time since epoch in milliseconds
        now = int(time.time() * 1000)

        if now - self._last_key_time < self._key_timeout:
            self._last_key_time = now


            self._matching = True

            res = self.perform()

            self._matching = False
            self._last_key_time = 0

            return res

        self._dfile.write("double_tap_insert BOTTOM key: %s\n" % key)
        #  self._matching = False
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


@neovim.plugin
class DoubleTap(object):
    """Docstring for DoubleTap """

    def __init__(self, vim):
        print("__init__")
        self._vim = vim
        self._last_key = ''
        self._last_key_time = int(time.time() * 1000)
        self._matching = False

        #  self._buf = self._vim.current.buffer
        self._dfile = open('/tmp/dtout.text', "a")
        #  self._dfile.write("%s\n" % (dir(vim),))
        self._dfile.write("Instatiating...\n")

        self._insert_key_handlers = {}

    @neovim.autocmd('BufEnter', pattern='*', eval='expand("<afile>")', sync=True)
    def autocmd_handler(self, filename):
        #  self._vim.current.line = "garbage!!! " + filename
        self._vim.command("echo 'garbage!!! %s'" % filename)

        for k, v in insert_map.items():
            self._insert_key_handlers[k] = InsertHandler(self._vim, k, v, ofd=self._dfile)
            self._dfile.write("autocmd_handler initializing %s : %s \n" % (k, v))

    @neovim.function('DoubleTapInsert', sync=True)
    def double_tap_insert(self, args):
        try:
            key = args[0]
        except KeyError:
            # Ignore and carry on. This would be a very strange scenario
            return

        handler = self._insert_key_handlers.get(key)
        self._dfile.write("double_tap_insert key: %s handler: %s \n" % (key, handler))
        return (handler and handler.trigger()) or key
