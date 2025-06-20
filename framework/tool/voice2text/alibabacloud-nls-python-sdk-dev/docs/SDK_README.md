# NLS Python SDK说明



本文介绍如何使用阿里云智能语音服务提供的Python SDK，包括SDK的安装方法及SDK代码示例。

> 说明
>
> * 当前版本：0.0.1，支持python3



## 安装

解压SDK压缩包后进入SDK根目录使用如下命令安装SDK依赖：

> python -m pip install -r requirements.txt

依赖安装完成后使用如下命令安装SDK：

> python -m pip install .

> 注意：
>
> 上述命令需要在SDK根目录中执行

安装完成后通过以下代码可以导入SDK：

> #!/bin/python
>
> import nls



## 多线程和多并发

根据Python官方文档：

> **CPython implementation detail:** 在 CPython 中，由于存在 [全局解释器锁](https://docs.python.org/zh-cn/3/glossary.html#term-global-interpreter-lock)，同一时刻只有一个线程可以执行 Python 代码（虽然某些性能导向的库可能会去除此限制）。 如果你想让你的应用更好地利用多核心计算机的计算资源，推荐你使用 [`multiprocessing`](https://docs.python.org/zh-cn/3/library/multiprocessing.html#module-multiprocessing) 或 [`concurrent.futures.ProcessPoolExecutor`](https://docs.python.org/zh-cn/3/library/concurrent.futures.html#concurrent.futures.ProcessPoolExecutor)。 但是，如果你想要同时运行多个 I/O 密集型任务，则多线程仍然是一个合适的模型。

如果单解释器有太多线程，那么线程间切换的消耗会非常客观，有可能会导致SDK出现错误，不建议超过200线程的使用，如果有必要使用multiprocessing技术或者手动使用脚本创建多个解释器



## 一句话识别

一句话识别对应的类为NlsSpeechRecognizer，其核心方法如下：

### 1. 初始化（\_\_init\_\_)

参数说明:

| 参数              | 类型     | 参数说明                                                     |
| ----------------- | -------- | ------------------------------------------------------------ |
| url               | str      | 网关websocket url，默认为wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1 |
| akid              | str      | 账号access id，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| aksecret          | str      | 账号access secret key，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| token             | str      | 访问token，参考开发指南—获取Token及获取Token协议说明相关内容 |
| on_start          | function | 当一句话识别就绪时的回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_result_changed | function | 当一句话识别返回中间结果时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_completed      | function | 当一句话识别返回最终识别结果时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_error          | function | 当SDK或云端出现错误时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_close          | function | 当和云端连接断开时回调，回调参数有一个——用户自定义参数，见后续callback_args参数说明 |
| callback_args     | list     | 用户自定义参数列表，里面的内容会pack成list传递给各个回调的最后一个参数 |

返回值：

无

### 2. start

> 同步开始一句话识别，该方法会阻塞当前线程直到一句话识别就绪（on_start回调返回）

参数说明：

| 参数                              | 类型 | 参数说明                                                     |
| --------------------------------- | ---- | ------------------------------------------------------------ |
| aformat                           | str  | 要识别音频格式，支持pcm，opus，opu，默认pcm，**SDK不会自动将pcm编码成opus或opu，如果需要使用opus或opu，需要用户自行编码** |
| sample_rate                       | int  | 识别音频采样率，默认16000                                    |
| ch                                | int  | 音频通道数，默认为1，不需要提供                              |
| enable_intermediate_result        | bool | 是否返回中间结果，默认False                                  |
| enable_punctuation_prediction    | bool | 是否进行识别结果标点预测，默认False                          |
| enable_inverse_text_normalization | bool | 是否进行ITN，默认False                                       |
| timeout                           | int  | 阻塞超时，默认10秒                                           |
| ping_interval                     | int  | ping包发送间隔，默认8，不需要可以设置为0或None               |
| ping_timeout                      | int  | 是否检查pong包超时，默认为None，None为不检查pong包超时       |
| ex                                | dict | 用户提供的额外参数，该字典内容会以key:value形式合并进请求的payload段中，具体可用参数见一句话语音识别接口说明 |

返回值：

bool类型，False为失败，True为成功

### 3. stop

> 停止一句话识别，并同步等待on_completed回调结束

参数说明：

| 参数    | 类型 | 参数说明           |
| ------- | ---- | ------------------ |
| timeout | int  | 阻塞超时，默认10秒 |

返回值：

bool类型，False为失败，True为成功

### 4. shutdown

> 强行关闭当前请求，重复调用无副作用

参数说明：

无

返回值：

无

### 5. send_audio

> 发送二进制音频数据，发送数据的格式需要和start中的aformat对应

参数说明：

| 参数     | 类型  | 参数说明                                                     |
| -------- | ----- | ------------------------------------------------------------ |
| pcm_data | bytes | 要发送的二进制音频数据，格式需要和上一次start中的aformat相对应。**SDK不会自动将pcm编码成opus或opu，如果需要使用opus或opu，需要用户自行编码** |

返回值：

bool类型，False为失败，True为成功



### 代码示例：

```python
import time
import threading
import sys

import nls


URL="wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
AKID="Your AKID"
AKKEY="Your AKSECRET"
APPKEY="Your APPKEY"

#以下代码会根据音频文件内容反复进行一句话识别
class TestSr:
    def __init__(self, tid, test_file):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
   
    def loadfile(self, filename):
        with open(filename, "rb") as f:
            self.__data = f.read()
    
    def start(self):
        self.loadfile(self.__test_file)
        self.__th.start()

    def test_on_start(self, message, *args):
        print("test_on_start:{}".format(message))

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))

    def test_on_result_chg(self, message, *args):
        print("test_on_chg:{}".format(message))

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))


    def __test_run(self):
        print("thread:{} start..".format(self.__id))
        
        sr = nls.NlsSpeechRecognizer(
                    url=URL,
                    akid=AKID,
                    aksecret=AKKEY,
                    appkey=APPKEY,
                    on_start=self.test_on_start,
                    on_result_changed=self.test_on_result_chg,
                    on_completed=self.test_on_completed,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    callback_args=[self.__id]
                )
        while True:
            print("{}: session start".format(self.__id))
            r = sr.start(aformat="pcm", ex={"hello":123})
           
            self.__slices = zip(*(iter(self.__data),) * 640)
            for i in self.__slices:
                sr.send_audio(bytes(i))
                time.sleep(0.01)

            r = sr.stop()
            print("{}: sr stopped:{}".format(self.__id, r))
            time.sleep(1)

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestSr(name, "tests/test1.pcm")
        t.start()

nls.enableTrace(True)
multiruntest(1)



```



## 实时语音识别

实时语音识别对应的类为NlsSpeechTranscriber，其核心方法如下：

### 1. 初始化（\_\_init\_\_)

参数说明:

| 参数              | 类型     | 参数说明                                                     |
| ----------------- | -------- | ------------------------------------------------------------ |
| url               | str      | 网关websocket url，默认为wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1 |
| akid              | str      | 账号access id，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| aksecret          | str      | 账号access secret key，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| token             | str      | 访问token，参考开发指南—获取Token及获取Token协议说明相关内容 |
| on_start          | function | 当实时识别就绪时的回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_sentence_begin | function | 当实时识别一句话开始时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_sentence_end   | function | 当实时识别一句话结束时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_result_changed | function | 当实时识别返回中间结果时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_completed      | function | 当实时识别返回最终识别结果时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_error          | function | 当SDK或云端出现错误时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_close          | function | 当和云端连接断开时回调，回调参数有一个——用户自定义参数，见后续callback_args参数说明 |
| callback_args     | list     | 用户自定义参数列表，里面的内容会pack成list传递给各个回调的最后一个参数 |

返回值：

无

### 2. start

> 同步开始实时识别，该方法会阻塞当前线程直到实时识别就绪（on_start回调返回）

参数说明：

| 参数                              | 类型 | 参数说明                                                     |
| --------------------------------- | ---- | ------------------------------------------------------------ |
| aformat                           | str  | 要识别音频格式，支持pcm，opus，opu，默认pcm，**SDK不会自动将pcm编码成opus或opu，如果需要使用opus或opu，需要用户自行编码** |
| sample_rate                       | int  | 识别音频采样率，默认16000                                    |
| ch                                | int  | 音频通道数，默认为1，不需要提供                              |
| enable_intermediate_result        | bool | 是否返回中间结果，默认False                                  |
| enable_punctuation_prediction    | bool | 是否进行识别结果标点预测，默认False                          |
| enable_inverse_text_normalization | bool | 是否进行ITN，默认False                                       |
| timeout                           | int  | 阻塞超时，默认10秒                                           |
| ping_interval                     | int  | ping包发送间隔，默认8，不需要可以设置为0或None               |
| ping_timeout                      | int  | 是否检查pong包超时，默认为None，None为不检查pong包超时       |
| ex                                | dict | 用户提供的额外参数，该字典内容会以key:value形式合并进请求的payload段中，具体可用参数见实时语音识别接口说明 |

返回值：

bool类型，False为失败，True为成功

### 3. stop

> 停止实时识别，并同步等待on_completed回调结束

参数说明：

| 参数    | 类型 | 参数说明           |
| ------- | ---- | ------------------ |
| timeout | int  | 阻塞超时，默认10秒 |

返回值：

bool类型，False为失败，True为成功

### 4. shutdown

> 强行关闭当前请求，重复调用无副作用

参数说明：

无

返回值：

无

### 5. send_audio

> 发送二进制音频数据，发送数据的格式需要和start中的aformat对应

参数说明：

| 参数     | 类型  | 参数说明                                                     |
| -------- | ----- | ------------------------------------------------------------ |
| pcm_data | bytes | 要发送的二进制音频数据，格式需要和上一次start中的aformat相对应。**SDK不会自动将pcm编码成opus或opu，如果需要使用opus或opu，需要用户自行编码** |

返回值：

bool类型，False为失败，True为成功

### 6. ctrl

> 发送控制命令，先阅读实时语音识别接口说明

参数说明：

| 参数 | 类型 | 参数说明                                                     |
| ---- | ---- | ------------------------------------------------------------ |
| ex   | dict | 自定义控制命令，该字典内容会以key:value形式合并进请求的payload段中 |

返回值：

bool类型，False为失败，True为成功



### 代码示例

```python
import time
import threading
import sys

import nls


URL="wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
AKID="Your AKID"
AKKEY="Your AKSECRET"
APPKEY="Your APPKEY"

#以下代码会根据音频文件内容反复进行实时识别（文件转写）
class TestSt:
    def __init__(self, tid, test_file):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
   
    def loadfile(self, filename):
        with open(filename, "rb") as f:
            self.__data = f.read()
    
    def start(self):
        self.loadfile(self.__test_file)
        self.__th.start()

    def test_on_sentence_begin(self, message, *args):
        print("test_on_sentence_begin:{}".format(message))

    def test_on_sentence_end(self, message, *args):
        print("test_on_sentence_end:{}".format(message))

    def test_on_start(self, message, *args):
        print("test_on_start:{}".format(message))

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))

    def test_on_result_chg(self, message, *args):
        print("test_on_chg:{}".format(message))

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))


    def __test_run(self):
        print("thread:{} start..".format(self.__id))
        sr = nls.NlsSpeechTranscriber(
                    url=URL,
                    akid=AKID,
                    aksecret=AKKEY,
                    appkey=APPKEY,
                    on_sentence_begin=self.test_on_sentence_begin,
                    on_sentence_end=self.test_on_sentence_end,
                    on_start=self.test_on_start,
                    on_result_changed=self.test_on_result_chg,
                    on_completed=self.test_on_completed,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    callback_args=[self.__id]
                )
        while True:
            print("{}: session start".format(self.__id))
            r = sr.start(aformat="pcm",
                    enable_intermediate_result=True,
                    enable_punctuation_prediction=True,
                    enable_inverse_text_normalization=True)

            self.__slices = zip(*(iter(self.__data),) * 640)
            for i in self.__slices:
                sr.send_audio(bytes(i))
                time.sleep(0.01)

            sr.ctrl(ex={"test":"tttt"})
            time.sleep(1)

            r = sr.stop()
            print("{}: sr stopped:{}".format(self.__id, r))
            time.sleep(1)

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestSt(name, "tests/test1.pcm")
        t.start()

nls.enableTrace(True)
multiruntest(1)

```



## 语音合成

语音合成对应的类为NlsSpeechSynthesizer，其核心方法如下：

### 1. 初始化（\_\_init\_\_)

参数说明:

| 参数          | 类型     | 参数说明                                                     |
| ------------- | -------- | ------------------------------------------------------------ |
| url           | str      | 网关websocket url，默认为wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1 |
| akid          | str      | 账号access id，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| aksecret      | str      | 账号access secret key，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| token         | str      | 访问token，参考开发指南—获取Token及获取Token协议说明相关内容 |
| on_metainfo   | function | 如果start中通过ex参数传递enable_subtitle，则会返回对应字幕信息，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_data       | function | 当存在合成数据后回调，回调参数有两个，一个是对应start方法aformat的二进制音频数据，一个是用户自定义参数，见后续callback_args参数说明 |
| on_completed  | function | 当合成完毕时候回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_error      | function | 当SDK或云端出现错误时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_close      | function | 当和云端连接断开时回调，回调参数有一个——用户自定义参数，见后续callback_args参数说明 |
| callback_args | list     | 用户自定义参数列表，里面的内容会pack成list传递给各个回调的最后一个参数 |

返回值：

无

### 2. start

> 同步开始语音合成，如果wait_complete为True（默认）则会阻塞直到所有音频合成完毕（on_completed返回之后）返回，否则会立即返回

参数说明：

| 参数              | 类型 | 参数说明                                                     |
| ----------------- | ---- | ------------------------------------------------------------ |
| text              | str  | 要合成的文字                                                 |
| aformat           | str  | 合成出来音频的格式，默认为"pcm"                              |
| voice             | str  | 发音人，默认为”xiaoyun“                                      |
| sample_rate       | int  | 识别音频采样率，默认16000                                    |
| volume            | int  | 音量大小，0~100，默认为50                                    |
| speech_rate       | int  | 语速，-500~500，默认为0                                      |
| pitch_rate        | int  | 语调，-500~500，默认为0                                      |
| wait_complete     | bool | 是否阻塞到合成完成                                           |
| start_timeout     | int  | 和云端连接建立超时，默认10秒                                 |
| completed_timeout | int  | 从连接建立到合成完成超时，默认60秒                           |
| ping_interval                     | int  | ping包发送间隔，默认8，不需要可以设置为0或None               |
| ping_timeout                      | int  | 是否检查pong包超时，默认为None，None为不检查pong包超时       |
| ex                | dict | 用户提供的额外参数，该字典内容会以key:value形式合并进请求的payload段中，具体可用参数见实时语音识别接口说明 |

返回值：

bool类型，False为失败，True为成功

### 3. shutdown

> 强行关闭当前请求，重复调用无副作用

参数说明：

无

返回值：

无

### 代码示例：

```python
import time
import threading
import sys

import nls

URL="wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
AKID="Your AKID"
AKKEY="Your AKSECRET"
APPKEY="Your APPKEY"



TEXT='大壮正想去摘取花瓣，谁知阿丽和阿强突然内讧，阿丽拿去手枪向树干边的阿强射击，两声枪响，阿强直接倒入水中'

#以下代码会根据上述TEXT文本反复进行语音合成
class TestTts:
    def __init__(self, tid, test_file):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
   
    def start(self, text):
        self.__text = text
        self.__f = open(self.__test_file, "wb")
        self.__th.start()
    
    def test_on_metainfo(self, message, *args):
        print("on_metainfo message=>{}".format(message))  

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))
        try:
            self.__f.close()
        except Exception as e:
            print("close file failed since:", e)

    def test_on_data(self, data, *args):
        try:
            self.__f.write(data)
        except Exception as e:
            print("write data failed:", e)

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))


    def __test_run(self):
        print("thread:{} start..".format(self.__id))
        tts = nls.NlsSpeechSynthesizer(
                    url=URL,
                    akid=AKID,
                    aksecret=AKKEY,
                    appkey=APPKEY,
                    on_metainfo=self.test_on_metainfo,
                    on_data=self.test_on_data,
                    on_completed=self.test_on_completed,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    callback_args=[self.__id]
                )

        while True:
            print("{}: session start".format(self.__id))
            r = tts.start(self.__text, voice="ailun")
            print("{}: tts done with result:{}".format(self.__id, r))
            time.sleep(1)

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestTts(name, "tests/test_tts.pcm")
        t.start(TEXT)

nls.enableTrace(True)
multiruntest(1)

```



## 高级用法——使用CommonProto实现任意接口

nls包下面的NlsCommonProto对象可以用来实现智能语音交互的任意接口，其核心方法如下：

### 1. 初始化（\_\_init\_\_)

参数说明:

| 参数          | 类型     | 参数说明                                                     |
| ------------- | -------- | ------------------------------------------------------------ |
| url           | str      | 网关websocket url，默认为wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1 |
| akid          | str      | 账号access id，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| aksecret      | str      | 账号access secret key，默认为None，如果需要获取token，则需要提供，如果已有token，则不需要提供 |
| token         | str      | 访问token，参考开发指南—获取Token及获取Token协议说明相关内容 |
| on_open       | function | 当和云端建连完成后回调，回调参数有一个——用户自定义参数，见后续callback_args参数说明 |
| on_error      | function | 当SDK或云端出现错误时回调，回调参数有两个，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| on_close      | function | 当和云端连接断开时回调，回调参数有一个——用户自定义参数，见后续callback_args参数说明 |
| on_data       | function | 当云端返回二进制数据时回调，回调参数有两个，一个是二进制数据，一个是用户自定义参数，见后续callback_args参数说明 |
| user_callback | dict     | 用户自定义回调字典，key为str类型，value为function类型，当SDK收到云端应答后，会根据应答内部header字段下面name字段来索引该字典，如果对应item存在则会回调对应function。该回调包括两个参数，一个是json形式的字符串，一个是用户自定义参数，见后续callback_args参数说明 |
| callback_args | list     | 用户自定义参数列表，里面的内容会pack成list传递给各个回调的最后一个参数 |

返回值：

无

### 2. start

> **异步**和云端建连并发起一次请求

参数说明：

| 参数    | 类型 | 参数说明                                 |
| ------- | ---- | ---------------------------------------- |
| name    | str  | 对应header字段中的name，用于指明请求类型 |
| payload | dict | 请求中的payload，默认为{}                |
| context | dict | 请求中的context，默认为{}                |
| ping_interval                     | int  | ping包发送间隔，默认8，不需要可以设置为0或None               |
| ping_timeout                      | int  | 是否检查pong包超时，默认为None，None为不检查pong包超时       |

返回值：

bool类型，False为失败，True为成功

### 3. shutdown

> 强行关闭当前请求，重复调用无副作用

参数说明：

无

返回值：

无

### 4. send_text

> 发送文本请求

参数说明：

| 参数    | 类型 | 参数说明                                 |
| ------- | ---- | ---------------------------------------- |
| name    | str  | 对应header字段中的name，用于指明请求类型 |
| payload | dict | 请求中的payload，默认为{}                |
| context | dict | 请求中的context，默认为{}                |

返回值：

bool类型，False为失败，True为成功

### 5. send_binary

> 发送二进制数据

参数说明：

| 参数     | 类型  | 参数说明           |
| -------- | ----- | ------------------ |
| pcm_data | bytes | 要发送的二进频数据 |

返回值：

bool类型，False为失败，True为成功



### 示例代码：

```python
import time
import threading
import sys

import nls

URL="wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"
AKID="Your AKID"
AKKEY="Your AKSECRET"
APPKEY="Your APPKEY"

#以下代码会通过文件反复进行一句话识别
class TestSrCommon:
    def __init__(self, tid, test_file):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
   
    def loadfile(self, filename):
        with open(filename, "rb") as f:
            self.__data = f.read()
    
    def start(self):
        self.loadfile(self.__test_file)
        self.__th.start()

    def test_on_open(self, *args):
        print("test_on_start")

    def test_on_start(self, message, *args):
        print("test_on_start:{}".format(message))

    def test_on_data(self, data, *args):
        pass

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))

    def test_on_result_chg(self, message, *args):
        print("test_on_chg:{}".format(message))

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))
        self.__sr.shutdown() 

    def __test_run(self):
        print("thread:{} start..".format(self.__id))
        callbacks = {
                "RecognitionStarted":self.test_on_start,
                "RecognitionResultChanged":self.test_on_result_chg,
                "RecognitionCompleted":self.test_on_completed
                }
        self.__sr = nls.NlsCommonProto(
                    url=URL,
                    akid=AKID,
                    aksecret=AKKEY,
                    appkey=APPKEY,
                    namespace="SpeechRecognizer",
                    on_open=self.test_on_open,
                    on_data=self.test_on_data,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    user_callback=callbacks,
                    callback_args=[self.__id]
                )

        while True:
            print("{}: session start".format(self.__id))
            r = self.__sr.start(name="StartRecognition",
                    payload={
                        "format":"pcm",
                        "sample_rate":16000
                        }
                    )
            if not r:
                print("start failed")
                break
            time.sleep(1)
           
            self.__slices = zip(*(iter(self.__data),) * 640)
            for i in self.__slices:
                self.__sr.send_binary(bytes(i))
                time.sleep(0.01)

            self.__sr.send_text(name="StopRecognition") 
            time.sleep(1)

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestSrCommon(name, "tests/test1.pcm")
        t.start()

nls.enableTrace(True)
multiruntest(1)

```

