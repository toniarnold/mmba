# Nur die Patches, die für die Runtime auch tatsächlich benötigt werden:
PD = _main.pd thumb.png \
     bulb.pd bulbs_r_s.pd \
     lfo.pd lfos_r_s.pd targets_r_s.pd \
     rg.pd sf.pd sg.pd \
     spigot8.pd 4spigot.pd \
     prepent.pd scale.pd speedlim.pd

CD = countdown.pd bulb.pd

.PHONY: clean

all: bulbs.pdz countdown.pdz

bulbs.pdz: $(PD)
	mkdir bulbs
	cp $(PD) bulbs
	zip -r bulbs.pdz bulbs
	rm -r bulbs

countdown.pdz: $(CD)
	mkdir countdown
	cp $(CD) countdown
	mv countdown/countdown.pd countdown/_main.pd
	zip -r countdown.pdz countdown
	rm -r countdown


clean:
	-rm bulbs.pdz
	-rm countdown.pdz

