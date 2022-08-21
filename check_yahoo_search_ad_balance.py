import os
import re
import csv
import sys
import json
import shutil
import datetime
import requests
import gspread
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager
from oauth2client.service_account import ServiceAccountCredentials

# Logger setting
from logging import getLogger, FileHandler, DEBUG
logger = getLogger(__name__)
today = datetime.datetime.now()
os.makedirs('./log', exist_ok=True)
handler = FileHandler(f'log/{today.strftime("%Y-%m-%d")}_result.log', mode='a')
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

### functions ###
def importCsvFromYahoo(downloadsDirPath):
    url = "https://business.yahoo.co.jp/"
    login = os.environ['YAHOO_BUSINESS_ID']
    password = os.environ['YAHOO_BUSINESS_PASS']

    ua = UserAgent()
    logger.debug(f'importCsvFromYahoo: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')

    prefs = {
        "profile.default_content_settings.popups": 1,
        "download.default_directory": 
                os.path.abspath(downloadsDirPath),
        "directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        driver.get(url)
        driver.maximize_window()
        driver.implicitly_wait(30)

        driver.find_element_by_class_name('loginBt').click()
        driver.find_element_by_id('user_name').send_keys(login)
        driver.find_element_by_id('password').send_keys(password)
        driver.find_element_by_xpath('//input[@value="ログイン"]').click()

        logger.debug('importCsvFromYahoo: Yahoo login')
        sleep(10)
        driver.get("https://ads.yahoo.co.jp/manager/#/search/list/accounts")
        driver.implicitly_wait(60)
        driver.find_element_by_xpath('//button[@class="css-1cqs7fo"]').click()
        driver.implicitly_wait(60)
        driver.find_element_by_class_name('css-enbjm8').click()
        sleep(10)
        
        driver.close()
        driver.quit()
    except Exception as err:
        driver.close()
        driver.quit()
        logger.debug(f'Error: importCsvFromYahoo: {err}')
        sleep(10)
        importCsvFromYahoo(downloadsDirPath)

def getLatestDownloadedFileName(downloadsDirPath):
    if len(os.listdir(downloadsDirPath)) == 0:
        return None
    return max (
        [downloadsDirPath + '/' + f for f in os.listdir(downloadsDirPath)],
        key=os.path.getctime
    )

def sendChatworkNotification(message):
    try:
        url = f'https://api.chatwork.com/v2/rooms/{os.environ["CHATWORK_ROOM_ID_BALANCE"]}/messages'
        headers = { 'X-ChatWorkToken': os.environ["CHATWORK_API_TOKEN"] }
        params = { 'body': message }
        requests.post(url, headers=headers, params=params)
    except Exception as err:
        logger.error(f'Error: sendChatworkNotification: {err}')
        exit(1)

### Yahoo! ###
def readCsvData(csvPath):
    with open(csvPath, newline='', encoding='utf-8') as csvfile:
        buf = csv.reader(csvfile, delimiter=',', lineterminator='\r\n', skipinitialspace=True)
        for row in buf:
            yield row

def getBalanceData(data):
        header = data.pop(0)
        for i, d in enumerate(header):
            if re.search('配信', d):
                bc = int(i)
            elif re.search('アカウント名', d):
                name = int(i)
            elif re.search('アカウント残高', d):
                balance = int(i)
            elif re.search('予想残日数', d):
                dl = int(i)
            elif re.search('平均コスト', d):
                cost = int(i)
            elif re.search('アカウントID', d):
                account_id = int(i)

        for row in data:
            if row[bc] == "オフ":
                continue
            elif row[cost] == "0":
                continue
            elif int(row[dl]) > 2:
                continue
            yield [row[account_id], row[name], row[balance], row[dl], row[cost]]

def getCsvPath(dirPath):
    os.makedirs(dirPath, exist_ok=True)
    importCsvFromYahoo(dirPath)

    csvPath = getLatestDownloadedFileName(dirPath)
    logger.info(f"check_yahoo_ad_balance: download completed: {csvPath}")

    return csvPath

### main_script ###
if __name__ == '__main__':

    try:
        csvPath = getCsvPath('./csv/')

        data = list(readCsvData(csvPath))
        data = list(getBalanceData(data))

        if len(data) == 0:
            message = "[info][title]【Yahoo!検索広告】アカウント残高通知[/title]"
            message += "予想残日数が迫っているアカウントはございません。\n"
            message += '[/info]'
        else:
            message = "[info][title]【Yahoo!検索広告】アカウント残高通知[/title]"
            message += f"予想残日数が迫っているアカウントが【{len(data)}件】あります。\n"
            message += "ご担当者の方は下記アカウントの残高をご確認ください。\n"
            for item in data:
                message += '\n＋＋＋\n\n'
                message += f'アカウントID：{item[0]}\n'
                message += f'アカウント名：{item[1]}\n'
                message += f'アカウント残高：{item[2]}\n'
                message += f'予想残日数：{item[3]}\n'
                message += f'平均コスト（日）：{item[4]}\n'
            message += '[/info]'

        sendChatworkNotification(message)
        logger.info("check_yahoo_ad_balance: Finish")
        os.remove(csvPath)
        os.remove(f'log/{today.strftime("%Y-%m-%d")}_result.log')
        exit(0)
    except Exception as err:
        logger.debug(f'check_yahoo_ad_balance: {err}')
        exit(1)
