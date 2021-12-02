# -*- coding: utf-8 -*-
from maya import cmds
from maya import OpenMayaUI
from collections import defaultdict

import os
import re
import locale
import json
import copy

from . import modeling
from . import qt
from . import common
from . import weight
from . import lang

import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
#PySide2、PySide両対応
import imp
try:
    imp.find_module('PySide2')
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *
except ImportError:
    from PySide.QtGui import *
    from PySide.QtCore import *
    
MAYA_VER = int(cmds.about(v=True)[:4])

if MAYA_VER >= 2016:
    from . import store_skin_weight_om2 as store_skin_weight
else:
    from . import store_skin_weight
    
class Option():
    def __init__(self):
        self.window = WeightTransferMultiple()
        self.window.resize(250, 65)
        self.window.show()
        
class WeightTransferMultiple(qt.SubWindow):
    copy_mesh = []
    def __init__(self, parent = None):
        super(WeightTransferMultiple, self).__init__(parent)
        
        #OpenMayaでウェイト取得するクラスを実態化しておく
        self.store_skin_weight = store_skin_weight.StoreSkinWeight()
        
        self.messenger()
        
        wrapper = QWidget()
        self.setCentralWidget(wrapper)
        self.mainLayout = QHBoxLayout()
        wrapper.setLayout(self.mainLayout)
        #ボタン追加
        button = QPushButton(self.msg03)
        #qt.change_button_color(button, textColor=20, bgColor=[128,128,160])#色変更
        button.clicked.connect(self.stock_copy_mesh)
        self.mainLayout.addWidget(button)
        #ボタン追加
        button = QPushButton(self.msg04)
        #.change_button_color(button, textColor=20, bgColor=[128,160,128])#色変更
        button.clicked.connect(qt.Callback(self.transfer_weight_multiple))
        self.mainLayout.addWidget(button)
        
    def messenger(self):
        self.msg01 = lang.Lang(
        en='Error ! : Please select weight mesh node and click copy button first',
        ja=u'エラー！: 最初にウェイト転送元メッシュを選択してコピーボタンをおしてください。').output()
        self.msg02 = lang.Lang(
        en='Error ! : Please select skin mesh',
        ja=u'エラー！: スキンメッシュを選択してください').output()
        self.msg03 = lang.Lang(
        en='Copy',
        ja=u'コピー').output()
        self.msg04 = lang.Lang(
        en='Transfer',
        ja=u'転写').output()
        self.msg05 = lang.Lang(
        en='Error ! : Copy mesh is not exist',
        ja=u'エラー！: コピー元メッシュがなくなっています').output()
        self.msg06 = lang.Lang(
        en='Error ! : Please select mesh or component',
        ja=u'エラー！: メッシュかコンポーネントを選択してください').output()
        
    def stock_copy_mesh(self):
        hl_node = cmds.ls(hl=True, l=True)
        sel_node = cmds.ls(sl=True, l=True)
        temp_copy_mesh = common.search_polygon_mesh(hl_node+sel_node, fullPath=True)
        self.copy_mesh = []
        for node in temp_copy_mesh:
            skin_cluster = cmds.ls(cmds.listHistory(node), type='skinCluster')
            if skin_cluster:
                self.copy_mesh.append(node)
        
        if not self.copy_mesh:
            cmds.confirmDialog( title='Error',
                  message= self.msg02)
            return self.msg02
        return 'Set Copy Mesh :\n'+str(self.copy_mesh)
        #print('copy mesh :',self.copy_mesh)
        
    def transfer_weight_multiple(self):
        global siweighteditor
        from . import siweighteditor
        
        if self.copy_mesh == []:
            cmds.confirmDialog( title='Error',
                  message= self.msg01)
            return self.msg01
            
        if not self.check_copy_mesh():
            cmds.confirmDialog( title='Error',
                  message= self.msg05)
            return self.msg05
            
        self.transfer_mesh = cmds.filterExpand(sm=12) or []
        self.transfer_comp = cmds.ls(sl=True, type='float3')
        self.hl_nodes = cmds.ls(hl=True, l=True, tr=True)
        if self.transfer_comp:
            self.store_current_vtxArray()
            self.pre_transfer_for_noskin_comp()
        #print('transfered mesh :', self.transfer_mesh)
        #メッシュ選択がなければ抜ける
        if not self.transfer_mesh and not self.transfer_comp:
            cmds.confirmDialog( title='Error',
                  message= self.msg06)
            return self.msg06
            
        #ウェイト付きで複製する
        self.dup_objs = self.dup_polygon_mesh()
        #一旦全部マージして転送もとオブジェクトにする
        self.marged_mesh = modeling.MeshMarge().main(self.dup_objs)
        #全てのインフルエンスを取得しておく
        self.store_all_influence()
        
        #オブジェクト、コンポーネント毎に転送実行
        if self.transfer_mesh:
            self.all_transfer()
        if self.transfer_comp:
            self.part_transfer()
            
        self.delete_sub_objects()
        
        cmds.select(self.transfer_mesh+self.hl_nodes+self.transfer_comp)
        
        return 'Transfer Weight to :\n'+str(self.transfer_mesh)
        
    def pre_transfer_for_noskin_comp(self):
        reselection_flag = False
        for node in self.hl_nodes:
            skin_cluster = cmds.ls(cmds.listHistory(node), type='skinCluster')
            if not skin_cluster:
                #print('pre transfer :', node, self.copy_mesh[0])
                weight.transfer_weight(self.copy_mesh[0], node, transferWeight=False)
                cmds.bakePartialHistory(node, ppt=True)
                reselection_flag = True
        if reselection_flag:
            #print('reselect for undo :')
            #アンドゥ、リドゥのためにエディタ側のスキン情報を更新しておく
            cmds.select(self.transfer_comp, r=True)
            siweighteditor.WINDOW.get_set_skin_weight()
                
    #インフルエンス合わせのために転送側の全てのインフルエンスを格納しておく
    all_influences = []
    def store_all_influence(self):
        skin_cluster = cmds.ls(cmds.listHistory(self.marged_mesh), type='skinCluster')
        if not skin_cluster:
            return
        skin_cluster = skin_cluster[0]
        self.all_influences = cmds.ls(cmds.skinCluster(skin_cluster, q=True, inf=True), l=True)
        #print('get all influences', self.all_influences)
        
    #足りないインフルエンスを追加しておく
    def adust_skin_influences(self, node):
        skin_cluster = cmds.ls(cmds.listHistory(node), type='skinCluster')
        if not skin_cluster:
            return
        skin_cluster = skin_cluster[0]
        node_influences = cmds.ls(cmds.skinCluster(skin_cluster, q=True, inf=True), l=True)
        sub_influences = list(set(self.all_influences) - set(node_influences))
        if sub_influences:
            cmds.skinCluster(node, e=True, ai=sub_influences, lw=True, ug=True, wt=0, ps=0)
        
        
    def delete_sub_objects(self):
        #不要な複製メッシュ削除
        try:
            if len(self.dup_objs) > 1:
                cmds.delete(self.dup_objs)
        except Exception as e:
            e.message
        cmds.delete(self.marged_mesh)
            
        cmds.select(self.transfer_mesh+self.transfer_comp, r=True)
        
    #メッシュ全体転送
    def all_transfer(self):
        for node in self.transfer_mesh:
            self.adust_skin_influences(node)#インフルエンスを合わせる
            #print('transfer method', self.marged_mesh, 'to',node)
            weight.transfer_weight(self.marged_mesh, node)
            
        
    #現在の頂点配列を取得しておく
    def store_current_vtxArray(self):
        self.node_vtxArray_dict = {}
        for node in self.hl_nodes:
            vtxArray = self.store_skin_weight.om_selected_mesh_vertex(node)
            self.node_vtxArray_dict[node] = vtxArray
        #print('get vtx array :', self.node_vtxArray_dict)
        
    def store_weight_data(self):
        self.store_skin_weight.run_store()
        #self.all_influences = copy.copy(self.store_skin_weight.all_influences)
        self.all_skin_clusters = self.store_skin_weight.all_skin_clusters#ロック全解除のためにスキンクラスタ全部入りリスト作っておく
        #self.hl_nodes = list(set(self.store_skin_weight.mesh_node_list))
        self.influences_dict  = self.store_skin_weight.influences_dict#メッシュごとのインフルエンス一覧
        self.node_vtx_dict  = self.store_skin_weight.node_vtx_dict#メッシュごとの頂点ID一覧
        self.node_weight_dict  = self.store_skin_weight.node_weight_dict#メッシュごとのウェイト一覧
        self.node_skinFn_dict = self.store_skin_weight.node_skinFn_dict
        self.inf_id_list = self.store_skin_weight.inf_id_list
        #print('store inf id list :', self.inf_id_list)
        #for node, infs in self.influences_dict.items():
            #print('node inf :', node, infs)
        
    #焼き込み用辞書を初期化しておく
    def init_bake_data(self):
        if MAYA_VER >= 2016:
            self.bake_node_id_dict = defaultdict(lambda : om2.MIntArray())
            self.bake_node_weight_dict = defaultdict(lambda : om2.MDoubleArray())
            self.bake_node_inf_dict = defaultdict(lambda : om2.MIntArray())
            self.org_node_weight_dict = defaultdict(lambda : om2.MDoubleArray())
        else:
            self.bake_node_id_dict = defaultdict(lambda : om.MIntArray())
            self.bake_node_weight_dict = defaultdict(lambda : om.MDoubleArray())
            self.bake_node_inf_dict = defaultdict(lambda : om.MIntArray())
            self.org_node_weight_dict = defaultdict(lambda : om.MDoubleArray())
        self.undo_node_weight_dict = defaultdict(lambda : [])
        self.redo_node_weight_dict = defaultdict(lambda : [])
        
    #部分転送
    def part_transfer(self):
        self.init_bake_data()#辞書初期化
        #print('part_transfer :', self.transfer_comp)
        
        temp_node_dict = {}
        temp_nodes = []
        for node in self.hl_nodes:
            #スキンクラスタがないとき用に元のメッシュにバインド情報だけ移す
            weight.transfer_weight(self.marged_mesh, node, transferWeight=False)
            self.adust_skin_influences(node)#インフルエンスを合わせる
            #ダミーに転写する
            temp_node = cmds.duplicate(node, rc=True)
            temp_node = cmds.ls(temp_node, l=True)[0]
            weight.transfer_weight(self.marged_mesh, temp_node)
            temp_node_dict[node] = temp_node
            temp_nodes.append(temp_node)
            
        #ダミーと元のウェイトを全取得
        cmds.selectMode(o=True)
        #cmds.select(cl=True)
        cmds.select(self.hl_nodes, temp_nodes)
        self.store_weight_data()
        
        for node in self.hl_nodes:
            vtxArray = self.node_vtxArray_dict[node]
            
            #print('node vtx array :', node , vtxArray)
            temp_node = temp_node_dict[node]
            org_infs = self.influences_dict[node]
            temp_infs = self.influences_dict[temp_node]
            #inf_id_list = range(len(org_weights_list[0]))
            #inf_id_list = [temp_infs.index(inf) for inf in org_infs]
            #インフルエンスの並び順がずれていることがあるので名前でソートする
            inf_id_list = [org_infs.index(inf) for inf in temp_infs]
            # print('adust weight data ;', node, vtxArray)
            # print('org_infs :', org_infs)
            # print('temp_infs :', temp_infs)
            # print('new_inf_list', inf_id_list)
            #ウェイトを整理する
            org_weights_list = self.node_weight_dict[node]
            trans_weights_list = self.node_weight_dict[temp_node]
            #print('get org weight :', org_weights_list)
            #print('get trans weight :', trans_weights_list)
            new_weights = []
            org_weights = []
            for id in vtxArray:
                new_weights += trans_weights_list[id]
                org_weights += org_weights_list[id]
            #print('bake inf ids :', inf_id_list)
            #ノードごとのMArray群辞書にキャスト
            self.bake_node_id_dict[node] += vtxArray
            self.bake_node_weight_dict[node] += new_weights
            self.bake_node_inf_dict[node] += inf_id_list
            self.org_node_weight_dict[node] += org_weights
            self.undo_node_weight_dict[node] = [org_weights_list[id] for id in vtxArray]
            self.redo_node_weight_dict[node] = [trans_weights_list[id] for id in vtxArray]
            
            self.om_bake_skin_weight()
            
        cmds.delete(temp_nodes)
        
    def om_bake_skin_weight(self, realbake=True, ignoreundo=False):
        #焼きこみデータを本体のグローバルに展開
        siweighteditor.set_current_data(self.bake_node_id_dict, self.bake_node_weight_dict, 
                                                    self.bake_node_inf_dict, self.node_skinFn_dict, 
                                                    self.undo_node_weight_dict, self.redo_node_weight_dict,
                                                    self.org_node_weight_dict)#最後はアンドゥようにオリジナル渡す
        #焼きこみコマンド実行
        cmds.bakeSkinWeight(rb=realbake, iu=ignoreundo)
        
    def check_copy_mesh(self):
        for node in self.copy_mesh:
            if cmds.ls(node) == []:
                return False
        return True
        
    def dup_polygon_mesh(self):
        dup_objs = []
        for node in self.copy_mesh:
            #子供のノード退避用ダミーペアレントを用意
            dummy = common.TemporaryReparent().main(mode='create')
            common.TemporaryReparent().main(node,dummyParent=dummy, mode='cut')
            #複製
            dup = cmds.duplicate(node, rc=True)[0]
            cmds.bakePartialHistory(dup, pc=True)
            dup_objs.append(dup)
            #ウェイト転送
            weight.WeightCopyPaste().main(node, mode='copy', saveName=__name__, weightFile=node)
            weight.WeightCopyPaste().main(dup, mode='paste', saveName=__name__, weightFile=node)
            cmds.bakePartialHistory(dup, ppt=True)
            #親子付けを戻す
            common.TemporaryReparent().main(node,dummyParent=dummy, mode='parent')
            #ダミーペアレントを削除
            common.TemporaryReparent().main(dummyParent=dummy, mode='delete')
        #cmds.select(dup_objs)
        return dup_objs
        
        