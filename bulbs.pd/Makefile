# Nur die Patches, die für die Runtime auch tatsächlich benötigt werden:
PD = _main.pd thumb.png info.json \
     bulb.pd bulbs_r_s.pd \
     lfo.pd lfos_r_s.pd targets_r_s.pd \
     preset.pd presets_r_s.pd \
     rg.pd sf.pd sg.pd \
     spigot8.pd 4spigot.pd \
     prepent.pd scale.pd speedlim.pd \
     peerreceive.pd peersend.pd \
     localcontrol.pd localgui.pd \
     rp.pd sp.pd spg.pd
     
CD = bulb.pd

.PHONY: clean

all: bulbs.pdz

bulbs.pdz: $(PD)
	mkdir bulbs
	cp $(PD) bulbs
	zip -r bulbs.pdz bulbs
	rm -r bulbs

clean:
	-rm bulbs.pdz
	-rm countdown.pdz

