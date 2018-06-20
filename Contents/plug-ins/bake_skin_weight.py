# -*- coding: utf-8 -*-
import sys
 
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
import maya.api.OpenMaya as om2
import maya.api.OpenMayaUI as omui
 
kPluginCmdName = "bakeSkinWeight" # MELコマンド名
 
kShortFlagName = "-ts"     # 引数のショートネーム
kLongFlagName = "-test"   # 引数のロングネーム
 
def maya_useNewAPI():
    pass
    
##########################################################
# Plug-in :メインの記述部分
##########################################################
class BakeSkinWeightClass( om2.MPxCommand ):
    
    def __init__(self):
        global siweighteditor
        from siweighteditor import siweighteditor
        ''' Constructor. '''
        om2.MPxCommand.__init__(self)
    
    def doIt(self, args):
        realbake, ignore_undo = self.parseArguments( args )
        self.ignore_undo = ignore_undo
        self.bake_node_id_dict, self.bake_node_weight_dict, \
        self.bake_node_inf_dict, self.node_skinFn_dict, \
        self.undo_node_weight_dict, self.redo_node_weight_dict, \
        self.org_node_weight_dict = siweighteditor.get_current_data()
        if realbake:
            self.redoIt(flash=False)
        
    def parseArguments(self, args):
        argData = om2.MArgParser(self.syntax(), args)
        
        if argData.isFlagSet( '-rb' ):
            flagValue = argData.flagArgumentBool( '-rb', 0)
        if argData.isFlagSet( '-iu' ):
            ignore_undo = argData.flagArgumentBool( '-iu', 0)
        return flagValue, ignore_undo
        
    def redoIt(self, flash=True):
        for node, vtxIndices in self.bake_node_id_dict.items():
            weights = self.bake_node_weight_dict[node]
            infIndices = self.bake_node_inf_dict[node]
            skinFn = self.node_skinFn_dict[node]
            
            sList = om.MSelectionList()
            sList.add(node)
            
            meshDag = om.MDagPath()
            component = om.MObject()
            
            sList.getDagPath(0, meshDag, component)
            
            # 指定の頂点をコンポーネントとして取得する
            singleIdComp = om.MFnSingleIndexedComponent()
            vertexComp = singleIdComp.create(om.MFn.kMeshVertComponent )
            singleIdComp.addElements(vtxIndices)
                        
            ##引数（dag_path, MIntArray, MIntArray, MDoubleArray, Normalize, old_weight_undo）
            skinFn.setWeights(meshDag, vertexComp , infIndices , weights, False)
        #アンドゥ用ウェイトデータをアップデートする
        siweighteditor.update_dict(self.redo_node_weight_dict, self.bake_node_id_dict)
        if flash:
            siweighteditor.refresh_window()
            
    
    def undoIt(self):
        siweighteditor.reverse_dict(self.undo_node_weight_dict, self.bake_node_id_dict)
        if self.ignore_undo:#スライダー制御中のアンドゥ履歴は全無視する
            return
        for node, vtxIndices in self.bake_node_id_dict.items():
            weights = self.org_node_weight_dict[node]
            infIndices = self.bake_node_inf_dict[node]
            skinFn = self.node_skinFn_dict[node]
            
            sList = om.MSelectionList()
            sList.add(node)
            
            meshDag = om.MDagPath()
            component = om.MObject()
            
            sList.getDagPath(0, meshDag, component)
            
            # 指定の頂点をコンポーネントとして取得する
            singleIdComp = om.MFnSingleIndexedComponent()
            vertexComp = singleIdComp.create(om.MFn.kMeshVertComponent )
            singleIdComp.addElements(vtxIndices)
                        
            ##引数（dag_path, MIntArray, MIntArray, MDoubleArray, Normalize, old_weight_undo）
            ##old_weightは聞かないので保留
            skinFn.setWeights(meshDag, vertexComp , infIndices , weights, False)
        #アンドゥの度に読み込むと重いからどうしよう。
        siweighteditor.refresh_window()
 
    def isUndoable(self):
        return True
 
##########################################################
# Plug-in initialization.
##########################################################
def cmdCreator():
    return BakeSkinWeightClass() 
    
def syntaxCreator():
    syntax = om2.MSyntax()
    syntax.addFlag( '-rb', '-realbake', om2.MSyntax.kBoolean )
    syntax.addFlag( '-iu', '-ignoreundo', om2.MSyntax.kBoolean )
    return syntax

#
def initializePlugin( mobject ):
    mplugin = om2.MFnPlugin( mobject )
    try:
        mplugin.registerCommand( kPluginCmdName, cmdCreator, syntaxCreator )
        #引数持たせないバージョン
        #mplugin.registerCommand( kPluginCmdName, cmdCreator)
    except:
        sys.stderr.write( 'Failed to register command: ' + kPluginCmdName )
 
def uninitializePlugin( mobject ):
    mplugin = om2.MFnPlugin( mobject )
    try:
        mplugin.deregisterCommand( kPluginCmdName )
    except:
        sys.stderr.write( 'Failed to unregister command: ' + kPluginCmdName ) 