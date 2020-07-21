import requests
import sys

HOST = '192.168.1.140'
PORT = 12080

def  make_url(url):
    url = f'ws://{HOST}:{PORT}/json/{url}'
    print(url)
    return url

def do_http(verb, url, *args):
    jargs = { args[i]:args[i+1] for i in range(0, len(args), 2)}
    print(str(jargs))
    r = requests.request(verb, make_url(url), json=jargs)
    print('Post:', r.status_code, r.text)

def get(url):
    r = requests.get(make_url(url))
    print(r.status_code, r.text)

verb = sys.argv[1]
if verb=='get':
    get(sys.argv[2])
else:
    do_http(sys.argv[1], sys.argv[2], *sys.argv[3:])




