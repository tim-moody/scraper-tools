#!/usr/bin/python3
import os, string, sys
import copy
import json
import re
import string
import requests
import posixpath
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup, Comment, SoupStrainer
from sp_lib import *

START_PAGE = 'https://edu.gcfglobal.org/es/topics/'
MAIN_SOURCE_DOMAIN = None
HTML_INCL_PATTERNS = ['https://edu.gcfglobal.org/es/', 'http://www.gcfaprendelibre.org/']
HTML_EXCL_PATTERNS = []
OUTPUT_FILE_PREFIX = 'site'
DOWNLOAD_DIR = 'site-download/'

dst_dir = '/library/www/html/modules/es-GCF2021/'
external_url_not_found = '/not-offline.html'

# read stats
site_urls = read_json_file(OUTPUT_FILE_PREFIX + '_urls.json')
site_pages = read_json_file(OUTPUT_FILE_PREFIX + '_pages.json')
site_redirects = read_json_file(OUTPUT_FILE_PREFIX + '_redirects.json')

page_links = {}

def main(argv):
    download_images()
    download_assets()
    pass

def download_images():
    download_image_type('image/jpeg')
    download_image_type('image/png')
    download_image_type('image/gif')
    download_image_type('image/svg+xml')
    download_image_type('image/bmp')

def download_assets():
    download_asset_type('application/javascript')
    download_asset_type('text/javascript')
    download_asset_type('text/css')

def download_image_type(content_type):
    matches = ['^https?://aprendelibvrefiles.blob.core.windows.net/aprendelibvre-container/',
                "^https?://edu.gcfglobal.org/es",
                "^https?://gcflearnfree.blob.core.windows.net/media",
                "^https?://media.gcflearnfree.org/assets",
                "^https?://media.gcflearnfree.org/content",
                "^https?://media.gcflearnfree.org/ctassets",
                "^https?://media.gcflearnfree.org/global",
                "^https?://media.gcflearnfree.org/ocp",
                "^https?://media.gcflearnfree.org/weborbassets",
                "^https?://edu.gcfglobal.org/images"]

    #https://gcflearnfree.blob.core.windows.net/media/Default/Mobile%20Apps/Assets/Good%20at%20Math.pdf

    #https://gcfal-media.azurewebsites.net/videos/excel2007/Excel2007_less1.mp4

    url_list = filter_urls(site_urls, content_type, matches)
    download_urls(url_list, content_type, download_dest_dir)

def download_asset_type(content_type):
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/content',
               match_prefix + '/Content',
               match_prefix + '/files']
    url_list = filter_urls(site_urls, content_type, matches)
    download_urls(url_list, content_type, download_dest_dir)


if __name__ == "__main__":
    main(sys.argv)
