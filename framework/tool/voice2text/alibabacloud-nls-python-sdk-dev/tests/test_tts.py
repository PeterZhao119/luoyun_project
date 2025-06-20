import time
import threading
import sys

import nls
from tests.test_utils import (TEST_ACCESS_TOKEN, TEST_ACCESS_APPKEY)


TEXT='大壮正想去摘取花瓣，谁知阿丽和阿强突然内讧，阿丽拿去手枪向树干边的阿强射击，两声枪响，阿强直接倒入水中'

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
                    token=TEST_ACCESS_TOKEN,
                    appkey=TEST_ACCESS_APPKEY,
                    long_tts=False,
                    on_metainfo=self.test_on_metainfo,
                    on_data=self.test_on_data,
                    on_completed=self.test_on_completed,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    callback_args=[self.__id]
                )

        print("{}: session start".format(self.__id))
        r = tts.start(self.__text, voice="ailun", ex={'enable_subtitle':True})
        print("{}: tts done with result:{}".format(self.__id, r))

def multiruntest(num=500):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestTts(name, "tests/test_tts.pcm")
        t.start(TEXT)

nls.enableTrace(True)
multiruntest(1)


