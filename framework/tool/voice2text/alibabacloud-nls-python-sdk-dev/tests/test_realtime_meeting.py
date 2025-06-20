import time
import threading
import sys
import nls

class TestRealtimeMeeting:
    def __init__(self, tid, test_file, url):
        self.__th = threading.Thread(target=self.__test_run)
        self.__id = tid
        self.__test_file = test_file
        self.__url = url

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
        print("on_error message=>{} args=>{}".format(message, args))

    def test_on_close(self, *args):
        print("on_close: args=>{}".format(args))

    def test_on_result_chg(self, message, *args):
        print("test_on_chg:{}".format(message))

    def test_on_result_translated(self, message, *args):
        print("test_on_translated:{}".format(message))

    def test_on_completed(self, message, *args):
        print("on_completed:args=>{} message=>{}".format(args, message))


    def __test_run(self):
        print("thread:{} start..".format(self.__id))
        rm = nls.NlsRealtimeMeeting(
                    url=self.__url,
                    on_sentence_begin=self.test_on_sentence_begin,
                    on_sentence_end=self.test_on_sentence_end,
                    on_start=self.test_on_start,
                    on_result_changed=self.test_on_result_chg,
                    on_result_translated=self.test_on_result_translated,
                    on_completed=self.test_on_completed,
                    on_error=self.test_on_error,
                    on_close=self.test_on_close,
                    callback_args=[self.__id]
                )

        print("{}: session start".format(self.__id))
        r = rm.start()

        self.__slices = zip(*(iter(self.__data),) * 640)
        for i in self.__slices:
            rm.send_audio(bytes(i))
            time.sleep(0.01)

        time.sleep(1)

        r = rm.stop()
        print("{}: rm stopped:{}".format(self.__id, r))
        time.sleep(5)

def multiruntest(num=1):
    for i in range(0, num):
        name = "thread" + str(i)
        t = TestRealtimeMeeting(name, "tests/test1.pcm", "wss://tingwu-realtime-cn-hangzhou-pre.aliyuncs.com/api/ws/v1?")
        t.start()

nls.enableTrace(True)
multiruntest(1)


