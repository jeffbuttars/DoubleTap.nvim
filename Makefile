
.DEFAULT: all
.PHONY: all install
PPKG := double_tap

export XDG_CONFIG_HOME ?= $(HOME)/.config
export NVIM_HOME := $(XDG_CONFIG_HOME)/nvim

all: install

install:
	mkdir -p $(NVIM_HOME)/rplugin/python3
	rm -fv  $(NVIM_HOME)/rplugin/python3/DoubleTap*
	rm -frv $(NVIM_HOME)/rplugin/python3/double_tap*
	mkdir -p $(NVIM_HOME)/rplugin/python3/$(PPKG)
	rm -fv $(HOME)/.local/share/nvim/rplugin.vim
	install --verbose --mode=0644 rplugin/python3/$(PPKG)/* $(NVIM_HOME)/rplugin/python3/$(PPKG)/
	nvim -c 'UpdateRemotePlugins' -c "qa" /tmp/doubletabe_make.tmp
