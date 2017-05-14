DIA = $(wildcard *.dia)
PNG = $(DIA:.dia=.png)

.PHONY: png clean

png: $(PNG)

%.png: %.dia
	dia $< --export $@

clean:
	rm *.png
