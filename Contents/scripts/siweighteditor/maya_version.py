# -*- coding: utf-8 -*-
from maya import cmds

MAYA_VER = int(cmds.about(v=True)[:4])
