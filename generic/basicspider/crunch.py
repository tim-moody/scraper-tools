
# started with https://dev.to/fprime/how-to-create-a-web-crawler-from-scratch-in-python-2p46
# and https://github.com/learningequality/BasicCrawler/blob/master/basiccrawler/crawler.py

from bs4 import BeautifulSoup
from cachecontrol import CacheControlAdapter
from cachecontrol.caches.file_cache import FileCache
from cachecontrol.heuristics import BaseHeuristic, expire_after, datetime_to_header
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json
import logging
import re
import os
import queue
import requests
import time
import threading
from urllib.parse import urljoin, urldefrag, urlparse
from youtube_dl.utils import std_headers
from basicspider.core import SpiderCore
from basicspider.sp_lib import *

# BASIC SPIDER
################################################################################

class SpiderCrunch(SpiderCore):

    OUTPUT_FILE_PREFIX = 'site'

    unique_urls = set()
    content_types = {}
    case_insensitive = {}
    all_pages = {}
    broken_links = {}
    image_urls = {}
    total_bytes = 0

    def __init__(self, main_source_domain=None, start_page=None, prefix=OUTPUT_FILE_PREFIX, load_data=True):
        super().__init__(prefix, load_data)

    # MAIN FUNCTION
    ############################################################################

    def crunch(self):
        self.calc_page_children()
        self.compare_urls() # look for page/url mismatches

        self.sum_content_types()
        #recursive_visit_extract_urls(channel_dict)
        self.image_urls = self.calc_image_sources()

        write_json_file(self.content_types, 'site_content_types.json')

        for content_type in self.content_types:
            print (content_type, self.content_types[content_type]['count'], human_readable(self.content_types[content_type]['bytes']))

        print ('Total Site Size: ' + human_readable(self.total_bytes))

    def sum_content_types(self):
    # pass through urls and sum by content type
        for url in self.site_urls:
            content_type = self.site_urls[url].get('content-type', None)
            size = int(self.site_urls[url].get('content-length', 0))
            parsed_url = urlparse(url)
            if parsed_url.path:
                root_path = '/' + parsed_url.path.split('/')[1]
            else:
                root_path = '/'
            root_path = parsed_url.netloc + root_path
            if content_type not in self.content_types:
                self.content_types[content_type] = {'count': 1, 'bytes': size}
                self.content_types[content_type]['paths'] = {root_path: 1}
            else:
                self.content_types[content_type]['count'] += 1
                self.content_types[content_type]['bytes'] += size
                if root_path in self.content_types[content_type]['paths']:
                    self.content_types[content_type]['paths'][root_path] += 1
                else:
                    self.content_types[content_type]['paths'][root_path] = 1
                if content_type == "broken-link":
                    self.broken_links[url] = "broken-link"
        for content_type in self.content_types:
            self.total_bytes += self.content_types[content_type]['bytes']

    def sum_level1(self):
        top_level = {}
        for u in self.site_urls:
            if self.site_urls[u]['content-type'] != "text/html": continue
            url_parts = urlparse(u)
            top_dir = url_parts.path.split('/')[1].lower()
            if top_dir in top_level:
                top_level[top_dir] +=1
            else:
                top_level[top_dir] =1
        return top_level

    def recursive_visit_extract_urls(self, subtree):
        url = subtree['url']
        if url not in self.unique_urls:
            self.unique_urls.add(url)
        for child in subtree['children']:
            kind = child['kind']
            if kind == 'PageWebResource':
                recursive_visit_extract_urls(child)
            elif kind == 'MediaWebResource':
                content_type = child.get('content-type', None)
                size = int(child.get('content-length', 0))
                if content_type not in self.content_types:
                    self.content_types[content_type] = {'count': 1, 'bytes': size}
                else:
                    self.content_types[content_type]['count'] += 1
                    self.content_types[content_type]['bytes'] += size
            else:
                pass # no other types now

    def check_lc(self):
        self.case_insensitive = {}
        for url in self.site_urls:
            url_lc = url.lower()
            if url != url_lc:
                r = requests.head(url_lc)
                if int(r.headers['Content-Length']) != self.site_urls[url]['content-length']:
                    print(url, r.headers['Content-Length'], self.site_urls[url]['content-length'])
                if url_lc not in self.case_insensitive:
                    self.case_insensitive[url_lc] = 1
                else:
                    self.case_insensitive[url_lc] += 1
                    if 'feedback/spanish' not in url:
                        print(url)
                        print (url_lc)
                    #print(self.case_insensitive[url_lc])
        #print_json(self.case_insensitive)
        for url in self.case_insensitive:
            if self.case_insensitive[url] != 1:
                #print (url)
                pass

    def compare_urls(self):
        cnt = 0
        cnt2 = 0
        for u in self.site_urls:
            if  self.site_urls[u]["content-type"] != "text/html":
                continue
            if u not in self.site_pages:
                print ('url not in pages: ' + u)
                cnt += 1
            if u not in self.all_pages:
                print ('url not in pages or children: ' + u)
                cnt2 += 1
        print ('total urls not in pages: ' + str(cnt))
        print ('total urls not in pages or children: ' + str(cnt2))

    def check_url_names(self):
        for u in self.site_urls:
            if  self.site_urls[u]["content-type"] == "text/html":
                continue
            if  self.site_urls[u]["content-type"] == "broken-link":
                continue
            parsed_url = urlparse(u)
            path = parsed_url.path
            query = parsed_url.query
            if query != '':
                path += '?' + query
            try:
                name = url_to_file_name(u, self.site_urls[u]["content-type"])
                if path != name:
                    print(u)
                    print('path: ' + path + ', name: ' + name)
            except:
                print('error in url_to_file_name for ' + u)

    def calc_page_children(self):
        for p in self.site_pages:
            self.all_pages[p] = 1
            for c in self.site_pages[p]['children']:
                self.all_pages[c] = 1

    def calc_image_sources(self, filter = None):
        self.image_urls = {}
        for p in self.site_pages:
            if filter and filter not in p:
                continue
            for c in self.site_pages[p]['children']:
                if c not in self.site_urls:
                    print(p,'child', c, 'not in site_urls')
                    continue
                contyp = self.site_urls[c]['content-type'].strip()
                if 'image' in contyp:
                    u = c
                    if c[-1] == '/':
                        u = c[:-1]
                    u = u.rpartition('/')[0]
                    if u not in self.image_urls:
                        self.image_urls[u] = {'count': 1, 'children': {}}
                        self.image_urls[u]['children'][c] = 1
                    else:
                        self.image_urls[u]['count'] += 1
                        if c in self.image_urls[u]['children']:
                            self.image_urls[u]['children'][c] += 1
                        else:
                            self.image_urls[u]['children'][c] = 1
        return self.image_urls

    def list_type_urls(self, type):
        for p in self.site_pages:
            children = self.site_pages[p]['children']
            for c in children:
                ctype = self.site_urls[c]['content-type']
                if 'video' in ctype:
                    print (p)
