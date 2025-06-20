# Copyright (c) Alibaba, Inc. and its affiliates.

import logging
import uuid
import json
import threading
from enum import IntEnum

from nls.core import NlsCore
from . import logging
from .exception import StartTimeoutException, WrongStateException, InvalidParameter

__STREAM_INPUT_TTS_NAMESPACE__ = "FlowingSpeechSynthesizer"

__STREAM_INPUT_TTS_REQUEST_CMD__ = {
    "start": "StartSynthesis",
    "send": "RunSynthesis",
    "stop": "StopSynthesis",
}
__STREAM_INPUT_TTS_REQUEST_NAME__ = {
    "started": "SynthesisStarted",
    "sentence_begin": "SentenceBegin",
    "sentence_synthesis": "SentenceSynthesis",
    "sentence_end": "SentenceEnd",
    "completed": "SynthesisCompleted",
    "task_failed": "TaskFailed",
}

__URL__ = "wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"

__all__ = ["NlsStreamInputTtsSynthesizer"]


class NlsStreamInputTtsRequest:
    def __init__(self, task_id, session_id, appkey):
        self.task_id = task_id
        self.appkey = appkey
        self.session_id = session_id

    def getStartCMD(self, voice, format, sample_rate, volumn, speech_rate, pitch_rate, ex):
        self.voice = voice
        self.format = format
        self.sample_rate = sample_rate
        self.volumn = volumn
        self.speech_rate = speech_rate
        self.pitch_rate = pitch_rate
        cmd = {
            "header": {
                "message_id": uuid.uuid4().hex,
                "task_id": self.task_id,
                "name": __STREAM_INPUT_TTS_REQUEST_CMD__["start"],
                "namespace": __STREAM_INPUT_TTS_NAMESPACE__,
                "appkey": self.appkey,
            },
            "payload": {
                "session_id": self.session_id,
                "voice": self.voice,
                "format": self.format,
                "sample_rate": self.sample_rate,
                "volumn": self.volumn,
                "speech_rate": self.speech_rate,
                "pitch_rate": self.pitch_rate,
            },
        }
        if ex:
            cmd["payload"].update(ex)        
        return json.dumps(cmd)

    def getSendCMD(self, text):
        cmd = {
            "header": {
                "message_id": uuid.uuid4().hex,
                "task_id": self.task_id,
                "name": __STREAM_INPUT_TTS_REQUEST_CMD__["send"],
                "namespace": __STREAM_INPUT_TTS_NAMESPACE__,
                "appkey": self.appkey,
            },
            "payload": {"text": text},
        }
        return json.dumps(cmd)

    def getStopCMD(self):
        cmd = {
            "header": {
                "message_id": uuid.uuid4().hex,
                "task_id": self.task_id,
                "name": __STREAM_INPUT_TTS_REQUEST_CMD__["stop"],
                "namespace": __STREAM_INPUT_TTS_NAMESPACE__,
                "appkey": self.appkey,
            },
        }
        return json.dumps(cmd)


class NlsStreamInputTtsStatus(IntEnum):
    Begin = 1
    Start = 2
    Started = 3
    WaitingComplete = 3
    Completed = 4
    Failed = 5
    Closed = 6

class ThreadSafeStatus:
    def __init__(self, state: NlsStreamInputTtsStatus):
        self._state = state
        self._lock = threading.Lock()
    
    def get(self) -> NlsStreamInputTtsStatus:
        with self._lock:
            return self._state
    
    def set(self, state: NlsStreamInputTtsStatus):
        with self._lock:
            self._state = state


class NlsStreamInputTtsSynthesizer:
    """
    Api for text-to-speech
    """

    def __init__(
        self,
        url=__URL__,
        token=None,
        appkey=None,
        session_id=None,
        on_data=None,
        on_sentence_begin=None,
        on_sentence_synthesis=None,
        on_sentence_end=None,
        on_completed=None,
        on_error=None,
        on_close=None,
        callback_args=[],
    ):
        """
        NlsSpeechSynthesizer initialization

        Parameters:
        -----------
        url: str
            websocket url.
        akid: str
            access id from aliyun. if you provide a token, ignore this argument.
        appkey: str
            appkey from aliyun
        session_id: str
            32-character string, if empty, sdk will generate a random string.
        on_data: function
            Callback object which is called when partial synthesis result arrived
            arrived.
            on_result_changed has two arguments.
            The 1st argument is binary data corresponding to aformat in start
            method.
            The 2nd argument is *args which is callback_args.
        on_sentence_begin: function
            Callback object which is called when detected sentence start.
            on_start has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_sentence_synthesis: function
            Callback object which is called when detected sentence synthesis.
            The incremental timestamp is returned within payload.
            on_start has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_sentence_end: function
            Callback object which is called when detected sentence end.
            The timestamp of the whole sentence is returned within payload.
            on_start has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_completed: function
            Callback object which is called when recognition is completed.
            on_completed has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_error: function
            Callback object which is called when any error occurs.
            on_error has two arguments.
            The 1st argument is message which is a json format string.
            The 2nd argument is *args which is callback_args.
        on_close: function
            Callback object which is called when connection closed.
            on_close has one arguments.
            The 1st argument is *args which is callback_args.
        callback_args: list
            callback_args will return in callbacks above for *args.
        """
        if not token or not appkey:
            raise InvalidParameter("Must provide token and appkey")
        self.__response_handler__ = {
            __STREAM_INPUT_TTS_REQUEST_NAME__["started"]: self.__synthesis_started,
            __STREAM_INPUT_TTS_REQUEST_NAME__["sentence_begin"]: self.__sentence_begin,
            __STREAM_INPUT_TTS_REQUEST_NAME__[
                "sentence_synthesis"
            ]: self.__sentence_synthesis,
            __STREAM_INPUT_TTS_REQUEST_NAME__["sentence_end"]: self.__sentence_end,
            __STREAM_INPUT_TTS_REQUEST_NAME__["completed"]: self.__synthesis_completed,
            __STREAM_INPUT_TTS_REQUEST_NAME__["task_failed"]: self.__task_failed,
        }
        self.__callback_args = callback_args
        self.__url = url
        self.__appkey = appkey
        self.__token = token
        self.__session_id = session_id
        self.start_sended = threading.Event()
        self.started_event = threading.Event()
        self.complete_event = threading.Event()
        self.__on_sentence_begin = on_sentence_begin
        self.__on_sentence_synthesis = on_sentence_synthesis
        self.__on_sentence_end = on_sentence_end
        self.__on_data = on_data
        self.__on_completed = on_completed
        self.__on_error = on_error
        self.__on_close = on_close
        self.__allow_aformat = ("pcm", "wav", "mp3")
        self.__allow_sample_rate = (
            8000,
            11025,
            16000,
            22050,
            24000,
            32000,
            44100,
            48000,
        )
        self.state = ThreadSafeStatus(NlsStreamInputTtsStatus.Begin)     
        if not self.__session_id:
            self.__session_id = uuid.uuid4().hex   
        self.request = NlsStreamInputTtsRequest(
            uuid.uuid4().hex, self.__session_id, self.__appkey
        )

    def __handle_message(self, message):
        logging.debug("__handle_message")
        try:
            __result = json.loads(message)
            if __result["header"]["name"] in self.__response_handler__:
                __handler = self.__response_handler__[__result["header"]["name"]]
                __handler(message)
            else:
                logging.error("cannot handle cmd{}".format(__result["header"]["name"]))
                return
        except json.JSONDecodeError:
            logging.error("cannot parse message:{}".format(message))
            return

    def __syn_core_on_open(self):
        logging.debug("__syn_core_on_open")
        self.start_sended.set()

    def __syn_core_on_data(self, data, opcode, flag):
        logging.debug("__syn_core_on_data")
        if self.__on_data:
            self.__on_data(data, *self.__callback_args)

    def __syn_core_on_msg(self, msg, *args):
        logging.debug("__syn_core_on_msg:msg={} args={}".format(msg, args))
        self.__handle_message(msg)

    def __syn_core_on_error(self, msg, *args):
        logging.debug("__sr_core_on_error:msg={} args={}".format(msg, args))

    def __syn_core_on_close(self):
        logging.debug("__sr_core_on_close")
        if self.__on_close:
            self.__on_close(*self.__callback_args)
        self.state.set(NlsStreamInputTtsStatus.Closed)
        self.start_sended.set()
        self.started_event.set()
        self.complete_event.set()

    def __synthesis_started(self, message):
        logging.debug("__synthesis_started")
        self.started_event.set()

    def __sentence_begin(self, message):
        logging.debug("__sentence_begin")
        if self.__on_sentence_begin:
            self.__on_sentence_begin(message, *self.__callback_args)

    def __sentence_synthesis(self, message):
        logging.debug("__sentence_synthesis")
        if self.__on_sentence_synthesis:
            self.__on_sentence_synthesis(message, *self.__callback_args)

    def __sentence_end(self, message):
        logging.debug("__sentence_end")
        if self.__on_sentence_end:
            self.__on_sentence_end(message, *self.__callback_args)

    def __synthesis_completed(self, message):
        logging.debug("__synthesis_completed")
        if self.__on_completed:
            self.__on_completed(message, *self.__callback_args)
        self.__nls.shutdown()
        logging.debug("__synthesis_completed shutdown done")
        self.complete_event.set()


    def __task_failed(self, message):
        logging.debug("__task_failed")
        self.start_sended.set()
        self.started_event.set()
        self.complete_event.set()
        if self.__on_error:
            self.__on_error(message, *self.__callback_args)
        self.state.set(NlsStreamInputTtsStatus.Failed)

    def startStreamInputTts(
        self,
        voice="longxiaochun",
        aformat="pcm",
        sample_rate=24000,
        volume=50,
        speech_rate=0,
        pitch_rate=0,
        ex:dict=None,
    ):
        """
        Synthesis start

        Parameters:
        -----------
        voice: str
            voice for text-to-speech, default is xiaoyun
        aformat: str
            audio binary format, support: 'pcm', 'wav', 'mp3', default is 'pcm'
        sample_rate: int
            audio sample rate, default is 24000, support:8000, 11025, 16000, 22050,
            24000, 32000, 44100, 48000
        volume: int
            audio volume, from 0~100, default is 50
        speech_rate: int
            speech rate from -500~500, default is 0
        pitch_rate: int
            pitch for voice from -500~500, default is 0
        ex: dict
            dict which will merge into 'payload' field in request
        """

        self.__nls = NlsCore(
            url=self.__url,
            token=self.__token,
            on_open=self.__syn_core_on_open,
            on_message=self.__syn_core_on_msg,
            on_data=self.__syn_core_on_data,
            on_close=self.__syn_core_on_close,
            on_error=self.__syn_core_on_error,
            callback_args=[],
        )

        if aformat not in self.__allow_aformat:
            raise InvalidParameter("format {} not support".format(aformat))
        if sample_rate not in self.__allow_sample_rate:
            raise InvalidParameter("samplerate {} not support".format(sample_rate))
        if volume < 0 or volume > 100:
            raise InvalidParameter("volume {} not support".format(volume))
        if speech_rate < -500 or speech_rate > 500:
            raise InvalidParameter("speech_rate {} not support".format(speech_rate))
        if pitch_rate < -500 or pitch_rate > 500:
            raise InvalidParameter("pitch rate {} not support".format(pitch_rate))

        request = self.request.getStartCMD(
            voice, aformat, sample_rate, volume, speech_rate, pitch_rate, ex
        )
        
        last_state = self.state.get()
        if last_state != NlsStreamInputTtsStatus.Begin:
            logging.debug("start with wrong state {}".format(last_state))
            self.state.set(NlsStreamInputTtsStatus.Failed)
            raise WrongStateException("start with wrong state {}".format(last_state))

        logging.debug("start with request: {}".format(request))
        self.__nls.start(request, ping_interval=0, ping_timeout=None)
        self.state.set(NlsStreamInputTtsStatus.Start)
        if not self.start_sended.wait(timeout=10):
            logging.debug("syn start timeout")
            raise StartTimeoutException(f"Waiting Connection before Start over 10s")

        if last_state != NlsStreamInputTtsStatus.Begin:
            logging.debug("start with wrong state {}".format(last_state))
            self.state.set(NlsStreamInputTtsStatus.Failed)
            raise WrongStateException("start with wrong state {}".format(last_state))

        if not self.started_event.wait(timeout=10):
            logging.debug("syn started timeout")
            self.state.set(NlsStreamInputTtsStatus.Failed)
            raise StartTimeoutException(f"Waiting Started over 10s")
        self.state.set(NlsStreamInputTtsStatus.Started)

    def sendStreamInputTts(self, text):
        """
        send text to server

        Parameters:
        -----------
        text: str
            utf-8 text
        """
        last_state = self.state.get()
        if last_state != NlsStreamInputTtsStatus.Started:
            logging.debug("send with wrong state {}".format(last_state))
            self.state.set(NlsStreamInputTtsStatus.Failed)
            raise WrongStateException("send with wrong state {}".format(last_state))

        request = self.request.getSendCMD(text)
        logging.debug("send with request: {}".format(request))
        self.__nls.send(request, None)

    def stopStreamInputTts(self):
        """
        Synthesis end
        """

        last_state = self.state.get()
        if last_state != NlsStreamInputTtsStatus.Started:
            logging.debug("send with wrong state {}".format(last_state))
            self.state.set(NlsStreamInputTtsStatus.Failed)
            raise WrongStateException("stop with wrong state {}".format(last_state))


        request = self.request.getStopCMD()
        logging.debug("stop with request: {}".format(request))
        self.__nls.send(request, None)
        self.state.set(NlsStreamInputTtsStatus.WaitingComplete)
        self.complete_event.wait()
        self.state.set(NlsStreamInputTtsStatus.Completed)
        self.shutdown()

    def shutdown(self):
        """
        Shutdown connection immediately
        """

        self.__nls.shutdown()
