in PyPI
basicspider is available
simplescraper is not

ours will be basicspider
started as changes to Ivan's basiccrawler,
but now backwards compatibility will not be maintained

docs at C:\DropBoxRoot\Dropbox\DesktopLaptop\Devel\ScraperTools
Ivan's repo as modified by me D:\GitXtra\BasicCrawler

something like https://github.com/webrecorder/browsertrix may ultimately be used to scrape,
but we need an analyzer to decide what to scrape

move work from iiab-working to iiab-content

apt install python3-pip
pip3 install CacheControl
pip3 install youtube_dl

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

we have two checks, in site_urls and in fs

when add to site_urls, site_pages, fs

depends on whether data read on startup

OUT TAKES from spider.py

def download_page(self, url, *args, **kwargs):

vs def download_page(url): in sp_lib

def make_request(self, url, timeout=60, *args, method='GET', **kwargs):

SESSION used by spider.py
