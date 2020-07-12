import re
import sys
import json
import random
import platform
from io import BytesIO
from collections import defaultdict
import requests
import pytesseract
from PIL import Image, ImageFilter

# Windows cmd needs colorama to run ANSI format code
if 'windows' in platform.system().lower():
    import colorama
    colorama.init()

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

with open('user.json', 'r', encoding='utf-8') as f:
    user = json.load(f)

session = requests.Session()


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
            print("Login ", end='')
            body = {
                'username': user['uid'],
                'password': user['passwd'],
                'quickforward': 'yes',
                'handlekey': 'ls'
            }
            response = session.post(URL_LOGIN, headers=HEADERS, data=body)
            if re.search(RE_LOGIN_FAILED, response.text):
                print("\033[1;31m[failed]\033[0m: uid and passwd are not match!")
                return
            elif re.search(RE_LOGIN_LOCKED, response.text):
                print("\033[1;31m[failed]\033[0m: IP address has been locked!")
                return
            elif not has_login():
                print("\033[1;33m[failed]\033[0m: unknown error!")
                return
            else:
                print("\033[1;32m[succeed]\033[0m: {}".format(user['uid']))
        return func(*args, **kwargs)

    return wrapper


@login
def check_in():
    """
    Take daily check in operation, fill the form with random mood and different saying everyday.
    """
    response = session.get(URL_CHECK_IN_PAGE, headers=HEADERS)
    # Get formhash from check in page, without it you can't check in
    formhash = re.search(RE_CHECK_IN_HASH, response.text)
    if not formhash:
        print("Check In \033[1;34m[failed]\033[0m: cannot get formhash!")
        return
    # Check whether user can check in or not
    if re.search(RE_HAS_CHECK_IN, response.text):
        # Case that user has checked in today or the user cannot check in now
        print("Check In \033[1;34m[failed]\033[0m: user has checked in today or cannot check in now!")
        return
    elif not re.search(RE_NOT_CHECK_IN, response.text):
        # Case that there's unknown reason user is not allowed to check in
        print("Check In \033[1;34m[failed]\033[0m: unknown reason cannot check in!")
        return
    # Case that user is allowed to check in
    mood = _get_mood()
    saying = _get_daily_sentence()[:49]  # 1point3acres doesn't accept more than 50 chars
    verify_code = _get_verify_code('S00')
    print("Check In ", end='')
    # Generate form, 'qdmode' is check in mode, 1 means say anything you like
    body = {
        'formhash': formhash.group(1),
        'qdxq': mood,
        'qdmode': 1,
        'todaysay': saying.encode('gbk', errors='ignore'),
        'fastreply': 0,
        'sechash': 'S00',
        'seccodeverify': verify_code
    }
    response = session.post(URL_CHECK_IN, headers=HEADERS, data=body)
    if re.search(RE_CANNOT_CHECK_IN, response.text):
        print("\033[1;31m[failed]\033[0m: 1point3acres rejected your request!")
    elif re.search(RE_CHECK_IN_SUCCEED, response.text):
        saying = saying[:9] + '...' if len(saying) > 10 else saying
        print("\033[1;32m[succeed]\033[0m: mood='{}', saying='{}'".format(mood, saying))
    else:
        print("\033[1;33m[failed]\033[0m: unknown error!")


@login
def take_quiz():
    """
    Get daily quiz, find the correct answer, recognize verify code and update database.
    """
    print("Get Quiz ", end='')
    # Get the quiz
    # Important variables: question, options
    data = session.get(URL_GET_QUIZ, headers=HEADERS).text
    if re.search(RE_CANNOT_QUIZ, data):
        print("\033[1;31m[failed]\033[0m: 1point3acres rejected your request!")
        return
    elif re.search(RE_QUIZ_TAKEN, data):
        print("\033[1;34m[failed]\033[0m: you have already finished the quiz today!")
        return
    formhash = re.search(RE_QUIZ_HASH, data).group(1)
    question = re.search(RE_QUIZ_QUESTION, data).group(1).strip()
    options = dict([(t[1].strip(), t[0]) for t in re.findall(RE_QUIZ_ANSWERS,data)])

    # Get the answer of quiz
    # Important variables: cheat_sheet, recommendations, correct
    # Get the intersect set of options and cheat sheet as the recommended answers
    with open('cheat_sheet.json', 'r', encoding='utf-8') as f:
        cheat_sheet = json.load(f)
    recommendations = [ans for ans in options if ans in cheat_sheet.setdefault(question, list())]
    print("\033[1;32m[succeed]\033[0m")
    print("  \033[1;34mQ: \033[0m{}".format(question))
    for ans in sorted(options.items(), key=lambda x: x[1]):
        if ans[0] in recommendations:
            print("    -[\033[1;32m{}\033[0m] {}".format(ans[1], ans[0]))
        else:
            print("    -[{}] {}".format(ans[1], ans[0]))
    # Case that the database has the answer and does not need user to provide one
    if len(recommendations) == 1:
        correct = options[recommendations[0]]
        print("  \033[1;34mA: \033[0m", end='')
        print("database recommended option ", end='')
        print("[\033[1;34m{}\033[0m] \033[1m{}\033[0m".format(correct, recommendations[0]))
    # Case that the database doesn't have answer or has multiple ones
    else:
        correct = None
        # Print a new line to standardized format
        print()
        while correct not in ['1', '2', '3', '4']:
            sys.stdout.write('\033[A\033[K')
            print("  \033[1;31mA: \033[0m", end='')
            if correct is not None:
                prompt = "please input valid option number, [1/2/3/4]? "
            elif len(recommendations) == 0:
                prompt = "database has no record, your answer? "
            else:
                prompt = "database can't decide, your answer? "
            correct = input(prompt)
        sys.stdout.write('\033[A\033[K')
        print("  \033[1;34mA: \033[0m{}".format(prompt), end='')
        option_text = [ans[0] for ans in options.items() if ans[1] == correct][0]
        print("[\033[1;34m{}\033[0m] \033[1m{}\033[0m".format(correct, option_text))

    # Submit the form
    # Important variable: is_right
    verify_code = _get_verify_code('SA00')
    body = {
        'formhash': formhash,
        'answer': correct,
        'sechash': 'SA00',
        'seccodeverify': verify_code,
        'submit': 'true'
    }
    response = session.post(URL_TAKE_QUIZ, headers=HEADERS, data=body)
    if re.search(RE_RIGHT_ANSWER, response.text):
        is_right = True
        print("Take Quiz \033[1;32m[correct]\033[0m")
    elif re.search(RE_WRONG_ANSWER, response.text):
        is_right = False
        print("Take Quiz \033[1;31m[wrong]\033[0m")
    else:
        print("Take Quiz \033[1;31m[failed]\033[0m: unknown error!")
        return
    
    # Update database
    if is_right and len(recommendations) != 1:
        print("Update Database \033[1;32m[succeed]\033[0m")
        # Remove all the answers which were recommended
        for answer in recommendations:
            cheat_sheet[question].remove(answer)
            print("  \033[1;31m-\033[0m {}[{}]".format(question, answer))
        # Add the correct answer to the database
        answer = [a[0] for a in options.items() if a[1] == correct][0]
        cheat_sheet[question].append(answer)
        print("  \033[1;32m+\033[0m {}[{}]".format(question, answer))
    elif not is_right and len(recommendations) != 0:
        print("Update Database \033[1;32m[succeed]\033[0m")
        answer = [a[0] for a in options.items() if a[1] == correct][0]
        # Get intersect set of answer and recommended options
        bad_answers = [a for a in recommendations if a == answer]
        # Remove the bad answers from database
        for answer in bad_answers:
            cheat_sheet[question].remove(answer)
            print("  \033[1;31m-\033[0m {}[{}]".format(question, answer))
    else:
        print("Update Database \033[1;34m[failed]\033[0m: no need to update!")
    # Save the database to json file
    with open('cheat_sheet.json','w', encoding='utf-8') as file:
        json.dump(cheat_sheet, file, ensure_ascii=False, indent=2)


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
            print("\033[1;31m[Warning]\033[0m: {} API failure!".format(api))
            api_table.pop(api)
    return '今天没什么好说的{}!'.format('啊'*random.randint(0,10))

def _get_mood():
    """
    Pick a mood randomly
    """
    moods = ['kx', 'ng', 'ym', 'wl', 'nu', 'ch', 'fd', 'yl', 'shuai']
    return moods[random.randint(0, len(moods)-1)]

def _get_verify_code(idhash):
    """
    Get a new verify image and recognize it to string
    :params idhash: check in set to "S00"; take quiz set to "SA00"
    """
    # Keep recognizing verify code if it is wrong
    is_wrong = True
    while is_wrong:
        print("Recognize Verify \033[1;34m[pending]: \033[0m", end='', flush=True)
        # Get the latest verify code image
        response = session.get(URL_ANOTHER_VERIFY.format(idhash, idhash), headers=HEADERS)
        verify_num = re.search(RE_VERIFY_NUM, response.text).group(1)
        verify_url = URL_VERIFY_IMAGE.format(verify_num, idhash)
        verify_gif = Image.open(BytesIO(session.get(verify_url, headers=HEADERS).content))
        # Find the frame of gif with the longest duration, save it to new image
        durations = []
        try:
            while True:
                durations.append(verify_gif.info['duration'])
                verify_gif.seek(verify_gif.tell() + 1)
        except EOFError:
            pass
        verify_gif.seek(durations.index(max(durations)))
        verify_image = Image.new('RGBA', verify_gif.size)
        verify_image.paste(verify_gif)
        # Recognize verify code from the image
        verify_code = _recognize_verify(verify_image)
        print(verify_code)
        # Check whether the code is right or wrong
        verify_status = session.get(URL_VERIFY_CODE.format(idhash) + verify_code, headers=HEADERS).text
        sys.stdout.write('\033[A\033[K')
        if (re.search(RE_RIGHT_VERIFY, verify_status)):
            is_wrong = False
            print("Recognize Verify \033[1;32m[succeed]\033[0m: {}".format(verify_code))
            return verify_code

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
            try:
                char = _refine(pytesseract.image_to_string(c_img, lang='verify-codes', config='--psm 10'))
            except:
                print("\r\033[KRecognize Verify \033[1;31m[failed]\033[0m: cannot find tesseract or tessdata!")
                sys.exit(1)
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


if __name__ == "__main__":
    # Get the arguments from terminal command line
    arguments = sys.argv
    if len(arguments) > 2:
        # Case that have more than 1 arguments other than filename
        print("\033[1;31mOnly accept one argument! [check_in / take_quiz]\033[0m")
    elif len(arguments) == 2:
        # Case that have 1 argument other than filename
        # Functions 'check_in' and 'take_quiz' are valid argument, run the funtion
        argument = arguments[1]
        try:
            exec(argument + '()')
        except NameError:
            print("\033[1;31mInvalid argument {}, only [check_in / take_quiz] are valid\033[0m".format(argument))
    else:
        # Case that no argument passed other than filename
        # Run all the functions in this case
        check_in()
        take_quiz()