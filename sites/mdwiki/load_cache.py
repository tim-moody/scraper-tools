#!/usr/bin/env python3

import logging
import sys
import datetime
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
mdwiki_uncached_session  = CachedSession(mdwiki_db, backend='sqlite', expire_after=0)
mdwiki_changed_list = []
mdwiki_changed_rd = []
enwp_list = []
enwp_domain = 'https://en.wikipedia.org'
enwp_db ='http_cache'
request_paths =  []
mdwiki_cached_urls = []
mdwiki_uncached_urls = []
mdwiki_uncached_pages = []

parse_page = 'https://mdwiki.org/w/api.php?action=parse&format=json&prop=modules%7Cjsconfigvars%7Cheadhtml&page='
videdit_page = 'https://mdwiki.org/w/api.php?action=visualeditor&mobileformat=html&format=json&paction=parse&page='

# session = CachedSession(cache_control=True)
# https://requests-cache.readthedocs.io/en/stable/user_guide/headers.html
status503_list = []

def main():
    global mdwiki_cached_urls
    global mdwiki_uncached_urls
    global mdwiki_uncached_pages

    set_logger()

    last_day_of_prev_month = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
    start_day_of_prev_month = datetime.date.today().replace(day=1) - datetime.timedelta(days=last_day_of_prev_month.day)
    refresh_cache_since = start_day_of_prev_month.strftime('%Y-%m-%dT%H:%M:%SZ')

    refresh_cache_since = '2021-12-11T00:00:00Z'

    logging.info('Refreshing cached pages with changes since: %s\n', str(refresh_cache_since))

    refresh_cache(refresh_cache_since)
    logging.info('Cache refreshed\n')

def refresh_cache(since):
    get_mdwiki_changed_page_list(since)
    for page in mdwiki_changed_list:
        refresh_cache_page(page)

def refresh_cache_page(page):
    # verify space or underscore
    # get_mdwiki_changed_page_list converts
    # find_in_cache('Heart_failure')
    # https://mdwiki.org/w/api.php?action=visualeditor&mobileformat=html&format=json&paction=parse&page=Heart_failure
    # https://mdwiki.org/w/api.php?action=query&format=json&prop=revisions&rdlimit=max&rdnamespace=0%7C3000&redirects=true&titles=Heart_failure
    # N.B find_in_cache('Heart failure') returns nothing
    # so in cache all spaces converted to underscore
    # same in mdwikimed.tsv, so already done at source

    # logging.info('Refreshing cache for page: %s\n', str(page))

    url = parse_page + page.replace('_', '%20').replace('/', '%2F').replace(':', '%3A').replace("'", '%27').replace("+", '%2B')
    refresh_cache_url(url)
    url2 = videdit_page + page
    refresh_cache_url(url2)

def refresh_cache_url(url):
    r = mdwiki_uncached_session.get(url)
    if r.status_code == 503 or r.content.startswith(b'{"error":'):
        r = retry_url(url)
    if r:
        mdwiki_cache.save_response(r)
    else:
        logging.info('Failed to get URL: %s\n', str(url))

def retry_url(url):
    logging.info("Error or 503 in URL: %s\n", str(url))
    sleep_secs = 20
    for i in range(10):
        resp = requests.get(url)
        if resp.status_code != 503 and not resp.content.startswith(b'{"error":'):
            return resp
        logging.info('Retrying URL: %s\n', str(url))
        time.sleep(i * sleep_secs)
    return None

def load_cache():
    global mdwiki_cached_urls
    global mdwiki_uncached_urls
    global mdwiki_uncached_pages
    count = -1
    print('Getting mdwiki pages')
    get_mdwiki_page_list()

    print('Getting list of cached urls')
    mdwiki_cached_urls = list(mdwiki_session.cache.urls) # all urls in cache
    print('Searching for uncached urls')
    for page in mdwiki_list:
        url = parse_page + page.replace('_', '%20').replace('/', '%2F').replace(':', '%3A').replace("'", '%27')
        url2 = videdit_page + page
        missing = False
        if url not in mdwiki_cached_urls:
            mdwiki_uncached_urls.append(url)
            missing = True
        if url2 not in mdwiki_cached_urls:
            mdwiki_uncached_urls.append(url2)
            missing = True
        if missing:
            print(page)
            mdwiki_uncached_pages.append(page)

def add_to_cache():
    global status503_list
    sleep_secs = 20
    status503_list = []
    for url in mdwiki_uncached_urls:
        print('Getting ' + url)
        for i in range(10):
            resp = mdwiki_session.get(url)
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
    for u in mdwiki_cached_urls:
        if '?action=parse' in u and '&page=' in u:
            page = u.split('&page=')[1]
            if ':' in page or "'" in page or '/' in page or '_' in page:
                print(page)

def find_in_cache(match):
    for u in mdwiki_cached_urls:
        if match in u:
            print(u)

def write_list(data, file):
    with open(file, 'w') as f:
        for d in data:
            f.write(d + '\n')

# https://www.mdwiki.org/w/api.php?action=query&format=json&list=recentchanges&rctoponly&rcstart=now&rcend=2021-11-01T00:00:00Z

# rcnamespace=0|4
# https://www.mdwiki.org/w/api.php?action=query&format=json&list=recentchanges&rclimit=max&rcnamespace=0|4&rctoponly&rcstart=now&rcend=2021-11-01T00:00:00Z
# changed_pages = 'https://www.mdwiki.org/w/api.php?action=query&format=json&list=recentchanges' # &rcend=2021-11-01T00:00:00Z &rctoponly

# "query":{"recentchanges":[{"type":"edit","ns":0,title":"Metastatic liver disease","pageid":61266,"revid":1274552,"old_revid":1274551,
# "rcid":144650,"timestamp":"2021-12-10T11:32:54Z"}, ... ]

def get_mdwiki_changed_page_list(since):
    global mdwiki_changed_list
    global mdwiki_changed_rd
    mdwiki_changed_list = []
    mdwiki_changed_rd = []
    #since = '2021-11-01T00:00:00Z'
    # q = 'https://www.mdwiki.org/w/api.php?action=query&format=json&list=recentchanges&rclimit=max&rcnamespace=0|4&rctoponly'
    q = 'https://www.mdwiki.org/w/api.php?action=query&format=json&list=recentchanges&rclimit=max&rctoponly&rcprop=redirect|title'
    q += '&rcnamespace=0&rcstart=now&rcend=' + since
    rccontinue_param = ''
    loop_count = -1
    while(loop_count):
        try:
            r = requests.get(q + rccontinue_param).json()
        except Exception as error:
            logging.error(error)
            logging.error('Request failed. Exiting.')
            sys.exit(1)
        pages = r['query']['recentchanges']
        rccontinue = r.get('continue',{}).get('rccontinue')
        print(rccontinue)
        for page in pages:
            if page in mdwiki_changed_list:
                print(page + ' encountered more than once')
            if page.get('redirect') == '':
                mdwiki_changed_rd.append(page['title'].replace(' ', '_'))
            else:
                mdwiki_changed_list.append(page['title'].replace(' ', '_'))
        if not rccontinue:
            break
        rccontinue_param = '&rccontinue=' + rccontinue
        loop_count -= 1

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

def set_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s',
                                '%m-%d-%Y %H:%M:%S')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('mdwiki-cache.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
