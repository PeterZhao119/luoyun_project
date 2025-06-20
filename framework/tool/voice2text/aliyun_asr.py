#! /usr/bin/env python
# coding=utf-8
import os
import time
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
import threading
import nls
import pysilk

from conf.config import CONF

def get_token():
    # 创建AcsClient实例
    client = AcsClient(
        os.getenv('ALIYUN_AK_ID'),
        os.getenv('ALIYUN_AK_SECRET_ASR'),
        "cn-shanghai"
    )

    # 创建request，并设置参数。
    request = CommonRequest()
    request.set_method('POST')
    request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
    request.set_version('2019-02-28')
    request.set_action_name('CreateToken')

    try : 
        response = client.do_action_with_exception(request)
        print(response)

        jss = json.loads(response)
        if 'Token' in jss and 'Id' in jss['Token']:
            token = jss['Token']['Id']
            expireTime = jss['Token']['ExpireTime']
            print("token = " + token)
            print("expireTime = " + str(expireTime))
        
        return token
    
    except Exception as e:
        print(e)

        return None

URL=CONF["aliyun_asr"]["URL"]
# TOKEN=get_token()  #参考https://help.aliyun.com/document_detail/450255.html获取token
APPKEY=CONF["aliyun_asr"]["APPKEY"]   #获取Appkey请前往控制台：https://nls-portal.console.aliyun.com/applist
# nls.enableTrace(True)

#以下代码会根据音频文件内容反复进行实时语音识别（文件转写）
class TestSt:
    def __init__(self, tid, test_file, token):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
        self.single_result = None
        self.TOKEN = token
   
    def loadfile(self, filename):
        with open(filename, "rb") as f:
            self.__data = f.read()
    
    def start(self):
        self.loadfile(self.__test_file)
        self.__th.start()

    def test_on_sentence_begin(self, message, *args):
        print("test_on_sentence_begin:{}".format(message))

    def test_on_sentence_end(self, message, *args):
        self.single_result = json.loads(message)["payload"]["result"]
        # print(self.single_result)
        print("test_on_sentence_end:{}".format(message))
        with open(self.__test_file + ".result", "w") as f:
            f.write(self.single_result)

    def test_on_start(self, message, *args):
        print("test_on_start:{}".format(message))

    def test_on_error(self, message, *args):
        print("on_error args=>{}".format(args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))

    def test_on_result_chg(self, message, *args):
        # print("test_on_chg:{}".format(message))
        pass

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))

    def __test_run(self):
        if self.TOKEN is None:
            self.TOKEN = get_token()
        print("thread:{} start..".format(self.__id))
        sr = nls.NlsSpeechTranscriber(
                    url=URL,
                    token=self.TOKEN,
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
        print("{}: session start".format(self.__id))

        for i in range(5):
            r = sr.start(aformat="pcm",
                    enable_intermediate_result=True,
                    enable_punctuation_prediction=True,
                    enable_inverse_text_normalization=True)

            self.__slices = zip(*(iter(self.__data),) * 640)
            for i in self.__slices:
                sr.send_audio(bytes(i))
                time.sleep(0.01)

            # sr.ctrl(ex={"test":"tttt"})
            time.sleep(1)
            if self.single_result is not None:
                r = sr.stop()
                print("{}: sr stopped:{}".format(self.__id, r))
                break

            r = sr.stop()
            print("{}: sr stopped:{}".format(self.__id, r))

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestSt(name, "tests/test1.pcm")
        t.start()

def singleruntest(file_path):
    # token = get_token()
    t = TestSt("test", file_path, None)
    t.start()

def silk_to_wav(file_path, sr=16000):
    new_file_path = f"{file_path}.wav"

    with open(new_file_path, "wb") as new_f:
        new_f.write(pysilk.decode_file(file_path, to_wav=True, sample_rate=16000))

    return new_file_path

import numpy as np
def wav2pcm(wavfile, pcmfile, data_type=np.int16):
    f = open(wavfile, "rb")
    f.seek(0)
    f.read(44)
    data = np.fromfile(f, dtype=data_type)
    data.tofile(pcmfile)

import pilk
def silk_to_pcm(file_path, sr=16000):
    duration = pilk.decode(file_path, file_path+".pcm", sr)
    return file_path+".pcm"

def voice_to_text(file_path):
    pcm_file = silk_to_pcm(file_path)
    singleruntest(pcm_file)

    for i in range(100):
        time.sleep(0.1)
        if os.path.isfile(file_path+".pcm.result"):
            with open(file_path+".pcm.result") as f:
                result = f.read()
                return result
    return None

if __name__ == "__main__":
    r = voice_to_text("luoyun/temp/1748503671911.silk")
    print("result:" + str(r))
# print("result:" + str(r))
# r = voice_to_text("yanhua_core/tool/multimodal/temp/message-4985866711614652198-audio.sil")
# print("result:" + str(r))