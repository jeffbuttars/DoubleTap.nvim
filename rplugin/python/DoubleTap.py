import neovim
import time

insert_map = {
        '(': {'l': '(', 'r': ')'},
        '"': {'l': '"', 'r': '"'},
        "'": {'l': "'", 'r': "'"},
        }


@neovim.plugin
class DoubleTap(object):
    """Docstring for DoubleTap """

    def __init__(self, vim):
        print("__init__")
        self._vim = vim
        self._last_key = ''
        self._last_key_time = int(time.time() * 1000)
        self._key_timeout = 1000
        self._matching = False

        #  self._buf = self._vim.current.buffer
        self._dfile = open('/tmp/dtout.text', "a")
        #  self._dfile.write("%s\n" % (dir(vim),))
        self._dfile.write("Instatiating...\n")

    @neovim.autocmd('BufEnter', pattern='*.c', eval='expand("<afile>")', sync=True)
    def autocmd_handler(self, filename):
        #  self._vim.current.line = "garbage!!! " + filename
        self._vim.command("echo 'garbage!!! %s'" % filename)
        for k in insert_map:
            self.key_subscribe(k)

    @neovim.function('DoubleTapInsert', sync=True)
    def double_tap_insert(self, args):
        key = args[0]

        if self._matching:
            self._dfile.write("double_tap_insert already matching key: %s\n" % key)
            return key

        pos = self._vim.current.window.cursor
        self._dfile.write("double_tap_insert key: %s\n" % key)
        self._dfile.write("double_tap_insert : window pos %s\n" % pos)
        if self._last_key == key and key in insert_map:
            buf = self._vim.current.buffer
            ln = pos[0] - 1
            line = buf[ln]
            lp = pos[1]

            self._matching = True
            self._last_key = ''
              line[lp] = insert_map[key]['r']
            bl = line[:lp -1]
            el = line[lp:]
            self._dfile.write("double_tap_insert : line %s\n" % ln)
            buf[ln] = bl + insert_map[key]['r'] + el
            self._vim.current.window.cursor = (pos[0], lp -1)
            self._matching = False
            return insert_map[key]['l']

        self._dfile.write("double_tap_insert BOTTOM key: %s\n" % key)
        self._matching = False
        self._last_key = key
        self._last_key_time = int(time.time() * 1000)
        return key

    def key_subscribe(self, key):
        cid = self._vim.channel_id
        self._dfile.write("key_subscribe %s cid:%s\n" % (key, cid))
        #  imap = "imap <silent><expr> %s DoubleTapInsert('%s')" % (key, key)
        imap = "imap <silent> %s <C-R>=DoubleTapInsert('%s')<CR>" % (key, key)
        self._dfile.write(imap + "\n")
        self._vim.command(imap)
