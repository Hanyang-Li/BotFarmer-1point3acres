# BotFarmer-1point3acres

BotFarmer 是一亩三分地论坛每日签到、答题赚取积分的自动脚本。项目分为本地命令行交互、AWS 云端部署两个版本。

**本项目仅用于学习交流，如有侵犯论坛利益，请联系我删除仓库！**

## 环境要求

* 开发环境：macOS Catalina 10.15.5
* 测试环境：macOS Catalina 10.15.5
* Python 版本：3.7.6
* Python 依赖库：requests, Pillow, pytesseract, boto3
* 软件依赖：tesseract-ocr 4.0.0+, docker


## 使用说明

分别介绍本地命令行版本环境的安装、脚本运行，AWS 云端部署版的搭建，以及tesseract模型的训练。

### 本地命令行交互版

#### 安装 tesseract

一亩三分地论坛在2020年5月底的更新后，每日签到、答题都需要输入验证码，因此我使用 tesseract OCR 识别验证码。接下来介绍 tesseract 的安装和模型导入。

对于 macOS 平台用户，在 `terminal（终端）`应用中输入以下命令，即可安装软件：

```console
$ brew install tesseract
```

接下来查看 tesseract 安装位置，命令及可能的运行结果如下：

```console
$ brew list tesseract

/usr/local/Cellar/tesseract/4.1.1/bin/tesseract
/usr/local/Cellar/tesseract/4.1.1/include/tesseract/ (19 files)
/usr/local/Cellar/tesseract/4.1.1/lib/libtesseract.4.dylib
/usr/local/Cellar/tesseract/4.1.1/lib/pkgconfig/tesseract.pc
/usr/local/Cellar/tesseract/4.1.1/lib/ (2 other files)
/usr/local/Cellar/tesseract/4.1.1/share/tessdata/ (35 files)
```

其中 `/usr/local/Cellar/tesseract/4.1.1/share/tessdata/` 目录中保存了 tesseract 的 OCR 模型，我们将自己训练的模型也放在这个目录下。 在本项目目录 `train-tesseract/` 中的 `verify-codes.traineddata` 文件即为针对一亩三分地验证码所训练的模型。

*进入项目目录 `train-tesseract/`*，运行以下命令导入模型（请根据刚才的输出更改后边目录地址）：

```console
$ cp verify-codes.traineddata /usr/local/Cellar/tesseract/4.1.1/share/tessdata/
```

对于 Windows 平台用户，请访问 [https://digi.bib.uni-mannheim.de/tesseract/](https://digi.bib.uni-mannheim.de/tesseract/ "Tesseract Versions") 下载 tesseract 4.0.0 之后版本的安装包，运行安装包，根据提示将软件安装在本地。

在安装目录（默认为 `C:\Program Files (x86)\Tesseract-OCR`）中找到 `tessdata` 文件夹，将本项目目录 `train-tesseract/` 中的 `verify-codes.traineddata` 文件复制到该文件夹中，完成模型的导入。

#### 安装 Python 依赖库

本项目提供了 `pipenv` 的环境配置文件，打开命令行工具，*进入项目目录 `bot-farmer-local/`*，运行以下命令安装 Python 虚拟环境：

```console
$ pipenv install
```

如果不想创建 Python 虚拟环境，也可以运行以下命令直接安装 Python 依赖库：

```console
$ pip3 install requests Pillow pytesseract
```

#### 修改配置文件

首先我们通过抓包获取一亩三分地前端加密后的登陆密码。用浏览器访问一亩三分地论坛主页 [https://www.1point3acres.com/bbs/](https://www.1point3acres.com/bbs/ "一亩三分地")，退出登录后打开浏览器的网页检查器，选择 `Network（网络）`选项卡，勾选 `Preserve log（保留日志）`选项，保持`录制`为打开状态，如图：

![网页检查器设置截图](./images/readme/local-01.png)

输入用户名和密码，点击登录，这时会录制到对网页的请求，在网页检查器中选择查看 `Doc （文稿）`，找到名称为 `member.php` 的 POST 方法记录，查看它的 `Header （标头）`，滚动到最下边就可以在请求数据中找到网页前端加密后的密码，如图：

![抓包查看加密密码截图](./images/readme/local-02.png)

在项目目录 `bot-farmer-local/` 中找到 `user.json` 文件，修改文件内容：

```json
{
    "uid": "填写请求数据中username后的值",
    "passwd": "填写请求数据中password后的值"
}
```

#### 运行脚本

打开命令行工具，*进入项目目录 `bot-farmer-local/`*。如果之前安装了 Python 虚拟环境，执行以下命令将其打开：

```console
$ pipenv shell
```

执行以下命令运行脚本进行论坛每日签到、答题：

```console
$ python automatic.py
```

也可以用传递参数的形式单独进行签到、答题操作。

用如下命令进行签到操作：

```console
$ python automatic.py check_in
```

脚本会随机选择一个心情，“今天最想说”中填写某字典每日一句，并自动识别验证码并检查验证码正确性。

用如下命令进行答题操作：

```console
$ python automatic.py take_quiz
```

脚本会获取用户今天的题目和对应的4个选项，并在项目目录 `bot-farmer-local/` 里的 `cheat_sheet.json` 中寻找该题目和正确答案。如果该文件能够提供唯一的答案，脚本会自动作出选择；如果找不到该题目，或者出现未知错误不能提供唯一答案，则会以命令行交互的方式向用户询问答案。之后脚本会自动识别验证码并检查验证码的正确性。在自动提交题目后，脚本会根据一亩三分地论坛的反馈信息判断作答的正确性，并据此更新 `cheat_sheet.json` 文件，将错误的答案删除，保留或添加正确的答案。

如果使用 Python 虚拟环境运行的脚本，关闭命令行工具窗口或执行以下命令退出虚拟环境：

```console
$ exit
```
-----

### AWS 云端部署版

部署在云端上的版本不仅可以实现定时自动触发签到、答题，也支持同时处理多个一亩三分地论坛账号。其结构如图所示：

![AWS 云端部署结构图](./images/readme/aws-01.png)

`CloudWatch` 中的事件定时触发 `Master Lambda Function（包工头）`读取 `S3` 桶中的所有论坛账号信息，将签到、答题任务通过 `SQS` 分配给多个 `Servant Lambda Function（BotFarmer）`去完成。`DynamoDB` 表格中存储 cheat sheet，`Servant Lambda` 在答题时从中获取、更新答案，也可以通过脚本同步本地 `cheat_sheet.json` 与云端的表格中的数据。由于云端与用户和开发者之间的交互不是以命令行输入、输出进行的，所以用户提供答案的方式变为收取带有提供答案网页 URL 的邮件，该 URL 由 `S3` 静态部署的网页地址和该用户账户、日志时间戳参数组合而成，网页通过 URL 中的参数在 `S3` 中提取用户和日志信息，生成表单。用户提交的答案会经过 `API Gateway` 转换为触发数据再次触发 `Servant Lambda` 进行答题操作。由于 `S3` 中文件不方便查看，所以运行的日志也会发送回 `CloudWatch` 中方便阅读。

接下来介绍实际部署过程。

#### DynamoDB

使用本地脚本控制 DynamoDB 表格的前提是提供访问、操作权限，因此登录 AWS 后，在服务中搜索 `IAM`。在`访问管理中`选择`用户`，再点击`添加用户`，你会看到如下页面，输入任意用户名，并勾选`编程访问`：

![AWS 创建IAM用户步骤1截图](./images/readme/aws-02.png)

点击`下一步：权限`进入步骤2页面，选择`直接附加现有策略`，并在`策略筛选`中搜索 `DynamoDB`，并勾选 `AmazonDynamoDBFullAcess`，给该用户访问、修改表格的权限。

![AWS 创建IAM用户步骤2截图](./images/readme/aws-03.png)

点击`下一步`，跳过步骤3和步骤4，进而看到添加用户成功的页面，将这个页面中提供的`访问密钥 ID` 和`私有访问密钥`记录下来。

![](./images/readme/aws-04.png)

进入项目目录 `bot-farmer-AWS/DynamoDB/` 中，找到 `aws-profile.json` 文件，修改其内容：

```json
{
    "IAM access key": "记录下来的访问密钥 ID",
    "IAM secret key": "记录下来的私有访问密钥",
    "region": "你希望表格存储的区域，如：us-west-1",
    "table": "创建出来表格的名字，避免与账户中所选区域内的表格重名，会造成数据丢失"
}
```

本项目提供了 `pipenv` 的环境配置文件，打开命令行工具，*进入项目目录 `bot-farmer-AWS/DynamoDB/`*，运行以下命令安装 Python 虚拟环境：

```console
$ pipenv install
```

如果不想创建 Python 虚拟环境，也可以运行以下命令直接安装 Python 依赖库：

```console
$ pip3 install boto3
```

打开命令行工具，*进入项目目录 `bot-farmer-AWS/DynamoDB/`*。如果之前安装了 Python 虚拟环境，执行以下命令将其打开：

```console
$ pipenv shell
```

目录中的 `table_data.py` 脚本必须传递正确的参数才可以运行，其支持三种操作：

1. `upload`：将目录里 `cheat_sheet.json` 文件中的数据上传到云端表格中，如果表格不存在则自动创建空表。执行命令如下：

    ```console
    $ python table_data.py upload
    ```

    将 `cheat_sheet.json` 文件数据（可能为空）上传到非空的云端表格中这个操作存在数据冲突、丢失等风险，因此会被脚本拒绝，如果执意做此操作，需要在命令后附加参数 `-f`。

2. `download`：将云端表格中的数据下载至目录里 `cheat_sheet.json` 文件中，如果文件不存在则自动创建空文件。执行命令如下：

    ```console
    $ python table_data.py download
    ```

    将云端表格中数据（可能为空）下载至非空的 `cheat_sheet.json` 文件中这个操作存在数据冲突、丢失等风险，因此会被脚本拒绝，如果执意做此操作，需要在命令后附加参数 `-f`。

3. `merge`：将目录里 `cheat_sheet.json` 文件中的数据与云端表格中的数据合并，并同步更新文件和表格。执行命令如下：

    ```console
    $ python table_data.py merge
    ```

    不管 `cheat_sheet.json` 文件中和云端表格中是否有数据，该操作都不会造成数据冲突、丢失，因此无需在命令后附加参数 `-f`，即使加上也会被脚本忽略。

如果使用 Python 虚拟环境运行的脚本，关闭命令行工具窗口或执行以下命令退出虚拟环境：

```console
$ exit
```
-----

