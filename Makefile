
.DEFAULT: all
.PHONY: all install
PFILE := DoubleTap2.py

export XDG_CONFIG_HOME ?= $(HOME)/.config
export NVIM_HOME := $(XDG_CONFIG_HOME)/nvim

all: install

install:
	mkdir -p $(NVIM_HOME)/rplugin/python/
	rm -fv  $(NVIM_HOME)/rplugin/python/DoubleTap* $(HOME)/.local/share/nvim/rplugin.vim
	install --verbose --mode=0644 rplugin/python/$(PFILE) $(NVIM_HOME)/rplugin/python/
	nvim -c 'UpdateRemotePlugins' -c "qa" /tmp/doubletabe_make.tmp
