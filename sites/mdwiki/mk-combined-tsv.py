#!/usr/bin/python3
import sys
import requests
import json

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

# these pages cause mwoffliner to fail when used with cacher
EXCLUDE_PAGES = ['1%_Rule_(aviation_medicine)',
                '1%_rule_(aviation_medicine)',
                'Nitrous_oxide_50%-oxygen_50%']

mdwiki_list = []
mdwiki_redirects_raw = {}
mdwiki_redirect_list = []
mdwiki_rd_lookup = {}

# assumes redirect.json already downloaded from mdwiki

# get all non-redirect pages from mdwiki
#   get_mdwiki_page_list() (ns 0, 4)
# get medicine.tsv from open zim
# get mdwiki redirects
# calc and store as json:
# mdwiki_redirect_list = []
# mdwiki_rd_lookup = {}
# calc enwp_list
#   remove articles that are mdwiki redirects from
#   add any page in mdwiki_rd_lookup not in mdwiki_list
# combine lists into mdwikimed.tsv
# all mdwiki
# add any enwp not in mdwiki_redirect_list
# add any page in mdwiki_rd_lookup not already there

def main():
    global mdwiki_list

    logging.info('Getting list of pages from mdwiki.')
    mdwiki_list = get_mdwiki_list() # list from mdwiki api
    logging.info('Processing downloaded list of redirects from mdwiki.')
    get_mdwiki_redirect_lists()
    logging.info('Getting list of pages from EN WP.')
    enwp_list = get_kiwix_med_list() # list from kiwix medicine

    write_output(mdwiki_list, 'mdwiki.tsv')
    write_output(enwp_list, 'enwp.tsv')
    #en_wp_only = en_wp_med - mdwiki_list # items only in en wp
    #en_wip_redir = get_en_wp_redirects(en_wp_only)
    #combined = mdwiki_list + en_wp_med + en_wip_redir
    # combined = list(set(en_wp_med + en_wp_med))

    mdwiki_redirects = {}
    mdwiki_redirects['list'] = mdwiki_redirect_list
    mdwiki_redirects['lookup'] = mdwiki_rd_lookup

    logging.info('Writing redirects from mdwiki to json file.')
    write_json_file(mdwiki_redirects, 'mdwiki_redirects.json')

    # put mdwiki at start so any timeouts can be rerun more easily

    combined = mdwiki_list
    for page in enwp_list:
        if page not in mdwiki_list:
            combined.append(page)

    logging.info('Writing combined page list for mwoffliner.')
    write_output(combined, 'mdwikimed.tsv')

    logging.info('List Creation Succeeded.')
    sys.exit(0)

# https://en.wikipedia.org/w/api.php?action=query&prop=redirects&titles=Cilazapril

def get_mdwiki_list(apfilterredir='nonredirects'):
    md_wiki_pages = []
    for namesp in ['0', '4']:
        # q = 'https://mdwiki.org/w/api.php?action=query&apnamespace=' + namesp + '&format=json&list=allpages&aplimit=max&apcontinue='
        q = 'https://mdwiki.org/w/api.php?action=query&apnamespace=' + namesp + '&format=json'
        q += '&list=allpages&apfilterredir=nonredirects&aplimit=max&apcontinue='
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
                md_wiki_pages.append(page['title'].replace(' ', '_'))
            if not apcontinue:
                break
            loop_count -= 1
    return md_wiki_pages


def get_mdwiki_redirect_lists():
    # redirect.json
    #   rd_from_id
    #   rd_to_namespace
    #   rd_to_title_hex
    #   rd_from_name_hex
#

    global mdwiki_redirects_raw
    global mdwiki_redirect_list
    global mdwiki_rd_lookup

    mdwiki_redirects_raw = {}
    mdwiki_redirect_list = []
    mdwiki_rd_lookup = {}
    #mdwiki_rd_lookup[HOME_PAGE] = [] # no redirects to home page

    try:
        mdwiki_redirects_hex = read_json_file('redirect.json')
    except Exception as error:
        logging.error(error)
        logging.error('Reading redirect.json failed.')

    for rd in mdwiki_redirects_hex:
        if rd['rd_to_namespace'] != 0: # skip if not in 0 namespace
            continue
        rd_from_title = bytearray.fromhex(rd['rd_from_name_hex']).decode()
        #print('hex: ' + rd['rd_from_name_hex'])
        # rd_from_title = decode_b64(rd['rd_from_name_hex'])
        #print('decoded: ' + rd_from_title)

        #print('hex2: ' + rd['rd_to_title_hex'])
        #rd_to_title = decode_b64(rd['rd_to_title_hex'])
        #print('decoded2: ' + rd_to_title)
        rd_to_title = bytearray.fromhex(rd['rd_to_title_hex']).decode()
        mdwiki_redirect_list.append(rd_from_title)
        if rd_to_title not in mdwiki_rd_lookup:
            mdwiki_rd_lookup[rd_to_title] = []
        mdwiki_rd_lookup[rd_to_title].append({'pageid': rd['rd_from_id'], 'ns': rd['rd_to_namespace'], 'title': rd_from_title})

def get_kiwix_med_list():
    allpages = []
    try:
        r = requests.get(WPMED_LIST)
        wikimed_pages = r._content.decode().split('\n')
        for p in wikimed_pages[0:-1]:
            if p in EXCLUDE_PAGES:
                continue
            if p in mdwiki_list: # exclude because is somewhere in mdwiki titles
                continue
            if p in mdwiki_redirect_list: # exclude because is somewhere in mdwiki redirects
                continue
            allpages.append(p.replace(' ', '_'))
        # now add in any redirects from mdwiki to enwp pages
        for p in mdwiki_rd_lookup.keys():
            if p not in allpages:
                allpages.append(p.replace(' ', '_'))
    except Exception as error:
        logging.error(error)
        logging.error('Request for medicine.tsv failed. Ignoring.')
        allpages = []
    return allpages

def write_output(data, output_file):
    try:
        with open(output_file, 'w') as f:
            for item in data:
                f.write("%s\n" % item)
    except Exception as error:
        logging.error(error)
        logging.error('Failed to write to list file.')

# These are taken from adm cons adm_lib so as not require dependency
def read_json_file(file_path):
    try:
        with open(file_path, 'r') as json_file:
            readstr = json_file.read()
            json_dict = json.loads(readstr)
        return json_dict
    except OSError as e:
        print('Unable to read url json file', e)
        raise

def write_json_file(src_dict, target_file, sort_keys=False):
    try:
        with open(target_file, 'w', encoding='utf8') as json_file:
            json.dump(src_dict, json_file, ensure_ascii=False, indent=2, sort_keys=sort_keys)
            json_file.write("\n")  # Add newline cause Py JSON does not
    except OSError as e:
        raise


if __name__ == "__main__":
    main()
