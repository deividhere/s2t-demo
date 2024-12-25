from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.core.clipboard import Clipboard

import threading
import time


# Design file
Builder.load_file("design.kv")


class MyLayout(Widget):
    should_update_db = True

    def __init__(self, **kwargs):
        super(MyLayout, self).__init__(**kwargs)

        t = threading.Thread(target=self.update_db)
    
        # set daemon to true so the thread dies when app is closed
        t.daemon = True

        # start the thread
        t.start()

    def update_db(self):
        while True:
            if self.should_update_db:
                slider_db = self.ids["slider_db"]

                if slider_db.value < 100:
                    slider_db.value += 1

                    value = slider_db.value

                    # 100dB -> green = 53
                    # 50dB -> green = 222
                    
                    green = 53 + (100 - value) * (222 - 53)/50
                    if green > 222:
                        green = 222

                    # 50dB -> red = 222
                    # 0dB -> red = 53

                    red = 53 + value * (222 - 53)/50
                    if red < 53:
                        red = 53
                    if red > 222:
                        red = 222
                    
                    slider_db.value_track_color = (red/255, green/255, 53/255, 1)
                
            time.sleep(0.1)
        

    def switch_mic_Active(self, switchObject, switchValue):
        slider_db = self.ids["slider_db"]

        if switchValue:
            self.should_update_db = True
            slider_db.value_track = True
        else:
            self.should_update_db = False
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
