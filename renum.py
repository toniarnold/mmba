#!/usr/bin/python3

import argparse
import re
import sys

helptext="./renum.py 1lfo.pd 3  Nummeriert direkt in der Datei 1lfo.pd alle send/receive wie s_lfo_1 neu mit s_lfo_3" 
parser = argparse.ArgumentParser(description=helptext)
parser.add_argument("name", type=str, help="Dateiname, z.B. 1lfo.pd")
parser.add_argument("nummer", type=int, help="Neue Nummer")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Gebe alle geänderten Zeilen auf stdtout aus")
args = parser.parse_args()

pd_name = args.name
nr = args.nummer

re_symbol = re.compile(r'\b([^_]+_[^_]+_)(\d+)\b')
with open(pd_name, "r") as pd:
    lines = pd.readlines()
with open(pd_name, "w") as pd:
    for line in lines:
        matches = re_symbol.finditer(line)
        count = 0
        for match in matches:
            count += 1
            symbol_old = match.group(0)
            symbol_only = match.group(1)
            symbol_new = symbol_only + str(nr)
            line = line.replace(symbol_old, symbol_new)
        if count and args.verbose:
            sys.stdout.write(line)
        pd.write(line)
