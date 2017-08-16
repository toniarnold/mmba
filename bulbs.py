#!/usr/bin/python3

# Webserver, welcher via REST-API mit den myStrom-Bulbs kommuniziert,
# um von Pure Data Requests im FUDI-Protokoll entgegenzunehmen,
# diese in myStrom REST-Requests umzuwandeln und die JSON-Response
# der Bulb wieder im FUDI-Protokoll zurückzuleiten.
#
# sudo systemctl enable bulbs.service
# sudo service start bulbs
# sudo service stop bulbs

# Netzwerk-Konfiguration entsprechend bulbs_r_s.pd
PORT_PY = 8081
PORT_PD = 8082
HOST_PD = "dahomey"
PORT_PD_PEER = 8083

# Bulbs jeweils DNS-Name : MAC-Adresse
BULBS = {
    "eingang" : "5CCF7FA0C8B4",
    "mitte" : "5CCF7FA0CA06",
}

# Ab dieser Warteschlangenlänge werden weitere Requests ignoriert
MAX_PUFFER = 25




import argparse
import pprint
pp = pprint.PrettyPrinter(width=1)
import collections
import doctest
import time
import datetime
import urllib.request
import urllib.parse
import json
import colorsys
import asyncio
import socket
import random
import numpy as np




bulb_namen = ", ".join(sorted(BULBS.keys()))
helptext = """Webserver, welcher via REST-API über Port {0} 
    mit den mystrom-Bulbs kommuniziert. Registrierte Bulbs:
    """.format(PORT_PY) + bulb_namen
parser = argparse.ArgumentParser(description=helptext)
parser.add_argument("-v", "--verbose", action="store_true",
    help="""Request/Response-Logging. Gebe auch doctest 
    output auf stdout aus.""")
parser.add_argument("-t", "--test", action="store_true",
    help="""ühre doctest aus. Setzt die
        Original-Bulbs-Konfiguration voraus.""")
parser.add_argument("-p", "--profile", type=int, metavar='N', nargs='?',
    default=0, const=10,
    help="""Messe die Performance der Kommunikation mit den 
        deklarierten Bulbs mit N Wiederholungen.""")
parser.add_argument("-m", "--mock", type=float, metavar='SEC', nargs='?',
    default=0.0, const=0.1,
    help="""Kommuniziere nicht mit den Bulbs, antworte nach SEC
        Sekunden Wartezeit mit einer konstanten Stub-Message.""")
args = parser.parse_args()




# ============ Profiler ============

# Verwendete Messreihen
echo_times = []
post_times = []
netsend_times = []

def pprint_times():
    print("\nEcho-Antwortzeiten")
    pp.pprint(percentiles(echo_times))
    print("Reine Bulb-Antwortzeiten")
    pp.pprint(percentiles(post_times))
    print("netsend Reply-Zeiten")
    pp.pprint(percentiles(netsend_times))


def profile(times):
    """Profile-Dekorator für Performance-Tests von Funktionen,
    hängt die gemessene Zeit an die übergebene times-Liste an.
    """
    def wrap(func):
        if args.profile:
            def timed_func(*args, **kw):
                begin = time.time()
                retval = func(*args, **kw)
                end = time.time()
                times.append(end - begin)
                return retval
            return timed_func
        else:
            return func
    return wrap


def percentiles(times):    
    """Dictionary mit Perzentilen der Performance-Verteilung
    Minimum, unteres Viertel, Median, oberes Viertel, Maximum
    
    >>> a = [.001, .003, .005, .007, .01]
    >>> percentiles(a)
    OrderedDict([('min', 1), ('1/4', 3), ('med', 5), ('3/4', 7), ('max', 10)])
    """
    if times:
        p = np.percentile(times, [0, 25, 50, 75, 100])
        d = collections.OrderedDict()
        def ms(sec):
            return int(round(sec * 1000, 0))
        d['min'] = ms(p[0])
        d['1/4'] = ms(p[1])
        d['med'] = ms(p[2])
        d['3/4'] = ms(p[3])
        d['max'] = ms(p[4])
        return d

    

def now():
    """String-Zeitstempel für args.verbose
    """
    now = datetime.datetime.now()
    return now.strftime('%H:%M:%S.%f')



 
# ============ Kommunikation bulbs.py -> Bulb ============

def url(bulb):
    """Generiere Bulb-URL aus dem Namen
    
    >>> url("mitte")
    'http://mitte/api/v1/device/5CCF7FA0CA06'
    """
    host = bulb
    mac = BULBS[bulb]
    return "http://{0}/api/v1/device/{1}".format(host, mac)


@profile(post_times)
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
    if args.mock:   # Nur Mock-Request zur Analyse von issue #1
        if args.verbose:
            print("Mock post({0}) mit sleep({1})".format(command, args.mock))
        time.sleep(args.mock)
        values = {'on': True, 'notifyurl': '', 'ramp': 100, 'color': '90;80;70', 'mode': 'hsv'}
        current[bulb] = values
        return values
    
    request = urllib.request.Request(url(bulb))
    request.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
    if not command is None:
        data = urllib.parse.urlencode(command, safe=';')
        data = data.encode('utf-8')
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
    """Frage bei der Initialisierung aktuelle Werte aller Bulbs ab
    
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




# ============ Kommunikation bulbs.py -> PureData ============

def netsend(ip, bulb, values):
    """Entspricht netsend zu netreceive in pd"""
    messages = fudi(bulb, values)
    if args.verbose:
        print("{} {} >PD:   {}".format(now(), tiefe, messages.replace('\n', ' ')))
    netsend_socket(ip, PORT_PD, messages)

    
@profile(netsend_times)
def netsend_socket(ip, port, messages):
    """Direkt den messages-String an die ip und port senden"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    sock.sendall(bytes(messages, 'ascii'))  # "ASCII text messages compatible with Pd"
    sock.close()


def fudi(bulb, values):
    r"""Erzeuge aus der Bulb-Reply eine netsend-Reply im FUDI-Protokoll für ein retreceive-Feedback im GUI
    
    >>> ack = {'on': True, 'notifyurl': '', 'ramp': 100, 'color': '90;80;70', 'mode': 'hsv'}
    >>> msg = fudi('mitte', ack)
    >>> msg == 'bulb;\nmitte;\non;\n1;\nhue;\n90;\nsat;\n80;\nval;\n70;\nrgb;\n-6992420;\neof;\n'
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
    
    >>> rgb_2_color(255, 255, 255)
    -16777216
    >>> rgb_2_color(0, 0, 0)
    -1
    """
    val = - 1 - ((r * 256 * 256) + (g * 256) + b)
    return val




# ============ Event Loop Handler ============

# Tiefe der Verschachtelung asynchroner Aufrufe, entspricht Warteschlangenlänge
tiefe = 0

@asyncio.coroutine
def handle_echo(reader, writer):
    """Nehme Kommandos von PureData entgegen und sende sie an die Bulb
    
    netcat -l 8081
    nc localhost 8081
    nc dahomey.local 8081
    """
    # Verhindere minutenlange Warteschlangen
    global tiefe
    if tiefe >= MAX_PUFFER:
        if args.verbose:
            print("{} {} !PD:   >MAX_PUFFER".format(now(), tiefe + 1))
        # Gib auf, aber stoppe zuvor alle hängigen Requests
        for task in asyncio.Task.all_tasks():
            task.cancel()
        writer.close()
        return
    tiefe += 1
    
    try:
        # Als coroutine kein @profile(echo_times) möglich, da formal sofort return
        if args.profile:
            beginrequest = time.time()

        (request_ip, _) = writer.get_extra_info('peername')

        # Schritt 1: Handle und beende den Request von pd
        data = yield from reader.read(255) 
        puredata = data.decode().strip()
        if args.verbose:
            print("{} {} <PD:   {}".format(now(), tiefe, repr(puredata)))
        # issue #1 race condition: >1 netsend commands get joined when they pile up
        # causes 'socket.send() raised exception.' when pd is not listeing no more
        messages = filter(None, puredata.split(';'))
        for msg in messages:
            peer_ip = None
            command = None
            
            bulb, *cmdarg = msg.strip().split()
            if not cmdarg and bulb == 'peer_ip':    # Hook: IP-Adresse des iOS-Clients zurückmelden
                peer_ip = request_ip
                if args.verbose:
                    print("Client: {0}".format(peer_ip))
            elif cmdarg and (len(cmdarg) == 2):     # ignoriere ill-formed cmd arg
                cmd, arg = cmdarg
                x = int(float(arg))  # pd sliders sind 0..1
                command = commands[cmd](bulb, x)       
            # issue #1: don't wait for a reply in pd
            yield from writer.drain()
            writer.close()

            if peer_ip:
                # Peer-IP synchron an den Server melden, wenn der Request vom iOS-Client kommt
                peer_ip_fudi = "peer_ip {0};".format(peer_ip) # FUDI
                if args.verbose:
                    print(">{0}:{1} {2}".format(HOST_PD, PORT_PD, peer_ip_fudi))
                try:
                    netsend_socket(HOST_PD, PORT_PD_PEER, peer_ip_fudi)
                    netsend_socket(HOST_PD, PORT_PD_PEER, "localcontrol 1;")
                    netsend_socket(HOST_PD, PORT_PD_PEER, "localgui 0;")
                    netsend_socket(peer_ip, PORT_PD_PEER, "localcontrol 0;")
                    netsend_socket(peer_ip, PORT_PD_PEER, "localgui 1;")
                except ConnectionRefusedError:
                    if args.verbose:
                        print("No local PureData on port {0}".format(PORT_PD))
                    netsend_socket(peer_ip, PORT_PD_PEER, "localcontrol 1;")
                    netsend_socket(peer_ip, PORT_PD_PEER, "localgui 1;")
               
            else:
                # Schritt 2: Request an die u.U. langsame Bulb in einem separaten Thread
                if args.verbose:
                    print("{} {} >Bulb: {}".format(now(), tiefe, command)) 
                reply = yield from loop.run_in_executor(None, post, bulb, command)
                if args.verbose:
                    print("{} {} <Bulb: {}".format(now(), tiefe, reply))
                # Sende Response mit netsend an das netreceive in pd
                yield from loop.run_in_executor(None, netsend, request_ip, bulb, reply)
                
        if args.profile:
            endresponse = time.time()
            echo_times.append(endresponse - beginrequest)
    
    finally:
        tiefe -= 1




# Performance-Profiling ausführen
if args.profile:
    count = args.profile
    print("Starte Bulb-Profiling mit {0} Wiederholungen".format(count))
    profiles = collections.OrderedDict()
    for bulb in BULBS.keys():
        # Timer-Listen-Dictionaries leer initialisieren
        times_bang = []
        times_on = []
        times_color = []
        bulb_profile = collections.OrderedDict([
            ('bang', times_bang),
            ('on', times_on),
            ('color', times_color),
        ])
        profiles[bulb] = bulb_profile
        
        # Jeden Request-Typ einzeln messen
        for i in range(0, count):
            post(bulb)
        bulb_profile['bang'] = percentiles(post_times)
        del post_times[:]
            
        for i in range(0, count):
            post(bulb, commands['on'](bulb, random.randint(0, 1)) )
        bulb_profile['on'] = percentiles(post_times)
        del post_times[:]
                 
        for i in range(0, count):
            post(bulb, commands['hue'](bulb, random.randint(0, 99)) )
        bulb_profile['color'] = percentiles(post_times)
        del post_times[:]
                
    pp.pprint(profiles)
    print("\nProfiling von Requests geht weiter bis <ctrl>+c")
    
    
    

# Wenn verlangt alle doctests in obigen Funktionen ausführen
if args.test:
    doctest.testmod(verbose=args.verbose)




# Starte das Programm als Service 
loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_echo, '', PORT_PY, loop=loop)
server = loop.run_until_complete(coro)

# Bang an alle Bulbs
if args.verbose:
    print("Frage die konfigurierten Bulbs {0} ab".format(bulb_namen))
get_current()
if args.verbose:
    pp.pprint(current) 

if __name__ == "__main__":
    print("Starte bulbs.py server auf {}".format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        if args.profile:
            pprint_times()

    server.close()
    for task in asyncio.Task.all_tasks():
        task.cancel()
    loop.run_until_complete(server.wait_closed())
    loop.close()
