# Simples Makefile für mmda - Modular MyStrom Bulb App

.PHONY: all doc bulbs install uninstall

all: doc bulbs bulbs.pdz

doc:
	$(MAKE) -C doc

bulbs:
	$(MAKE) -C bulbs.pd

bulbs.pdz: bulbs.pd/bulbs.pdz
	cp -u bulbs.pd/bulbs.pdz ./

install:
	cp bulbs.py /etc/network/
	cp bulbs.service /etc/systemd/system 
	systemctl enable bulbs.service
	systemctl start bulbs.service

uninstall:
	-systemctl stop bulbs.service
	-systemctl disable bulbs.service
	-rm /etc/systemd/system/bulbs.service 
	-rm /etc/network/bulbs.py