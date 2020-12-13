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
import iiab.adm_lib as adm

Pattern = re.Pattern

# BASIC SPIDER
################################################################################

class BasicSpider(object):
    """
    Basic web spider that uses request.head to analyze potential urls to crawl.
    """
    BASE_IGNORE_URLS = [
        'javascript:void(0)', '#',
        re.compile('^mailto:.*'), re.compile('^javascript:.*'),
    ]
    ALLOW_BROKEN_HEAD_URLS = []     # proceed with request even
    MEDIA_FILE_FORMATS = ['pdf', 'zip', 'rar', 'mp4', 'wmv', 'mp3', 'm4a', 'ogg',
                          'exe', 'deb']
    MEDIA_CONTENT_TYPES = [
        'application/pdf',
        'application/zip', 'application/x-zip-compressed', 'application/octet-stream',
        'video/mpeg', 'video/mp4', 'video/x-ms-wmv',
        'audio/vorbis', 'audio/mp3', 'audio/mpeg',
        'image/png', 'image/jpeg', 'image/gif',
        'application/msword', 'application/vnd.ms-excel', 'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/x-msdownload', 'application/x-deb'
    ]

    GLOBAL_NAV_THRESHOLD = 0.7
    # subclass should change these
    OUTPUT_FILE_PREFIX = './scanned_site'
    # place holders
    CRAWLING_OUTPUT_URLS = OUTPUT_FILE_PREFIX + '_urls.json'
    CRAWLING_OUTPUT_PAGES = OUTPUT_FILE_PREFIX + '_pages.json'
    CRAWLING_OUTPUT_REDIRECTS = OUTPUT_FILE_PREFIX + '_redirects.json'
    CRAWLING_OUTPUT_ERROR_URLS = OUTPUT_FILE_PREFIX + '_error_urls.json'
    CRAWLING_OUTPUT_IGNORED_URLS = OUTPUT_FILE_PREFIX + '_ignored_urls.json'

    SHORTEN_CRAWL = False # if True don't revisit pages seen in order to gather statistics

    # Subclass attributes
    MAIN_SOURCE_DOMAIN = None   # should be defined by subclass
    SOURCE_DOMAINS = []         # should be defined by subclass
    START_PAGE = None           # should be defined by subclass
    START_PAGE_CONTEXT = {}     # should be defined by subclass
    IGNORE_URLS = []            # should be defined by subclass
    kind_handlers = {}          # map from web resource kinds and handlers
                                # e.g. {'LesssonWebResource': self.on_lesson, .. }

    # CACHE LOGIC
    SESSION = requests.Session()
    CACHE = FileCache('.webcache')

    # queue used keep track of what pages we should crawl next
    queue = None  # instance of queue.Queue created insite `crawl` method

    # keep track of how many times a given URL is seen during crawl
    # first time a URL is seen will be automatically followed, but
    # subsequent occureces will record link existence but not recurse
    #global_urls_seen_count = defaultdict(int)  # DB of all urls that have ever been seen
    #  { 'http://site.../fullpath?a=b#c': 3, ... }
    # urls_visited = {}  # 'http://site.../fullpath?a=b#c' --> 'visited'

    # Track attributes and counts of site components
    # global_site_struct = {} # Hierarchical structure of site pages
    # for now we use channel_dict (channel tree) as site structure
    global_site_pages = {} # DB of all pages that have ever been parsed
    global_site_urls = {} # DB of all urls that have ever been seen
    global_site_redirects = {} # DB of all urls that redirect
    global_site_error_urls = {}
    global_site_ignored_urls = {}

    continue_processing_flag = True

    def __init__(self, main_source_domain=None, start_page=None):
        if main_source_domain is None and start_page is None:
            raise ValueError('Need to specify main_source_domain or start_page.')
        if main_source_domain:
            self.MAIN_SOURCE_DOMAIN = main_source_domain.rstrip('/')
            self.START_PAGE = self.MAIN_SOURCE_DOMAIN
        if self.MAIN_SOURCE_DOMAIN is None:
            parsedurl = urlparse(start_page)
            self.MAIN_SOURCE_DOMAIN = parsedurl.scheme + '://' + parsedurl.netloc
        if self.MAIN_SOURCE_DOMAIN not in self.SOURCE_DOMAINS:
            self.SOURCE_DOMAINS.append(self.MAIN_SOURCE_DOMAIN)
        if start_page:
            self.START_PAGE = start_page

        # make resolve any redirects
        #verdict, head_response = self.is_html_file(self.START_PAGE)
        is_new_url, content_type, content_length, return_url = self.get_url_type(self.START_PAGE)
        if content_type == 'text/html':
            self.START_PAGE = return_url
        else:
            raise ValueError('The Starting URL ' + self.START_PAGE + ' did not return any html.')

        forever_adapter= CacheControlAdapter(heuristic=CacheForeverHeuristic(), cache=self.CACHE)
        for source_domain in self.SOURCE_DOMAINS:
            self.SESSION.mount(source_domain, forever_adapter)   # TODO: change to less aggressive in final version

    # MAIN LOOP
    ############################################################################

    def crawl(self, limit=1000, save_web_resource_tree=True, devmode=True):
        # initialize or reset crawler state
        self.queue = queue.Queue()

        self.urls_visited = {}
        # self.global_site_struct = {}
        self.global_site_pages = {}
        self.global_site_urls = {}
        self.global_site_redirects = {} # DB of all urls that redirect
        self.global_site_error_urls = {}
        self.global_site_ignored_urls = {}

        #  add the start page to the crawling queue
        channel_dict = dict(
            url='This is a temp. outer container for the crawler channel tree.'
                'Its unique child node is the web root.',
            kind='WEB_RESOURCE_TREE_CONTAINER',
            children=[],
        )
        start_url = self.START_PAGE
        root_context = {'parent': channel_dict}
        if self.START_PAGE_CONTEXT:
            root_context.update(self.START_PAGE_CONTEXT)
        self.enqueue_url(start_url)

        threading.Thread(target=self.key_capture_thread, args=(), name='key_capture_thread', daemon=True).start()
        print('Press the ENTER key to terminate')

        counter = 0
        dot_count = 0
        while self.continue_processing_flag and not self.queue_is_empty():

            # 1. GET next url from queue
            # only html will be on queue
            # probably should not do pages already seen, but they should not have gone into queue
            original_url, _ = self.queue.get() # any url on queue is expected to return a page (no media or redirects)

            url, html = self.download_page(original_url)
            if html is None:
                LOGGER.warning('GET ' + original_url + ' did not return page.')
                self.global_site_error_urls[original_url] = '???'
                continue

            # record page URL as visited
            self.urls_visited[original_url] = 'visited'

            # ************ TODO REMOVE **************
            # annotate context to keep track of URL befor redirects
            #if url != original_url:
            #    context['original_url'] = original_url

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


        # ************ TODO REMOVE **************
        # remove parent links before output tree
        self.cleanup_web_resource_tree(channel_dict)


        # hoist entire tree one level up to get rid of the tmep. outer container
        #channel_dict = channel_dict['children'][0]

        # Save output
        if save_web_resource_tree:
            #self.write_web_resource_tree_json(channel_dict, self.CRAW)
            self.write_web_resource_tree_json(self.global_site_urls, self.CRAWLING_OUTPUT_URLS)
            self.write_web_resource_tree_json(self.global_site_pages, self.CRAWLING_OUTPUT_PAGES)
            self.write_web_resource_tree_json(self.global_site_redirects, self.CRAWLING_OUTPUT_REDIRECTS)
            self.write_web_resource_tree_json(self.global_site_error_urls, self.CRAWLING_OUTPUT_ERROR_URLS)
            self.write_web_resource_tree_json(self.global_site_ignored_urls, self.CRAWLING_OUTPUT_IGNORED_URLS)


        # Display debug info
        if devmode:
            self.print_crawler_devmode(channel_dict)

        return channel_dict


    # TOP LEVEL FUNCTIONS
    ############################################################################

    def do_one_page(self, url, html, spider=True):
        """
        Basic handler that appends current page to parent's children list and
        adds all links on current page to the crawling queue.
        """
        if url in self.global_site_pages:
            self.global_site_pages[url]['count'] += 1
            LOGGER.debug('Skipping already crawled page ' + url)
            return
        page = BeautifulSoup(html, "html.parser")
        LOGGER.debug('Downloaded page ' + str(url) + ' title:' + self.get_title(page))


        #LOGGER.debug('do_one_page is visiting the URL ' + url)
        # ************ TODO REMOVE **************
        #page_dict = dict(
        #    kind='PageWebResource',
        #    url=url,
        #    children=[],
        #)
        #page_dict.update(context)
        children = []

        links = page.find_all(['a', 'link']) # check for both a and link tags
        for i, link in enumerate(links):
            if link.has_attr('href'):
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
            link_url = self.cleanup_url(link_url) # This is the main place new urls arise
            LOGGER.debug('link_url: ' + link_url)
            if self.should_ignore_url(link_url): # should really not ignore 'near' images
                self.global_site_ignored_urls[link_url] = url
                continue
                # Uncomment three lines below for debugging to record ignored links
                # ignored_rsrc_dict = self.create_ignored_url_dict(link_url)
                # ignored_rsrc_dict['parent'] = page_dict
                # page_dict['children'].append(page_dict)
            else:
                is_new_url, content_type, content_length, real_url = self.get_url_type(link_url)
                if link_url not in dedup_children:
                    dedup_children.append(link_url) # handle any redirects
                    if content_type == 'text/html': # it's html so queue it for parsing if not in queue
                        if self.SHORTEN_CRAWL: # don't revisit pages for statistical purposes
                            if is_new_url and spider: # only queue pages that have never been visited
                                self.enqueue_url(link_url)
                        else:
                            if link_url not in self.global_site_pages and spider: # queue pages that may already be in queue but not yet parsed
                                self.enqueue_url(link_url)
                if link_url not in self.global_site_urls:
                    url_attr = {'content-type': content_type, 'content-length': content_length, 'real-url': real_url, 'count': 1}
                    self.global_site_urls[link_url] = url_attr
                else:
                    self.global_site_urls[link_url]['count'] += 1

                if content_type == 'broken-link': # track
                    self.global_site_error_urls[link_url] = url # track broken child links and parent

            self.global_site_pages[url] = {'count': 1, 'children': dedup_children}

            # add page to self.site_struct


    def do_one_link(self, url):
        pass


    # GENERIC URL HELPERS
    ############################################################################

    def cleanup_url(self, url):
        """
        Removes URL fragment that falsely make URLs look diffent.
        Subclasses can overload this method to perform other URL-normalizations.
        """
        url = urldefrag(url)[0]
        url_parts = urlparse(url)
        url_parts = url_parts._replace(path=url_parts.path.replace('//','/'))
        return url_parts.geturl()

    def url_to_path(self, url):
        """
        Remove any of the SOURCE_DOMAINS from url if it starts with one of them.
        """
        for source_domain in self.SOURCE_DOMAINS:
            if url.startswith(source_domain):
                path = url.replace(source_domain, '')
                return path
        return url


    def should_ignore_url(self, url):
        """
        Returns True if `url` matches any of the IGNORE_URL criteria.
        """
        url = self.cleanup_url(url)

        # 1. run through ignore lists
        combined_ignore_patterns = self.BASE_IGNORE_URLS.copy()
        combined_ignore_patterns.extend(self.IGNORE_URLS)
        for pattern in combined_ignore_patterns:
            if isinstance(pattern, str):
                if url == pattern:
                    return True
            elif isinstance(pattern, Pattern):
                if pattern.match(url):
                    return True
            elif callable(pattern):
                if pattern(url):
                    return True
            else:
                raise ValueError('Unrecognized pattern in IGNORE_URLS. Use strings, REs, or callables.')

        # 2. check if url is on one of the specified source domains
        found = False
        parsedurl = urlparse(url)
        for source_domain in self.SOURCE_DOMAINS:
            parsedomain = urlparse(source_domain)
            if parsedurl.netloc == parsedomain.netloc:
                found = True
        return not found     # should ignore if not found in SOURCE_DOMAINS list

    def get_url_type(self, url):
        """
        Makes a HEAD request for `url` and reuturns (vertict, head_response),
        where verdict is True if `url` points to a html file
        Does up to 5 redirects to find url of content-type html
        """
        content_type = None
        return_url = url
        content_length = 0

        if url in self.global_site_urls:
            content_type = self.global_site_urls[url]['content-type']
            content_length = self.global_site_urls[url]['content-length']
            return_url = self.global_site_urls[url]['real-url']
            is_new_url = False
            return (is_new_url, content_type, content_length, return_url)

        if url in self.global_site_redirects:
            content_type = 'redirect'
            content_length = 0
            return_url = self.global_site_redirects[url]
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
                    return_url = head_response.headers['Location']
                    self.global_site_redirects[url] = return_url
                    LOGGER.warning('Found redirect for url = ' + url + ' = ' + return_url)
                    retries -= 1
                    continue
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
        return_url = self.cleanup_url(return_url)

        return (is_new_url, content_type, content_length, return_url)


    # CRAWLING TASK QUEUE API
    ############################################################################
    #
    # queue tasks are tuples (url, context) where
    #  - url (str): which page should be visited
    #  - context (dict): generic container for data associated with url, notably
    #     - `context['parent']` is the web resources dict of the referring page
    #     - `context['kind']` can be used to assign a custom handler, e.g., on_course

    def queue_is_empty(self):
        return self.queue.empty()

    def get_url_and_context(self):
        return self.queue.get()

    #def enqueue_url_and_context(self, url, context, force=False):
    def enqueue_url(self, url, force=False):
        # TODO(ivan): clarify crawl-only-once logic and use of force flag in docs
        # we are only crawling pages
        # other urls are handled in on_page
        url = self.cleanup_url(url)
        if url not in self.global_site_pages or force:
            LOGGER.debug('adding to queue:  url=' + url)
            self.queue.put((url, ''))
        else:
            LOGGER.debug('Not going to crawl url ' + url + ' because previously seen.')
            pass



    def download_page(self, url, *args, **kwargs):
        """
        Download `url` (following redirects) and soupify response contents.
        Returns (final_url, page) where final_url is URL afrer following redirects.
        """
        response = self.make_request(url, *args, **kwargs)
        if not response:
            return (None, None)
        response.encoding = 'utf-8'  # to avoid guessing logic which has a problem parsing https://learningequality.org/directions/
        html = response.text
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
            self.global_site_error_urls[url] = '???'
            return None
        return response

    def make_head_request(self, url):
        """
        Failure-resistant HTTP GET/HEAD request helper method.
        """
        retry_count = 0
        max_retries = 10
        while True:
            try:
                response = self.SESSION.head(url)
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
        return response

    # WEB RESOURCE INFO UTILS (CRAWLER DEVMODE)
    ############################################################################

    def print_crawler_devmode(self, channel_tree):
        """
        Craweler devmode info useful during interactive development of the cralwer.
        """
        print('\n\n\n')
        print('#'*80)
        print('# CRAWLER RECOMMENDATIONS BASED ON URLS ENCOUNTERED:')
        print('#'*80)

        print('\n1. These URLs are very common and look like global navigation links:')
        global_nav_candidates = self.infer_gloabal_nav(channel_tree)
        for c in global_nav_candidates['children']:
            print('  - ', c['url'])

        print('\n2. These are common path fragments found in URLs paths, so could correspond to site struture:')
        fragments_tuples = self.infer_tree_structure(channel_tree)
        for fpath, fcount in fragments_tuples:
            print('  - ', str(fcount), 'urls on site start with ', '/'+fpath)

        if len(self.global_site_error_urls) > 0:
            print('\n3. These are broken links --- you might want to add them to IGNORE_URLS')
            print(self.global_site_error_urls)

        print('\n')
        print('#'*80)
        print('\n\n')


    def infer_tree_structure(self, tree_root, show_top=10):
        """
        Walk web resource tree and look for patterns in urls.
        Print the top 10 occurence of subpaths that are common to multiple URLs.
        E.g. if we see a lot of URLs like /pat/smth1 /pat/smth2 /pat/smth3, we'll
        identify `/pat` as a candidate for site structure: Returns ['/pat', ...]
        """
        # Get URLs
        unique_urls = set()
        def recursive_visit_extract_urls(subtree):
            url = subtree['url']
            if url not in unique_urls:
                unique_urls.add(url)
            for child in subtree['children']:
                recursive_visit_extract_urls(child)
        recursive_visit_extract_urls(tree_root)

        # Build path trie
        subpath_trie = {}
        def _add_parts_here(path_parts, here):
            if not path_parts:
                return
            else:
                part = path_parts.pop(0)
                if part not in here.keys():
                    here[part] = {}
                    _add_parts_here(path_parts, here[part])
                else:
                    _add_parts_here(path_parts, here[part])
        for url in unique_urls:
            path = self.url_to_path(url)
            path = path.split('?')[0]  # rm query string
            path_parts = path.split('/')[1:]
            _add_parts_here(path_parts, subpath_trie)

        # annotate with counts
        def _recursive_count_children(here):
            if not here.keys():
                return 1
            count = 0
            for subpath in here.keys():
                count += _recursive_count_children(here[subpath])
            return count

        path_count_tuples = []
        for path, subtrie in subpath_trie.items():
            count = _recursive_count_children(subtrie)
            path_count_tuples.append( (path, count) )

        # top 10 sorted by count
        sorted_path_count_tuples = sorted(path_count_tuples, key=lambda t: t[1], reverse=True)
        return sorted_path_count_tuples[0:show_top]


    def compute_subtree_stats(self, subtree, counter=None):
        """
        recursively compute counts of different `kind` web sesources in subtree.
        """
        if counter is None:
            counter = Counter()
            # don't count subtree itself, only its children
        else:
            counter[subtree['kind']] += 1
        if 'children' in subtree:
            for child in subtree['children']:
                self.compute_subtree_stats(child, counter=counter)
        return counter

    def print_tree(self, tree_root, print_depth=4, hide_keys=[]):
        """
        Print contents of web resource tree starting at `tree_root`.
        """
        def print_web_resource_node(node, depth=1):
            INDENT_BY = 3
            extra_attrs = ''
            if node is None:
                print('Encountered a None node in print_web_resource_node')
                return
            if 'kind' in node:
                extra_attrs = ' ('+node['kind']+') '
            path = self.url_to_path(node['url'])  # print paths instead of full URLs
            if 'title' in node:
                title = node['title']
            else:
                title = ''
            print(' '*INDENT_BY*depth + '  -', title, 'path:', path, extra_attrs)
            if depth < print_depth:                 # recurse and print children
                if node['children']:
                    print(' '*INDENT_BY*depth + '   ', 'children:')
                    for child in node['children']:
                        print_web_resource_node(child, depth=depth+1)
            else:                                    # print only summary counts
                counts = self.compute_subtree_stats(node)
                if counts:
                    counts_str = str(counts).replace('Counter', '').strip('()')
                    print(' '*INDENT_BY*depth + '   ', 'children counts:', counts_str)
        print_web_resource_node(tree_root)


    def infer_gloabal_nav(self, tree_root, debug=False):
        """
        Returns a list of web resources that are likely to be global nav links.
        """
        global_nav_nodes = dict(
            url=self.MAIN_SOURCE_DOMAIN,
            kind='GlobalNavLinks',
            children=[],
        )

        # 1. infer global nav URLs based on total seen count / total pages visited
        total_urls_seen_count = len(self.global_site_urls.keys())

        def _is_likely_global_nav(url):
            """
            Returns True if `url` is likely a global nav link based on how often seen in pages.
            """
            if url not in self.global_site_urls: # this should not be necessary but not worth figuring it out
                return False

            seen_count = self.global_site_urls[url]['count']
            if debug:
                LOGGER.debug('seen_count/total_urls_seen_count='
                              + str(float(seen_count)/total_urls_seen_count)
                              + '=' + str(seen_count) + '/' + str(total_urls_seen_count)
                              + self.url_to_path(url))
            # if previously determined to be a global nav link
            for global_nav_resource in global_nav_nodes['children']:
                if url == global_nav_resource['url']:
                    return True
            # if new link that is seen a lot
            if float(seen_count)/total_urls_seen_count > self.GLOBAL_NAV_THRESHOLD:
                return True
            return False

        def recursive_visit_find_global_nav_children(subtree):
            for child in subtree['children']:
                child_url = child['url']
                if len(child['children'])== 0 and _is_likely_global_nav(child_url):
                    LOGGER.debug('Found candidate for global nav url=' + str(child_url)
                                  + 'adding to global_nav_nodes')
                    global_nav_resource = dict(
                        kind='GlobalNavLink',
                        url=child_url,
                    )
                    global_nav_resource.update(child)
                    global_nav_nodes['children'].append(global_nav_resource)
                # recurse
                recursive_visit_find_global_nav_children(child)

        recursive_visit_find_global_nav_children(tree_root)
        return global_nav_nodes


    def remove_global_nav(self, tree_root, global_nav_nodes):
        """
        Walks web resource tree and removes all web resources whose URLs match
        nodes in global_nav_nodes['children'].
        This method is a helper for debugging. Your production crawler should use
        `self.IGNORE_URLS` to remove global nav links so won't crawl them at all.
        """
        global_nav_urls = [d['url'] for d in global_nav_nodes['children']]
        def _recursive_visit_rm_global_nav_children(subtree):
            newchildren = []
            for child in subtree['children']:
                child_url = child['url']
                if len(child['children'])== 0 and child_url in global_nav_urls:
                    LOGGER.info('Removing global nav url =' + child_url)
                else:
                    clean_child = _recursive_visit_rm_global_nav_children(child)
                    newchildren.append(clean_child)
            subtree['children'] = newchildren
            return subtree
        _recursive_visit_rm_global_nav_children(tree_root)


    def cleanup_web_resource_tree(self, tree_root):
        """
        Remove nodes' parent links (otherwise tree is not json serializable).
        """
        def cleanup_subtree(subtree):
            if 'parent' in subtree:
                del subtree['parent']
            for child in subtree['children']:
                cleanup_subtree(child)
        cleanup_subtree(tree_root)
        return tree_root



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

    def write_url_to_file(url, site):
        #pathname = urllib.
        pass

    def pre_crawl_setup(self):
        self.queue = queue.Queue()

        self.urls_visited = {}
        self.global_site_pages = {}
        self.global_site_urls = {}
        self.global_site_redirects = {} # DB of all urls that redirect
        self.global_site_error_urls = {}
        self.global_site_ignored_urls = {}

    def read_global_site_json(self):
        try:
            self.global_site_urls = adm.read_json(self.CRAWLING_OUTPUT_URLS)
            self.global_site_pages = adm.read_json(self.CRAWLING_OUTPUT_PAGES)
            self.global_site_redirects = adm.read_json(self.CRAWLING_OUTPUT_REDIRECTS)
            self.global_site_error_urls = adm.read_json(self.CRAWLING_OUTPUT_ERROR_URLS)
            self.global_site_ignored_urls = adm.read_json(self.CRAWLING_OUTPUT_IGNORED_URLS)
        except:
            pass

    def post_crawl_output(self):
        self.write_web_resource_tree_json(self.global_site_urls, self.CRAWLING_OUTPUT_URLS)
        self.write_web_resource_tree_json(self.global_site_pages, self.CRAWLING_OUTPUT_PAGES)
        self.write_web_resource_tree_json(self.global_site_redirects, self.CRAWLING_OUTPUT_REDIRECTS)
        self.write_web_resource_tree_json(self.global_site_error_urls, self.CRAWLING_OUTPUT_ERROR_URLS)
        self.write_web_resource_tree_json(self.global_site_ignored_urls, self.CRAWLING_OUTPUT_IGNORED_URLS)

    # OUTPUT JSON
    ############################################################################

    def write_web_resource_tree_json(self, channel_dict, destpath):
        parent_dir, _ = os.path.split(destpath)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(destpath, 'w') as wrt_file:
            json.dump(channel_dict, wrt_file, ensure_ascii=False, indent=2, sort_keys=True)

    def set_output_file_names(self, site):
        site = './' + site
        self.CRAWLING_OUTPUT_URLS = site + '_urls.json'
        self.CRAWLING_OUTPUT_PAGES = site + '_pages.json'
        self.CRAWLING_OUTPUT_REDIRECTS = site + '_redirects.json'
        self.CRAWLING_OUTPUT_ERROR_URLS = site + '_error_urls.json'
        self.CRAWLING_OUTPUT_IGNORED_URLS = site + '_ignored_urls.json'

    # KEYBOARD CAPTURE
    ############################################################################
    def key_capture_thread(self):
            input()
            self.continue_processing_flag = False

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

# HTTP CACHE
################################################################################

class CacheForeverHeuristic(BaseHeuristic):
    """
    Cache the response effectively forever.
    """
    def update_headers(self, response):
        headers = {}
        expires = expire_after(timedelta(weeks=10*52), date=datetime.now())
        headers['expires'] = datetime_to_header(expires)
        headers['cache-control'] = 'public'
        return headers
