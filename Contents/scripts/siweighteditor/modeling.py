#!/usr/bin/env python
# -*- coding: utf-8 -*-
from maya import cmds
from maya import mel
import os, json
import pymel.core as pm
from . import weight
from . import common
from . import qt
import maya.api.OpenMaya as om
import re

    
def setSoftEdge(mesh, angle=120):
    # 法線のロック解除
    cmds.polyNormalPerVertex(mesh + '.vtx[*]', unFreezeNormal=True)
    # アングルを設定
    cmds.polySoftEdge(mesh+'.e[*]', a=angle)
    

# Separate_Face,Duplicate_Faceから呼び出してくるモジュール
def face_extraction(faces=None, deleteOrg=True, selectDuplicated=True, transferWeight=True):
    '''
    メッシュを選択したフェイスで切り分ける
    deleteOrg　切り分け元のフェイスを削除するかどうかを指定デフォルトTrue
    faces →　外部ツールからフェイスのリストを渡して実行したい場合の引数
    '''
    if faces is None:
        selection = cmds.ls(sl=True)
    else:
        selection = faces
    selObjects = []
    for sel in selection:
        objNameTemp = sel.split('.')
        if not objNameTemp[0] in selObjects:
            selObjects.append(objNameTemp[0])

    cmds.select(cl=True)
    duplicated = []  # 最後の選択格納用
    # ハイライトされているオブジェクト毎に処理
    for selObj in selObjects:
        compTemp = []  # バラバラのコンポーネントをオブジェクト毎に格納するリスト
        # 選択されているコンポーネントを整理
        for sel in selection:
            objNameTemp = sel.split('.')
            objName = objNameTemp[0]  # コンポーネントのオブジェクト名
            # オブジェクト名が一致且つフェイス選択ならリスト入り
            if selObj == objName and '.f[' in sel:
                compTemp.append(sel)
        # print 'compTemp ALL : '+str(compTemp)
        if len(compTemp) != 0:
            dupObj = cmds.duplicate(selObj, rr=True)
            # 子供のオブジェクト取得関数呼び出し
            children = cmds.listRelatives(dupObj[0], type='transform', ad=True)
            # 子供のオブジェクトがある場合は重複を避けるため削除
            if children:
                cmds.delete(children)
            duplicated.append(dupObj[0])
            if transferWeight:  # ウェイト転送フラグが有効だったら
                weight.transfer_weight(selObj, dupObj, logTransfer=False)  # ウェイトを転送
            faces = ",".join(compTemp)  # リストを括弧のない文字列に
            faces = faces.replace(selObj, dupObj[0])  # 名前置き換え
            delface = faces.split(',')
            cmds.selectMode(co=True)
            cmds.hilite(dupObj)
            cmds.select(delface, r=True)
            #print 'del face :',delface
            for obj in dupObj:
                face_count = str(len(common.conv_comp(obj, mode='face')))
                cmds.select(obj+'.f[0:'+face_count+']', tgl=True)
            #mel.eval('InvertSelection;')  # 選択の反転
            deleter = cmds.ls(sl=True)
            cmds.delete(deleter)  # 最初に選択されていなかったフェース部分のみ削除
            # 削除フラグが立っていたら古いフェイス削除
            if deleteOrg is True:
                cmds.delete(compTemp)
    if selectDuplicated:
        cmds.select(duplicated)
    return duplicated
    
#クラスタデフォーマの書き戻し
class ClusterCopy():
    def copy(self, mesh):
        self.cluster_list = []
        self.point_dict = {}
        self.cls_weight_dict = {}
            
        dummy = common.TemporaryReparent().main(mode='create')
        common.TemporaryReparent().main(mesh, dummyParent=dummy, mode='cut')
        
        cluster = cmds.ls(cmds.listHistory(mesh), type='cluster', l=True)
        for cls in cluster:
            set_node = cmds.ls(cmds.listHistory(cls, f=True), type='objectSet', l=True)[0]
            cmds.select(set_node)
            vertices = cmds.ls(sl=True)
            vertices = cmds.filterExpand(vertices, sm=31)
            cmds.select(vertices, r=True)
            try:
                weights = cmds.percent(cls, q=True, v=True)
                print weights
            #値が取れないときアンドゥするとなぜか直ることがある
            except Exception as e:
                print e.message
                cmds.delete(cls)
                cmds.undo()
                set_node = cmds.ls(cmds.listHistory(cls, f=True), type='objectSet', l=True)[0]
                vertices = cmds.ls(sl=True)
                vertices = cmds.filterExpand(vertices, sm=31)
                cmds.select(vertices, r=True)
                weights = cmds.percent(cls, q=True, v=True)
            self.cluster_list.append(cls)
            self.cls_weight_dict[cls] = weights
            self.point_dict[cls] = vertices
        common.TemporaryReparent().main(mesh, dummyParent=dummy, mode='parent')#コピーのおわったメッシュの子供を元に戻す
        common.TemporaryReparent().main(dummyParent=dummy, mode='delete')#ダミー親削除
        return self.point_dict, self.cls_weight_dict
        
    def paste(self, mesh):
        if not self.cluster_list:
            return
        for cls in self.cluster_list:
            weights = self.cls_weight_dict[cls]
            print 'paste cls :',cls
            cmds.select(cl=True)            
            points = self.point_dict[cls]
            newcls = cmds.cluster(points, n=cls)
            for i, v in enumerate(points):
                cmds.percent(newcls[0], v, v=(weights[i])) 
        return newcls
        
#ポリゴンメッシュをウェイト付きで複製する関数
def duplicate_with_skin(nodes, parentNode=None):
    #親子付けがあってもエラーはかないように修正
    #print nodes
    # リストタイプじゃなかったらリストに変換する
    if not isinstance(nodes, list):
        nodes = [nodes]
    dupObjs = []
    for node in nodes:
        #子供のノード退避用ダミーペアレントを用意
        dummy = common.TemporaryReparent().main(mode='create')
        common.TemporaryReparent().main(node,dummyParent=dummy, mode='cut')
        #複製
        dup = cmds.duplicate(node)[0]
        #ウェイト転送メソッドをSimpleWeightコピペに変更
        weight.SimpleWeightCopyPaste().main(node, mode='copy', saveName=__name__, weightFile=node)
        weight.SimpleWeightCopyPaste().main(dup, mode='paste', saveName=__name__, weightFile=node)
        #親子付けを戻す
        common.TemporaryReparent().main(node,dummyParent=dummy, mode='parent')
        #ダミーペアレントを削除
        common.TemporaryReparent().main(dummyParent=dummy, mode='delete')
        if parentNode is not None:
            cmds.parent(dup, parentNode)
        dupObjs.append(dup)
    return dupObjs
    
#シーン内、もしくは入力メッシュ内にゼロポリゴンオブジェクトがあるかどうか調べる関数
def cehck_zero_poly_object(mesh=None, pop_msg=True):
    #mesh 入力メッシュ
    #pop_msg　探索結果を表示するかどうか
    if mesh == None:
        polyMeshes = common.search_polygon_mesh(cmds.ls(tr=True))
    else:
        polyMeshes = common.search_polygon_mesh(mesh)
    zeroPolyObj = []
    if polyMeshes == None:
        if pop_msg:
            cmds.confirmDialog( title="Check",message='Zero Polygon Object Count :  0')
        return zeroPolyObj
    for p in polyMeshes:
        vtx = cmds.polyListComponentConversion(p, tv=True)
        if vtx == []:
            zeroPolyObj.append(p)
    if not pop_msg:
        return zeroPolyObj
    if zeroPolyObj == []:
        cmds.confirmDialog( title="Check",message='Zero Polygon Object Count :  0')
    else:
        msg = 'Zero Polygon Object Count : '+str(len(zeroPolyObj))
        for p in zeroPolyObj:
            msg+='\n[ '+p+' ]'
        cmds.confirmDialog( title="Check",message=msg )
        cmds.select(zeroPolyObj, r=True)
    return zeroPolyObj
    
#スキニングを保ったままメッシュマージするクラス
class MeshMarge():
    def main(self, objects):
        self.objects= objects
        qt.Callback(self.marge_run())
        return self.marged_mesh
        
    def marge_run(self):
        objects = common.search_polygon_mesh(self.objects, serchChildeNode=True, fullPath=True)
        #print 'marge target :', objects
        if len(objects) < 2:
            self.marged_mesh = objects
            return True
        skined_list = []
        no_skin_list = []
        parent_list = [cmds.listRelatives(obj, p=True, f=True) for obj in objects]
        
        for obj in objects:
            skin = cmds.ls(cmds.listHistory(obj), type='skinCluster')
            if skin:
                skined_list.append(obj)
            else:
                no_skin_list.append(obj)
                
        if no_skin_list and skined_list:
            skined_mesh = skined_list[0]
            for no_skin_mesh in no_skin_list:
                weight.transfer_weight(skined_mesh, no_skin_mesh, transferWeight=False, returnInfluences=False, logTransfer=False)
                
        if skined_list:
            marged_mesh = pm.polyUniteSkinned(objects)[0]
            pm.polyMergeVertex(marged_mesh, d=0.001)
            target_mesh = pm.duplicate(marged_mesh)[0]
            weight.transfer_weight(str(marged_mesh), str(target_mesh), transferWeight=True, returnInfluences=False, logTransfer=False)
        else:
            marged_mesh = pm.polyUnite(objects, o=True)[0]
            pm.polyMergeVertex(marged_mesh, d=0.001)
            target_mesh = pm.duplicate(marged_mesh)[0]
            #pm.delete(objects)
        for obj in objects:
            if pm.ls(obj):
                pm.delete(obj)
            
        pm.delete(marged_mesh)
        
        all_attr_list = [['.sx', '.sy', '.sz'], ['.rx', '.ry', '.rz'], ['.tx', '.ty', '.tz']]
        for p_node in parent_list:
            if cmds.ls(p_node, l=True):
                all_lock_list = []
                for attr_list in all_attr_list:
                    lock_list = []
                    for attr in attr_list:
                        lock_list.append(pm.getAttr(target_mesh+attr, lock=True))
                        pm.setAttr(target_mesh+attr, lock=False)
                    all_lock_list.append(lock_list)
                pm.parent(target_mesh, p_node[0])
                for lock_list, attr_list in zip(all_lock_list, all_attr_list):
                    for lock, attr in zip(lock_list, attr_list):
                        #continue
                        #print 'lock attr :', lock, target_mesh, attr
                        pm.setAttr(target_mesh+attr, lock=lock)
                break
        pm.rename(target_mesh, objects[0])
        pm.select(target_mesh)
        self.marged_mesh = str(target_mesh)
        return True
    
    