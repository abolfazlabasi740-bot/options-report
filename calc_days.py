from datetime import datetime
import sys

# فرمت تاریخ سررسید: 1405/04/24
def jalali_to_gregorian(jy, jm, jd):
    jy = int(jy) - 979
    jm = int(jm) - 1
    jd = int(jd) - 1

    j_day_no = 365*jy + jy//33*8 + ((jy % 33)+3)//4
    for i in range(jm):
        j_day_no += [31,31,31,31,31,31,30,30,30,30,30,29][i]
    j_day_no += jd

    g_day_no = j_day_no + 79

    gy = 1600 + 400*(g_day_no//146097)
    g_day_no %= 146097

    leap = True
    if g_day_no >= 36525:
        g_day_no -= 1
        gy += 100*(g_day_no//36524)
        g_day_no %= 36524
        if g_day_no >= 365:
            g_day_no += 1
        else:
            leap = False

    gy += 4*(g_day_no//1461)
    g_day_no %= 1461

    if g_day_no >= 366:
        leap = False
        g_day_no -= 1
        gy += g_day_no//365
        g_day_no %= 365

    gd = g_day_no + 1
    months = [31,29 if leap else 28,31,30,31,30,31,31,30,31,30,31]
    gm = 0
    while gm < 12 and gd > months[gm]:
        gd -= months[gm]
        gm += 1
    return gy, gm+1, gd

def days_left(jdate):
    jy, jm, jd = jdate.split('/')
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    target = datetime(gy, gm, gd)
    today = datetime.now()
    return (target.date() - today.date()).days

if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(d, days_left(d))
