# -*- coding: utf-8 -*-

import sys
import requests
from bs4 import BeautifulSoup
import hashlib
import os
import pygame
import getopt


class Dictionary(object):

    def __init__(self):
        self.root = None
        self.result = None
        self.api_result = None
        self.api_response = None

    def translate(self, word, api=False):
        if api:
            self.searchAPI(word)
            return
        else:
            self.searchWeb(word)
            result = {
                'noInfo': self.getNoInfo(),
                'errInput': self.checkErrorInput(),
                'baseInfo': self.getBaseInfo(),
                'webInfo': self.getWebInfo(),
                'webPhrase': self.getWebphrase(),
                'wordGroup': self.getWordgroup(),
                'synonym': self.getSynonym(),
                'cognate': self.getCognate(),
                'discription': self.getDiscription(),
                'baike': self.getBaike(),
            }
            self.result = result
            return result

    def searchAPI(self, word):
        # 从youdao api 获取数据
        url = 'http://openapi.youdao.com/api'
        params = {
            'q': word,
            'appKey': '',
            'salt': '2',
        }

        sign = self.getMD5(params)
        # print sign
        params['from'] = 'EN'
        params['to'] = 'zh_CHS'
        params['sign'] = str(sign).upper()
        url_params = ''
        for key, value in params.items():
            url_params +=  "&%s=%s" % (key, value)
        # print url + url_params
        r = requests.get(url, params=params)
        r.raise_for_status()
        self.api_response = r.json()
        # print self.api_response
        self.api_result = {
            'baseInfo': self.getBaseInfoByAPI(),
        }

    def getMD5(self, params):
        data = params['appKey'] + params['q'] + params['salt'] + 'lyDIVgM4Et3J73GGzq9WXULxvzWC5yic'
        hash_md5 = hashlib.md5(data)
        res = hash_md5.hexdigest()
        return res

    def searchWeb(self, word):
        # 从youdao web 抓取数据
        url = 'http://dict.youdao.com/w/eng/{0}/#keyfrom=dict2.index'
        r = requests.get(url.format(word))
        r.raise_for_status()
        # print '_____', r.text
        self.parseHtml(r.text)
        # self.youdao_info = BeautifulSoup(r.text, 'html5lib')

    def parseHtml(self, html):
        # 解析web
        soup = BeautifulSoup(html, "lxml")
        self.root = soup.find(id='results-contents')

    def getBaseInfo(self):
        # 基本解释
        phrs_list = self.root.find(id='phrsListTab')
        result = {'title': '', 'pronounce': '', 'content': []}
        if phrs_list:
            title = phrs_list.find('h2', class_='wordbook-js')
            if title:
                word = title.find(class_='keyword')
                result['title'] = word.get_text().strip() if word else ''
                pronounce = title.find(class_='phonetic')
                result['pronounce'] = pronounce.get_text().strip() if pronounce else ''

            try:
                content = phrs_list.find(class_='trans-container').find('ul')
                lis = content.find('li')
                if lis:
                    all_lis = content.find_all('li')
                    for wt in all_lis:
                        result['content'].append(wt.get_text().replace('\n', '').strip())

                wg = content.find('p', class_='wordGroup')
                if not lis and wg:
                    wgs = content.find_all('p', class_='wordGroup')
                    for wt in wgs:
                        s = []
                        ss = wt.find_all('span')
                        for k in ss:
                            t = k.get_text().replace('\n', '').strip()
                            if t != '':
                                s.append(t)
                        result['content'].append(' '.join(s).replace('; ;', ';'))

            except:
                pass
        # print "getBaseInfo---------", result
        return result

    def getWebphrase(self):
        # 网络短语
        result = []
        web_phrase = self.root.find(id='webPhrase')
        if web_phrase:
            for wg in web_phrase.find_all(class_="wordGroup"):
                w = {
                    'title': wg.find('span').get_text().strip(),
                    'content': '; '.join([s.strip() for s in wg.contents[-1].strip().split(';')]),
                }
                result.append(w)

        return result

    def getNoInfo(self):
        # 没有结果
        result = ''
        err_wrapper = self.root.find(class_='error-note')
        if err_wrapper is not None:
            try:
                dt = err_wrapper.find('dt').get_text().strip()
                dd = err_wrapper.find('dd').get_text().strip()
                result = '%s\n%s' % (dt, dd)
            except:
                pass
        # print 'getNoInfo---------', result
        return result

    def getWebInfo(self):
        # 网络释义
        result = []
        web_info = self.root.find(id='tWebTrans')
        if web_info:
            web_infos = web_info.find_all(class_='wt-container')
            for wi in web_infos:
                w = {
                    'title': wi.find(class_="title").find('span').get_text().replace('\n', '').strip(),
                    'content': wi.find(class_="collapse-content").get_text().replace('\n', '').strip(),
                }
                result.append(w)
        # print "getWebinfo-----------", result
        return result

    def checkErrorInput(self):
        # 检查是否拼写错误
        result = ''
        err_wrapper = self.root.find(class_='typo-rel')
        if err_wrapper:
            word = err_wrapper.find(class_='title').get_text().strip()
            content = err_wrapper.contents[-1].strip()
            result = '%s %s' % (word, content)
        # print "checkErrorInfo-----", result
        return result

    def getSynonym(self):
        # 同义词
        result = []
        synonyms = self.root.find(id='synonyms')
        if synonyms:
            syns = synonyms.find_all('li')
            for s in syns:
                cts = s.next_sibling.next_sibling.find_all(class_='contentTitle')
                w = {
                    'title': s.get_text().strip(),
                    'content': ', '.join([k.get_text().replace('\n', '').replace(',', '').strip() for k in cts]),
                }
                result.append(w)
        # print "同义词---------", result
        return result

    def getWordgroup(self):
        # 词组短语
        return self.getLoop('wordGroup')

    def getCognate(self):
        # 同根词
        return self.getLoop('relWordTab')

    def getDiscription(self):
        # 词语辨析
        result = []
        disc = self.root.find(id='discriminate')
        if disc:
            wordGroup = disc.find_all(class_='wordGroup')
            for wg in wordGroup:
                w = {
                    'title': wg.find('span').get_text().strip(),
                    'content': wg.find('p').contents[-1].strip(),
                }
                result.append(w)
        # print "词语辨析---------", result
        return result

    def getBaike(self):
        # 百科
        result = ''
        ebaike = self.root.find(id='eBaike')
        if ebaike:
            result = ebaike.find(id='bk').find(class_='content').find('p').get_text().strip()

        return result

    def getLoop(self, id):
        result = []
        info = self.root.find(id=id)
        if info:
            for wg in info.find_all(class_='wordGroup'):
                w = {
                    'title': wg.find('span').get_text().strip(),
                    'content': wg.contents[-1].strip(),
                }
                result.append(w)
        # print "getLoop---------", result
        return result

    def show(self):
        # 找不到结果
        if not self.result:
            return
        if self.result['noInfo'] != '':
            print ' %s \n' % self.result['noInfo']

        # 错误信息
        if self.result['errInput'] != '':
            print u'你是不是在找: %s \n' % self.result['errInput']

        self.printWord(self.result['baseInfo'])
        self.printList(self.result, 'webInfo', u'网络释义')
        self.printList(self.result, 'webPhrase', u'网络短语')
        self.printList(self.result, 'synonym', u'同近义词')
        self.printList(self.result, 'wordGroup', u'词组短语')
        self.printList(self.result, 'cognate', u'同根词')
        self.printList(self.result, 'discription', u'词语辨析')

        # 百科
        if self.result['baike']:
            self.printTitle(u'有道百科')
            print '%s\n' % self.result['baike']

    def printList(self, result, key, title):
        # print list
        if result[key]:
            self.printTitle(title)
            for wt in result[key]:
                con = ' %s ' % wt['title'] + ''.join([' ' for i in xrange(30-len(wt['title']))]) + '%s' % ( wt['content'])
                print con
            print ''

    def printTitle(self, title):
        # print title
        print '%s ' % title

    def printWord(self, word):
        # print word
        pw = ''
        if word['title']:
            pw += word['title'] + ' '
        if word['pronounce']:
            pw += word['pronounce'] + ' '
        print pw
        if word['content']:
            for wt in word['content']:
                print '%s ' % wt

            print ''

    def getBaseInfoByAPI(self):
        # 基本解释
        if "0" != self.api_response['errorCode']:
            return
        result = {'title': '', 'pronounce': '', 'content': []}
        result['title'] = self.api_response['query']
        result['pronounce'] = self.api_response['basic']['phonetic']
        result['content'] = self.api_response['basic']['explains']

        # print "getBaseInfo---------", result
        return result

    def showByAPI(self):
        if not self.api_result:
            return
        self.printWord(self.api_result['baseInfo'])

    def getVoice(self, word):
        voice_file = 'test.mp3'
        voice_url = 'http://dict.youdao.com/dictvoice?type=2&audio=%s' % word
        r = requests.get(voice_url)
        with open(voice_file, 'wb') as f:
            f.write(r.content)
            f.close()

        # play mp3
        pygame.init()
        track = pygame.mixer.music.load(voice_file)
        pygame.mixer.music.play()
        import time
        time.sleep(1)
        pygame.mixer.music.stop()


def main():

    shortargs = 'va'
    longargs = ['voice', 'api']
    opts, args = getopt.getopt(sys.argv[1:], shortargs, longargs)
    # print opts, args
    word = ' '.join(args)
    dictionary = Dictionary()

    api = False
    for o, a in opts:
        if o in ('-v', '--voice'):
            dictionary.getVoice(word)
        elif o in ('-a', '--api'):
            api = True

    dictionary.translate(word, api)
    if dictionary.api_result:
        dictionary.showByAPI()
    else:
        dictionary.show()


if __name__ == '__main__':
    main()
