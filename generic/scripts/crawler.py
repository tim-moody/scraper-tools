#!/usr/bin/python3
import re

from basicspider.crawl import BasicSpider
from basicspider.crawl import LOGGER, logging, set_log_level
set_log_level(logging.DEBUG)

# PARAMS
################################################################################
site = 'rarediseases.info.nih.gov'
MAIN_SOURCE_DOMAIN = 'https://' + site
START_PAGE = 'https://' + site
SOURCE_DOMAINS = []
IGNORE_URLS = []
HTML_INCL_PATTERNS = []
HTML_EXCL_PATTERNS = []

crawler = BasicSpider(main_source_domain=MAIN_SOURCE_DOMAIN)
# crawler = BasicSpider(start_page=START_PAGE)

crawler.IGNORE_URLS.extend(IGNORE_URLS)
crawler.add_incl_patterns(HTML_INCL_PATTERNS)
crawler.add_excl_patterns(HTML_EXCL_PATTERNS)

# optional output override
# crawler.OUTPUT_FILE_PREFIX = site
# crawler.DOWNLOAD_DEST_DIR = ''

crawler.SHORTEN_CRAWL = True


# CLI
################################################################################

if __name__ == '__main__':

    channel_tree = crawler.crawl(limit=None)

    #crawler.print_tree(channel_tree)
    print('\nOutput saved to ./' + site)
