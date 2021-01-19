#!/usr/bin/python3
import re

from basicspider.spider import BasicSpider
from basicspider.spider import LOGGER, logging, set_log_level
set_log_level(logging.DEBUG)

# PARAMS
################################################################################
site = 'rarediseases.info.nih.gov'
MAIN_SOURCE_DOMAIN = 'https://' + site
START_PAGE = 'https://' + site
SOURCE_DOMAINS = []
IGNORE_URLS = []
crawler = BasicSpider(main_source_domain=MAIN_SOURCE_DOMAIN)
crawler.IGNORE_URLS.extend(IGNORE_URLS)

crawler.set_output_file_names(site)
crawler.SHORTEN_CRAWL = True


# CLI
################################################################################

if __name__ == '__main__':

    channel_tree = crawler.crawl(limit=None)

    #crawler.print_tree(channel_tree)
    print('\nOutput saved to ./' + site)
