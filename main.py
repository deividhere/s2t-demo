from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder

# Design file
Builder.load_file("design.kv")


class MyLayout(Widget):
    def btn_copy_Released(self):
        print('hey')
    
    def btn_clear_Released(self):
        print('hey')


class SPD(App):
    def build(self):
        return MyLayout()


if __name__ == '__main__':
    SPD().run()
