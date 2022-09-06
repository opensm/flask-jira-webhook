from flask import Flask, request, datetime, requests
from copy import deepcopy
import json

app = Flask(__name__)


@app.route('/jira_webhook', methods=["POST"])
def send_message():
    set_config = request.get_data()
    if set_config is None or set_config == "":
        return print(403, "Parameter set_config can not be empty.")
    set_config = json.loads(set_config)
    print(set_config)
    return 'Hello World!'


def body_select(body, fields):
    m_issue = body.get("issue")
    m_fields = m_issue.get("fields")
    m_key = m_issue.get("key")

    base_field = {
        '概要': m_fields.get("summary"),
        '创建人': m_fields.get("creator", {}).get("displayName", '无'),
        '报告人': m_fields.get("reporter", {}).get("displayName", '无'),
        '经办人': m_fields.get("assignee", {}).get("displayName", '无'),
        '状态': m_fields.get("status", {}).get("name", '无'),
        '创建日期': m_fields.get("created"),
        '更新日期': m_fields.get("updated")[0:-9],
        'jira链接': m_fields.get("issuetype").get("self").split("rest")[0] + "browse/" + m_key,
        '更新开始时间': m_fields.get("customfield_11415", '无'),
        '进度详情': m_fields.get("comment", {}).get("comments", [{}])[-1].get("body", '无') if m_fields.get("comment",
                                                                                                       {}).get(
            "comments", [{}]) else '无',
        'issue': m_key + "-" + m_fields.get("project", {}).get("name"),
        '计划完成时间': m_fields.get("customfield_11426", '无')[0:-9] if m_fields.get("customfield_11426", '') else '无',
        '优先级': m_fields.get('priority', {}).get('name', '无'),
        '到期日': m_fields.get('duedate', '无') + 'T23:59:00' if m_fields.get('duedate', '无') else '无',
        '问题类型': m_fields.get('issuetype', {}).get('name', '无'),
    }

    if base_field.get('经办人') == '无':
        return 0
    text = ''
    to_aite = base_field.get('经办人')
    for i in fields:
        if i == '更新经办人':
            i_values = base_field.get('创建人')
            to_aite = i_values
            m_changlog = body.get("changelog")
            if m_changlog:
                for j in m_changlog.get("items"):
                    if j.get("field") == "当前经办人":
                        i_values = j.get("toString")
                        to_aite = i_values

        elif i == '剩余时间':
            if '计划完成时间' in fields and base_field.get('计划完成时间') != "无":
                aa = datetime.strptime(base_field.get('计划完成时间'), "%Y-%m-%dT%H:%M:%S")
                bb = datetime.strptime(base_field.get('更新日期'), "%Y-%m-%dT%H:%M:%S")
                if (aa - bb).days < 0:
                    i_values = "已逾期"
                else:
                    i_values = "%s天%s小时" % (
                        str((aa - bb).days),
                        str(round((aa - bb).seconds / 60 / 60, 2)),
                    )
            elif '到期日' in fields and base_field.get('到期日') != "无":
                aa = datetime.strptime(base_field.get('到期日'), "%Y-%m-%dT%H:%M:%S")
                bb = datetime.strptime(base_field.get('更新日期'), "%Y-%m-%dT%H:%M:%S")
                if (aa - bb).days < 0:
                    i_values = "已逾期"
                else:
                    i_values = "%s天%s小时" % (
                        str((aa - bb).days),
                        str(round((aa - bb).seconds / 60 / 60, 2)),
                    )
            else:
                i_values = "无"
        elif i == 'sprint':
            try:
                i_values = m_fields.get('customfield_10100', ['name=无'])[0].split('name=')[-1].split(',')[0]
            except:
                i_values = '无'
        elif i == '当前经办人':
            if "customfield_11310" in m_fields.keys():
                if not m_fields['customfield_11310']:
                    i_values = '无'
                    continue
                if not len(m_fields['customfield_11310']):
                    print('key customfield_11310 exist value not exist!')
                    i_values = "无"
                    continue
                print(m_fields['customfield_11310'])
                display_name = [user['displayName'] for user in m_fields['customfield_11310']]
                a_user_list = deepcopy(display_name)
                a_user_list.append(to_aite)
                to_aite = ','.join(a_user_list)
                i_values = ','.join(display_name)
        elif i == "操作开始时间":
            print("操作开始时间:{}".format(m_fields.get('customfield_12308', None)))
            i_values = m_fields.get('customfield_12308', None)
        elif i == "更新开始时间":
            print("更新开始时间:{}".format(m_fields.get('customfield_11415', None)))
            i_values = m_fields.get('customfield_11415', None)
        else:
            i_values = base_field.get(i, '无')

        text = text + i + ' : ' + i_values + '\n'

    aite = get_userid(to_aite, 111, 222)

    print("-----------------人员原为----------------")
    print(to_aite)
    print("-----------------当前消息内容为----------------")
    print(text)
    print("-----------------当前消息接受人为----------------")
    print(aite)
    print("-----------------信息汇总成功----------------")
    return text, aite


def messages_v2(r):
    if r.method == "POST":

        token = r.GET.get("wx_token")

        fields = r.GET.get("fields").split(',')
        # print(fields)
        if not token or not fields:
            return "err token or err fields"
        # print(token)
        # print(fields)
        try:
            body = json.loads(r.body)
        except:
            return "err body"

        res_tup = body_select(body, fields)
        if res_tup:
            wechatwork2(res_tup[0], token, res_tup[1])
        return "post ok"

    return "get ok"


# 普通通知
def messages(r):
    if r.method == "POST":

        token = r.GET.get("wx_token")
        if not token:
            return "err token"
        print(token)
        try:
            body = json.loads(r.body)
        except:
            return "err body"

        # body 信息过滤
        m_issue = body.get("issue")
        m_fields = m_issue.get("fields")
        m_key = m_issue.get("key")
        m_summary = m_fields.get("summary")
        try:
            m_project = m_fields.get("project").get("name")
        except:
            m_project = "not find"
        try:
            m_creator = m_fields.get("creator").get("displayName")
        except:
            m_creator = "not find"
        try:
            m_reporter = m_fields.get("reporter").get("displayName")
        except:
            m_reporter = "not find"
        try:
            m_assignee = m_fields.get("assignee").get("displayName")
        except:
            m_assignee = "not find"
            print("无经办人")
        m_url1 = m_fields.get("issuetype").get("self").split("rest")[0]
        m_url = m_url1 + "browse/" + m_key
        try:
            m_status = m_fields.get("status").get("name")
        except:
            m_status = "not find"
        m_i = m_key + "-" + m_project
        m_created = m_fields.get("created")
        m_updated = m_fields.get("updated")
        # 获取@的userid
        aite = get_userid(m_assignee, 11, 22)

        total_mess = """
summary：%s
issue：%s
issue_url：%s
创建人：%s
报告人：%s
经办人：%s
状态：%s 
创建日期：%s
更新日期：%s
        """ % (
            m_summary,
            m_i,
            m_url,
            m_creator,
            m_reporter,
            m_assignee,
            m_status,
            m_created,
            m_updated,
        )

        print(total_mess)
        if m_assignee != "not find":
            wechatwork2(total_mess, token, aite)
        return "post ok"

    return "get ok"


def update_messages(r):
    if r.method == "POST":

        token = r.GET.get("wx_token")

        if not token:
            return "err parameter "
        print(token)

        try:
            body = json.loads(r.body)
        except:
            return "err body"
        # print(body)

        # body 信息过滤
        m_issue = body.get("issue")
        m_changlog = body.get("changelog")
        m_fields = m_issue.get("fields")
        m_key = m_issue.get("key")
        c_update_time = m_fields.get("customfield_11415")
        if not c_update_time:
            c_update_time = "not find"
        print(c_update_time)
        m_summary = m_fields.get("summary")
        try:
            m_project = m_fields.get("project").get("name")
        except:
            m_project = "not find"
        try:
            m_creator = m_fields.get("creator").get("displayName")
        except:
            m_creator = "not find"
        try:
            m_reporter = m_fields.get("reporter").get("displayName")
        except:
            m_reporter = "not find"
        try:
            m_assignee = m_fields.get("assignee").get("displayName")
        except:
            m_assignee = "not find"
            print("无经办人")
        m_url1 = m_fields.get("issuetype").get("self").split("rest")[0]
        m_url = m_url1 + "browse/" + m_key
        try:
            m_status = m_fields.get("status").get("name")
        except:
            m_status = "not find"
        m_i = m_key + "-" + m_project
        m_created = m_fields.get("created")
        m_updated = m_fields.get("updated")
        m_muti_assignee = m_creator
        if m_changlog:
            for i in m_changlog.get("items"):
                if i.get("field") == "当前经办人":
                    m_muti_assignee = i.get("toString")
        # 获取@的userid
        aite = get_userid(m_muti_assignee, 11, 22)

        total_mess = """
summary：%s
issue：%s
issue_url：%s
更新开始时间：%s
创建人：%s
报告人：%s
经办人：%s
状态：%s 
创建日期：%s
更新日期：%s
        """ % (
            m_summary,
            m_i,
            m_url,
            c_update_time,
            m_creator,
            m_reporter,
            m_muti_assignee,
            m_status,
            m_created,
            m_updated,
        )

        print(total_mess)
        if m_assignee != "not find":
            wechatwork2(total_mess, token, aite)
        return "post ok"

    return "get ok"


# 任务变更通知
def job_messages(r):
    if r.method == "POST":

        token = r.GET.get("wx_token")
        # 1project= r.GET.get('project')
        if not token:
            return "err parameter "
        print(token)

        try:
            body = json.loads(r.body)
        except:
            return "err body"
        print('+++++++++++++++')
        print(body)

        # body 信息过滤
        m_issue = body.get("issue")
        m_fields = m_issue.get("fields")
        m_key = m_issue.get("key")
        m_summary = m_fields.get("summary")
        try:
            m_project = m_fields.get("project").get("name")
        except:
            m_project = "not find"
        try:
            m_creator = m_fields.get("creator").get("displayName")
        except:
            m_creator = "not find"
        try:
            m_reporter = m_fields.get("reporter").get("displayName")
        except:
            m_reporter = "not find"
        try:
            m_assignee = m_fields.get("assignee").get("displayName")
        except:
            m_assignee = "not find"
            print("无经办人")
        m_url1 = m_fields.get("issuetype").get("self").split("rest")[0]
        m_url = m_url1 + "browse/" + m_key
        try:
            m_status = m_fields.get("status").get("name")
        except:
            m_status = "not find"
        try:
            m_deadline = m_fields.get("customfield_11426")
            m_deadline = m_deadline[0:-8] + m_deadline[-5:]
        except:
            m_deadline = "无"
        try:
            print(m_fields.get("comment"))
            m_descripe = m_fields.get("comment").get("comments")[-1].get("body")
        except:
            m_descripe = "无"
        m_i = m_key + "-" + m_project
        m_created = m_fields.get("created")
        m_updated = m_fields.get("updated")
        m_updated = m_updated[0:-8] + m_updated[-5:]
        if m_assignee != "not find":
            if m_deadline != "无":
                aa = datetime.strptime(m_deadline, "%Y-%m-%dT%H:%M:%S.%z")
                bb = datetime.strptime(m_updated, "%Y-%m-%dT%H:%M:%S.%z")
                m_deadline_str = aa.strftime("%Y-%m-%d %H:%M:%S")
                m_updated_str = bb.strftime("%Y-%m-%d %H:%M:%S")
                if (aa - bb).days < 0:
                    delta_time = "已逾期"
                else:
                    delta_time = "%s天%s小时" % (
                        str((aa - bb).days),
                        str(round((aa - bb).seconds / 60 / 60, 2)),
                    )
                print(delta_time)
            else:
                bb = datetime.strptime(m_updated, "%Y-%m-%dT%H:%M:%S.%z")
                delta_time = "无"
                m_deadline_str = "无"
                m_updated_str = bb.strftime("%Y-%m-%d %H:%M:%S")
            # 获取@的userid
            aite = get_userid(m_assignee, 11, 22)

            total_mess = """
概要：%s
报 告人：%s
计划完成时间：%s
经办人：%s
状态：%s
更新日期：%s   
剩余时间：%s
jira链接：%s
进度详情：%s
            """ % (
                m_summary,
                m_reporter,
                m_deadline_str,
                m_assignee,
                m_status,
                m_updated_str,
                delta_time,
                m_url,
                m_descripe,
            )
            print(total_mess)
            wechatwork2(total_mess, token, aite)
        return "post ok"
    return "get  ok"


# 任务变更通知
def p02_job_messages(r):
    if r.method == "POST":

        token = r.GET.get("wx_token")
        # 1project= r.GET.get('project')
        if not token:
            return "err parameter "
        print(token)

        try:
            body = json.loads(r.body)
        except:
            return "err body"
        print('+++++++++++++++')
        print(body)

        # body 信息过滤
        m_issue = body.get("issue")
        m_fields = m_issue.get("fields")
        m_key = m_issue.get("key")
        m_summary = m_fields.get("summary")
        try:
            m_project = m_fields.get("project").get("name")
        except:
            m_project = "not find"
        try:
            m_creator = m_fields.get("creator").get("displayName")
        except:
            m_creator = "not find"
        try:
            m_reporter = m_fields.get("reporter").get("displayName")
        except:
            m_reporter = "not find"
        try:
            m_assignee = m_fields.get("assignee").get("displayName")
        except:
            m_assignee = "not find"
            print("无经办人")
        m_url1 = m_fields.get("issuetype").get("self").split("rest")[0]
        m_url = m_url1 + "browse/" + m_key
        try:
            m_status = m_fields.get("status").get("name")
        except:
            m_status = "not find"
        try:
            m_deadline = m_fields.get("customfield_11426")
            m_deadline = m_deadline[0:-8] + m_deadline[-5:]
        except:
            m_deadline = "无"
        try:
            print(m_fields.get("comment"))
            m_descripe = m_fields.get("comment").get("comments")[-1].get("body")
        except:
            m_descripe = "无"
        try:
            m_priority = m_fields.get('customfield_11601').get('value')
        except:
            m_priority = "无"
        try:
            m_sprint = m_fields.get('customfield_10100')[0].split('name=')[-1].split(',')[0]
        except:
            m_sprint = "无"
        m_i = m_key + "-" + m_project
        m_created = m_fields.get("created")
        m_updated = m_fields.get("updated")
        m_updated = m_updated[0:-8] + m_updated[-5:]
        if m_assignee != "not find":
            if m_deadline != "无":
                aa = datetime.strptime(m_deadline, "%Y-%m-%dT%H:%M:%S.%z")
                bb = datetime.strptime(m_updated, "%Y-%m-%dT%H:%M:%S.%z")
                m_deadline_str = aa.strftime("%Y-%m-%d %H:%M:%S")
                m_updated_str = bb.strftime("%Y-%m-%d %H:%M:%S")
                if (aa - bb).days < 0:
                    delta_time = "已逾期"
                else:
                    delta_time = "%s天%s小时" % (
                        str((aa - bb).days),
                        str(round((aa - bb).seconds / 60 / 60, 2)),
                    )
                print(delta_time)
            else:
                bb = datetime.strptime(m_updated, "%Y-%m-%dT%H:%M:%S.%z")
                delta_time = "无"
                m_deadline_str = "无"
                m_updated_str = bb.strftime("%Y-%m-%d %H:%M:%S")
            # 获取@的userid
            aite = get_userid(m_assignee, '1', 2)

            total_mess = """
概要：%s
报 告人：%s
计划完成时间：%s
经办人：%s
状态：%s
更新日期：%s   
剩余时间：%s
优先级: %s
sprint: %s
进度详情：%s
jira链接：%s
            """ % (
                m_summary,
                m_reporter,
                m_deadline_str,
                m_assignee,
                m_status,
                m_updated_str,
                delta_time,
                m_priority,
                m_sprint,
                m_descripe,
                m_url,
            )
            print(total_mess)
            wechatwork2(total_mess, token, aite)
        return "post ok"
    return "get  ok"


# 通知1
def wechatwork(texs, token):
    webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=%s" % token
    header = {"Content-Type": "application/json", "Charset": "UTF-8"}
    tex = texs
    message = {"msgtype": "text", "text": {"content": tex}, "at": {"isAtAll": True}}
    message_json = json.dumps(message)
    info = requests.post(url=webhook, data=message_json, headers=header)
    print(info.text)


# 通知2 markdown格式
def wechatwork2(texs, token, aite):
    webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=%s" % token
    header = {"Content-Type": "application/json", "Charset": "UTF-8"}
    tex = texs
    message = {
        "msgtype": "text",
        "text": {
            "content": tex,
            "mentioned_list": aite
        },
        "at": {"isAtAll": True},
    }
    message_json = json.dumps(message)
    info = requests.post(url=webhook, data=message_json, headers=header)
    print(info.text)


# 获取用户userid
def get_userid(text, c_id, c_secret):
    header = {"Content-Type": "application/json", "Charset": "UTF-8"}
    aite_list = text.replace(" ", "").split(",")
    token_url = (
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s"
            % (c_id, c_secret)
    )
    try:
        res1 = requests.get(url=token_url, headers=header)
        token = res1.json()["access_token"]
        user_url = (
                "https://qyapi.weixin.qq.com/cgi-bin/user/simplelist?access_token=%s&department_id=1&fetch_child=1"
                % token
        )
        res2 = requests.get(url=user_url, headers=header)
        uesrlist = res2.json().get("userlist")
        # print(uesrlist)
        userdir = {}
        for i in uesrlist:
            userdir[i["name"]] = i["userid"]
        # print(userdir)
        aite_id_list = [userdir.get(i, "") for i in aite_list]
        aite_text = ",".join(["<@%s>" % userdir.get(i, "") for i in aite_list])
        print(aite_text)
        print(aite_id_list)
        # return aite_text
        return list(set(aite_id_list))
    except:
        return "err"


if __name__ == '__main__':
    app.run(host='0.0.0.0')
