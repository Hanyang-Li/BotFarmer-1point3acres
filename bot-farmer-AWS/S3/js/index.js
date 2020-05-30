window.onload = function() {
    
    // Config of this web page
    const SQS_API_URL = 'Url of AWS API Gateway to pass the message to SQS';
    
    // Initialize global variables
    const QUERY_STRING = window.location.search;  // Get the query behind '?' in URL
    const URL_PARAMS = new URLSearchParams(QUERY_STRING);  // Parse the query into params
    const UID = URL_PARAMS.get('uid');
    const LOG = URL_PARAMS.get('log');
    var question;
    var options;
    var answer;
    var correct;

    // Display error page if url or log is invalid
    if (!isValidPage()) {
        let form = document.querySelector('.quiz-form');
        let image = document.createElement('img');
        setHint('无效的页面！', '#ff5161')
        form.innerHTML = '';
        form.style.cssText = 'text-align: center;';
        image.src = './images/professional_team.png';
        image.style.cssText = 'max-width: 100%; max-height: 100%;';
        form.appendChild(image);
    } else {
        let now = new Date(Date.now());
        let due = new Date(Date.UTC(LOG.slice(0,4), LOG.slice(4,6), LOG.slice(6,8), 23, 59));
        // Render page with log info
        let quizQuestion = document.querySelector('.quiz-question p');
        quizQuestion.innerText = question;
        for (let i = 1; i <= 4; i++) {
            document.querySelector('label[for="o' + i + '"]').innerText = options[i];
            if (answer == i) {
                this.document.getElementById('o' + i).checked = true;
            }
        }
        // Change hints and button logic with log info
        if (now > due) {
            // Case that the question is expired
            disableButton();
            setHint('题目已过期！', '#ff5161');
        } else if (answer) {
            // Case that the question has an answer in log
            disableButton();
            if (correct === true) {
                setHint('已提交，答案正确！', '#00b400');
            } else if (correct === false) {
                setHint('已提交，答案错误！', '#ff5161');
            } else {
                setHint('答题出现未知错误！', '#ffa500');
            }
        } else {
            // Case that the user need to give an answer
            let form = document.querySelector('.quiz-form');
            setHint('提交错误答案会扣除积分！', '#ffa500');
            form.addEventListener('submit', event => {
                // Prevent refeshing the page
                event.preventDefault();
                // Get user's answer
                let givenAnswer;
                document.querySelectorAll('input[type=radio]').forEach(input => {
                    if(input.hasAttribute('name') && input.checked) {
                        givenAnswer = input.value;
                    }
                })
                // Submit form to SQS API
                if (givenAnswer) {
                    // Construct the request body
                    let body = {
                        uid: UID,
                        methods: ['take_quiz'],
                        log: LOG,
                        answer: givenAnswer
                    };
                    // Post SQS API
                    $.ajax({
                        url: SQS_API_URL,
                        type: "POST",
                        crossDomain: "true",
                        dataType: "json",
                        contentType: "application/json; charset=utf-8",
                        data: JSON.stringify(body),
                        success: function () {
                            disableButton();
                            setHint('已提交！', '#00b400');
                        },
                        error: function () {
                            setHint('未提交成功！', '#ff5161');
                        }
                    });
                }
            });
        }
    }

    function isValidPage() {
        // Check validation of params
        if (!(UID && LOG)) return false;
        // Check validation of log file
        let url = "./users/" + UID + "/log/" + LOG + ".json"
        let isValidLog;
        $.ajax({
            url: url,
            async: false, // Must sync with the main thread!
            type: 'GET',
            dataType: 'json',
            error: function() {
                isValidLog = false;
            },
            success: function(data) {
                // Check validation of question and options in log
                console.log(data);
                question = data['take quiz']['content']['question'];
                options = data['take quiz']['content']['options'];
                answer = data['take quiz']['content']['answer'];
                correct = data['take quiz']['content']['correct'];
                if (question === undefined || Object.keys(options).sort().join('') !== '1234') {
                    isValidLog = false;
                } else {
                    isValidLog = true;
                }
            }
        });
        return isValidLog;
    }

    function setHint(prompt, color) {
        let hint = document.querySelector('.quiz-hint p');
        hint.innerText = prompt;
        hint.style.color = color;
    }

    function disableButton() {
        let btn = document.querySelector('button');
        btn.disabled = true;
        btn.style.backgroundColor = '#ddd';
        btn.style.color = '#aaa';
        btn.style.border = '1px solid #ccc';
    }

}