import os
import json
import datetime
import requests
from time import sleep

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


def send_chatwork_notification(message):
    try:
        url = f'https://api.chatwork.com/v2/rooms/{os.environ["CHATWORK_ROOM_ID_BALANCE"]}/messages'
        headers = { 'X-ChatWorkToken': os.environ["CHATWORK_API_TOKEN"] }
        params = { 'body': message }
        requests.post(url, headers=headers, params=params)
    except Exception as err:
        logger.error(f'Error: send_chatwork_notification: {err}')
        exit(1)


def get_access_token():
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
        message = "[toall]\nYahoo!APIのアクセストークンの取得に失敗しました。\n"
        send_chatwork_notification(message)
        exit(1)


def get_available_balance(access_token, account_id, account_name):
    url_api = 'https://ads-display.yahooapis.jp/api/v10/BalanceService/getAvailableBalance'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    params = {
      "accountId": account_id
    }
    try:
        req = requests.post(url_api, json.dumps(params), headers=headers)
        body = json.loads(req.text)
        status_code = req.status_code
    except Exception as e:
        message = "[toall]\n"
        message += "APIの実行に失敗しました。\n"
        message += "システム担当者は実行ログの確認を行ってください。\n"
        message += f'アカウントID：{account_id}\n\n'
        message += f'アカウント名：{account_name}\n\n'
        sendChatworkNotification(message)

    if status_code != 200:
        message = "[toall]\n"
        message += "[info][title]【Yahoo!広告】アカウント残高通知[/title]\n"
        message += 'アカウント残高の取得に失敗しました。\n'
        message += 'システム担当者は実行ログの確認を行ってください。\n\n'
        message += f'アカウントID：{account_id}\n\n'
        message += f'アカウント名：{account_name}\n\n'
        message += f'ステータスコード：{status_code}\n\n'
        sendChatworkNotification(message)
    elif body['errors'] != None:
        errors = body['errors'][0]
        message = "[toall]\n"
        message += "[info][title]【Yahoo!広告】アカウント残高通知[/title]\n"
        message += 'アカウント残高の取得に失敗しました。\n'
        message += 'システム担当者は実行ログの確認を行ってください。\n\n'
        message += f'アカウントID：{account_id}\n\n'
        message += f'アカウント名：{account_name}\n\n'
        message += f'ステータスコード：{status_code}\n'
        message += f'エラーコード：{errors["code"]}\n'
        message += f'エラーメッセージ：{errors["message"]}\n'
        message += f'エラー詳細：{errors["details"]}\n\n'
        sendChatworkNotification(message)
    else:
        return body['rval']['values'][0]['availableBalance']['availableBalance']
    return None

class BasicInfo():
    def __init__(self, access_token, account_id, account_name):
        self.access_token = access_token
        self.id = account_id
        self.name = account_name
        self.balance = get_available_balance(self.access_token, self.id, self.name)
        sleep(1)


### main_script ###
if __name__ == '__main__':
    access_token = get_access_token()
    accounts = [
        BasicInfo(access_token, 1002584978, 'ブレスマイルウォッシュ'),
        BasicInfo(access_token, 1002532490, 'マンション貸す.com（専用LP）'),
        BasicInfo(access_token, 1002492185, '育毛剤選び研究室')
    ]
    output = [account for account in accounts if not account.balance == None and int(account.balance) <= 30000]

    if len(output) == 0:
        message = "[info][title]【Yahoo!ディスプレイ広告】アカウント残高通知[/title]"
        message += "アラート対象のアカウントはございません。\n"
        message += '[/info]'
    else:
        message = "[toall]\n"
        message += "[info][title]【Yahoo!ディスプレイ広告】アカウント残高通知[/title]"
        message += f"残高が少なくなってきているアカウントが【{len(output)}件】あります。\n"
        message += "ご担当者の方は下記アカウントの残高をご確認ください。\n"
        for item in output:
            message += '\n＋＋＋\n\n'
            message += f"アカウントID：{item.id}\n"
            message += f"アカウント名：{item.name}\n"
            message += f"アカウント残高：{'{:,}'.format(item.balance)}\n"
        message += '[/info]'

    send_chatwork_notification(message)
    logger.info("check_yahoo_display_ad_balance: Finish")
    os.remove(f'log/{today.strftime("%Y-%m-%d")}_result.log')