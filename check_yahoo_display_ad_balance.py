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
def getAccessToken():
    try:
        url_token = f'https://biz-oauth.yahoo.co.jp/oauth/v1/token?grant_type=refresh_token' \
                f'&client_id={os.environ["YAHOO_CLIENT_ID"]}' \
                f'&client_secret={os.environ["YAHOO_CLIENT_SECRET"]}' \
                f'&refresh_token={os.environ["YAHOO_REFRESH_TOKEN"]}'
        req = requests.get(url_token)
        body = json.loads(req.text)
        access_token = body['access_token']
        return access_token
    except Exception as err:
        logger.error(f'Error: getAccessToken: {err}')
        exit(1)

def getAvailableBalance(account_id):
    try:
        url_api = 'https://ads-display.yahooapis.jp/api/v8/BalanceService/getAvailableBalance'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {getAccessToken()}'
        }
        params = {
          "accountId": account_id
        }
        req = requests.post(url_api, json.dumps(params), headers=headers)
        body = json.loads(req.text)
        logger.info(f'uploadCsvFile - status_code: {req.status_code}')
        logger.info(f'uploadCsvFile - response:\n--> {req.text}')

        if req.status_code != 200:
            message = "[info][title]【Yahoo!広告】アカウント残高通知[/title]\n"
            message += 'アカウント残高の取得に失敗しました。\n'
            message += '担当者は実行ログの確認を行ってください。\n\n'
            message += f'アカウントID：{account_id}\n\n'
            message += f'ステータスコード：{req.status_code}\n\n'
            sendChatworkNotification(message)
            exit(0)

        if body['errors'] != None:
            errors = body['errors'][0]
            message = "[info][title]【Yahoo!広告】アカウント残高通知[/title]\n"
            message += 'アカウント残高の取得に失敗しました。\n'
            message += '担当者は実行ログの確認を行ってください。\n\n'
            message += f'アカウントID：{account_id}\n\n'
            message += f'ステータスコード：{req.status_code}\n'
            message += f'エラーコード：{errors["code"]}\n'
            message += f'エラーメッセージ：{errors["message"]}\n'
            message += f'エラー詳細：{errors["details"]}\n\n'
            sendChatworkNotification(message)
            exit(0)

        return body['rval']['values'][0]['availableBalance']['availableBalance']
    except Exception as e:
            logger.debug(f'Error: getAvailableBalance: {e}')
            exit(1)

def sendChatworkNotification(message):
    try:
        url = f'https://api.chatwork.com/v2/rooms/{os.environ["CHATWORK_ROOM_ID_BALANCE"]}/messages'
        headers = { 'X-ChatWorkToken': os.environ["CHATWORK_API_TOKEN"] }
        params = { 'body': message }
        requests.post(url, headers=headers, params=params)
    except Exception as err:
        logger.error(f'Error: sendChatworkNotification: {err}')
        exit(1)

### main_script ###
if __name__ == '__main__':

    try:
        data = [
            {'account_id': 1002584978, 'account_name': 'ブレスマイルウォッシュ'},
            {'account_id': 1002532490, 'account_name': 'マンション貸す.com（専用LP）'},
            {'account_id': 1002492185, 'account_name': '育毛剤選び研究室'}
        ]
        for d in data:
            d['balance'] = getAvailableBalance(d['account_id'])
            sleep(1)
        output = []
        for d in data:
            if int(d['balance']) <= 30000:
                output.append(d)

        if len(data) == 0:
            message = "[info][title]【Yahoo!ディスプレイ広告】アカウント残高通知[/title]"
            message += "アラート対象のアカウントはございません。\n"
            message += '[/info]'
        else:
            message = "[info][title]【Yahoo!ディスプレイ広告】アカウント残高通知[/title]"
            message += f"残高が少なくなってきているアカウントが【{len(data)}件】あります。\n"
            message += "ご担当者の方は下記アカウントの残高をご確認ください。\n"
            for item in data:
                message += '\n＋＋＋\n\n'
                message += f'アカウントID：{item['account_id']}\n'
                message += f'アカウント名：{item['account_name']}\n'
                message += f'アカウント残高：{item['balance']}\n'
                #message += f'予想残日数：{item[3]}\n'
                #message += f'平均コスト（日）：{item[4]}\n'
            message += '[/info]'

        sendChatworkNotification(message)
        os.remove(f'log/{today.strftime("%Y-%m-%d")}_result.log')
        logger.info("check_yahoo_ad_balance: Finish")
        exit(0)
    except Exception as err:
        logger.debug(f'check_yahoo_ad_balance: {err}')
        exit(1)
