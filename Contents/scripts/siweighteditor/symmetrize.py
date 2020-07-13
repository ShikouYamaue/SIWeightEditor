# -*- coding: utf-8 -*-
from maya import cmds
from maya import mel
import pymel.core as pm
from . import weight
from . import common
from . import lang
from . import modeling
import os
import json
#-*-coding:utf-8 -*-
import datetime as dt

#メッシュを反転コピーしてからウェイトを対象化
def mesh_weight_symmetrize():
    exFace = []
    if cmds.selectMode( q=True, co=True ):
        selection = cmds.ls(sl=True)
        faces = common.conv_comp(selection , mode='face')
        #print 'comp mode? :', cmds.selectMode(q=True, co=True)
        if faces == []:
            #print 'no select'
            return
        #print faces
        exFace = modeling.face_extraction(faces=faces, deleteOrg=False, selectDuplicated=True, transferWeight=True)
    selection = pm.ls(sl=True)
    #選択しているものの子供のノードを取得してリスト化
    allNodes = alignmentParentList(selection)
    duplicated = []
    for node in allNodes:
        #複製して反転する関数呼び出し、戻り値は
        duplicateObj = duplycateSymmetry(node)
        duplicated.append(duplicateObj)
        #ウェイトシンメトリーする関数呼び出し
        weight.symmetry_weight(node,duplicateObj)
        #continue
    cmds.select(duplicated,  r=True)
    if exFace != []:
        cmds.delete(exFace)

def alignmentParentList(parentList):
    #親子順にリストを整理
    alignedList = []
    for node in parentList:
        #子のノードを取得※順序がルート→孫→子の順番なので注意、いったんルートなしで取得
        #children = common.get_children(node,type=['transform'], root_includes=False)
        children = pm.listRelatives(node, ad=True, type='transform', f=True)
        #末尾にルートを追加
        children.append(node)
        #逆順にして親→子→孫順に整列
        children.reverse()
        #同一ツリー内マルチ選択時の重複回避のためフラグで管理
        for child in children:
            appendedFlag = False
            for alignedNode in alignedList :
                if alignedNode == child:
                    appendedFlag = True
            if appendedFlag is False:
                alignedList.append(str(child))
    return alignedList

def duplycateSymmetry(object):
    meshNode = cmds.listRelatives(object, s=True, pa=True, type='mesh', fullPath=True)
    if meshNode is not None:
        #エラー吐くことがあるのでノンデフォーマヒストリを削除
        cmds.bakePartialHistory(object,ppt=True)
    #ネームスペースから分割
    nemeSplit = object.split('|')
    newName = nemeSplit[-1]
    #左右リネーム関数呼び出し
    newName = renameLR(newName)
    #複製して反転
    duplicated = pm.duplicate(object, name=newName)
    try:
        parentNode =  duplicated[0].firstParent()#Pymelの機能で親の階層を取得しておく。listRelativesと同じような。
        parentNode = str(parentNode)#cmdsで使えるように文字列に変換
        #左右リネーム関数呼び出し
        newParent = renameLR(parentNode)
    except:
        parentNode = None
        newParent = None
    duplicated = str(duplicated[0])#cmdsで使えるように文字列に変換
    #子供のオブジェクト取得関数呼び出し
    children = pm.listRelatives(duplicated, ad=True, type='transform', f=True)
    #子供のオブジェクトがある場合は重複を避けるため削除
    if len(children) != 0:
        cmds.delete(children)
    #アトリビュートのロック解除
    #全部のロック解除しないと親が変わったときのロカール値が変わらず、ズレることがある。
    attr = ['.translate', '.rotate', '.scale']
    axis = ['X', 'Y', 'Z']
    for varA in range(0, 3):
        for varB in range(0, 3):
            cmds.setAttr(duplicated + attr[varA] + axis[varB], lock=False)
    #ワールドスケール用ダミーロケータ作成
    dummy = common.TemporaryReparent().main(mode='create')
    cmds.parent(duplicated, dummy)
    #X方向に-1スケーリングしてからスケールフリーズ
    cmds.scale(-1, 1, 1, dummy, relative=True, pivot=(0,0,0))
    #杏仁生成を防ぐためにダミーロケータのスケールをフリーズ、負の値が親に入ってると杏仁が生成されるような。
    if cmds.nodeType(duplicated) == 'joint':
        #ジョイントを正しい回転、位置に修正するため、スケールフリーズ前のグローバル値を取得しておく
        pos = cmds.xform(duplicated, q=True, t=True, ws=True)
        rot = cmds.xform(duplicated, q=True, ro=True, ws=True)
        cmds.makeIdentity(dummy, apply=True, translate=False, rotate=False, scale=True, preserveNormals=True)
    #元の親名と違い、かつ新しい親名のオブジェクトが存在する場合は付け替え
    if parentNode is None:
            cmds.parent(duplicated, w=True)
    else:
        if parentNode != newParent and cmds.ls(newParent):
            cmds.parent(duplicated, newParent)
        else:
            cmds.parent(duplicated, parentNode)
    #ダミーペアレントを削除
    common.TemporaryReparent().main(dummyParent=dummy, mode='delete')
    cmds.makeIdentity(duplicated, apply=True, translate=False, rotate=False, scale=True, preserveNormals=True)
    if cmds.nodeType(duplicated) == 'joint':
        cmds.xform(duplicated , t=pos, ro=rot, ws=True)
    return duplicated
    
def renameLR(rename):
    #左右のLRをリネームする関数
    #1つのオブジェクト内にLRが混在する可能性を考慮して一時的に別の名前にしてから最後にLRリネーム
    if rename.startswith('L_')==True:
        rename = 'RightRenameTemp_'+rename[2:]
    elif rename.startswith('R_')==True:
        rename = 'LeftRenameTemp_'+rename[2:]
    if rename.endswith('_L')==True:
        rename = rename[0:-2]+'_RightRenameTemp'
    elif rename.startswith('_R')==True:
        rename = rename[0:-2]+'_LeftRenameTemp'
    if '_L_' in rename:
        rename = rename.replace('_L_', '_RightRenameTemp_')
    if '_R_' in rename:
        rename = rename.replace('_R_', '_LeftRenameTemp_')
    rename = rename.replace( 'LeftRenameTemp','L')
    rename = rename.replace( 'RightRenameTemp','R')
    return rename

class WeightSymmetrize():
    vtx_L = []
    vtx_R = []
    vtx_L_All = []
    vtx_R_All = []
    def __init__(self):
        #メッセージ設定
        self.msg03 = lang.Lang(
        en='One mesh weight mirror',
        ja=u'1メッシュのウェイトミラー').output()
        self.msg00 = lang.Lang(
        en='There is one selected mesh\nPlease select the direction to mirror',
        ja=u'選択されているメッシュが1つです\nミラーリングする方向を選択してください').output()
        self.msg01 = lang.Lang(
        en='From + X to - X',
        ja=u' + X から - X へ').output()
        self.msg02 = lang.Lang(
        en='From - X to + X',
        ja=u' - X から + X へ').output()
        
        self.selection = cmds.ls(sl=True)
        vertices = common.conv_comp(self.selection, mode='vtx')
        vertices = cmds.filterExpand(vertices, sm=31)
        meshes = cmds.filterExpand(self.selection, sm=12)
        #メッシュからジョイントラベルを設定
        if vertices:
            self.all_meshes = list(set(x.split(".", 1)[0] for x in vertices))
        else:
            self.all_meshes = meshes
        if not self.all_meshes:
            return
        #スキンクラスタからジョイントラベルを設定する
        for mesh in self.all_meshes:
            srcSkinCluster = cmds.ls(cmds.listHistory(mesh), type='skinCluster')
            if srcSkinCluster:
                #シムウェイト関数をジョイントラベル設定するだけのオプションで呼び出し
                weight.symmetry_weight(srcNode=mesh, symWeight=False)
                break
        else:#スキンが一個もなかったら抜ける
            return
        #スキンクラスタがないメッシュがあったらせっていしておく
        for check_skin in self.all_meshes:
            srcSkinCluster = cmds.ls(cmds.listHistory(check_skin), type='skinCluster')
            if not srcSkinCluster:
                weight.transfer_weight(mesh, check_skin, transferWeight=False, returnInfluences=False, logTransfer=True)
        #オブジェクト単位でのシンメトリ
        if meshes is not None:
            if len(meshes) == 1:
                mirrorDir = cmds.confirmDialog( title=self.msg03, 
                                                            message=self.msg00, 
                                                            button=[self.msg01, self.msg02], 
                                                            defaultButton=self.msg01, 
                                                            cancelButton=self.msg02, 
                                                            dismissString='escape')
                if mirrorDir == 'escape':
                    return
                if mirrorDir == self.msg01:
                    mirrorDir = False
                elif mirrorDir == self.msg02:
                    mirrorDir = True
            else:
                mirrorDir = False
            self.ezSymWeight(meshes, mirror=mirrorDir)
        #頂点がなかったら関数抜ける
        if vertices is not None:
            #選択頂点を左右に振り分け
            self.vtx_L = self.listEachMesh(vertices, self.all_meshes, negaPosi = 1, plane=0)
            self.vtx_R = self.listEachMesh(vertices, self.all_meshes, negaPosi = -1, plane=0)
            #メッシュの頂点をすべて取得
            self.vtx_All = cmds.polyListComponentConversion(list(self.all_meshes), tv=True)
            self.vtx_All = cmds.filterExpand(self.vtx_All, sm=31)
            #全頂点を左右に振り分け
            self.vtx_L_All= self.distributeVertex(self.vtx_All, negaPosi = 1, plane=0)
            self.vtx_R_All = self.distributeVertex(self.vtx_All, negaPosi = -1, plane=0)
            #左右それぞれにシムウェイト。左全部と右選択頂点を選択して実行、その反対を実行を順次処理。
            #オブジェクト単位でミラーしないと1メッシュにしか適用されないっぽいので振り分けたメッシュ頂点リスト事にループ
            for vtx_R in self.vtx_R:
                self.ezSymWeight(target=self.vtx_L_All+vtx_R, mirror=False)#左から右へ転送
            for vtx_L in self.vtx_L:
                self.ezSymWeight(target=self.vtx_R_All+vtx_L, mirror=True)#右から左へ転送
            
            #選択状態を元通りにする
            cmds.select(self.selection, r=True)
        
    #ウェイトミラー
    def ezSymWeight(self, target, mirror=False):
        cmds.select(target, r=True)
        cmds.copySkinWeights(mirrorMode='YZ', 
                            mirrorInverse=mirror, 
                            surfaceAssociation='closestPoint', 
                            influenceAssociation='label' ,
                            normalize=False)
                            
    #頂点位置と指定プレーンから+-方向どちらにあるか判定して振り分ける関数
    def distributeVertex(self, vtx, negaPosi = 1, plane=0):
        #negaPosi 1：+方向、　-1：-方向
        #plane指定　'yz'0, 'xz':1, 'yx':2
        return [v for v in vtx if cmds.pointPosition(v, w=True)[plane]*negaPosi > 0]
        
    #メッシュごとにそれぞれ頂点リストを分ける
    def listEachMesh(self, vtx, meshes,  negaPosi = 1, plane=0):
        meshVtxList = []
        preID = meshes.index(vtx[0].split('.')[0])#メッシュ名を判別するためのID
        tempList = []#メッシュごとのグループに分けるためのテンポラリ
        for v in vtx:
            if cmds.pointPosition(v, w=True)[plane]*negaPosi > 0:
                id = meshes.index(v.split('.')[0])#メッシュ名を取得してIDに変換
                if preID == id:#メッシュ名が同じ間はテンポラリに頂点を追加
                    tempList.append(v)
                else:#メッシュ名が変わったらリストをアペンドしてテンポラリをクリア
                    meshVtxList.append(tempList)
                    tempList = []
                    tempList.append(v)
                preID = id
        if tempList != []:#最後の一個も追加
            meshVtxList.append(tempList)
        return meshVtxList
            