from urllib.parse import urljoin, urldefrag, urlparse
from basicspider.sp_lib import *

# SPIDER CORE
################################################################################

class SpiderCore(object):
    """
    Common functions and data structures
    """
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

    # subclass can change these
    OUTPUT_FILE_PREFIX = 'site'
    DOWNLOAD_DEST_DIR = 'site-download/'

    HTML_INCL_PATTERNS = []
    HTML_EXCL_PATTERNS = []

    # saved data structures
    site_pages = {} # DB of all pages that have ever been parsed
    site_urls = {} # DB of all urls that have ever been seen
    site_redirects = {} # DB of all urls that redirect
    site_error_urls = {}
    site_ignored_urls = {}

    def __init__(self, prefix=OUTPUT_FILE_PREFIX, load_data=True):
        if load_data:
            self.read_site_json(prefix)

    def add_incl_patterns(self, pattern_list):
        self.HTML_INCL_PATTERNS += list(set(pattern_list) - set(self.HTML_INCL_PATTERNS))

    def add_excl_patterns(self, pattern_list):
        self.HTML_EXCL_PATTERNS += list(set(pattern_list) - set(self.HTML_EXCL_PATTERNS))

    def pre_crawl_setup(self):
        #self.queue = queue.Queue()

        self.urls_visited = {}
        self.site_pages = {}
        self.site_urls = {}
        self.site_redirects = {} # DB of all urls that redirect
        self.site_error_urls = {}
        self.site_ignored_urls = {}

    def read_site_json(self, prefix):
        try:
            self.site_urls = read_json_file(prefix + '_urls.json')
            self.site_pages = read_json_file(prefix + '_pages.json')
            self.site_redirects = read_json_file(prefix + '_redirects.json')
            self.site_error_urls = read_json_file(prefix + '_error_urls.json')
            self.site_ignored_urls = read_json_file(prefix + '_ignored_urls.json')
        except:
            pass

    def write_site_json(self, prefix):
        write_json_file(self.site_urls, prefix + '_urls.json', sort_keys=True)
        write_json_file(self.site_pages, prefix + '_pages.json', sort_keys=True)
        write_json_file(self.site_redirects, prefix + '_redirects.json', sort_keys=True)
        write_json_file(self.site_error_urls, prefix + '_error_urls.json', sort_keys=True)
        write_json_file(self.site_ignored_urls, prefix + '_ignored_urls.json', sort_keys=True)


    def post_crawl_output(self):
        self.write_site_json(self.OUTPUT_FILE_PREFIX)

    # KEYBOARD CAPTURE
    ############################################################################
    def key_capture_thread(self):
        input()
        self.continue_processing_flag = False
