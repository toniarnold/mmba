# Simples Makefile für mmda - Modular MyStrom Bulb App

.PHONY: all doc bulbs clean install uninstall

all: doc bulbs bulbs.pdz countdown.pdz

doc:
	$(MAKE) -C doc

bulbs:
	$(MAKE) -C bulbs.pd

bulbs.pdz: bulbs.pd/bulbs.pdz
	cp bulbs.pd/bulbs.pdz ./

countdown.pdz: bulbs.pd/countdown.pdz
	cp bulbs.pd/countdown.pdz ./

clean:
	-rm bulbs.pdz
	-rm countdown.pdz

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
