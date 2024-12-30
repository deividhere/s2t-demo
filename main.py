from kivy.app import App
from kivy.clock import mainthread
from kivy.core.clipboard import Clipboard
from kivy.lang import Builder
from kivy.uix.widget import Widget

from google.oauth2 import service_account
from google.cloud import speech

import io
import numpy as np
import os
import pyaudio
import struct
import threading
import time
import wave


# Design file
Builder.load_file("design.kv")


class MyLayout(Widget):
    should_record = True
    recording_on = False
    silent_chunks = 0
    is_silent = True

    # Audio settings
    CHUNK = 1024  # Number of audio frames per buffer
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    DEVICE = 1
    RATE = 16000
    SHORT_NORMALIZE = (1.0/32768.0)
    SILENCE_THRESHOLD = 2.5  # Adjust threshold for silence detection
    MAX_SILENCE_CHUNKS = 32  # Number of chunks to consider silence before stopping recording
    # 8 chunks -> 32 * 0.064s = ~2s
    swidth = 2

    frames = []

    def __init__(self, **kwargs):
        super(MyLayout, self).__init__(**kwargs)

        # init Google Speech-to-Text API
        client_file = 'api/spd-iisc.json'
        credentials = service_account.Credentials.from_service_account_file(client_file)
        self.client = speech.SpeechClient(credentials=credentials)
        
        # init pyaudio
        self.p = pyaudio.PyAudio()

        t = threading.Thread(target=self.record_chunk)
    
        # set daemon to true so the thread dies when app is closed
        t.daemon = True

        # start the thread
        t.start()

    @staticmethod
    def rms(self, frame):
        count = len(frame) / self.swidth
        format = "%dh" % (count)
        shorts = struct.unpack(format, frame)

        sum_squares = 0.0
        for sample in shorts:
            n = sample * self.SHORT_NORMALIZE
            sum_squares += n * n
        rms = np.pow(sum_squares / count, 0.5)

        return rms * 1000


    def record_chunk(self):
        while True:
            if self.should_record:
                if self.recording_on == False:
                    self.recording_on = True
                    self.is_silent = True
                    self.stream = self.p.open(format=self.FORMAT, input_device_index=self.DEVICE, channels=self.CHANNELS, rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)
                    self.silent_chunks = 0
                
                if self.silent_chunks < self.MAX_SILENCE_CHUNKS:
                    data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    self.frames.append(data)

                    # Analyze volume level
                    volume = self.rms(self, data)
                    if volume < self.SILENCE_THRESHOLD:
                        self.silent_chunks += 1
                    else:
                        self.is_silent = False
                        self.silent_chunks = 0
                    
                    # new level in UI (max 100)
                    new_volume = int(volume / 2)

                    if new_volume > 100:
                        new_volume = 100

                    # update volume level in UI
                    self.update_db(new_volume)

                else:
                    # two seconds of no activity
                    self.recording_on = False

                    self.stream.stop_stream()
                    self.stream.close()

                    if self.is_silent == False:
                        # save to file
                        temp_filename = "temp_audio.wav"
                        wf = wave.open(temp_filename, 'wb')
                        wf.setnchannels(self.CHANNELS)
                        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
                        wf.setframerate(self.RATE)
                        wf.writeframes(b''.join(self.frames))
                        wf.close()

                        # transcribe audio
                        try:
                           self.transcribe_audio(temp_filename)
                        finally:
                            # clean up temporary file
                            os.remove(temp_filename)
                    else:
                        pass

                    self.frames.clear()
            
            else:
                # user stopped the microphone
                if self.recording_on == True:
                    self.recording_on = False

                    self.stream.stop_stream()
                    self.stream.close()

                    # TODO: Also send to API if user turned off microphone?

                    self.frames.clear()

    @mainthread
    def update_textbox(self, new_text): # this will run in mainthread, even if called  outside.
        tb_input = self.ids["tb_input"]
        tb_input.text += new_text + "\n"

    def transcribe_audio(self, filename):
        """Transcribes audio from a file using Google Cloud Speech-to-Text API."""
        with io.open(filename, 'rb') as audio_file:
            content = audio_file.read()
        
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.RATE,
            language_code="en-US",
        )

        response = self.client.recognize(config=config, audio=audio)

        for result in response.results:
            new_text = str(result.alternatives[0].transcript)
            
            if len(new_text) > 0:
                self.update_textbox(new_text)
                
        
    def update_db(self, new_value):
        slider_db = self.ids["slider_db"]

        # 100dB -> green = 53
        # 50dB -> green = 22
        green = 53 + (100 - new_value) * (222 - 53)/50
        if green > 222:
            green = 222

        # 50dB -> red = 222
        # 0dB -> red = 53
        red = 53 + new_value * (222 - 53)/50
        if red < 53:
            red = 53
        if red > 222:
            red = 222
        
        slider_db.value_track_color = (red/255, green/255, 53/255, 1)
        slider_db.value = new_value

    def switch_mic_Active(self, switchObject, switchValue):
        slider_db = self.ids["slider_db"]

        if switchValue:
            self.should_record = True
            slider_db.value_track = True
        else:
            self.should_record = False
            slider_db.value = 0
            slider_db.value_track = False

    def btn_copy_Released(self):
        tb_input = self.ids["tb_input"]
        Clipboard.copy(tb_input.text)
    
    def btn_clear_Released(self):
        tb_input = self.ids["tb_input"]
        tb_input.text = ""


class SPD(App):
    def build(self):
        return MyLayout()


if __name__ == '__main__':
    SPD().run()
