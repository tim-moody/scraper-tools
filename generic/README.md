## Status

Still under development

## Deployment - Future

will put in PyPI

apt install python3-pip
pip3 install CacheControl
pip3 install youtube_dl

## Components

* sp_lib.py - importable functions
* core.py - Class of common functions and variables
* crawl.py - Class for spidering a target site
* crunch.py - Class for analyzing crawl data
* scripts/crawler.py - template for spidering site
* scripts/cruncher.py - template for analyzing site

## BasicSpider Algorithm

* Get start url from parameter or start domain
* Verify that it returns html with no redirect
* Add start url to queue
* Loop until done or key pressed
    * Get next url from queue
    * Compute file name
    * If already downloaded and not force
        * Read html from file
    * Else
        * Requests.get page html for url (can only be html url)
        * Write html to file
    * If already in site_pages
        * add to page count
        * continue
    * For each link on page
        * If matches ignore list continue
        * Get link info with requests.head
        * Record link in site_urls
        * If html
            * If matches include and not matches exclude
                * Add to queue
    * Record page and children in site_pages
* Write data structures to files

## Links

A page is searched for 'a' and 'link' tags that have an 'href' property and 'audio', 'embed', 'iframe', 'img', 'input', 'script', 'source', 'track', and 'video' tags that have a 'src' property. For each of the resulting links, if the url does not match Ignore Links, requests.head is used to determine the content type of its target and its size.

## Filtering

In order to be queued for parsing a url must return html and must not match Ignore Links, must match a Pattern to Include and not match a Pattern to Exclude.

? Add constraining div container in do_one_page()

### Ignore Links

These are things like 'javascript:void(0)' which will be ignored without any request for attributes. The list is in IGNORE_LINKS, which can be extended.

### Url Patterns to Include

These are a list of strings or compiled regular expressions in HTML_INCL_PATTERNS. Any url that returns html is matched against these patterns and if there is a match it is queued for parsing. Strings match to the first part of the url.

### Url Patterns to Exclude

These are a list of strings or compiled regular expressions in HTML_EXCL_PATTERNS. Any url that returns html is matched against these patterns and if there is a match it is not queued for parsing. Strings match to the first part of the url.

## Output

* url_to_file_name

* always add .html or not