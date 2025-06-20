import sys
sys.path.append(".")
from datetime import datetime

def timestamp2str(timestamp, week=False):
    dt_object = datetime.fromtimestamp(timestamp)
    result =  dt_object.strftime('%Y年%m月%d日%H时%M分')
    
    if week:
        week_cn = ""
        week_en = dt_object.strftime('%A')
        if week_en == "Monday":
            week_cn = "星期一"
        if week_en == "Tuesday":
            week_cn = "星期二"
        if week_en == "Wednesday":
            week_cn = "星期三"
        if week_en == "Thursday":
            week_cn = "星期四"
        if week_en == "Friday":
            week_cn = "星期五"
        if week_en == "Saturday":
            week_cn = "星期六"
        if week_en == "Sunday":
            week_cn = "星期日"

        result = result + " " + week_cn
    
    return result

def str2timestamp(time_str, format="%Y年%m月%d日%H时%M分"):
    try:
    # 尝试将字符串转换为datetime对象
        dt = datetime.strptime(time_str, format)
    except ValueError as e:
        return None
    except Exception as e:
        return None
    
    return int(dt.timestamp())

from datetime import datetime

def date2str(timestamp, week=False):
    dt_object = datetime.fromtimestamp(timestamp)
    result =  dt_object.strftime('%Y年%m月%d日')
    
    if week:
        week_cn = ""
        week_en = dt_object.strftime('%A')
        if week_en == "Monday":
            week_cn = "星期一"
        if week_en == "Tuesday":
            week_cn = "星期二"
        if week_en == "Wednesday":
            week_cn = "星期三"
        if week_en == "Thursday":
            week_cn = "星期四"
        if week_en == "Friday":
            week_cn = "星期五"
        if week_en == "Saturday":
            week_cn = "星期六"
        if week_en == "Sunday":
            week_cn = "星期日"

        result = result + " " + week_cn
    
    return result