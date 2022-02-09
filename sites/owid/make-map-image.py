# tried on Debian 11
# this works
# taken from scraper-tools selenium.py
# THIS IS A ROUGH DRAFT

# apt install chromium
# chromium --headless --no-sandbox --nogpu --remote-debugging-port=9222 https://chromium.org to start (with complaints)
# apt -y install python3-pip
# pip3 install selenium
# pip3 install webdriver_manager
# https://chromedriver.chromium.org/downloads
# https://chromedriver.storage.googleapis.com/97.0.4692.71/chromedriver_linux64.zip\
# unzip in cwd

# https://www.browserstack.com/guide/python-selenium-to-run-web-automation-test - a little out of date

# https://www.selenium.dev/documentation/webdriver/actions_api/

from base64 import encode
from cgitb import text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from PIL import Image

# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
# should try this again with the correct options from below
# or just move ./chromedriver to /usr/local/bin

# https://peter.sh/experiments/chromium-command-line-switches/

ser = Service("/usr/local/bin/chromedriver")
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
# chrome_options.add_argument('--window-size=1024,1500')
# chrome_options.add_argument('--window-size=900,1500')
chrome_options.add_argument('--window-size=800,1500')
# chrome_options.add_argument('--window-size=700,1500')

# --headless --disable-gpu --screenshot --window-size1280,1696 (--window-size=1280,1696)
# https://www.adoclib.com/blog/selenium-wrong-screenshot-resolution-when-using-headless-firefox.html

driver = webdriver.Chrome(service=ser, options=chrome_options)

url = 'https://ourworldindata.org/grapher/covid-vaccination-doses-per-capita?tab=map&time=latest'
page1 = 'https://mdwiki.org/wiki/Deployment_of_COVID-19_vaccines' # has url as iframe

malurl = 'https://ourworldindata.org/grapher/share-of-population-with-schizophrenia?tab=map&time=latest'


# create map with iframe of reasonable dimensions

# wr_map_html(malurl)

driver.get(malurl) # open that page
#driver.get('http://192.168.3.53/map.html') # open that page
#driver.save_screenshot('/var/www/html/shot900.png')

# strategy to get svg of only map

# this gets just the map and bottom legend

map_svg = driver.find_element(By.CSS_SELECTOR, "svg g.mapTab") # didn't work when page was http and iframe https?!
svg = map_svg.find_element(By.XPATH, "./..")

screenshot_as_bytes = svg.screenshot_as_png

map_shot = '/var/www/html/map-shot.png'

with open(map_shot, 'wb') as f:
    f.write(screenshot_as_bytes)

im = Image.open(map_shot)

xsize, ysize = im.size
blank = im.crop((xsize - 150, 100, xsize, 150 ))
im.paste(blank, (xsize - 150, 0, xsize, 50))
im.save("/var/www/html/map-edit.png", "PNG")

# trim sides
cropped = im.crop((50, 0, xsize - 50, ysize))

cropped.save("/var/www/html/cropped.png", "PNG")

svg_container = map_svg.find_element(By.XPATH, "./..")

screenshot_as_bytes = svg_container.screenshot_as_png
with open('/var/www/html/map3.png', 'wb') as f:
    f.write(screenshot_as_bytes)

# img_width = im.size[0]
xsize, ysize = im.size

blank = im.crop(xsize - 50, 20, xsize, 40 )


# size is 600 by 2xx a little small

title = driver.find_element(By.CSS_SELECTOR, "div.HeaderHTML h1 span").text

footer = driver.find_element(By.CSS_SELECTOR, "footer.SourcesFooterHTML span").text

parent = map_svg.find_element(By.XPATH, "./..")

parent.get_attribute('style')

element.get_attribute('innerHTML')
element.get_attribute('outerHTML')

# led to

# raise MaxRetryError(_pool, url, error or ResponseError(cause))
# urllib3.exceptions.MaxRetryError: HTTPConnectionPool(host='localhost', port=39151): Max retries exceeded with url: /session/3ae883bcb92fe55b2c27804af72dd224/window (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7fb4a5631d30>: Failed to establish a new connection: [Errno 111] Connection refused'))
# <svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="646" height="260" viewBox="0 0 646 260"
# #style="font-family: Lato, &quot;Helvetica Neue&quot;, Helvetica, Arial, sans-serif; font-size: 16px; background-color: white; text-rendering: geometricprecision; -webkit-font-smoothing: antialiased;">

driver.quit()

driver.get(malurl) # now works again
map_svg = driver.find_element(By.CSS_SELECTOR, "svg g.mapTab")
svg_container = map_svg.find_element(By.XPATH, "./..")
svg_container.get_attribute('width')
svg_container.get_attribute('height')

# write stripped map

driver.get('http://192.168.3.53/map.html') # open that page
map_svg = driver.find_element(By.CSS_SELECTOR, "svg g.mapTab")

map = map_svg.find_element(By.CSS_SELECTOR, "g.ChoroplethMap").get_attribute('outerHTML')
scale = map_svg.find_element(By.CSS_SELECTOR, "g.numericColorLegend").get_attribute('outerHTML')

# svg = map_svg.get_attribute('outerHTML')

svg = map + scale

def wr_html(title, footer, svg):
    h = '''
        <html>
        <head>
        <style>
        .owid-title{
            font-size: 20px;
            line-height: 1;
        }
        .owid-frame{
            width:750px;
            height:600px;
            /* float:right; */
            }
        .owid-footer{
            font-size: 16px;
            line-height: 1;
        }
        </style>
        </head>
        <body>
        <div class="owid-frame">
        '''
    h += '<span class="owid-title">' + title + '</span>'
    h += '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="750" height="600" viewBox="0 0 750 600">'
    # h += '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="100%" height="auto">'
    f = '</svg>' + '<span class="owid-footer">' + footer + '</span>'
    f +=  '''
        </div>
        </body>
        </html>
        '''
    s = str(svg)
    html = h + s + f
    with open('/var/www/html/map2.html', 'wb') as f:
        f.write(html.encode())

def wr_map_html(map_url):
    h = '''
        <html>
        <head>
        <style>
        .owid-title{
            font-size: 20px;
            line-height: 1;
        }
        .owid-frame{
            width:750px;
            height:600px;
            /* float:right; */
            }
        .owid-footer{
            font-size: 16px;
            line-height: 1;
        }
        </style>
        </head>
        <body>
        <div class="owid-frame">
        '''
    h += '<iframe src="' + map_url + '" class="owid-frame"></iframe>'
    f =  '''
        </div>
        </body>
        </html>
        '''
    html = h + f
    with open('/var/www/html/map.html', 'wb') as f:
        f.write(html.encode())

# back to requests

import requests
from bs4 import BeautifulSoup

r = requests.get(malurl)
page = BeautifulSoup(r.text, "html.parser")
svg = page.find("svg")
map_svg = svg.find("g", class_="mapTab")
# didn't work - as if map wasn't loaded yet
# https://stackoverflow.com/questions/65902700/scraping-svg-tags-from-website-using-beautiful-soup
