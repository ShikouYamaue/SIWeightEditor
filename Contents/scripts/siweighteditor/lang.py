# -*- coding: utf-8 -*-
from maya import cmds

UI_LANGUAGE = cmds.about(uil=True)


class Lang(object):
    def __init__(self, en='', ja=''):
        self.jp = ja
        self.en = en

    def output(self):
        if UI_LANGUAGE == "ja_JP":
            return self.jp
        return self.en
