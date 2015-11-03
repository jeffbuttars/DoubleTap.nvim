
.DEFAULT: all
.PHONY: all install

export XDG_CONFIG_HOME ?= $(HOME)/.config
export NVIM_HOME := $(XDG_CONFIG_HOME)/nvim

all: install

install:
	mkdir -p $(NVIM_HOME)/rplugin/python/
	rm -fv  $(NVIM_HOME)/rplugin/python/DoubleTap*
	install --verbose --mode=0644 rplugin/python/DoubleTap.py $(NVIM_HOME)/rplugin/python/
	rm -f ~/..nvimrc-rplugin~
	nvim -c 'UpdateRemotePlugins<\CR>' -c "qa"
