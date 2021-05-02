#!/usr/bin/python3
import sys
import requests

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

if INCL_WP:
    output_file = 'combined.tsv'
else:
    output_file = 'mdwiki-only.tsv'

MAX_LOOPS = -1 # -1 is all

# get wp med article list if desired
if INCL_WP:
    try:
        r = requests.get(WPMED_LIST)
        wikimed_pages = r._content.decode().split('\n')
        allpages = set(wikimed_pages)
    except Exception as error:
        logging.error(error)
        logging.error('Request for medicine.tsv failed. Ignoring.')
        allpages = set()
else:
    allpages = set()

for namesp in ['0', '3000']:
    q = 'https://mdwiki.org/w/api.php?action=query&apnamespace=' + namesp + '&format=json&list=allpages&aplimit=max&apcontinue='
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
            allpages.add(page['title'])

        if not apcontinue:
            break
        loop_count -= 1

try:
    with open(output_file, 'w') as f:
        for item in allpages:
            f.write("%s\n" % item)
except Exception as error:
    logging.error(error)
    logging.error('Failed to write to list file. Exiting.')
    sys.exit(1)

logging.info('List Creation Succeeded.')
sys.exit(0)
