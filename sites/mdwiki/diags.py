#!/usr/bin/env python3

import os,sys
import requests
from urllib.parse import urljoin, urldefrag, urlparse

from basicspider.sp_lib import *

c = 'cache-urls-21-11-19.txt'

f = open(c,'r')
urls = f.readlines()

for u in urls:
    if u[0] == '/':
        r = requests.get('https://mdwiki.org' + u.rstrip())
        if '{"error":' in r.text:
            print(u)
            print(r.text)

for u in urls:
    if u[0] == '/':
        r = requests.get('https://mdwiki.org' + u.rstrip())
        if r.status_code != 200:
            print(r.status_code, u)

for u in urls:
    if u[0] == '/':
        if '&prop=redirects' in u:
            print(u)
