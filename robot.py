# -*- coding: utf-8 -*-

import re
import sys
import json
import random
import urllib
import urllib2
import itchat

reload(sys)
sys.setdefaultencoding("utf-8")


@itchat.msg_register(itchat.content.TEXT, isGroupChat=True)
def text_reply(msg):
    if msg.isAt:
        print msg
        handle_msg(msg)


def handle_msg(msg):
    roll_re = re.compile(ur"roll$")
    help_re = re.compile(ur"帮助")
    score_all_re = re.compile(ur"(全部|所有人)战绩")
    score_one_re = re.compile(ur"战绩")
    group_re = re.compile(ur"分拨")
    record_re = re.compile(ur"记录胜(负|场)")

    scan_list = [
        [roll_re, handle_roll],
        [help_re, handle_help], [score_all_re, handle_score_all], [score_one_re, handle_score_one],
        [group_re, handle_group], [record_re, handle_record]
    ]

    chat_flag = True
    for item in scan_list:
        re_obj = item[0]
        result = re_obj.search(msg.text)
        if result:
            exe_fun = item[1]
            exe_fun(msg)
            chat_flag = False
            break

    if chat_flag:
        text = talks_robot(msg.text[5:].strip())
        msg.user.send(u'@%s\u2005 %s' % (msg.actualNickName, text))


def handle_help(msg):
    text = u"cdec机器人，预期功能：查询战绩，比赛分拨，记录结果，查询个人战绩，roll等"
    normal_send(msg, text)


def handle_roll(msg):
    text = u"%d" % random.randint(0, 100)
    normal_send(msg, text)


def handle_score_all(msg):
    try:
        players = request_score()
        counter = 0
        text = ""
        for player in players:
            counter += 1
            name = player["name"]
            score = player["score"]
            rate = str(player["win"]) + u"胜/" + str(player["times"]) + u"场"
            text += "%d\t%s\t%d\t%s\n" % (counter, name, score, rate)
            if counter % 10 == 0:
                text = text[:-1]
                msg.user.send(u'@%s\u2005\n%s' % (msg.actualNickName, text))
                text = ""
        if len(text) > 0:
            text = text[:-1]
            msg.user.send(u'@%s\u2005\n%s' % (msg.actualNickName, text))

    except:
        text = u"cdec机器人挂掉啦！"
        normal_send(msg, text)


def handle_score_one(msg):
    if len(msg.text) > 5:
        msg.text = msg.text[5:]
    try:
        players = request_score()
        counter = 0
        text = ""
        for player in players:
            counter += 1
            name = player["name"]
            score = player["score"]
            rate = str(player["win"]) + u"胜/" + str(player["times"]) + u"场"

            if re.search(name, msg.text):
                text += "%d\t%s\t%d\t%s\n" % (counter, name, score, rate)
        if len(text) > 0:
            text = text[:-1]
            msg.user.send(u'@%s\u2005\n%s' % (msg.actualNickName, text))
        else:
            text = u"没找到这个人"
            msg.user.send(u'@%s\u2005 %s' % (msg.actualNickName, text))
    except:
        text = u"cdec机器人挂掉啦！"
        normal_send(msg, text)


def handle_group(msg):
    if len(msg.text) > 5:
        msg.text = msg.text[5:]

    counter = 0
    ids = list()
    try:
        players = request_score()
        for player in players:
            name = player["name"]
            pid = player["id"]
            if re.search(name, msg.text) and counter < 10:
                counter += 1
                ids.append(pid)
            elif counter >= 10:
                break
        if counter == 10:
            data = request_group(ids)
            match_id = data["matchId"]
            players = data["radiant"] + data["dire"]
            balance = data["balance"]
            text = u"比赛id:%s\n" % match_id
            counter = 0
            ssum = 0
            for player in players:
                name = player["name"]
                score = player["score"]
                ssum += score
                counter += 1
                text += u"%s(%d), " % (name, score)
                if counter == 5:
                    text = text[:-2]
                    text += u"\n总分: %d" % ssum
                    text += u"\nVS\n"
                    ssum -= ssum
            text = text[:-2]
            text += u"\n总分: %d\n分差: %d" % (ssum, balance)
            msg.user.send(u'@%s\u2005 \n%s' % (msg.actualNickName, text))
        else:
            text = u"参赛人数过少"
            normal_send(msg, text)
    except:
        text = u"cdec机器人挂掉啦！"
        normal_send(msg, text)


def handle_record(msg):
    id_re = re.compile(ur"[a-zA-Z0-9]{32}")
    winner_re = re.compile(ur"([01])\s*胜")

    result = id_re.search(msg.text)
    if result:
        match_id = result.group(0)
        result = winner_re.search(msg.text)
        if result:
            winner = result.group(1)
            try:
                request_record(match_id, winner)
                text = u"记录比赛成功"
                normal_send(msg, text)
            except:
                text = u"记录比赛结果出问题啦"
                normal_send(msg, text)
        else:
            text = u"不知道谁赢了哦"
            normal_send(msg, text)
    else:
        text = u"没有找到比赛id哦"
        normal_send(msg, text)


def request_score():
    url = "http://rocxing.wang/cdec/api/score"
    data = json.loads(urllib2.urlopen(url).read(), encoding="utf-8")
    if data["status"] == 0:
        return data["data"]
    else:
        raise Exception()


def request_group(ids):
    url = "http://rocxing.wang/cdec/api/match/group"
    params = {"list": json.dumps(ids)}
    data = json.loads(post(url, params), encoding="utf-8")
    if data["status"] == 0:
        return data["data"]
    else:
        raise Exception()


def request_record(match_id, winner):
    url = "http://rocxing.wang/cdec/api/match/record"
    params = {"matchId": match_id, "winner": int(winner)}
    data = json.loads(post(url, params), encoding="utf-8")
    if data["status"] == 0:
        return data["data"]
    else:
        raise Exception()


def post(url, data):
    header = {"Content-Type": "application/x-www-form-urlencoded"}
    data = urllib.urlencode(data)
    req = urllib2.Request(url, headers=header, data=data)
    res = urllib2.urlopen(req)
    return res.read()


def normal_send(msg, text):
    msg.user.send(u'@%s\u2005 %s' % (msg.actualNickName, text))


def talks_robot(info):
    api_url = 'http://www.tuling123.com/openapi/api'
    apikey = "56acddfe14fb4f729e5b5a0367e7ec9c"
    data = {'key': apikey,
            'info': info}
    replys = json.loads(post(api_url, data))['text']
    return replys


itchat.auto_login()
itchat.run()
