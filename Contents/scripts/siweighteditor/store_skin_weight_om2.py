# -*- coding: utf-8 -*-
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
from maya import cmds
from . import common

class StoreSkinWeight():
    def run_store(self):
        self.dag_skin_id_dict = {}
        self.om_all_mesh_vertex()
        self.om_get_skin_weight()
        #self.om_selected_mesh_vertex()
        
    #指定ノード中の選択バーテックスを返す
    def om_selected_mesh_vertex(self, node, show_bad=False):
        sList = om2.MGlobal.getActiveSelectionList()
                
        iter = om2.MItSelectionList(sList)
        selObj = {}
        loop = 0
        vtxArrays = []
        while not iter.isDone():
            loop += 1
            if loop >= 10000:
                print 'too many loop :'
                return []
                
            try:
                meshDag, component = iter.getComponent () 
                #print 'get dag node :', meshDag.fullPathName(), component
            except Exception as e:#2016ではノード出したばかりの状態でシェイプがなぜか帰ってくるのでエラー回避
                print 'get current vtx error :', e.message
                iter.next()
                continue
            
            mesh_path_name = meshDag.fullPathName()
            if cmds.nodeType(mesh_path_name) == 'mesh':
                mesh_path_name = cmds.listRelatives(mesh_path_name, p=True, f=True)[0]
            if node != mesh_path_name:
                iter.next()
                continue
            
            #print 'get current vtx :', node, mesh_path_name
            skinFn, vtxArray, skinName = self.adust_to_vertex_list(meshDag, component)
            #print 'get vtx array :', vtxArray
            vtxArrays += vtxArray
            #return vtxArray
            #print 'get selected vtx array', vtxArray
            #print 'get current vtx :', vtxArray
            iter.next()
        return vtxArrays
       
        
    #すべてのバーテックスIDリストとメッシュ情報の辞書を作って返す
    def om_all_mesh_vertex(self):
        #print 'run om2 sotre skin weight :'
        sList = om2.MGlobal.getActiveSelectionList()
        iter = om2.MItSelectionList(sList)
        loop = 0
        om_add_nodes = []
        while not iter.isDone():
            loop += 1
            if loop >= 10000:
                print 'too many loop :'
                return []
            #meshDag = om2.MDagPath()
            #component = om2.MObject()
            try:
                meshDag = iter.getDagPath()
                #print 'get dag node :', meshDag.fullPathName()
            except Exception as e:#2016ではノード出したばかりの状態でシェイプがなぜか帰ってくるのでエラー回避
                #iter.next()
                print 'get dag path error1 :', e.message
                iter.next()
                continue
            mesh_path_name = meshDag.fullPathName()
            om_add_nodes += [mesh_path_name]
            iter.next()
        #print 'om add nodes :', om_add_nodes
        om_add_nodes = [cmds.listRelatives(node, p=True, f=True)[0] if cmds.nodeType(node) == 'mesh' else node for node in om_add_nodes]
        #print 'om add nodes :', om_add_nodes
        
        if cmds.selectMode(q=True, co=True):
            #コンポーネント選択の時でもこのポイントがハイライトされた時表示されるように末端まで取る
            self.hl_nodes = cmds.ls(hl=True, l=True)
            self.hl_nodes = common.search_polygon_mesh(self.hl_nodes, fullPath=True, serchChildeNode=True)
            add_node = common.search_polygon_mesh(cmds.ls(sl=True, l=True, tr=True), fullPath=True, serchChildeNode=True)
            if add_node:
                self.hl_nodes += add_node
            if om_add_nodes:
                self.hl_nodes += om_add_nodes
        else:
            self.hl_nodes = cmds.ls(sl=True, l=True, tr=True) + cmds.ls(hl=True, l=True, tr=True)
            self.hl_nodes = common.search_polygon_mesh(self.hl_nodes, fullPath=True, serchChildeNode=True)
            if om_add_nodes:
                self.hl_nodes += om_add_nodes
        self.hl_nodes = list(set(self.hl_nodes))
            
        for node in self.hl_nodes[:]:
            
            sList = om2.MSelectionList()
            sList.add(node)
            
            
            try:
                meshDag, component = sList.getComponent (0) 
                #print 'get dag node :', meshDag.fullPathName(), component
            except Exception as e:#2016ではノード出したばかりの状態でシェイプがなぜか帰ってくるのでエラー回避
                #iter.next()
                print 'get dag path error2 :', e.message
                continue
            
            skinFn, vtxArray, skinName = self.adust_to_vertex_list(meshDag, component)
            if skinFn is None:
                continue
            self.dag_skin_id_dict[meshDag.fullPathName()] = [skinFn, vtxArray, skinName, meshDag]
            
    def adust_to_vertex_list(self, meshDag, component):
            
            skinFn, skinName = self.om_get_skin_cluster(meshDag)
            if not skinFn or not skinName:
                #iter.next()
                return None, None, None
            #print 'get skin node :', skinFn, skinName
            
            if not meshDag.hasFn(om2.MFn.kMesh) or skinName == '' : #メッシュ持ってるかどうか
                #iter.next()
                return None, None, None
            selId = {}
            cmpType = None
            
            #コンポーネントタイプとコンポーネント情報を対にしてMFnMeshクラスとさらに入れ子辞書にする
            #つまりこういうこと{MFnMesh : (CompType:CompData)}
            if component.hasFn(om2.MFn.kMeshVertComponent):
                cmpType = "vtx"
            elif component.hasFn(om2.MFn.kMeshEdgeComponent):
                cmpType = "edge"
            elif component.hasFn(om2.MFn.kMeshPolygonComponent):
                cmpType = "face"
            if cmpType:
                compFn = om2.MFnSingleIndexedComponent(component)
            #print 'comp type :', cmpType
            
            #作った辞書情報から頂点情報に変換してIDリストを格納する
            
            meshFn = om2.MFnMesh(meshDag)
            #print 'get meshFn Vtx :', meshFn
            if "vtx" == cmpType:
                vtxArray = compFn.getElements()
            #エッジを頂点IDに変換する
            elif "edge" == cmpType:
                eid = compFn.getElements()
                eSet = []
                for e in eid:
                    evid = meshFn.getEdgeVertices(e)
                    eSet.extend(evid)
                vids = list(set(eSet))
                vtxArray = om2.MIntArray()
                [vtxArray.append(id) for id in vids]
            #フェースを頂点IDに変換する
            elif "face" == cmpType:
                fid = compFn.getElements()
                #print 'get face id :', fid
                fSet = []
                for f in fid:
                    vid = meshFn.getPolygonVertices(f)
                    fSet.extend(vid)
                vids = list(set(fSet))
                vtxArray = om2.MIntArray()
                [vtxArray.append(id) for id in vids]
            else:
                vids = range(meshFn.numVertices)
                vtxArray = om2.MIntArray()
                [vtxArray.append(id) for id in vids]
            #print 'get mesh vtx :', vtxArray
            return skinFn, vtxArray, skinName
        
    #ディペンデンシーグラフをたどってスキンクラスタを探す
    def om_get_skin_cluster(self, dagPath=None):
        if not dagPath:
            return None
        skinCluster = cmds.ls(cmds.listHistory(dagPath.fullPathName()), type='skinCluster')
        if not skinCluster:
            return None, None
        clusterName =skinCluster[0]
        sellist = om2.MGlobal.getSelectionListByName(clusterName)
        
        skinNode = sellist.getDependNode(0)
        skinFn = oma2.MFnSkinCluster( skinNode )
        #print 'get skin cluster :', clusterName, skinFn
        return skinFn, clusterName
        
    def om_get_skin_weight(self):
        self.node_weight_dict = {}
        self.node_vtx_dict = {}
        self.inf_id_list = list()
        self.influences_dict = {}
        self.all_influences = list()
        self.all_skin_clusters = {}
        self.mesh_node_list = list()
        self.show_dict = {}#選択セルに表示をフォーカスする辞書
        self.node_skinFn_dict = {}
        for mesh_path_name, skin_vtx in self.dag_skin_id_dict.items():
            skinFn = skin_vtx[0]#スキンFn
            vtxArry = skin_vtx[1]#バーテックスIDのリスト
            skinName = skin_vtx[2]#スキン名
            meshPath = skin_vtx[3]
            #print skinName, vtxArry
            
            self.node_skinFn_dict[mesh_path_name] = skinFn
            #print mesh_path_name
            if cmds.nodeType(meshPath) == 'mesh':
                mesh_path_name = cmds.listRelatives(mesh_path_name, p=True, f=True)[0]
            
            # シェイプの取得
            #meshPath = self.om_get_shape(mesh_path_name)
            #meshNode = meshPath.node()
            
            #print 'try to get skin weight :', mesh_path_name, skinFn, vtxArry
            #print 'try to get skin weight :', meshPath.fullPathName()
            
            # 指定の頂点をコンポーネントとして取得する
            singleIdComp = om2.MFnSingleIndexedComponent()
            vertexComp = singleIdComp.create(om2.MFn.kMeshVertComponent )
            singleIdComp.addElements(vtxArry)
            
            # インフルエンスの数のIntArray
            infDags = skinFn.influenceObjects()#インフルエンスを全取得
            infIndices = om2.MIntArray( len(infDags), 0 )
            for x in xrange(len(infDags)):
                infIndices[x] = int(skinFn.indexForInfluenceObject(infDags[x]))
            #print 'get influence id list :', infIndices
                
            # すべてのウエイトの値を取得
            
            try:
                #print 'get weight :',meshPath , vertexComp , weights , infCountPtr
                weights = skinFn.getWeights( meshPath , vertexComp)
            except Exception as e:
                print 'get skin weight error :', e.message
                continue
            #print 'check weight data type :', type(weights)
            #print "getWeights :", weights
            weights = self.conv_weight_shape(len(infIndices), weights[0])
            #print "getWeights :", weights
            
            #インフルエンス名をフルパスで取得
            influence_list = [infDags[x].fullPathName() for x in range(len(infIndices))]
            #print 'all ifluences :', influence_list
            
            self.node_vtx_dict[mesh_path_name] = vtxArry
            self.all_skin_clusters[mesh_path_name] = skinName
            self.mesh_node_list.append(mesh_path_name)
            self.inf_id_list.append(infIndices)
            self.node_weight_dict[mesh_path_name] = weights#全ての頂点のウエイト一覧
            self.influences_dict[mesh_path_name] = influence_list
            self.all_influences += influence_list
            self.show_dict[mesh_path_name] = vtxArry
        #全てのインフルエンスをまとめる
        self.all_influences = sorted(list(set(self.all_influences)))
    
    #ウェイトをバーテックス単位の2次元配列にリシェイプする
    def conv_weight_shape(self, shape, weights):
        return [[weights[i+j*shape] for i in xrange(shape)] for j in xrange(len(weights)/shape)]
        
    #名前からシェイプを逆引きして返す
    def om_get_shape(self, name):
        sllist = om.MSelectionList()
        om.MGlobal.getSelectionListByName( name , sllist )
        dpg = om.MDagPath()
        sllist.getDagPath( 0 , dpg )
        return dpg

        
        
