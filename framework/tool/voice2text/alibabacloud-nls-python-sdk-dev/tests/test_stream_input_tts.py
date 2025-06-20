import nls
import pyaudio
import time
from tests.test_utils import TEST_ACCESS_TOKEN, TEST_ACCESS_APPKEY


test_text = [
    "流式文本语音合成SDK，",
    "可以将输入的文本",
    "合成为语音二进制数据，",
    "相比于非流式语音合成，",
    "流式合成的优势在于实时性",
    "更强。用户在输入文本的同时",
    "可以听到接近同步的语音输出，",
    "极大地提升了交互体验，",
    "减少了用户等待时间。",
    "适用于调用大规模",
    "语言模型（LLM），以",
    "流式输入文本的方式",
    "进行语音合成的场景。",
]

if __name__ == "__main__":
    player = pyaudio.PyAudio()
    stream = player.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)

    # 创建SDK实例
    # 配置回调函数
    def test_on_data(data, *args):
        stream.write(data)

    def test_on_message(message, *args):
        print('on message=>{}'.format(message))

    def test_on_close(*args):
        print('on_close: args=>{}'.format(args))

    def test_on_error(message, *args):
        print('on_error args=>{}, message=>{}'.format(args, message))
    
    sdk = nls.NlsStreamInputTtsSynthesizer(
        token=TEST_ACCESS_TOKEN,
        appkey=TEST_ACCESS_APPKEY,
        on_data=test_on_data,
        on_sentence_begin=test_on_message,
        on_sentence_synthesis=test_on_message,
        on_sentence_end=test_on_message,
        on_completed=test_on_message,
        on_error=test_on_error,
        on_close=test_on_close,
        callback_args=[],
    )

    # 发送文本消息
    sdk.startStreamInputTts()
    for text in test_text:
        sdk.sendStreamInputTts(text)
        time.sleep(0.05)
    sdk.stopStreamInputTts()

    stream.stop_stream()
    stream.close()
    player.terminate()
