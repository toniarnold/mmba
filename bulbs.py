#!/usr/bin/python3

# Webserver, welcher via REST-API mit den mystrom-Bulbs kommuniziert
# um von Pure Data Requests entgegenzunehmen.
#
# sudo service start bulbs
# sudo service stop bulbs

PORT = 8081
BULBS = {
    "eingang" : "5CCF7FA0C8B4",
    "mitte" : "5CCF7FA0CA06",
}


import argparse
import doctest
import time
import urllib.request
import urllib.parse
import json
import colorsys
import asyncio


bulb_namen = ", ".join(sorted(BULBS.keys()))
helptext="""Webserver, welcher via REST-API über Port {0} 
    mit den mystrom-Bulbs kommuniziert. Registrierte Bulbs:
    """.format(PORT) + bulb_namen
parser = argparse.ArgumentParser(description=helptext)
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Gebe auch doctest output auf stdout aus")
args = parser.parse_args()



# Kommunikation mit der Bulb

def url(bulb):
    """Generiere Bulb-URL aus dem Namen
    
    >>> url("mitte")
    'http://mitte/api/v1/device/5CCF7FA0CA06'
    """
    host = bulb
    mac = BULBS[bulb]
    return "http://{0}/api/v1/device/{1}".format(host, mac)


def post(bulb, command=None):
    """Sende ein HTTP POST Kommando an die Bulb, dump ohne command
    
    >>> ack = post("mitte", {'color':'90;80;70', 'action':'on'})
    >>> ack == {'on': True, 'notifyurl': '', 'ramp': 100, 'color': '90;80;70', 'mode': 'hsv'}
    True
    
    >>> time.sleep(1)   # wg. 'power'
    >>> info = post("mitte")
    >>> info == {'mode': 'hsv', 'battery': False, 'on': True, 'fw_version': '2.25', 'color': '90;80;70', 'reachable': True, 'ramp': 100, 'type': 'rgblamp', 'meshroot': False, 'power': 2.975}
    True
    """
    request = urllib.request.Request(url(bulb))
    request.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8')
    if not command is None:
        data = urllib.parse.urlencode(command, safe=';')
        data = data.encode('ascii")
        f = urllib.request.urlopen(request, data)
    else:
        f = urllib.request.urlopen(request)
    response = f.read().decode('utf-8')
    response_dict = json.loads(response)
    mac, values = next(iter(response_dict.items()))
    current[bulb] = values
    return values


current = {}

def get_current():
    """ Frage bei der Initialisierung aktuelle Werte aller Bulbs ab
    
    >>> get_current()
    >>> sorted(current.keys())
    ['eingang', 'mitte']
    """
    for bulb in BULBS.keys():
        post(bulb)

        
# Übersetzung json-Response nach POST-Kommandos

commands = {
    'on' : lambda bulb, x : {
             0 : {'action' : 'off'},
             1 : {'action' : 'on'},
        }[x],
    'hue' : lambda bulb, x : hue(bulb, x),
    'sat' : lambda bulb, x : sat(bulb, x),
    'val' : lambda bulb, x : val(bulb, x),
}

def hue(bulb, x):
    """Setze den Hue-Wert im HSV-Tripel
    
    >>> current['mitte'] = {'color' : '12;34;56'}
    >>> hue('mitte', '99')
    {'color': '99;34;56'}
    """
    h, s, v = split_color(current[bulb]['color'])
    return {'color' : '{0};{1};{2}'.format(x, s, v) }

def sat(bulb, x):
    """Setze den Saturation-Wert im HSV-Tripel
    
    >>> current['mitte'] = {'color' : '12;34;56'}
    >>> sat('mitte', '99')
    {'color': '12;99;56'}
    """
    h, s, v = split_color(current[bulb]['color'])
    return {'color' : '{0};{1};{2}'.format(h, x, v) }

def val(bulb, x):
    """Setze den Value-Wert im HSV-Tripel
    
    >>> current['mitte'] = {'color' : '12;34;56'}
    >>> val('mitte', '99')
    {'color': '12;34;99'}
    """
    h, s, v = split_color(current[bulb]['color'])
    return {'color' : '{0};{1};{2}'.format(h, s, x) }

def split_color(color):
    """Weiss wird ohne hue, tiefem sat und val 100 geliefert
    
    >>> h, s, v = split_color("123;45;6")
    >>> h
    '123'
    >>> s
    '45'
    >>> v
    '6'
    >>> h, s, v = split_color("2;100")
    >>> h
    '0'
    >>> s
    '2'
    >>> v
    '100'
    """
    hsv = color.split(';')
    h = '0'
    s = '0'
    v = '0'
    if len(hsv) == 3:
        h = hsv[0]
        s = hsv[1]
        v = hsv[2]  
    elif  len(hsv) == 2:
        s = hsv[0]
        v = hsv[1]
    return h, s, v


def netreceive(bulb, values):
    r"""Erzeuge aus der Bulb-Reply eine netreceive-Reply für das Feedback im GUI
    
    >>> ack = {'on': True, 'notifyurl': '', 'ramp': 100, 'color': '90;80;70', 'mode': 'hsv'}
    >>> msg = netreceive('mitte', ack)
    >>> msg == 'bulb;\nmitte;\non;\n1;\nhue;\n90;\nsat;\n80;\nval;\n70;\nrgb;\n-6992419;\neof;\n'
    True
    """
    on = 1 if values['on'] else 0
    h, s, v = split_color(values['color'])
    r, g, b = hsv_2_rgb(h, s, v)
    rgb = rgb_2_color(r, g, b)
    return """bulb;
{0};
on;
{1};
hue;
{2};
sat;
{3};
val;
{4};
rgb;
{5};
eof;
""".format(bulb, on, h, s, v, rgb)
    

def hsv_2_rgb(h, s, v):
    """Konversion inklusive Abbildung der Bulb-HSV-Wertebereiche zu RGB
    >>> hsv_2_rgb(0, 0, 100)
    (255, 255, 255)
    """
    h = float(h) / 359.0
    s = float(s) / 100.0
    v = float(v) / 100.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    r = int(r * 255.0)
    g = int(g * 255.0)
    b = int(b * 255.0)
    return r, g, b    


def rgb_2_color(r, g, b):
    """Konversion RGB zu PureData RGB color
    >>> rgb_2_color(0, 0, 255)
    -255
    >>> rgb_2_color(0, 255, 0)
    -65280
    >>> rgb_2_color(255, 0, 0)
    -16711680
    >>> rgb_2_color(255, 255, 255)
    -16777215
    >>> rgb_2_color(0, 0, 0)
    -1
    """
    val = - ((r * 256 * 256) + (g * 256) + b)
    val = - 1 if val == 0 else val  # Spezialfall Scwarz: kein negatives -0 trotz float
    return val


@asyncio.coroutine
def handle_echo(reader, writer):
    """Nehme Kommandos von PureData entgegen und sende sie an die Bulb
    Teste mit 
    netcat -l 8081
    nc localhost 8081
    nc dahomey.local 8081
    """
    data = yield from reader.read(255)
    puredata = data.decode().strip()
    if args.verbose:
        print("PureData: {}".format(repr(puredata)))
    bulb, cmd, x = puredata[:-1].split()  # entferne ;
    x=int(float(x))  # pd sliders sind float
    command = commands[cmd](bulb, x)
    if args.verbose:
        print("Command: {}".format(command))
    reply=post(bulb, command)
    if args.verbose:
        print("Reply: {}".format(reply))
    messages = netreceive(bulb, reply)
    writer.write(bytes(messages, 'utf-8'))
    yield from writer.drain()
    writer.close()


    
# Bei --verbose Ausgabe auf stdout
doctest.testmod()

    
# Starte das Programm als Service

get_current()
if args.verbose:
    print(current)    
    
loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_echo, '', PORT, loop=loop)
server = loop.run_until_complete(coro)

print('Starte bulbs.py server auf {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
