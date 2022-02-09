# tried on Debian 11
# this works
# CONTAINS WORKING FRAGMENTS

# apt install chromium
# chromium --headless --no-sandbox --nogpu --remote-debugging-port=9222 https://chromium.org to start (with complaints)
# apt -y install python3-pip
# pip3 install selenium
# pip3 install webdriver_manager
# pip3 install pillow # repackaged PIL
# https://pillow.readthedocs.io/en/stable/
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
chrome_options.add_argument('--window-size=800,1500')

# --headless --disable-gpu --screenshot --window-size1280,1696 (--window-size=1280,1696)
# https://www.adoclib.com/blog/selenium-wrong-screenshot-resolution-when-using-headless-firefox.html

driver = webdriver.Chrome(service=ser, options=chrome_options)
driver.get("https://www.python.org")
print(driver.title)
# search_bar = driver.find_element_by_name("q") - deprecated
search_box = driver.find_element(By.ID, "id-search-field")

search_bar.clear()
search_bar.send_keys("getting started with python")
search_bar.send_keys(Keys.RETURN)

print(driver.current_url)

# now works to here 1/29/2022

url = 'https://ourworldindata.org/grapher/covid-vaccination-doses-per-capita?tab=map&time=latest'
malurl = 'https://ourworldindata.org/grapher/share-of-population-with-schizophrenia?tab=map&time=latest'

driver.get(url)

download_tab = driver.find_element(By.CLASS_NAME, "download-tab-button")

download_tab = driver.find_element(By.CSS_SELECTOR, "li.download-tab-button")
download_tab = driver.find_element(By.CSS_SELECTOR, "li.download-tab-button > a")

# cookie question gets clicked

accept = driver.find_element(By.CSS_SELECTOR, "div.cookie-notice  button.accept")
accept.click()

download_tab.click() # works after accept.click()

img = driver.find_element(By.CSS_SELECTOR, "div.DownloadTab img")

src = img.get_attribute("src")

driver.save_screenshot("screenshot.png")

# could also just take a screen shot of the top level page with <iframe>

frame_url = 'http://iiab-ref/test/owid-frame.html'
driver.get(frame_url)
driver.save_screenshot("frame-shot.png")
driver.refresh() # if write new html file

from PIL import Image
from Screenshot import Screenshot_clipping

# pip3 install above

from Screenshot import Screenshot_Clipping
from selenium import webdriver
from PIL import Image
ss = Screenshot_clipping.Screenshot()
driver = webdriver.Chrome()
driver.get("https://www.google.com/”’)
screen_shot = ss.full_screenshot(driver, save_path = ‘/path’, image_name= ‘name.png’)
screen = Image.open(screen_shot)
screen.show()

# https://github.com/PyWizards/Selenium_Screenshot

# use local file - none of these worked

file_url = 'file:///test.html'
file_url = 'file://test.html'
file_url = 'file:////root/owidtest.html'

file_url = 'file:///root/owid/test.html' # works


# strategy to get svg of only map

driver.get(malurl)

# this gets just the map and bottom legend

map_svg = driver.find_element(By.CSS_SELECTOR, "svg g.mapTab")

screenshot_as_bytes = map_svg.screenshot_as_png

with open('map.png', 'wb') as f:
    f.write(screenshot_as_bytes)

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

map = map_svg.find_element(By.CSS_SELECTOR, "g.ChoroplethMap").get_attribute('outerHTML')
scale = map_svg.find_element(By.CSS_SELECTOR, "g.numericColorLegend").get_attribute('outerHTML')

svg = map_svg.get_attribute('outerHTML')

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
            width:400px;
            height:400px;
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
    h += '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="400" height="300" viewBox="0 0 400 300">'
    # h += '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="100%" height="auto">'
    f = '</svg>' + '<span class="owid-footer">' + footer + '</span>'
    f +=  '''
        </div>
        </body>
        </html>
        '''
    s = str(svg)
    html = h + s + f
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

# Try images
# 640 x 300 chrome size

from PIL import Image
im = Image.open("/var/www/html/map.png")
cropped = im.crop((0, 50, 500, 400))

cropped.save("/var/www/html/map2.png", "PNG")

svg_container = map_svg.find_element(By.XPATH, "./..")

screenshot_as_bytes = svg_container.screenshot_as_png
with open('/var/www/html/map3.png', 'wb') as f:
    f.write(screenshot_as_bytes)

# img_width = im.size[0]
xsize, ysize = im.size

blank = im.crop(xsize - 50, 20, xsize, 40 )
