#!/usr/bin/env python3
"""
Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""
# https://pymotw.com/3/urllib.parse/#:~:text=The%20return%20value%20from%20parse_qs,a%20name%20and%20a%20value.

# mwoffliner called urls:

# http://iiab-ref:8080/w/api.php?action=query&meta=siteinfo&format=json&siprop=general|namespaces|statistics|variables|category|wikidesc


from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import sys
import time
import requests
import json
import base64
import pymysql.cursors
from urllib.parse import urljoin, urldefrag, urlparse, parse_qs
from requests_cache import CachedSession
from basicspider.sp_lib import *

LOCAL_SETTINGS = '/library/www/html/w/LocalSettings.php'
DBPW = 'Monkey123'
WPMED_LIST = 'http://download.openzim.org/wp1/enwiki/customs/medicine.tsv'
HOME_PAGE = "WikiProjectMed:App/IntroPage"

mdwiki_list = []
mdwiki_redirect_list = []
mdwiki_rd_lookup = {}

mdwiki_domain = 'https://mdwiki.org'
enwp_list = []
enwp_domain = 'https://en.wikipedia.org'
request_paths =  []
enwp_db ='http_cache'
mdwiki_db  = 'mdwiki'

class S(BaseHTTPRequestHandler):
    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self.request_paths.append(self.path)
        # self._set_response()
        #resp = read_html_file('general.json')
        # 5 cases:
        #   is path with no titles - get_path with mdwiki_domain
        #   is redirect no titles - get_path with mdwiki_domain
        #   is redirect with titles - get_redirect
        #   is page=page on mdwiki - get_path with mdwiki_domain
        #   is page=page not on mdwiki - get_path with enwp_domain

        # args = parse_qs(urlparse(self.path).query) FUTURE

        # N.B. the param for getting pages is &page= not &title=
        # current code will just get all enwp from mdwiki

        if '&titles=' in self.path: # is a redirect or a page request
            if '&prop=redirects' in self.path:
                self.get_redir_path(self.path)
            else:
                # this is not expected for zims
                # but can happen when mirroring site
                # logging.error("Skipping Unknown Path: %s\n", str(self.path))
                self.get_mdwiki_url(self.path)
        elif '&page=' in self.path:
            # page = self.path.split('&page=')[1]
            args = parse_qs(urlparse(self.path).query)
            page = args['page'][0].replace(' ', '_')
            if page in mdwiki_list:
                self.get_mdwiki_url(self.path)
            elif page in enwp_list:
                self.get_enwp_url(self.path)
            else:
                logging.error("Skipping Unknown Page: %s\n", str(self.path))
                self.respond_404()
        else:
            self.get_mdwiki_url(self.path) # use mdwiki for anything else

    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                str(self.path), str(self.headers), post_data.decode('utf-8'))

        self._set_response()
        self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))

    def get_mdwiki_url(self, path):
        # ADD RETRY
        url = mdwiki_domain + path
        logging.info("Downloading from URL: %s\n", str(url))
        resp = self.mdwiki_session.get(url)
        if resp.status_code == 503 or resp.content.startswith(b'{"error":'):
            resp = self.retry_url(url)
        self.start_response(resp)
        self.wfile.write(resp.content)
        return

    def get_enwp_url(self, path):
        # ADD RETRY
        url = enwp_domain + path
        logging.info("Downloading from URL: %s\n", str(url))
        resp = self.enwp_session.get(url)
        if resp.status_code == 503 or resp.content.startswith(b'{"error":'):
            resp = self.retry_url(url)
        self.start_response(resp)
        self.wfile.write(resp.content)
        return

    def get_redir_path(self, path): # top level
        # path queried for redirects can have multiple titles
        # break them out because some could be mdwiki and some enwp
        # the query also requests other properties than redirect
        # process redirect separately from the other properties
        # skip enwp page redirect if is name of mdwiki page or redirect
        args = parse_qs(urlparse(path).query)
        titles = args['titles'][0].split('|')
        base_query = path.split('&titles=')[0] + '&titles='
        more_rd_query = '/w/api.php?action=query&format=json&prop=redirects&rdlimit=max&rdnamespace=0&redirects=true&titles='
        pages_resp = {}
        title_page_ids = {}
        for title in titles:
            if title in mdwiki_list: # do one mdwiki title
                #print(f'Getting redirect for {title}')
                # remove redirect from query
                query = base_query.replace('&prop=redirects%7C', '&prop=') + title
                resp = self.mdwiki_session.get(mdwiki_domain + query)
                #resp = requests.session.get(mdwiki_domain + query)
                batch_resp = json.loads(resp.content)
                mdwiki_pageid = next(iter(batch_resp['query']['pages'])) # there should only be one
                title_page_ids[title] = {}
                title_page_ids[title]['mdwiki_pageid'] = mdwiki_pageid
                page_resp = batch_resp['query']['pages'][mdwiki_pageid]
                #pages_resp[title] = {}
                #pages_resp[title][mdwiki_pageid] = page_resp
                pages_resp[mdwiki_pageid] = page_resp

                redirects = get_mdwiki_redirects(title) # all redirects for this title known to mdwiki
                pages_resp[mdwiki_pageid]['redirects'] = redirects

                # get any redirects from EN WP
                # do not include if is name of page or redirect on mdwiki
                # mdwiki is primary so we only want any unknown redirects

                #'Gefitinib' in enwp_list
                #False
                # problem is that titles in enwp_list removed if in mdwiki_list
                # excluded in mk-combined
                if title in enwp_list:
                    # now get list from enwp
                    enwp_resp = self.enwp_session.get(enwp_domain + more_rd_query + title)
                    wp_batch_resp = json.loads(enwp_resp.content)
                    enwp_pageid = next(iter(wp_batch_resp['query']['pages'])) # there should only be one
                    enwp_rd = wp_batch_resp['query']['pages'][enwp_pageid].get('redirects', []) # make it have an empty list instead of no list
                    title_page_ids[title]['enwp_pageid'] = enwp_pageid # store in case need it

                    for rd in enwp_rd:
                        if rd['title'] in mdwiki_list: # exclude because is somewhere in mdwiki titles
                            continue
                        if rd['title'] in mdwiki_redirect_list: # exclude because is somewhere in mdwiki redirects
                            continue
                        redirects.append(rd) # add it

                    #pages_resp[title][mdwiki_pageid]['redirects'] = redirects
                    pages_resp[mdwiki_pageid]['redirects'] = redirects
            else: # do one enwp title that is not in mdwiki
                resp = self.enwp_session.get(enwp_domain + base_query + title)
                #enwp_resp = requests.session.get(enwp_domain + base_query + title)
                batch_resp = json.loads(resp.content)
                enwp_pageid = next(iter(batch_resp['query']['pages'])) # there should only be one
                title_page_ids[title] = {}
                title_page_ids[title]['enwp_pageid'] = enwp_pageid
                title_rds = batch_resp['query']['pages'][enwp_pageid].get('redirects', [])

                # add any mdwiki redirects to this enwp page
                more_rds = mdwiki_rd_lookup.get(title, [])
                title_rds += more_rds

                if title_rds: # not sure if mwoffliner supports empty redirects list
                    batch_resp['query']['pages'][enwp_pageid]['redirects'] = title_rds

                page_resp = batch_resp['query']['pages'][enwp_pageid]

                pages_resp[enwp_pageid] = page_resp

        # now reassemble response for all page tiles requested
        #print('***pages_resp')
        #print(pages_resp)
        batch_resp['query']['pages'] = pages_resp
        #print('***batch_resp')
        #print(batch_resp)

        outp = json.dumps(batch_resp)
        self.start_response(resp)
        self.wfile.write(bytes(outp, "utf-8"))
        return

    def retry_url(self, url):
        logging.info("Error or 503 in URL: %s\n", str(url))
        sleep_secs = 20
        for i in range(10):
            resp = requests.get(url)
            if resp.status_code != 503 and not resp.content.startswith(b'{"error":'):
                return resp
            logging.info('Retrying URL: %s\n', str(url))
            time.sleep(i * sleep_secs)
        return None

    def respond_404(self):
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Unknown Page')

    def start_response(self, resp):
        self.send_response(resp.status_code)
        self.send_header('Content-type', resp.headers['content-type'])
        #if 'content-length' in resp.headers:
        #    self.send_header('content-length', resp.headers['content-length'])
        self.end_headers()

def get_mdwiki_redirects(rd_to_title):
    # returns list of dict of redirects to td_to_title
    rd_list = mdwiki_rd_lookup.get(rd_to_title, []) # list of rd_from_titles for rd_to_titles
    return rd_list

def get_mdwiki_redirects_from_db(rd_to_title):
    con = pymysql.connect(host='localhost',
                        user='mdwiki',
                        password=DBPW,
                        database='mdwiki_wiki',
                        cursorclass=pymysql.cursors.DictCursor)
    cursor = con.cursor()
    q = 'SELECT r.rd_from, rd_namespace, p.page_title '
    q += 'FROM redirect r '
    q += 'INNER JOIN page p ON p.page_id = r.rd_from '

    # this yields conversion error on parameter substitution
    # q += 'WHERE r.rd_namespace = 0 AND r.rd_title = ?'
    # cursor.execute(q, (rd_to_title,))
    # maybe sql injection results in illegal syntax

    q += f'WHERE r.rd_namespace = 0 AND r.rd_title = "{rd_to_title}"'
    try:
        cursor.execute(q)
        results = cursor.fetchall()
    except Exception as error:
        logging.error(error)
        logging.error('SQL exception getting redirects.')
        results = None
    finally:
        con.close()
    return results

def get_mdwiki_passwd():
    global DBPW
    with open(LOCAL_SETTINGS, 'r') as f:
        settings = f.read().split('\n')
    for s in settings:
        if '$wgDBpassword' in s:
            DBPW = s.split('"')[1]

def get_enwp_page_list():
    global enwp_list
    #mdwiki_redirects = read_json_file('data/mdwiki_redirects.json')
    try:
        with open('data/enwp.tsv') as f:
            txt = f.read()
        enwp_list = txt.split('\n')
    except Exception as error:
        logging.error(error)
        logging.error('Failed to read enwp.tsv. Exiting.')
        sys.exit(1)

def get_mdwiki_page_list():
    global mdwiki_list

    try:
        with open('data/mdwiki.tsv') as f:
            txt = f.read()
        mdwiki_list = txt.split('\n')
    except Exception as error:
        logging.error(error)
        logging.error('Failed to read mdwiki.tsv. Exiting.')
        sys.exit(1)

def get_mdwiki_redirect_lists():
    # redirect.json
    #   rd_from_id
    #   rd_to_namespace
    #   rd_to_title_hex
    #   rd_from_name_hex

    global mdwiki_redirect_list
    global mdwiki_rd_lookup

    mdwiki_redirects = read_json_file('data/mdwiki_redirects.json')
    mdwiki_redirect_list = mdwiki_redirects['list']
    mdwiki_rd_lookup = mdwiki_redirects['lookup']

def run(server_class=HTTPServer, handler_class=S, port=8080):
    global request_paths
    # logging.basicConfig(level=logging.INFO)
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

    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    handler_class.request_paths = []
    #handler_class.session = CachedSession()
    handler_class.enwp_session = CachedSession(enwp_db, backend='sqlite')
    handler_class.mdwiki_session = CachedSession(mdwiki_db, backend='sqlite')
    # get_mdwiki_passwd()
    logging.info('Getting page and redirect lists...\n')
    get_mdwiki_page_list()
    get_mdwiki_redirect_lists()
    get_enwp_page_list()
    logging.info('Mdwiki cache ready\n')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')

    request_paths = handler_class.request_paths
    with open('request_paths.txt', 'w') as f:
        for url in handler_class.request_paths:
            print(url)
            f.write(url + '\n')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
