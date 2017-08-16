# Simples Makefile für mmda - Modular MyStrom Bulb App
# "make install" installiert sowohl das bulbs.py-Server-Skript
# als auch das binär identische PureData bulbs.pdz als Server-Dienste.
# Manuell starten:
# sudo service bulbs-py start
# sudo service bulbs-pd start

.PHONY: all doc bulbs clean install uninstall \
        install-pd uninstall-pd install-py uninstall-py

all: doc bulbs bulbs.pdz

doc:
	$(MAKE) -C doc

bulbs:
	$(MAKE) -C bulbs.pd

bulbs.pdz: bulbs.pd/bulbs.pdz
	cp bulbs.pd/bulbs.pdz ./

clean:
	-rm bulbs.pdz
    
install: install-py install-pd

uninstall: uninstall-py uninstall-pd

install-py:
	cp bulbs.py /etc/network/
	cp bulbs-py.service /etc/systemd/system 
	systemctl enable bulbs-py.service
	systemctl start bulbs-py.service

uninstall-py:
	-systemctl stop bulbs-py.service
	-systemctl disable bulbs-py.service
	-rm /etc/systemd/system/bulbs-py.service 
	-rm /etc/network/bulbs.py

install-pd:
	unzip bulbs.pdz -d /etc/network/
	mv /etc/network/bulbs /etc/network/bulbs.pd
	chmod 755 bulbs.pd
	cp bulbs-pd.service /etc/systemd/system 
	systemctl enable bulbs-pd.service
	systemctl start bulbs-pd.service

uninstall-pd:
	-systemctl stop bulbs-py.service
	-systemctl disable bulbs-py.service
	-rm /etc/systemd/system/bulbs-pd.service 
	-rm -r /etc/network/bulbs.pd
