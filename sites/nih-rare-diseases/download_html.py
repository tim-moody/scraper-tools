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
    #download_disease_cases()
    #download_disease_nav()
    #download_glossary()
    #download_espanol()
    pass

def download_disease_cases():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/diseases/.+/cases'] # disease cases
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    download_urls(url_list, content_type, download_dest_dir)

def download_disease_nav():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/diseases/categories',
                match_prefix + '/diseases/diseases-by-category',
                match_prefix + '/diseases/browse-by-first-letter']
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    download_urls(url_list, content_type, download_dest_dir)

def download_glossary():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/glossary',
                match_prefix + '/Glossary']
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    download_urls(url_list, content_type, download_dest_dir)

def download_espanol():
    match_prefix = '^https?://rarediseases.info.nih.gov'
    matches = [match_prefix + '/espanol',
                match_prefix + '/glosario']
    content_type = 'text/html'
    url_list = filter_urls(site_urls, content_type, matches)
    download_urls(url_list, content_type, download_dest_dir)

if __name__ == "__main__":
    main(sys.argv)
