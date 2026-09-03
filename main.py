# -*- coding: utf8 -*-
import datetime
import json
import math
import random
import re
import sys
import time

import requests

# 开启根据地区天气情况降低步数（默认关闭）
open_get_weather = sys.argv[3]
# 设置获取天气的地区（上面开启后必填）如：area = "宁波"
area = sys.argv[4]

# 以下如果看不懂直接默认就行只需改上面

# 系数K查询到天气后降低步数比率，如查询得到设置地区为多云天气就会在随机后的步数乘0.9作为最终修改提交的步数
K_dict = {"多云": 0.9, "阴": 0.8, "小雨": 0.7, "中雨": 0.5, "大雨": 0.4, "暴雨": 0.3, "大暴雨": 0.2, "特大暴雨": 0.2}

# 北京时间
time_bj = datetime.datetime.today() + datetime.timedelta(hours=8)
now = time_bj.strftime("%Y-%m-%d %H:%M:%S")
headers = {'User-Agent': 'MiFit/5.3.0 (iPhone; iOS 14.7.1; Scale/3.00)'}


# 获取区域天气情况
def getWeather():
    if area == "NO":
        print(area == "NO")
        return
    else:
        global K, type
        url = 'http://wthrcdn.etouch.cn/weather_mini?city=' + area
        hea = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url=url, headers=hea)
        if r.status_code == 200:
            result = r.text
            res = json.loads(result)
            if "多云" in res['data']['forecast'][0]['type']:
                K = K_dict["多云"]
            elif "阴" in res['data']['forecast'][0]['type']:
                K = K_dict["阴"]
            elif "小雨" in res['data']['forecast'][0]['type']:
                K = K_dict["小雨"]
            elif "中雨" in res['data']['forecast'][0]['type']:
                K = K_dict["中雨"]
            elif "大雨" in res['data']['forecast'][0]['type']:
                K = K_dict["大雨"]
            elif "暴雨" in res['data']['forecast'][0]['type']:
                K = K_dict["暴雨"]
            elif "大暴雨" in res['data']['forecast'][0]['type']:
                K = K_dict["大暴雨"]
            elif "特大暴雨" in res['data']['forecast'][0]['type']:
                K = K_dict["特大暴雨"]
            type = res['data']['forecast'][0]['type']
        else:
            print("获取天气情况出错")


# 获取北京时间确定随机步数&启动主函数
def getBeijinTime():
    global K, type
    K = 1.0
    type = ""
    hea = {'User-Agent': 'Mozilla/5.0'}
    url = r'https://apps.game.qq.com/CommArticle/app/reg/gdate.php'
    if open_get_weather == "True":
        getWeather()
    r = requests.get(url=url, headers=hea)
    if r.status_code == 200:
        result = r.text
        pattern = re.compile('\\d{4}-\\d{2}-\\d{2} (\\d{2}):\\d{2}:\\d{2}')
        find = re.search(pattern, result)
        hour = find.group(1)
        min_ratio = max(math.ceil((int(hour) / 3) - 1), 0)
        max_ratio = math.ceil(int(hour) / 3)
        min_1 = 3500 * min_ratio
        max_1 = 3500 * max_ratio
        min_1 = int(K * min_1)
        max_1 = int(K * max_1)
    else:
        print("获取北京时间失败")
        return
    if min_1 != 0 and max_1 != 0:
        user_mi = sys.argv[1]
        # 登录密码
        passwd_mi = sys.argv[2]
        user_list = user_mi.split('#')
        passwd_list = passwd_mi.split('#')
        if len(user_list) == len(passwd_list):
            if K != 1.0:
                msg_mi = "由于天气" + type + "，已设置降低步数,系数为" + str(K) + "。\n"
            else:
                msg_mi = ""
            for user_mi, passwd_mi in zip(user_list, passwd_list):
                msg_mi += main(user_mi, passwd_mi, min_1, max_1)
                # print(msg_mi)
    else:
        print("当前主人设置了0步数呢，本次不提交")
        return


# 获取登录code
def get_code(location):
    code_pattern = re.compile("(?<=access=).*?(?=&)")
    code = code_pattern.findall(location)[0]
    return code


# 登录
def login(user, password):
    is_phone = False
    if re.match(r'^\d{11}$', user):
        is_phone = True

    if is_phone:
        url1 = "https://api-user.huami.com/registrations/+86" + user + "/tokens"
    else:
        url1 = "https://api-user.huami.com/registrations/" + user + "/tokens"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2"
    }
    data1 = {
        "client_id": "HuaMi",
        "password": f"{password}",
        "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
        "token": "access"
    }

    # 发起第一次 POST（不自动跟随重定向），但做网络异常保护与超时
    try:
        r1 = requests.post(url1, data=data1, headers=headers, allow_redirects=False, timeout=10)
    except requests.RequestException as e:
        print(f"Network error during login POST: {e}")
        return 0, 0

    # 如果服务端返回重定向且包含 Location，安全获取；否则打印调试信息并返回失败
    location = r1.headers.get("Location")
    if not location:
        print("登录第一步未返回 Location（可能是密码或账号错误或接口变更）")
        print(f"Status code: {r1.status_code}")
        try:
            print(f"Headers: {dict(r1.headers)}")
            print(f"Body (truncated): {r1.text[:2000]}")
        except Exception:
            pass
        return 0, 0

    # 提取 access code
    try:
        code = get_code(location)
    except Exception as e:
        print(f"从 Location 提取 code 失败: {e}")
        return 0, 0

    url2 = "https://account.huami.com/v2/client/login"
    if is_phone:
        data2 = {
            "app_name": "com.xiaomi.hm.health",
            "app_version": "4.6.0",
            "code": f"{code}",
            "country_code": "CN",
            "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
            "device_model": "phone",
            "grant_type": "access_token",
            "third_name": "huami_phone",
        }
    else:
        data2 = {
            "allow_registration": "false",
            "app_name": "com.xiaomi.hm.health",
            "app_version": "6.3.5",
            "code": f"{code}",
            "country_code": "CN",
            "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
            "device_model": "phone",
            "dn": "api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com",
            "grant_type": "access_token",
            "lang": "zh_CN",
            "os_version": "1.5.0",
            "source": "com.xiaomi.hm.health",
            "third_name": "email",
        }

    # 执行第二次 POST 并保护解析
    try:
        r2 = requests.post(url2, data=data2, headers=headers, timeout=10)
    except requests.RequestException as e:
        print(f"Network error during second login POST: {e}")
        return 0, 0

    try:
        r2_json = r2.json()
    except Exception:
        print("第二步登录返回非 JSON，内容（truncated）:", r2.text[:2000])
        return 0, 0

    # 检查返回结构是否包含必要字段
    token_info = r2_json.get("token_info")
    if not token_info:
        print("登录返回未包含 token_info，返回体：", r2_json)
        return 0, 0

    login_token = token_info.get("login_token")
    userid = token_info.get("user_id")
    if not login_token or not userid:
        print("登录返回缺失 login_token 或 user_id，返回 token_info：", token_info)
        return 0, 0

    return login_token, userid


# 主函数
def main(_user, _passwd, min_1, max_1):
    user = str(_user)
    password = str(_passwd)
    step = str(random.randint(min_1, max_1))
    print("已设置为随机步数(" + str(min_1) + "~" + str(max_1) + ")")
    if user == '' or password == '':
        print("用户名或密码填写有误！")
        return
    login_token, userid = login(user, password)
    if login_token == 0:
        print("登陆失败！")
        return "login fail!"

    t = get_time()

    app_token = get_app_token(login_token)

    today = time.strftime("%F")

    data_json = '%5B%7B%22data_hr%22%3A%22%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F9L%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2FVv%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2F%5C%2[...]

    finddate = re.compile(r".*?date%22%3A%22(.*?)%22%2C%22data.*?")
    findstep = re.compile(r".*?ttl%5C%22%3A(.*?)%2C%5C%22dis.*?")
    data_json = re.sub(finddate.findall(data_json)[0], today, str(data_json))
    data_json = re.sub(findstep.findall(data_json)[0], step, str(data_json))

    url = f'https://api-mifit-cn.huami.com/v1/data/band_data.json?&t={t}'
    head = {
        "apptoken": app_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = f'userid={userid}&last_sync_data_time=1597306380&device_type=0&last_deviceid=DA932FFFFE8816E7&data_json={data_json}'

    response = requests.post(url, data=data, headers=head).json()
    # print(response)
    result = f"[{now}]\n账号：{user[:3]}****{user[7:]}\n修改步数（{step}）[" + response['message'] + "]\n"
    print(result)
    return result


# 获取时间戳
def get_time():
    url = 'http://worldtimeapi.org/api/timezone/Asia/Shanghai'
    response = requests.get(url, headers=headers).json()
    t = str(response['unixtime'])+'000'
    return t


# 获取app_token
def get_app_token(login_token):
    url = f"https://account-cn.huami.com/v1/client/app_tokens?app_name=com.xiaomi.hm.health&dn=api-user.huami.com%2Capi-mifit.huami.com%2Capp-analytics.huami.com&login_token={login_token}"
    response = requests.get(url, headers=headers).json()
    app_token = response['token_info']['app_token']
    # print("app_token获取成功！")
    # print(app_token)
    return app_token


if __name__ == "__main__":
    getBeijinTime()
