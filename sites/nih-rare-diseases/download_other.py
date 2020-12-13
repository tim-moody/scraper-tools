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

site = 'rarediseases.info.nih.gov'

orig_dir = '/articlelibrary/viewarticle/'
base_url = 'https://' + site + orig_dir
download_dest_dir = 'site-download'
dst_dir = '/library/www/html/modules/en-nih_rarediseases'

# read stats
site_urls = read_json_file(site + '_urls.json')
site_redirects = read_json_file(site + '_redirects.json')

disease_catalog = read_json_file('disease-catalog.json')

page_links = {}

def main(argv):
    download_images()
    download_assets()
    pass

def download_images():
    download_image_type('image/jpeg')
    download_image_type('image/png')

def download_assets():
    download_asset_type('application/javascript')
    download_asset_type('text/javascript')
    download_asset_type('text/css')

def download_image_type(content_type):
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/content',
               match_prefix + '/Content',
               match_prefix + '/files']
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
