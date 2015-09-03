
.DEFAULT: all
.PHONY: all install

all: install

install:
	mkdir -p ~/.nvim/rplugin/python/
	rm -fv  ~/.nvim/rplugin/python/DoubleTap*
	install --verbose --mode=0644 rplugin/python/DoubleTap.py ~/.nvim/rplugin/python/
	rm -f ~/..nvimrc-rplugin~
	nvim -c "UpdateRemotePlugins" -c "qa"
