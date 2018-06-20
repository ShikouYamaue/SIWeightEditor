# -*- coding: utf-8 -*-
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
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
        sList = om.MSelectionList()
        if cmds.selectMode(q=True, co=True) and not show_bad:
            om.MGlobal.getActiveSelectionList(sList)
        else:
            #オブジェクト選択の時は子のノードも含める
            #self.hl_nodes = cmds.ls(sl=True, l=True, tr=True)
            selection = cmds.ls(sl=True, type='float3')#コンポーネント選択が混じる場合は強制的にモード変更する
            if selection:
                cmds.selectMode(co=True)
                om.MGlobal.getActiveSelectionList(sList)
            else:
                self.hl_nodes = common.search_polygon_mesh(node, fullPath=True, serchChildeNode=True)
                for node in self.hl_nodes[:]:
                    sList.add(node)
                
        iter = om.MItSelectionList(sList)
        selObj = {}
        loop = 0
        vtxArray = []
        while not iter.isDone():
            loop += 1
            if loop >= 10000:
                print 'too many loop :'
                return []
                
            meshDag = om.MDagPath()
            component = om.MObject()
            
            try:
                iter.getDagPath(meshDag, component)
                #print 'get dag node :', meshDag.fullPathName()
            except:#2016ではノード出したばかりの状態でシェイプがなぜか帰ってくるのでエラー回避
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
            return vtxArray
            #print 'get selected vtx array', vtxArray
            #print 'get current vtx :', vtxArray
            iter.next()
        return []
        
    #すべてのバーテックスIDリストとメッシュ情報の辞書を作って返す
    def om_all_mesh_vertex(self):
        if cmds.selectMode(q=True, co=True):
            #コンポーネント選択の時でもこのポイントがハイライトされた時表示されるように末端まで取る
            self.hl_nodes = cmds.ls(hl=True, l=True)
            self.hl_nodes = common.search_polygon_mesh(self.hl_nodes, fullPath=True, serchChildeNode=True)
            add_node = common.search_polygon_mesh(cmds.ls(sl=True, l=True, tr=True), fullPath=True, serchChildeNode=True)
            if add_node:
                self.hl_nodes += add_node
        else:
            self.hl_nodes = cmds.ls(sl=True, l=True, tr=True) + cmds.ls(hl=True, l=True, tr=True)
            self.hl_nodes = common.search_polygon_mesh(self.hl_nodes, fullPath=True, serchChildeNode=True)
            
        for node in self.hl_nodes[:]:
            
            sList = om.MSelectionList()
            sList.add(node)
            
            meshDag = om.MDagPath()
            component = om.MObject()
            
            try:
                sList.getDagPath(0, meshDag, component)
                #print 'get dag node :', meshDag.fullPathName()
            except Exception as e:#2016ではノード出したばかりの状態でシェイプがなぜか帰ってくるのでエラー回避
                #iter.next()
                print 'get dag path error :'
                continue
            
            skinFn, vtxArray, skinName = self.adust_to_vertex_list(meshDag, component)
            if skinFn is None:
                continue
            self.dag_skin_id_dict[meshDag] = [skinFn, vtxArray, skinName]
            
    def adust_to_vertex_list(self, meshDag, component):
            
            skinFn, skinName = self.om_get_skin_cluster(meshDag)
            if not skinFn or not skinName:
                #iter.next()
                return None, None, None
            #print 'get skin node :', skinFn, skinName
            
            if not meshDag.hasFn(om. MFn.kMesh) or skinName == '' : #メッシュ持ってるかどうか
                #iter.next()
                return None, None, None
            selId = {}
            cmpType = None
            
            #コンポーネントタイプとコンポーネント情報を対にしてMFnMeshクラスとさらに入れ子辞書にする
            #つまりこういうこと{MFnMesh : (CompType:CompData)}
            if component.hasFn(om.MFn.kMeshVertComponent):
                cmpType = "vtx"
            elif component.hasFn(om.MFn.kMeshEdgeComponent):
                cmpType = "edge"
            elif component.hasFn(om.MFn.kMeshPolygonComponent):
                cmpType = "face"
            if cmpType:
                compFn = om.MFnSingleIndexedComponent(component)
                
            #作った辞書情報から頂点情報に変換してIDリストを格納する
            mUtl = om.MScriptUtil()#MScriptUtilはインスタンス化を個別にする必要があるみたい。
            
            meshFn = om.MFnMesh(meshDag)
            #print 'get meshFn Vtx :', meshFn
            if "vtx" == cmpType:
                vtxArray = om.MIntArray()
                compFn.getElements(vtxArray)
            #エッジを頂点IDに変換する
            elif "edge" == cmpType:
                eid = om.MIntArray()
                compFn.getElements(eid)
                eSet = []
                evid = mUtl.asInt2Ptr()#エッジ頂点を受け取るInt2を定義する
                for e in eid:
                    meshFn.getEdgeVertices(e, evid)
                    vid = [mUtl.getInt2ArrayItem(evid, 0, i) for i in range(2)]
                    eSet.extend(vid)
                vids = list(set(eSet))
                vtxArray = om.MIntArray()
                [vtxArray.append(id) for id in vids]
            #フェースを頂点IDに変換する
            elif "face" == cmpType:
                fid = om.MIntArray()
                compFn.getElements(fid)
                #print 'get face id :', fid
                fSet = []
                vid = om.MIntArray()
                for f in fid:
                    meshFn.getPolygonVertices(f, vid)
                    fSet.extend(vid)
                vids = list(set(fSet))
                vtxArray = om.MIntArray()
                [vtxArray.append(id) for id in vids]
            else:
                vids = range(meshFn.numVertices())
                vtxArray = om.MIntArray()
                [vtxArray.append(id) for id in vids]
            #print 'get mesh vtx :', vtxArray
            return skinFn, vtxArray, skinName
        
    #ディペンデンシーグラフをたどってスキンクラスタを探す
    def om_get_skin_cluster(self, dagPath=None):
        if not dagPath:
            return None
        #print 'get dag in skin search :', dagPath.fullPathName()
        
        #メッシュのダグノードイテレータを作って探索、ディペンデンシーデンシーグラフ
        #親子付けがある場合末端まで探してしまうので最初に見つかったらDagノードとノードのDagループ両方Breakする
        dagIterator = om.MItDag(om.MItDag.kDepthFirst,
            om.MFn.kInvalid)
        dagIterator.reset(dagPath .node(),om.MItDag.kDepthFirst,
            om.MFn.kInvalid)
        clusterName = ""
        
        skinFn = None
        while not dagIterator.isDone():
            #print 'search skinFn :', dagIterator.fullPathName()
            curr_obj = dagIterator.currentItem()
            
            #でぃぺんデンシーグラフのイテレータ
            itDG = om.MItDependencyGraph(curr_obj,
                om.MFn.kSkinClusterFilter,
                om.MItDependencyGraph.kUpstream)
                
            #イテレーションが終わるまでスキンクラスタを探す。見つかったら終わり
            while not itDG.isDone():
                try:
                    currentCluster = itDG.currentItem()
                    skinFn = oma.MFnSkinCluster(currentCluster)
                    clusterName = skinFn.name()
                    #print 'get skin :', clusterName, dagIterator.fullPathName()
                except Exception as e:
                    print 'get skin error in om :',e.message
                if skinFn:#見つかったらすぐ終わり
                    break
                itDG.next()
            if skinFn:#こっちも抜ける
                break
            dagIterator.next()
        if clusterName:
            #print 'skincluster founded :', skinFn, clusterName
            return skinFn, clusterName
        else:
            return None, None
        
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
        for meshPath, skin_vtx in self.dag_skin_id_dict.items():
            skinFn = skin_vtx[0]#スキンFn
            vtxArry = skin_vtx[1]#バーテックスIDのリスト
            skinName = skin_vtx[2]#スキン名
            #print skinName, vtxArry
            
            mesh_path_name = meshPath.fullPathName()
            
            self.node_skinFn_dict[mesh_path_name] = skinFn
            #print mesh_path_name
            if cmds.nodeType(meshPath.fullPathName()) == 'mesh':
                mesh_path_name = cmds.listRelatives(mesh_path_name, p=True, f=True)[0]
            
            # シェイプの取得
            meshPath = self.om_get_shape(meshPath.fullPathName())
            meshNode = meshPath.node()
            
            #print 'try to get skin weight :', mesh_path_name, skinFn, vtxArry
            #print 'try to get skin weight :', meshPath.fullPathName()
            
            # 指定の頂点をコンポーネントとして取得する
            singleIdComp = om.MFnSingleIndexedComponent()
            vertexComp = singleIdComp.create(om.MFn.kMeshVertComponent )
            singleIdComp.addElements(vtxArry)
            
            # インフルエンスの数のIntArray
            infDags = om.MDagPathArray()
            skinFn.influenceObjects( infDags )#インフルエンスを全取得
            infIndices = om.MIntArray( infDags.length() , 0 )
            for x in range(infDags.length()):
                infIndices[x] = int(skinFn.indexForInfluenceObject(infDags[x]))
            #print 'get influence id list :', infIndices
                
            # すべてのウエイトの値を取得
            weights = om.MDoubleArray()
            infCountUtil = om.MScriptUtil()
            infCountPtr = infCountUtil.asUintPtr()
            
            try:
                #print 'get weight :',meshPath , vertexComp , weights , infCountPtr
                skinFn.getWeights( meshPath , vertexComp , weights , infCountPtr )
            except Exception as e:
                print 'get skin weight error :', e.message
                continue
            #print 'check weight data type :', type(weights)
            weights = self.conv_weight_shape(len(infIndices), weights)
            #print "getWeights()", weights
            
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
        return [[weights[i+j*shape] for i in range(shape)] for j in range(len(weights)/shape)]
        
    #名前からシェイプを逆引きして返す
    def om_get_shape(self, name):
        sllist = om.MSelectionList()
        om.MGlobal.getSelectionListByName( name , sllist )
        dpg = om.MDagPath()
        sllist.getDagPath( 0 , dpg )
        return dpg

        
        