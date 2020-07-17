import scrapy
import logging
import unicodedata
import numpy as np
import wget
import time
import os
from selenium import webdriver
from urllib.request import urlretrieve
from lit_crawler.items import LitCrawlerItem

def unify(string):
    return unicodedata.normalize("NFKD", string)

# spider class
class GoogleLit(scrapy.Spider):
    '''
    Download literatures from Google Scholar.
    '''
    name = 'google_lit'
    def __init__(self, keywords):
        self.keywords = keywords
        synthetic_keyword = "+".join(keywords.split(' '))
        self.start_urls = [f'https://scholar.google.com/scholar?as_vis=1&q={synthetic_keyword}&hl=en&as_sdt=1,47']
        self.driver = webdriver.Safari()
        super().__init__()
    
    def parse(self, response):
        item = LitCrawlerItem()
        articles = response.css('div.gs_r')
        for ii, article in enumerate(articles[:-1]): # The last one is "create alert"
            time.sleep(5)
            item['url'] = article.css('h3.gs_rt a').attrib['href']
            item['title'] = ''.join(article.css('h3.gs_rt ::text').getall())
            desc = ''.join(article.css('div.gs_a ::text').getall()).strip(', ')
            item['desc'] = desc
            item['first_author'] = desc.split('-')[0].split(',')[0].strip().split(' ')[-1].strip()
            if len(desc.split('-')) == 2:
                item['journal'] = ''
                item['year'] = ''
            elif len(desc.split('-')[1].split(',')) == 1:
                item['journal'] = ''
                item['year'] = desc.split('-')[1].split(',')[0].strip()
            else:
                item['journal'] = desc.split('-')[1].split(',')[0].strip()
                item['year'] = desc.split('-')[1].split(',')[1].strip()
            item['abstract'] = ''.join(article.css('div.gs_rs::text').getall())
            temp = np.array(article.css('div.gs_fl ::text').getall())
            mask = np.array(['Cited' in keyword for keyword in temp])
            if np.sum(mask) == 0:
                item['cite_count'] = '0'
            else:
                item['cite_count'] = temp[mask][0].lstrip('Cited by').strip()

            self.logger.info('{0} et al., {1}, {2}'.format(item['first_author'], item['year'], item['journal']))

            for key in item.keys():
                item[key] = unicodedata.normalize("NFKD", item[key])

            if len(article.css('div.gs_ggs')) != 0:
                item['pdf_url'] = article.css('div.gs_or_ggsm a').attrib['href']
                # Download PDF file
                filename = '{0}-{1}-{2}.pdf'.format(item['first_author'], item['year'], item['journal'])
                if not os.path.isfile(filename):
                    wget.download(item['pdf_url'], out=filename)
            else:
                item['pdf_url'] = ''
                self.logger.warning('No PDF file available for this paper.')
                # raise Warning('No PDF file available for this paper.')
            
            ## Citation ##
            self.driver.get(response.url)
            cite_button = self.driver.find_elements_by_css_selector('a.gs_or_cit')[ii]
            cite_button.click()
            time.sleep(5)
            
            citation = {}   ##设置一个字典
            cite_style_list = self.driver.find_elements_by_css_selector('th.gs_cith')
            cite_list = self.driver.find_elements_by_css_selector('div.gs_citr')
            for i in range(len(cite_list)):
                style = cite_style_list[i].text
                citation[style] = cite_list[i].text

            cite_list = self.driver.find_elements_by_css_selector('a.gs_citi')
            for i in range(len(cite_list)):
                style = cite_list[i].text
                if style == 'BibTeX':
                    bibtex_button = cite_list[i]
            bibtex_button.click()
            time.sleep(10)

            citation['BibTeX'] = self.driver.find_element_by_css_selector('pre').text

            item['apa'] = citation['APA']
            item['bibtex'] = citation['BibTeX']
            
            yield item

        #### next_page = self.driver.find_elements_by_css_selector('div#gs_n td a')[0]
        #### next_page.click()
        next_page = response.css("div#gs_n td a::attr(href)").getall()[-1]
        if next_page is not None:
            time.sleep(15)
            yield response.follow(next_page, callback=self.parse)

            #except:
            #    break
       # self.driver.close()

### ADD 404 warning if inside GFW
### ADD overwrite
### ADD brief description for every paper
### inputs: key words, year, directory, 
