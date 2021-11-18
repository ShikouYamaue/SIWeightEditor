# -*- coding: utf-8 -*-
import functools
import datetime as dt
import maya.cmds as cmds

    
def timer(func):
    """
    デバッグ用デコレータ
    実効時間を表示するデコレータ
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = dt.datetime.today()
        result = func(*args, **kwargs)
        end = dt.datetime.today()
        print('----------------------------------')
        print('end:', end)
        print('start:', start)
        print('running:', end - start, func)
        print('-------------------------------------------------------------')
        return result
    return wrapper
    
def timer(func):
    """
    何もしないデコレータ
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

class LapCounter():
    lap_times = 0
    lap_list = []
    def __init__(self):
        self.start = dt.datetime.today()
    def count(self):
        self.end = dt.datetime.today()
        lap_str = 'lap_time :', self.lap_times, ':', self.end - self.start
        self.lap_list.append(lap_str)
        self.lap_times += 1
        self.start = dt.datetime.today()
    def lap_print(self):
        print('----------------------------------')
        for lap_time in self.lap_list:
            print(lap_time)
        
#指定タイプへのコンポーネント変換をまとめて
def conv_comp(obj, mode=''):
    if mode == 'edge':
        comp = cmds.polyListComponentConversion(obj, te=True)
        comp = cmds.filterExpand(comp, sm=32)
    if mode == 'face':
        comp = cmds.polyListComponentConversion(obj, tf=True)
        comp = cmds.filterExpand(comp, sm=34)
    if mode == 'vtx':
        comp = cmds.polyListComponentConversion(obj, tv=True)
        comp = cmds.filterExpand(comp, sm=31)
    if mode == 'uv':
        comp = cmds.polyListComponentConversion(obj, tuv=True)
        comp = cmds.filterExpand(comp, sm=35)
    if mode == 'vf':
        comp = cmds.polyListComponentConversion(obj, tvf=True)
        comp = cmds.filterExpand(comp, sm=70)
    return comp
    
    
def search_polygon_mesh(object, serchChildeNode=False, fullPath=False, mesh=True, nurbs=False):
    '''
    選択したものの中からポリゴンメッシュを返す関数
    serchChildeNode→子供のノードを探索するかどうか
    '''
    # リストタイプじゃなかったらリストに変換する
    if not isinstance(object, list):
        temp = object
        object = []
        object.append(temp)
    polygonMesh = []
    # 子供のノードを加えるフラグが有効な場合は追加
    if serchChildeNode is True:
        parentNodes = object
        for node in parentNodes:
            try:
                nodes = cmds.listRelatives(node, ad=True, c=True, typ='transform', fullPath=fullPath, s=False)
            except:
                pass
            if nodes is not None:
                object = object + nodes
    # メッシュノードを探して見つかったらリストに追加して返す
    for node in object:
        if mesh:
            try:
                meshnode = cmds.listRelatives(node, s=True, pa=True, type='mesh', fullPath=True)
                if meshnode:
                    polygonMesh.append(node)
            except:
                pass
        if nurbs:
            try:
                nurbsnode = cmds.listRelatives(node, s=True, pa=True, type='nurbsSurface', fullPath=True)
                if nurbsnode:
                    polygonMesh.append(node)
            except:
                pass
    if len(polygonMesh) != 0:
        return polygonMesh
    else:
        return []
        
class TemporaryReparent():
    '''
    一時的に子供のノードをダミーロケータの子供に退避、再親子付けする関数。
    ウェイト操作、UVSet操作など親子付けがあると処理が破たんする場合に利用
    parent→カットしてダミーに親子付けするか、ダミーから再親子付けするか 'cut'or'reparent'or'create'or'delete'
    createした場合はダミーペアレントを戻り値として返す
    objects→カット、リペアレントする対象親ノード
    dummyParent→リペアレントする場合は作成したダミーペアレントのノードを渡す。
    '''
    node_list = ['transform', 'joint', 'KTG_ModelRoot', 'KTG_SSCTransform']

    def main(self, objects=None, dummyParent=None, srtDummyParent=None, mode='cut', preSelection=None):
        self.objects = objects
        self.dummyParent = dummyParent
        self.srtDummyParent = srtDummyParent
        self.preSelection = preSelection
        # リストタイプじゃなかったらリストに変換する
        if not isinstance(self.objects, list):
            temp = self.objects
            self.objects = []
            self.objects.append(temp)
        for self.node in self.objects:
            if mode == 'create':
                self.dummyParent = cmds.spaceLocator(name='dummyLocatorForParent')
                return self.dummyParent
            elif mode == 'delete':
                cmds.delete(self.dummyParent)
                return
            elif mode == 'cut':
                self.cutChildNode()
                return
            elif mode == 'custom_cut':
                self.customCutChildNode()
                return
            elif mode == 'parent':
                self.reparentNode()
                return

    def cutChildNode(self):
        # 処理ノードの親子を取得しておく
        nodeChildren = cmds.listRelatives(self.node, children=True, fullPath=True) or []
        for child in nodeChildren:
            # 子のノードがトランスフォームならダミーに親子付けして退避
            if cmds.nodeType(child) in self.node_list:
                cmds.parent(child, self.dummyParent)
                
    #フリーズトランスフォーム用に場合分け親子付け関数を用意
    #子を含むマルチ選択状態の場合は別のダミー親につけてフリーズ後のSRT状態を調整する
    def customCutChildNode(self):
        nodeChildren = cmds.listRelatives(self.node, children=True, fullPath=True) or []
        for child in nodeChildren:
            if cmds.nodeType(child) in self.node_list:
                if child in self.preSelection:
                    #print('parent to dummy')
                    cmds.parent(child, self.dummyParent)
                else:
                    #print('parent to srt dummy')
                    cmds.parent(child, self.srtDummyParent)

    def reparentNode(self):
        dummyChildren = cmds.listRelatives(self.dummyParent, children=True, fullPath=True) or []
        for child in dummyChildren:
            if cmds.nodeType(child) in self.node_list:
                cmds.parent(child, self.node)
                