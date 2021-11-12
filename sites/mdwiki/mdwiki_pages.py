#!/usr/bin/python3
import sys
import requests
from basicspider.crawl import BasicSpider

# revisions https://mdwiki.org/w/api.php?action=query&format=json&list=allrevisions&arvdir=newer&arvlimit=max&arvcontinue=

import logging
import logging.handlers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler("mdwiki-list.log", 'a', maxBytes=5000, backupCount=10),
        logging.StreamHandler()
    ]
)

INCL_WP = True
WPMED_LIST = 'http://download.openzim.org/wp1/enwiki/customs/medicine.tsv'
MAX_LOOPS = -1 # -1 is all

def main(args):
    en_wp_med = get_kiwix_med_list() # list from kiwix medicine
    mdwiki_list = get_mdwiki_list() # list from mdwiki api
    en_wp_only = en_wp_med - mdwiki_list # items only in en wp
    en_wip_redir = get_en_wp_redirects(en_wp_only)
    combined = mdwiki_list + en_wp_med + en_wip_redir

    logging.info('List Creation Succeeded.')
    sys.exit(0)

# https://en.wikipedia.org/w/api.php?action=query&prop=redirects&titles=Cilazapril

def get_kiwix_med_list():
    try:
        r = requests.get(WPMED_LIST)
        wikimed_pages = r._content.decode().split('\n')
        allpages = set(wikimed_pages)
    except Exception as error:
        logging.error(error)
        logging.error('Request for medicine.tsv failed. Ignoring.')
        allpages = set()
    return allpages

def get_mdwiki_list(apfilterredir='nonredirects'):
    md_wiki_pages = set()
    for namesp in ['0', '3000']:
        # q = 'https://mdwiki.org/w/api.php?action=query&apnamespace=' + namesp + '&format=json&list=allpages&aplimit=max&apcontinue='
        q = 'https://mdwiki.org/w/api.php?action=query&apnamespace=' + namesp + '&format=json'
        q += '&list=allpages&apfilterredir=' + apfilterredir + '&aplimit=max&apcontinue='
        apcontinue = ''
        loop_count = MAX_LOOPS
        while(loop_count):
            try:
                r = requests.get(q + apcontinue).json()
            except Exception as error:
                logging.error(error)
                logging.error('Request failed. Exiting.')
                sys.exit(1)
            pages = r['query']['allpages']
            apcontinue = r.get('continue',{}).get('apcontinue')
            for page in pages:
                #allpages[page['title']] = page
                md_wiki_pages.add(page['title'])
            if not apcontinue:
                break
            loop_count -= 1
    return md_wiki_pages

def get_en_wp_redirects(search_list):
    en_wip_redir = set()
    q = 'https://en.wikipedia.org/w/api.php?action=query&prop=redirects&format=json&titles='
    for title in search_list:
        if not title:
            continue
        #print(title)
        rdcontinue = ''
        loop_count = MAX_LOOPS
        while(loop_count):
            qq = q + title + '&rdcontinue=' + rdcontinue
            r = requests.get(qq).json()
            rdcontinue = r.get('continue',{}).get('rdcontinue')
            pages = r['query']['pages']
            for page in pages:
                redirects = pages[page].get('redirects')
                if redirects:
                    for red in redirects:
                        en_wip_redir.add(red['title'])
            if not rdcontinue:
                break
            loop_count -= 1
    return en_wip_redir

def write_output(data, output_file):
    try:
        with open(output_file, 'w') as f:
            for item in data:
                f.write("%s\n" % item)
    except Exception as error:
        logging.error(error)
        logging.error('Failed to write to list file.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert downloaded html. By default downloads asset files")
    parser.add_argument("-n", "--nodownload", help="don't download assets", action="store_true")
    args = parser.parse_args()
    main(args)
