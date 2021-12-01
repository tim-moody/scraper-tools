#!/usr/bin/env python3

import logging
import sys
import time
import requests
import json
import pymysql.cursors
from urllib.parse import urljoin, urldefrag, urlparse, parse_qs
from requests_cache import CachedSession
from requests_cache.backends.sqlite import SQLiteCache
from basicspider.sp_lib import *

LOCAL_SETTINGS = '/library/www/html/w/LocalSettings.php'
DBPW = 'Monkey123'
WPMED_LIST = 'http://download.openzim.org/wp1/enwiki/customs/medicine.tsv'
HOME_PAGE = 'WikiProjectMed:App/IntroPage'
RETRY_SECONDS = 20
RETRY_LOOP = 10
mdwiki_list = []
mdwiki_domain = 'https://mdwiki.org'
mdwiki_db  = 'mdwiki'
mdwiki_cache  = SQLiteCache(db_path=mdwiki_db)
mdwiki_session  = CachedSession(mdwiki_db, backend='sqlite')
enwp_list = []
enwp_domain = 'https://en.wikipedia.org'
enwp_db ='http_cache'
request_paths =  []
cached_urls = []
parse_page = 'https://mdwiki.org/w/api.php?action=parse&format=json&prop=modules%7Cjsconfigvars%7Cheadhtml&page='
videdit_page = 'https://mdwiki.org/w/api.php?action=visualeditor&mobileformat=html&format=json&paction=parse&page='
uncached_urls = []
uncached_pages = []
session = CachedSession()
# session = CachedSession(cache_control=True)
# https://requests-cache.readthedocs.io/en/stable/user_guide/headers.html
status503_list = []

def main():
    global cached_urls
    global uncached_urls
    global uncached_pages

    count = -1
    print('Getting mdwiki pages')
    get_mdwiki_page_list()

    print('Getting list of cached urls')
    cached_urls = list(session.cache.urls) # all urls in cache
    print('Searching for uncached urls')
    for page in mdwiki_list:
        url = parse_page + page.replace('_', '%20').replace('/', '%2F').replace(':', '%3A').replace("'", '%27')
        url2 = videdit_page + page
        missing = False
        if url not in cached_urls:
            uncached_urls.append(url)
            missing = True
        if url2 not in cached_urls:
            uncached_urls.append(url2)
            missing = True
        if missing:
            print(page)
            uncached_pages.append(page)

    print('Ready to add more urls to cache')

def add_to_cache():
    global status503_list
    sleep_secs = 20
    status503_list = []
    for url in uncached_urls:
        print('Getting ' + url)
        for i in range(10):
            resp = session.get(url)
            if resp.status_code == 503:
                status503_list.append(url)
                print('# %i Retrying URL: %s\n', i, str(url))
                time.sleep(i * sleep_secs)
            else:
                if resp.status_code != 200:
                    print(url)
                break

def copy_cache(): # was run from mdwiki-cache/cache-tests
    src_db ='../http_cache.sqlite'
    src_db ='has_errors.sqlite'
    dest_db  = 'mdwiki'

    src = SQLiteCache(db_path=src_db)
    dest  = SQLiteCache(db_path=dest_db)

    for key in list(src.keys()):
        r = src.get_response(key)
        if not r.url.startswith('https://mdwiki.org'):
            continue
        if r.status_code != 200:
            dest.save_response(r)
        else:
            if not r.content.startswith(b'{"error":'):
                # save in dest
                dest.save_response(r)
            else:
                # get without a 503 error
                sleep_secs = 20
                url = r.url
                print("Downloading from URL: %s\n", str(url))
                for i in range(10):
                    resp = requests.get(url)
                    if not resp.content.startswith(b'{"error":'):
                        dest.save_response(resp)
                        break
                    else:
                        print('# %i Retrying URL: %s\n', i, str(url))
                        time.sleep(i * sleep_secs)


def find_to_encode():
    for u in cached_urls:
        if '?action=parse' in u and '&page=' in u:
            page = u.split('&page=')[1]
            if ':' in page or "'" in page or '/' in page or '_' in page:
                print(page)

def find_in_cache(match):
    for u in cached_urls:
        if match in u:
            print(u)

def write_list(data, file):
    with open(file, 'w') as f:
        for d in data:
            f.write(d + '\n')

def get_mdwiki_page_list():
    global mdwiki_list
    mdwiki_list = []
    mdwiki_list.append(HOME_PAGE)

    # q = 'https://mdwiki.org/w/api.php?action=query&apnamespace=' + namesp + '&format=json&list=allpages&aplimit=max&apcontinue='
    q = 'https://mdwiki.org/w/api.php?action=query&apnamespace=0&format=json'
    q += '&list=allpages&apfilterredir=nonredirects&aplimit=max&apcontinue='
    apcontinue = ''
    loop_count = -1
    while(loop_count):
        try:
            r = requests.get(q + apcontinue).json()
        except Exception as error:
            logging.error(error)
            logging.error('Request failed. Exiting.')
            sys.exit(1)
        pages = r['query']['allpages']
        apcontinue = r.get('continue',{}).get('apcontinue')
        for page in pages:
            mdwiki_list.append(page['title'].replace(' ', '_'))
        if not apcontinue:
            break
        loop_count -= 1

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
