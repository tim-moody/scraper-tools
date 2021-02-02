
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

class BasicSpider(SpiderCore):
    """
    Basic web spider that uses request.head to analyze potential urls to crawl.
    """
    # can be extended by subclass
    IGNORE_LINKS = [
        'javascript:void(0)', '#',
        re.compile('^mailto:.*'), re.compile('^javascript:.*'),
    ]

    ALLOW_BROKEN_HEAD_URLS = []     # proceed with request even
    # subclass should change these
    SHORTEN_CRAWL = False # if True don't revisit pages seen in order to gather statistics

    # Subclass attributes
    MAIN_SOURCE_DOMAIN = None   # should be defined by subclass
    #SOURCE_DOMAINS = []         # should be defined by subclass
    START_PAGE = None           # should be defined by subclass
    REFRESH_HTML = False

    OUTPUT_FILE_PREFIX = 'site'
    SESSION = requests.Session()
    # queue used keep track of what pages we should crawl next
    queue = None  # instance of queue.Queue created insite `crawl` method

    continue_processing_flag = True

    def __init__(self, main_source_domain=None, start_page=None, prefix=OUTPUT_FILE_PREFIX, load_data=True):
        super().__init__(prefix, load_data)

        if main_source_domain is None and start_page is None:
            raise ValueError('Need to specify main_source_domain or start_page.')
        if main_source_domain:
            self.MAIN_SOURCE_DOMAIN = main_source_domain.rstrip('/')
            self.START_PAGE = self.MAIN_SOURCE_DOMAIN
        if self.MAIN_SOURCE_DOMAIN is None:
            parsedurl = urlparse(start_page)
            self.MAIN_SOURCE_DOMAIN = parsedurl.scheme + '://' + parsedurl.netloc
        if self.MAIN_SOURCE_DOMAIN:
            self.HTML_INCL_PATTERNS.append(self.MAIN_SOURCE_DOMAIN)
        if start_page:
            self.START_PAGE = start_page

        self.load_data = load_data

        # make resolve any redirects
        #verdict, head_response = self.is_html_file(self.START_PAGE)
        is_new_url, content_type, content_length, return_url = self.get_url_type(self.START_PAGE)
        if content_type == 'text/html':
            self.START_PAGE = return_url
            #self.HTML_INCL_PATTERNS.extend(source_domain_to_regex(self.SOURCE_DOMAINS))
        else:
            raise ValueError('The Starting URL ' + self.START_PAGE + ' did not return any html.')

    # MAIN LOOP
    ############################################################################

    def crawl(self, limit=1000, devmode=True):
        # initialize or reset crawler state
        self.queue = queue.Queue()
        start_url = self.START_PAGE
        self.enqueue_url(start_url)

        # reload processing queue
        if self.load_data:
            self.enqueue_all_site_urls(start_url)

        threading.Thread(target=self.key_capture_thread, args=(), name='key_capture_thread', daemon=True).start()
        print('Press the ENTER key to terminate')

        counter = 0
        dot_count = 0
        while self.continue_processing_flag and not self.queue_is_empty():
            original_url, _ = self.queue.get() # any url on queue is expected to return a page (no media or redirects)

            url, html = self.get_page(original_url)
            if html is None:
                LOGGER.warning('GET ' + original_url + ' did not return page.')
                self.site_error_urls[original_url] = '???'
                continue

            self.do_one_page(url, html)

            ####################################################################

            # limit crawling to 1000 pages unless otherwise told (failsafe default)
            counter += 1
            if limit and counter > limit:
                break
            # show some output to know we're alive
            if LOGGER.level >= logging.INFO:
                if counter % 1 == 0:
                    print('.', end = '', flush=True)
                    dot_count += 1
                    if dot_count == 80:
                        print('!')
                        dot_count = 0



    # TOP LEVEL FUNCTIONS
    ############################################################################

    def do_one_page(self, url, html, spider=True):
        """
        Basic handler that appends current page to parent's children list and
        adds all html links on current page to the crawling queue.
        """
        if url in self.site_pages:
            self.site_pages[url]['count'] += 1
            LOGGER.debug('Skipping already crawled page ' + url)
            return
        page = BeautifulSoup(html, "html.parser")
        LOGGER.debug('Downloaded page ' + str(url) + ' title:' + self.get_title(page))
        #LOGGER.debug('do_one_page is visiting the URL ' + url)

        children = []

        links = page.find_all(['a', 'link']) # check for both a and link tags
        for i, link in enumerate(links):
            if link.has_attr('href'):
                #if should_ignore_link(link, self.IGNORE_LINKS): continue
                link_url = urljoin(url, link['href'])
                if link_url not in children:
                    children.append(link_url)
        elements = page.find_all(['audio', 'embed', 'iframe', 'img', 'input', 'script', 'source', 'track', 'video'])
        for i, element in enumerate(elements):
            if element.has_attr('src'):
                link_url = urljoin(url, element['src'])
                if link_url not in children:
                    children.append(link_url)

        dedup_children = []
        for i, link_url in enumerate(children):
            link_url = cleanup_url(link_url) # This is the main place new urls arise
            LOGGER.debug('link_url: ' + link_url)
            if should_ignore_link(link_url, self.IGNORE_LINKS): # these are things like # and javascript:void(0)
                self.site_ignored_urls[link_url] = url
                continue
            else:
                is_new_url, content_type, content_length, real_url = self.get_url_type(link_url)
                if link_url not in dedup_children:
                    dedup_children.append(link_url) # handle any redirects
                    if content_type == 'text/html': # it's html so queue it for parsing if not in queue
                        if not should_include_url(link_url, self.HTML_INCL_PATTERNS, self.HTML_EXCL_PATTERNS):
                            continue

                        if self.SHORTEN_CRAWL: # don't revisit pages for statistical purposes
                            if is_new_url and spider: # only queue pages that have never been visited
                                self.enqueue_url(link_url)
                        else:
                            if link_url not in self.site_pages and spider: # queue pages that may already be in queue but not yet parsed
                                self.enqueue_url(link_url)
                if link_url not in self.site_urls:
                    url_attr = {'content-type': content_type, 'content-length': content_length, 'real-url': real_url, 'count': 1}
                    self.site_urls[link_url] = url_attr
                else:
                    self.site_urls[link_url]['count'] += 1

                if content_type == 'broken-link': # track
                    self.site_error_urls[link_url] = url # track broken child links and parent

            self.site_pages[url] = {'count': 1, 'children': dedup_children}


    def do_one_link(self, url):
        pass


    # GENERIC URL HELPERS
    ############################################################################
    def get_url_type(self, url):
        """
        Makes a HEAD request for `url` and reuturns (vertict, head_response),
        where verdict is True if `url` points to a html file
        Does up to 5 redirects to find url of content-type html
        """
        content_type = None
        return_url = url
        content_length = 0

        if url in self.site_urls:
            content_type = self.site_urls[url]['content-type']
            content_length = self.site_urls[url]['content-length']
            return_url = self.site_urls[url]['real-url']
            is_new_url = False
            return (is_new_url, content_type, content_length, return_url)

        if url in self.site_redirects:
            content_type = 'redirect'
            content_length = 0
            return_url = self.site_redirects[url]
            is_new_url = False
            return (is_new_url, content_type, content_length, return_url)

        is_new_url = True
        retries = 5
        while retries > 0:
            head_response = self.make_head_request(return_url)
            #head_response = requests.head(return_url)
            if head_response:
                # TODO HANDLE 400 INVALID URL
                if head_response.status_code >=300 and head_response.status_code < 400: # redirect
                    if 'Location' in head_response.headers:
                        return_url = urljoin(return_url, head_response.headers['Location'])
                        self.site_redirects[url] = return_url
                        LOGGER.warning('Found redirect for url = ' + url + ' = ' + return_url)
                        retries -= 1
                        continue
                    else:
                        LOGGER.warning('HEAD request status in 300s without Location for url ' + url)
                        content_type = 'broken-link'
                        break
                content_type = head_response.headers.get('Content-Type', None)
                if not content_type:
                    LOGGER.warning('HEAD response does not have `Content-Type` header. url = ' + url)
                    content_type = 'broken-link'
                    break
                else:
                    content_type.strip()
                if head_response.status_code == 200: # does 304 enter into the picture?
                    content_length = int(head_response.headers.get('content-length', 0))
                    break
            else:
                LOGGER.warning('HEAD request failed for url ' + url)
                content_type = 'broken-link'
                break
        if retries == 0:
            content_type = 'broken-link'
        content_type = content_type.split(';')[0] # remove char format
        return_url = cleanup_url(return_url)

        return (is_new_url, content_type, content_length, return_url)


    # CRAWLING TASK QUEUE API
    ############################################################################

    def queue_is_empty(self):
        return self.queue.empty()

    #def enqueue_url_and_context(self, url, context, force=False):
    def enqueue_url(self, url, force=False):
        # TODO(ivan): clarify crawl-only-once logic and use of force flag in docs
        # we are only crawling pages
        # other urls are handled in on_page
        url = cleanup_url(url)
        if url not in self.site_pages or force:
            LOGGER.debug('adding to queue:  url=' + url)
            self.queue.put((url, ''))
        else:
            LOGGER.debug('Not going to crawl url ' + url + ' because previously seen.')
            pass

    def enqueue_all_site_urls(self, start_url):
        for url in self.site_urls:
            if url == start_url:
                continue
            content_type = self.site_urls[url]. get('content-type', '')
            if content_type == 'text/html':
                self.enqueue_url(url)

    def get_page(self, url, *args, **kwargs):
        return_url = url
        content_type = 'text/html'
        download_file_name = url_to_file_name(url, content_type)
        input_file_path = self.DOWNLOAD_DEST_DIR + download_file_name
        if os.path.exists(input_file_path) and not self.REFRESH_HTML:
            html = read_html_file(input_file_path)
        else:
            return_url, html = self.download_page( url, *args, **kwargs)

        return (return_url, html)

    def download_page(self, url, *args, **kwargs):
        """
        Download `url` (following redirects) and soupify response contents.
        Returns (final_url, page) where final_url is URL afrer following redirects.
        """
        response = self.make_request(url, *args, **kwargs)
        if not response:
            return (None, None)
        response.encoding = 'utf-8'
        html = response.text
        content_type = 'text/html'
        download_file_name = url_to_file_name(url, content_type)
        output_file_path = self.DOWNLOAD_DEST_DIR + download_file_name
        write_html_file(output_file_path, html)
        return (response.url, html)


    def make_request(self, url, timeout=60, *args, method='GET', **kwargs):
        """
        Failure-resistant HTTP GET/HEAD request helper method.
        """
        retry_count = 0
        max_retries = 10
        while True:
            try:
                kwargs['headers'] = std_headers  # set random user-agent headers
                response = self.SESSION.request(method, url, *args, timeout=timeout, **kwargs)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                retry_count += 1
                LOGGER.warning("Connection error ('{msg}'); about to perform retry {count} of {trymax}."
                               .format(msg=str(e), count=retry_count, trymax=max_retries))
                time.sleep(retry_count * 1)
                if retry_count >= max_retries:
                    LOGGER.error("FAILED TO RETRIEVE:" + str(url))
                    return None
            except Exception as e:
                LOGGER.error("FAILED TO RETRIEVE:" + str(url))
                LOGGER.error("GOT ERROR: " + str(e))
                return None
        if response.status_code != 200 and method == 'GET':
            LOGGER.error("ERROR " + str(response.status_code) + ' when getting url=' + url)
            self.site_error_urls[url] = '???'
            return None
        return response

    def make_head_request(self, url):
        """
        Failure-resistant HTTP GET/HEAD request helper method.
        """
        # head can fail where get succeeds
        # we could do a get in that case after retries exhausted
        retry_count = 0
        max_retries = 5
        while True:
            try:
                response = self.SESSION.head(url, timeout=2)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                retry_count += 1
                LOGGER.warning("Connection error ('{msg}'); about to perform retry {count} of {trymax}."
                               .format(msg=str(e), count=retry_count, trymax=max_retries))
                time.sleep(retry_count * 1)
                if retry_count >= max_retries:
                    LOGGER.error("FAILED TO RETRIEVE:" + str(url))
                    response = None
                    break
            except Exception as e:
                LOGGER.error("FAILED TO RETRIEVE:" + str(url))
                LOGGER.error("GOT ERROR: " + str(e))
                response = None
                break
        return response

    # TEXT HELPERS
    ############################################################################

    def get_text(self, element):
        """
        Extract stripped text content of `element` and normalize newlines to spaces.
        """
        if element is None:
            return ''
        else:
            return element.get_text().replace('\r', '').replace('\n', ' ').strip()

    def get_title(self, page):
        title = ''
        head_el = page.find('head')
        if head_el:
            title_el = head_el.find('title')
            if title_el:
                title = title_el.get_text().strip()
        return title

# LOGGING
################################################################################
LOGGER = logging.basicConfig()

def set_log_level(level):
    global LOGGER
    if level >= logging.INFO:
        log_format = '\n\r%(levelname)s:%(name)s:%(message)s'
    else:
        log_format = None
    # reset format
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    LOGGER = logging.basicConfig(format=log_format)
    LOGGER = logging.getLogger('crawler')
    LOGGER.setLevel(level)

logging.getLogger("cachecontrol.controller").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

set_log_level(logging.WARNING)
