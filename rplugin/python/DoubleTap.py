from __future__ import print_function
import neovim


@neovim.plugin
class DoubleTap(object):
    """Docstring for DoubleTap """

    def __init__(self, vim):
        print("__init__")
        self._vim = vim
        self._buf = self._vim.current.buffer
        self._dfile = open('/tmp/dtout.text', "w")

        self._dfile.write("%s\n" % (dir(vim),))
        self.key_subscribe('(', 'dti')

    def key_subscribe(self, key, to):
        cid = self._vim.channel_id
        self._dfile.write("key_subscribe %s %s cid:%s\n" % (key, to, cid))
        self._vim.command('imap %s )')
        #  self._vim.command(
        #      ('inoremap <silent> <buffer> %s :call rpcnotify(%d, "keypress", "%s")<cr>') %
        #      (key, cid, to))
 
    def key_unsubscribe(self, key):
        self.vim.command('unmap <buffer> %s' % key)
 
    #  #  imap <silent><expr> %s DoubleTapInsert( \"%s\", \"%s\", \"%s\" )
    #  #  @neovim.autocmd('FileType', pattern='*.*', eval="imap <slient><expr> ( DoubleTapInsert()",
    #  #                  sync=True)
    #  @neovim.autocmd('FileType', pattern='*.*', eval='expand("<afile>")',
    #                  sync=True)
    #  def char_insert_acm(self, *args, **kwargs):
    #      print "char_insert_acm"
    #      self._vim.current.line = 'char_insert_acm: Called with %s and %s' % (args, kwargs)

    #  @neovim.function('DoubleTapInsert')
    #  def double_tap_insert(self, *args, **kwargs):
    #      print "double_tap_insert"
    #      self._vim.current.line = 'double_tap_insert: Called with %s and %s' % (args, kwargs)

    @neovim.rpc_export('keypress')
    def keypress(self, key, to=None):
        print("key:", key)
        self._dfile.write("key: %s, to: %s\n" % key, to)
