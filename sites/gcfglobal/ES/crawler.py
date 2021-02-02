#!/usr/bin/python3
import re

from basicspider.crawl import BasicSpider
from basicspider.crawl import LOGGER, logging, set_log_level
set_log_level(logging.DEBUG)

# PARAMS
################################################################################
START_PAGE = 'https://edu.gcfglobal.org/es/topics/'
MAIN_SOURCE_DOMAIN = None
HTML_INCL_PATTERNS = ['https://edu.gcfglobal.org/es/', 'http://www.gcfaprendelibre.org/']
HTML_EXCL_PATTERNS = []

crawler = BasicSpider(main_source_domain=MAIN_SOURCE_DOMAIN, start_page=START_PAGE)
# crawler = BasicSpider(start_page=START_PAGE)

#crawler.IGNORE_URLS.extend(IGNORE_URLS)
crawler.add_incl_patterns(HTML_INCL_PATTERNS)
crawler.add_excl_patterns(HTML_EXCL_PATTERNS)

# optional output override
# crawler.OUTPUT_FILE_PREFIX = 'site'
# crawler.DOWNLOAD_DEST_DIR = ''

crawler.SHORTEN_CRAWL = True


# CLI
################################################################################

if __name__ == '__main__':

    crawler.crawl(limit=None)

    crawler.post_crawl_output()
