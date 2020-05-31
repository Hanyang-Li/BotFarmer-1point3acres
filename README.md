# BotFarmer-1point3acres

BotFarmer 是一亩三分地论坛每日签到、答题赚取积分的自动脚本。项目分为本地命令行交互、AWS 云端部署两个版本。

**本项目仅用于学习交流，如有侵犯论坛利益，请联系我删除仓库！**

---

## 环境要求

* 开发环境：macOS Catalina 10.15.5
* 测试环境：macOS Catalina 10.15.5
* Python 版本：3.7.6
* python 依赖库：requests, Pillow, pytesseract, boto3
* 软件依赖：tesseract-ocr 4.0.0+, docker

---

## 使用说明

分别介绍本地命令行版本环境的安装、脚本运行，AWS 云端部署版的搭建，以及tesseract模型的训练。

===

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

**进入项目目录 `train-tesseract/`**，运行以下命令导入模型（请根据刚才的输出更改后边目录地址）：

```console
$ cp verify-codes.traineddata /usr/local/Cellar/tesseract/4.1.1/share/tessdata/
```

对于 Windows 平台用户，请访问 [https://digi.bib.uni-mannheim.de/tesseract/](https://digi.bib.uni-mannheim.de/tesseract/ "Tesseract Versions") 下载 tesseract 4.0.0 之后版本的安装包，运行安装包，根据提示将软件安装在本地。

在安装目录（默认为 `C:\Program Files (x86)\Tesseract-OCR`）中找到 `tessdata` 文件夹，将本项目目录 `train-tesseract/` 中的 `verify-codes.traineddata` 文件复制到该文件夹中，完成模型的导入。

#### 安装 Python 依赖库

本项目提供了 `pipenv` 的环境配置文件，打开命令行工具，**进入项目目录 `bot-farmer-local`**，运行以下命令安装 Python 虚拟环境：

```console
$ pipenv install
```

如果不想创建 Python 虚拟环境，也可以运行以下命令直接安装 Python 依赖库：

```console
$ pip3 install requests Pillow pytesseract
```

#### 修改配置文件


