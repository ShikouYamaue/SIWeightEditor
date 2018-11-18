# -*- coding: utf-8 -*-
from textwrap import dedent
import maya.cmds as cmds
import maya.mel as mel
import maya.utils
from . import siweighteditor
from . import qt

def menu_setup():
    #Maya_Windowが見つからない場合はスタートしない
    if not qt.get_maya_window():
        return
        
    cmd = '''
    buildViewMenu MayaWindow|mainWindowMenu;
    setParent -menu "MayaWindow|mainWindowMenu";
    '''

    mel.eval(cmd)

    cmds.menuItem(divider=True)
    cmds.menuItem(
        'siweighteditor_folder',
        label='SiWeightEditor',
        subMenu=True,
        tearOff=True
    )

    cmds.menuItem(
        'siweighteditor_open',
        label=jpn('SiWeightEditor'),
        annotation="open SiWeightEditor",
        parent='siweighteditor_folder',
        echoCommand=True,
        command=dedent(
            '''
                import siweighteditor.siweighteditor
                siweighteditor.siweighteditor.Option()
            ''')
    )


def register_runtime_command(opt):

    # check if command already exists, then skip register
    runtime_cmd = dedent('''
        runTimeCommand
            -annotation "{annotation}"
            -category "{category}"
            -commandLanguage "{commandLanguage}"
            -command ({command})
            {cmd_name};
    ''')

    name_cmd = dedent('''
        nameCommand
            -annotation "{annotation}"
            -sourceType "{commandLanguage}"
            -command ("{cmd_name}")
            {cmd_name}NameCommand;
    ''')

    exits = mel.eval('''exists "{}";'''.format(opt['cmd_name']))
    if exits:
        #print 'custom command is already exist : *-*-*-*-*-*-*-*-*-*-*-*-*-***-**-*'
        return
    try:
        mel.eval(runtime_cmd.format(**opt))
        mel.eval(name_cmd.format(**opt))

    except Exception as e:
        print opt['cmd_name']
        print opt['command']
        raise e


def register_siwieighteditor_runtime_command():
    opts = {
        'annotation':      "Open SiWeightEditor",
        'category':        "SiWeightEditor",
        'commandLanguage': "python",
        'command':         r'''"from siweighteditor import siweighteditor\r\rreload(siweighteditor)\r\siweighteditor.Option() "''',
        'cmd_name':        "OpenSiWeightEditor"
    }
    register_runtime_command(opts)


def jpn(string):
    # type: (str) -> str
    """encode utf8 into cp932"""

    try:
        string = unicode(string, "utf-8")
        string = string.encode("cp932")
        return string

    except Exception:
        return string

def execute():
    menu_setup()
    #今のところコマンド登録しない
    register_siwieighteditor_runtime_command()
    # 2017以降ではworkspaceControlがあるので記録と復元は必要ない
    #if int(cmds.about(v=True)[:4]) < 2017:
        #maya.utils.executeDeferred(sisidebar_main.load_with_start_up)