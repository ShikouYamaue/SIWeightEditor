# -*- coding: utf-8 -*-
from maya import cmds
import os
import json

def maya_export():
    selection = cmds.ls(sl=True)
    long_names = cmds.ls(sl=True, l=True)
    if selection:
        cmds.inViewMessage( amg='<hl>Go Maya</hl> : Export Selected Objects', pos='midCenterTop', fade=True, ta=0.75, a=0.5)
        temp = __name__.split('.')#nameは自分自身のモジュール名。splitでピリオドごとに3分割。
        folderPath = os.path.join(
            os.getenv('MAYA_APP_DIR'),#Mayaのディレクトリ環境変数を取得
            'Scripting_Files',
            temp[-1]
            )
        if not os.path.exists(folderPath):
            os.makedirs(os.path.dirname(folderPath+'\\'))  # 末尾\\が必要なので注意
        print folderPath
        files = os.listdir(folderPath)
        sel_dict = dict()
        if files is not None:
            for file in files:
                os.remove(folderPath + '\\' + file)
        for sel, long_name in zip(selection, long_names):
            cmds.select(sel, r=True)
            name = sel.replace('|', '__Pipe__')
            cmds.file(folderPath+'\\'+name+'.ma', force=True, options="v=0", typ="mayaAscii", pr=True, es=True)
            sel_dict[name+'.ma'] = long_name
        cmds.select(selection, r=True)
        #選択ノード名を保存
        fine_name = folderPath+'\\go_maya_selection_node.json'
        with open(fine_name, 'w') as f:
            json.dump(sel_dict, f)
            
def maya_import():
    temp = __name__.split('.')#nameは自分自身のモジュール名。splitでピリオドごとに3分割。
    folderPath = os.path.join(os.getenv('MAYA_APP_DIR'),'Scripting_Files','go')
    if not os.path.exists(folderPath):
        os.makedirs(os.path.dirname(folderPath+'\\'))  # 末尾\\が必要なので注意
    #print folderPath
    files = os.listdir(folderPath)
    if files is not None:
        for file in files:
            print file
            nameSpace = file.replace('.ma', '')
            cmds.file(folderPath+'\\'+file, i=True, typ="mayaAscii", iv=True, mnc=False, options="v=0;", pr=True)
            #重複マテリアルにファイル名が頭に付与されてしまうのを修正
            allMat = cmds.ls(mat=True)
            fileName = file.split('.')[0]
            for mat in allMat:
                if mat.startswith(fileName+'_'):
                    cmds.rename(mat, mat.replace(fileName+'_', ''))
        cmds.inViewMessage( amg='<hl>Go Maya</hl> : Imoprt objects', pos='midCenterTop', fade=True, ta=0.75, a=0.5)
    else:
        cmds.inViewMessage( amg='<hl>Go Maya</hl> : There is no exported object', pos='midCenterTop', fade=True, ta=0.75, a=0.5)
