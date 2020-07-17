import scrapy
import unicodedata
from konbini.items import KonbiniItem
import logging
import numpy as np
import time
import wget
import os
import sys
import urllib
from selenium import webdriver

class GooglecrawlerSpider(scrapy.Spider):
    '''
    A spider for crawling paper information and pdf from GoogleScholar.
    Problems remaining to be solved: crawl citations

    Parameters:
        keywords (str): spaced by ' ', e.g., 'land entitlement'.
        directory (str): directory of PDF files. Using alias as `~` is prohibited. Use `/Users/xxxx/` instead.

    '''
    name = 'googlecrawler'

    def __init__(self, keywords, directory='./', verbose=True, startpage=1):
        self.keywords = keywords
        self.dir = directory
        self.verbose = verbose
        synthetic_keyword = "+".join(keywords.split(' '))
        start_num = int((int(startpage) - 1) * 10)
        start_urls = ['https://scholar.google.com/scholar?start={0}&as_vis=1&q={1}&hl=en&as_sdt=1,47'.format(start_num, synthetic_keyword)]
        self.start_urls = start_urls
        self.driver = webdriver.Safari()
        self.logger.propagate = True
        self.page = int(startpage)
        super().__init__()


    def parse(self, response):
        item = KonbiniItem()
        papers = response.css('div.gs_r.gs_or.gs_scl')
        ## If you are banned by Google ##
        if len(response.css('div#gs_bdy form ::text').getall()) != 0:
            if response.css('div#gs_bdy form ::text').get() == "Please show you're not a robot":
                raise ValueError('You are banned by Google! Try to run this code later, or change your IP address!')

        for jj, paper in enumerate(papers):
            sleep_time = np.random.randint(1, 3, 1)
            time.sleep(sleep_time)
            ## Retrieve information ##
            item['title'] = "".join(paper.css('h3.gs_rt').css('a ::text').getall())
            info = ''.join(paper.css('div.gs_a').css('::text').getall())
            info = unicodedata.normalize("NFKD", info)
            item['author'] = info.split(' - ')[0].strip()
            year = paper.css('div.gs_a').css('::text').re(r'[0-9]{4}')
            if len(year) != 0:
                item['year'] = year[0]
            else:
                item['year'] = ''
            item['journal'] =  info.split(' - ')[1].split(',')[0].strip().strip(item['year'])
            item['abstract'] = "".join(paper.css('div.gs_rs ::text').getall()).strip('\xa0…')
            item['pdf'] = paper.css('div.gs_or_ggsm a::attr(href)').get()
            item['url'] = paper.css('h3.gs_rt a::attr(href)').get() 
            print('--------------------------------------------------')
            print('### Page {0}, item {1} ###'.format(self.page, jj + 1))

            ## Download PDF ##
            filename = '{0}_{1}_{2}.pdf'.format(item['author'], item['year'], item['journal'])
            filename = os.path.join(self.dir, filename)
            item['if_download'] = True
            if not os.path.isfile(filename):
                if item['pdf'] is None:
                    item['if_download'] = False
                    print('Warning: No PDF available for this paper!')
                    self.logger.warning('No PDF available for this paper!')
                else:
                    try:
                        #urllib.request.urlretrieve(item['pdf'], filename=filename)
                        wget.download(item['pdf'], out=filename)
                    except Exception as e:
                        if e is urllib.error.HTTPError or e is urllib.error.URLError:
                            print('Warning: {}'.format(e))
                            self.logger.warning(e)
                            item['if_download'] = False
            else:
                print('Warning: PDF already exists!')
                self.logger.warning('PDF already exists!')

            ## Extract citation ##
            try:
                self.driver.get(response.url)
                cite_button = self.driver.find_elements_by_css_selector('a.gs_or_cit')[jj]
                cite_button.click()
                time_lap = np.random.randint(10, 20, 1)
                time.sleep(time_lap)

                citation = {}   ##设置一个字典
                cite_style_list = self.driver.find_elements_by_css_selector('th.gs_cith')
                cite_list = self.driver.find_elements_by_css_selector('div.gs_citr')
                for i in range(len(cite_list)):
                    style = cite_style_list[i].text
                    citation[style] = cite_list[i].text

                if 'APA' in citation.keys():
                    item['citation'] = citation['APA']
                else:
                    item['citation'] = 'No citation'
            except Exception as e:
                print('Error: {}'.format(e))
                item['citation'] = 'No citation'

            ## -w- ##
            print('{0}, {1}, {2} is finished.'.format(item['author'], item['year'], item['journal']))
            self.logger.info('{0}, {1}, {2} is finished.'.format(item['author'], item['year'], item['journal']))
            
            yield item
        
        next_page = response.css('div#gs_n td')[-1].css('::attr(href)').get()
        if next_page is not None:
            sleep_time = np.random.randint(20, 30, 1)
            time.sleep(sleep_time)
            self.page += 1
            yield response.follow(next_page, callback=self.parse)