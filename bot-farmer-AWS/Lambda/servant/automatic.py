import re
import ssl
import sys
import json
import random
import smtplib
from io import BytesIO
from datetime import datetime
from urllib.parse import urlencode
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import boto3
import requests
import pytesseract
from PIL import Image, ImageFilter

URL_ICIBA_API = 'http://open.iciba.com/dsapi/'
URL_ONE_API = 'http://api.youngam.cn/api/one.php'
URL_SHANBAY_API = 'https://apiv3.shanbay.com/weapps/dailyquote/quote/'
URL_JINRISHICI_API = 'https://v1.jinrishici.com/rensheng.txt'
URL_EMAIL = 'https://www.1point3acres.com/bbs/home.php?mod=spacecp&ac=profile&op=password'
URL_LOGIN = 'https://www.1point3acres.com/bbs/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1'
URL_CHECK_IN_PAGE = 'https://www.1point3acres.com/bbs/dsu_paulsign-sign.html'
URL_CHECK_IN = 'https://www.1point3acres.com/bbs/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=0&inajax=0'
URL_GET_QUIZ = 'https://www.1point3acres.com/bbs/plugin.php?id=ahome_dayquestion:pop&infloat=yes&handlekey=pop&inajax=1&ajaxtarget=fwin_content_pop'
URL_ANOTHER_VERIFY = 'https://www.1point3acres.com/bbs/misc.php?mod=seccode&action=update&idhash={}&inajax=1&ajaxtarget=seccode_{}'
URL_VERIFY_IMAGE = 'https://www.1point3acres.com/bbs/misc.php?mod=seccode&update={}&idhash={}'
URL_VERIFY_CODE = 'https://www.1point3acres.com/bbs/misc.php?mod=seccode&action=check&inajax=1&&idhash={}&secverify='
URL_TAKE_QUIZ = 'https://www.1point3acres.com/bbs/plugin.php?id=ahome_dayquestion:pop'

RE_USERNAME = r'<strong class=\"vwmy\"><a href=\".*\.html\" target=\"_blank\" title=\"访问我的空间\">(.*)<\/a><\/strong>'
RE_EMAIL = r'<input type=\"text\" name=\"emailnew\" id=\"emailnew\" value=\"(.*)\" disabled \/>'
RE_LOGIN_FAILED = r'登录失败'
RE_LOGIN_LOCKED = r'密码错误次数过多'
RE_CHECK_IN_HASH = r'<a href=\"member\.php\?mod=logging&amp;action=logout&amp;formhash=(.{8})\">退出<\/a>'
RE_NOT_CHECK_IN = r'今天签到了吗？请选择您此刻的'
RE_HAS_CHECK_IN = r'您今天已经签到过了或者签到时间还未开始'
RE_CANNOT_CHECK_IN = r'请做微信验证（网站右上角）后参与每日答题。'
RE_CHECK_IN_SUCCEED = r'恭喜你签到成功!'
RE_CANNOT_QUIZ = r'您的积分不足以支付答错惩罚|请做微信验证'
RE_QUIZ_TAKEN = r'您今天已经参加过答题，明天再来吧！'
RE_QUIZ_HASH = r'<input type=\"hidden\" name=\"formhash\" value=\"(.{8})\">'
RE_QUIZ_QUESTION = r'<b>【题目】<\/b>&nbsp;(.*)<\/font>'
RE_QUIZ_ANSWERS = r'name=\"answer\" value=\"(\d)\"\s*>&nbsp;&nbsp;(.*?)<\/div>'
RE_VERIFY_NUM = r'src=\"misc\.php\?mod=seccode&update=(\d*)\&idhash=(S00|SA00)\"'
RE_RIGHT_VERIFY = r'<root><\!\[CDATA\[succeed\]\]><\/root>'
RE_EXPIRE_VERIFY = r'抱歉，验证码填写错误'
RE_WRONG_ANSWER = r'抱歉，回答错误！扣除1大米'
RE_RIGHT_ANSWER = r'恭喜你，回答正确！奖励1大米'

HEADERS = {
    'origin': 'https://www.1point3acres.com',
    'referer': 'https://www.1point3acres.com/bbs/',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
}

with open('config.json', 'r') as f:
    config = json.load(f)
S3_USERS_BUCKET = config['S3_USERS_BUCKET']
DYNAMODB_TABLE = config['DYNAMODB_TABLE']
STATIC_WEBSITE = config['STATIC_WEBSITE']
GMAIL_ACCOUNT = config['GMAIL_ACCOUNT']
GMAIL_PASSWORD = config['GMAIL_PASSWORD']

# Initialize AWS objects
s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb')

# Initialize user dictionary
user = {'uid': '', 'passwd': ''}

# Initialize log dictionary
log = {}

def set_user_info(uid, passwd, log_num=None):
    """
    Called by lambda function, and initialize user and log dictionary
    """
    global log
    user['uid'] = uid
    user['passwd'] = passwd
    try:
        obj = s3.Object(S3_USERS_BUCKET, 'users/{}/log/{}.json'.format(uid, log_num))
        log = json.loads(obj.get()['Body'].read().decode('utf-8'))
    except:
        log['num'] = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        log['uid'] = uid
    return log


# Create a ssesion to make requests
session = requests.Session()

def close_lambda():
    """
    Called by lambda function when it has done to eliminate affects of global variables
    """
    global session, log
    log = {}
    session.cookies.clear()
    session.close()


def login(func):
    """
    A decorator which runs before all the other operations, to make sure user has logged in
    """

    def has_login():
        """
        Check the login status of specific user
        """
        # This page contains the username and email if user have already logged in
        response = session.get(URL_EMAIL, headers=HEADERS)
        # The case that no one has logged in
        if not re.search(RE_USERNAME, response.text):
            return False
        # The case that another user may have logged in
        username = re.search(RE_USERNAME, response.text).group(1)
        email = re.search(RE_EMAIL, response.text).group(1)
        return (user['uid'] == username) or (user['uid'] == email)

    def wrapper(*args, **kwargs):
        """
        Closure which takes the main login operation
        """
        if not has_login():
            log['login'] = {}
            body = {
                'username': user['uid'],
                'password': user['passwd'],
                'quickforward': 'yes',
                'handlekey': 'ls'
            }
            response = session.post(URL_LOGIN, headers=HEADERS, data=body)
            if re.search(RE_LOGIN_FAILED, response.text):
                log['login']['status'] = 'failed'
                log['login']['error'] = 'uid and passwd are not match!'
                return log
            elif re.search(RE_LOGIN_LOCKED, response.text):
                log['login']['status'] = 'failed'
                log['login']['error'] = 'IP address has been locked!'
                return log
            elif not has_login():
                log['login']['status'] = 'failed'
                log['login']['error'] = 'unknown error!'
                return log
            else:
                log['login']['status'] = 'succeed'
        return func(*args, **kwargs)

    return wrapper


@login
def check_in(attempt=0):
    """
    Take daily check in operation, fill the form with random mood and different saying everyday.
    """
    log['check in'] = {}
    response = session.get(URL_CHECK_IN_PAGE, headers=HEADERS)
    # Get formhash from check in page, without it you can't check in
    formhash = re.search(RE_CHECK_IN_HASH, response.text)
    if not formhash:
        log['check in']['status'] = 'failed'
        log['check in']['error'] = 'cannot get formhash!'
        return log
    # Check whether user can check in or not
    if re.search(RE_HAS_CHECK_IN, response.text):
        # Case that user has checked in today or the user cannot check in now
        log['check in']['status'] = 'failed'
        log['check in']['error'] = 'user has checked in today or cannot check in now!'
        return log
    elif not re.search(RE_NOT_CHECK_IN, response.text):
        # Case that there's unknown reason user is not allowed to check in
        log['check in']['status'] = 'failed'
        log['check in']['error'] = 'unknown reason cannot check in!'
        return log
    # Case that user is allowed to check in
    mood = _get_mood()
    saying = _get_daily_sentence()[:49]  # 1point3acres doesn't accept more than 50 chars
    verify_code = _get_verify_code('check in')
    if not verify_code:
        return log
    body = {
        'formhash': formhash.group(1),
        'qdxq': mood,
        'qdmode': 1,
        'todaysay': saying.encode('gbk'),
        'fastreply': 0,
        'sechash': 'S00',
        'seccodeverify': verify_code
    }
    response = session.post(URL_CHECK_IN, headers=HEADERS, data=body)
    if re.search(RE_CANNOT_CHECK_IN, response.text):
        log['check in']['status'] = 'failed'
        log['check in']['error'] = '1point3acres rejected your request!'
    elif re.search(RE_CHECK_IN_SUCCEED, response.text):
        log['check in']['status'] = 'succeed'
        log['check in']['content'] = {'mood': mood, 'saying': saying}
    elif not response.text:
        # Case that sometimes no response from 1point3acres server
        log['check in']['attempt times'] = attempt + 1;
        if attempt < 10:
            check_in(attempt + 1)
        else:
            log['check in']['status'] = 'failed'
            log['check in']['error'] = 'no response!'
    else:
        log['check in']['status'] = 'failed'
        log['check in']['error'] = 'unknown error!'
        log['check in']['response'] = response.text
    return log


@login
def take_quiz(given_ans=None):
    """
    Get daily quiz, find the correct answer, recognize verify code and update database.
    """
    # Check if the quiz has been taken by bot farmer
    if re.search(r'\"answer\": \"[1234]\"', json.dumps(log, ensure_ascii=False)):
        return log
    # Get the quiz
    # Important variables: question, options
    log['take quiz'] = {}
    data = session.get(URL_GET_QUIZ, headers=HEADERS).text
    if re.search(RE_CANNOT_QUIZ, data):
        log['take quiz']['status'] = 'failed'
        log['take quiz']['error'] = '1point3acres rejected your request!'
        return log
    elif re.search(RE_QUIZ_TAKEN, data):
        log['take quiz']['status'] = 'failed'
        log['take quiz']['error'] = 'user has already finished the quiz today!'
        return log
    formhash = re.search(RE_QUIZ_HASH, data).group(1)
    question = re.search(RE_QUIZ_QUESTION, data).group(1).strip()
    options = dict([(t[1].strip(), t[0]) for t in re.findall(RE_QUIZ_ANSWERS,data)])
    # Avoid of question changed case
    if log['take quiz'].setdefault('content', {}).setdefault('question', question) != question:
        given_ans = None
        log['num'] = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    log['take quiz']['content']['options'] = dict([(t[0], t[1].strip()) for t in re.findall(RE_QUIZ_ANSWERS,data)])

    # Get the answer of quiz
    # Important variables: cheat_sheet, recommendations, correct, item
    # Get the intersect set of options and cheat sheet as the recommended answers
    cheat_sheet = dynamodb.Table(DYNAMODB_TABLE)
    item = cheat_sheet.get_item(Key={'Question':question}).setdefault('Item', {'Question': question, 'Answers': []})
    recommendations = [ans for ans in options if ans in item['Answers']]
    # Case that the database has the answer and does not need user to provide one
    if len(recommendations) == 1:
        correct = options[recommendations[0]]
        log['take quiz']['content']['answer'] = correct
    # Case that the database doesn't have answer or has multiple ones
    elif given_ans:
        # Case that user has given an answer
        correct = str(given_ans)
        log['take quiz']['content']['answer'] = correct
    else:
        # Case that no answer, send an email to ask for an answer
        email = re.search(RE_EMAIL, session.get(URL_EMAIL, headers=HEADERS).text).group(1)
        url = '{}?{}'.format(STATIC_WEBSITE, urlencode({'uid': log['uid'], 'log': log['num']}))
        _send_email(email, url)
        log['take quiz']['status'] = 'suspend'
        log['take quiz']['notes'] = 'waiting for answer from user'
        log['take quiz']['email url'] = url
        return log
    
    # Get a correct verify code
    verify_code = _get_verify_code('take quiz')
    if not verify_code:
        return log

    # Submit the form
    # Important variable: is_right
    body = {
        'formhash': formhash,
        'answer': correct,
        'sechash': 'SA00',
        'seccodeverify': verify_code,
        'submit': 'true'
    }
    # Check whether 1point3acres has changed the quiz question
    if datetime.utcnow().strftime('%Y%m%d%H%M%S') > log['num'][:8] + '235900':
        log['take quiz']['status'] = 'failed'
        log['take quiz']['error'] = 'quiz expired!'
        return log
    # Take the quiz, and get response of answer correctness
    response = session.post(URL_TAKE_QUIZ, headers=HEADERS, data=body)
    if re.search(RE_RIGHT_ANSWER, response.text):
        is_right = True
        log['take quiz']['status'] = 'succeed'
        log['take quiz']['content']['correct'] = True
    elif re.search(RE_WRONG_ANSWER, response.text):
        is_right = False
        log['take quiz']['status'] = 'succeed'
        log['take quiz']['content']['correct'] = False
    else:
        log['take quiz']['status'] = 'failed'
        log['take quiz']['error'] = 'unknown error!'
        return log
    
    # Update database
    answers = item['Answers']
    log['take quiz']['content']['database'] = {'key': question, 'value': {'before': [a for a in answers]}}
    if is_right and len(recommendations) != 1:
        # Remove all the answers which were recommended
        for answer in recommendations:
            answers.remove(answer)
        # Add the correct answer to the database
        answer = [a[0] for a in options.items() if a[1] == correct][0]
        answers.append(answer)
        log['take quiz']['content']['database']['value']['after'] = answers
    elif not is_right and len(recommendations) != 0:
        answer = [a[0] for a in options.items() if a[1] == correct][0]
        # Get intersect set of answer and recommended options
        bad_answers = [a for a in recommendations if a == answer]
        # Remove the bad answers from database
        for answer in bad_answers:
            answers.remove(answer)
        log['take quiz']['content']['database']['value']['after'] = answers
    else:
        log['take quiz']['content'].pop('database')
    # Update DynamoDB table on cloud
    response = cheat_sheet.update_item(
        Key={
            'Question':question
        },
        UpdateExpression="set Answers=:a",
        ExpressionAttributeValues={
            ':a': answers
        }
    )
    return log


def _get_daily_sentence():
    """
    Pick an API to get daily sentence randomly
    """
    api_table = {
        'iciba': {
            'url': URL_ICIBA_API,
            'parse': "json.loads({}).get('note')"
        },
        'one': {
            'url': URL_ONE_API,
            'parse': "json.loads({}).get('data')[0]['text']"
        },
        'shanbay': {
            'url': URL_SHANBAY_API,
            'parse': "json.loads({}).get('translation')"
        },
        'jinrishici': {
            'url': URL_JINRISHICI_API,
            'parse': "{}"
        }
    }
    while api_table:
        api = [k for k in api_table.keys()][random.randint(0, len(api_table)-1)]
        try:
            response = requests.get(api_table[api]['url']).text
            sentence = eval(api_table[api]['parse'].format('response'))
            return sentence
        except:
            log['check in'].setdefault('API warning', []).append(api + ' API failure!')
            api_table.pop(api)
    return '今天没什么好说的{}！'.format('啊'*random.randint(0,10))

def _get_mood():
    """
    Pick a mood randomly
    """
    moods = ['kx', 'ng', 'ym', 'wl', 'nu', 'ch', 'fd', 'yl', 'shuai']
    return moods[random.randint(0, len(moods)-1)]

def _send_email(email, url):
    """
    Send the email with the url of asking the answer
    """
    message = MIMEMultipart('alternative')
    message['Subject'] = 'Asking for 1point3acres Daily Quiz Answer'
    message['From'] = GMAIL_ACCOUNT
    message['To'] = email

    text = """\
    Howdy!
    
    Bot Farmer doesn't know the anwser of your daily quiz, please click the link below to help it:
    {}.
    
    Bot Farmer from 1point3acres
    """.format(url)

    part = MIMEText(text, 'plain')
    message.attach(part)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(GMAIL_ACCOUNT, GMAIL_PASSWORD)
        server.sendmail(GMAIL_ACCOUNT, email, message.as_string())

def _get_verify_code(method):
    """
    Get a new verify image and recognize it to string
    """
    idhash = {'check in': 'S00', 'take quiz': 'SA00'}[method]
    # Keep recognizing verify code if it is wrong for 20 times
    is_wrong = True
    for i in range(20):
        # Get the latest verify code image
        response = session.get(URL_ANOTHER_VERIFY.format(idhash, idhash), headers=HEADERS)
        verify_num = re.search(RE_VERIFY_NUM, response.text).group(1)
        verify_url = URL_VERIFY_IMAGE.format(verify_num, idhash)
        verify_image = Image.open(BytesIO(session.get(verify_url, headers=HEADERS).content))
        # Recognize verify code from the image
        verify_code = _recognize_verify(verify_image)
        # Check whether the code is right or wrong
        verify_status = session.get(URL_VERIFY_CODE.format(idhash) + verify_code, headers=HEADERS).text
        if (re.search(RE_RIGHT_VERIFY, verify_status)):
            is_wrong = False
            return verify_code
    # Case that has tried 20 times and it must have errors in OCR operations
    log[method]['status'] = 'failed'
    log[method]['error'] = 'verify codes OCR failed!'
    return None

def _recognize_verify(img):
    """
    Recognize the verify code image to string
    """
    # Initialize
    rgb_dict = defaultdict(int)
    ans = ""
    # Remove background color
    pix = img.load()
    width = img.size[0]
    height = img.size[1]
    for x in range(width):
        for y in range(height):
            res_code = _validate_img(width, height, x, y, pix)
            if res_code == 1: 
                for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                    nx, ny = x+dx, y+dy
                    rgb_dict[pix[nx, ny]] += 10
                rgb_dict[pix[x, y]] += 10
            elif res_code == 3:
                rgb_dict[pix[x, y]] += 1
            else:
                img.putpixel((x,y),(255, 255, 255))
    # Remove noise lines and color verify code in black
    rank = sorted(rgb_dict.items(), key = lambda k_v : k_v[1])
    color_set = set([colr[0] for colr in rank[-4:]])
    pix = img.load()
    for x in range(width):
        for y in range(height):
            p = (255, 255, 255) if pix[x, y] not in color_set else (0, 0, 0)
            img.putpixel((x, y), p)
    # Cut image vertically for recognition
    left = right = top = 0
    bottom = height - 1
    is_white = True
    is_char = False
    for x in range(width):
        for y in range(height):
            rgb = pix[x, y][:3]
            if y == 0:
                is_white = True
            elif rgb == (0, 0, 0):
                is_white = False
            if not is_white and not is_char:
                is_char = True 
                left = x - 3
        if is_char and is_white:
            is_char = False
            right = x + 3
            c_img = img.crop((left, top, right, bottom))
            c_img = c_img.resize((c_img.size[0]*2, c_img.size[1]*2))
            c_img = c_img.filter(ImageFilter.GaussianBlur(radius=1))
            char = _refine(pytesseract.image_to_string(c_img, lang='verify-codes', config='--psm 10'))
            ans += char
    return ans

def _validate_img(width, height, x, y, pix):
    direct = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    diff = same = 0
    for dx, dy in direct:
        nx, ny = x+dx, y+dy 
        if 0 <= nx and nx < width and 0 <= ny and ny < height:
            if  pix[x, y] == pix[nx, ny]:
                same += 1
            else:
                diff += 1
        else:
            diff += 1
    if diff == 4:
        # Invalid case
        return 0
    elif same == 4:
        # Full valid case
        return 1
    else:
        # Partial valid case
        return 3

def _refine(char):
    if len(char) > 1:
        return char[-1]
    if char == '¥':
        return 'Y'
    else:
        return char
