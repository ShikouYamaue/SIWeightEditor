# -*- coding: utf-8 -*-
from maya import mel
from maya import cmds
from . import lang
from . import common
import os
import json
import re

class WeightCopyPaste():
    def main(self, skinMeshes, mode='copy', saveName='default', method='index', weightFile='auto', 
                        threshold=0.2, engine='maya', tgt=1, path='default', viewmsg=False):
        if viewmsg:
            cmds.inViewMessage( amg='<hl>Simple Weight</hl> : '+mode, pos='midCenterTop', fade=True, ta=0.75, a=0.5)
        '''
        ウェイトデータの保存、読み込み関数
        mode→コピーするかペーストするか'copy'or'paste'
        saveName→ウェイトデータの保存フォルダ名。ツール、モデル名とかで分けたい場合に指定
        method→ペーストの仕方,「index」、「nearest」、「barycentric」、「over」
        「index」法は、頂点インデックスを使用してウェイトをオブジェクトにマッピングします。マッピング先のオブジェクトと書き出し後のデータのトポロジが同じ場合、これが最も便利な手法です。
        「nearest」法は、読み込んだデータのニアレスト頂点を検索し、ウェイト値をその値に設定します。これは、高解像度メッシュを低解像度メッシュにマッピングする場合に最適です。
        「barycentric」法はポリゴン メッシュでのみサポートされます。ターゲット ジオメトリのニアレスト三角を検索し、
        ソース ポイントと頂点の距離に応じてウェイトを再スケールします。これは通常、高解像度メッシュにマッピングされる粗いメッシュで使用されます。
        「over」法は「index」法に似ていますが、マッピング前に対象メッシュのウェイトがクリアされないため、一致していないインデックスのウェイトがそのまま維持されます。

        nearest と barycentricは不具合のため現状仕様不可能(処理が終わらない)2016/11/03現在
        →barycentric、bylinearはMaya2016Extention2から利用可能

        weightFile→メッシュ名検索でなく手動指定したい場合にパスを指定。methodのnearest、barycentricとセットで使う感じ。
        →Mayaコピー時にファイル名指定すると複数保存できないので注意。
        
        threshold→nearest,barycentricの位置検索範囲
        '''
        self.skinMeshes = skinMeshes
        self.saveName = saveName
        self.method = method
        self.weightFile = weightFile
        self.threshold = threshold
        self.engine = engine
        self.memShapes = {}
        self.target = tgt
        self.pasteMode = {'index':1, 'nearest':3}
        # リストタイプじゃなかったらリストに変換する
        if not isinstance(self.skinMeshes, list):
            temp = self.skinMeshes
            self.skinMeshes = []
            self.skinMeshes.append(temp)
        # ファイルパスを生成しておく
        if path == 'default':
            self.filePath = os.getenv('MAYA_APP_DIR') + '\\Scripting_Files\\weight\\' + self.saveName
        elif path == 'project':
            self.scene_path = '/'.join(cmds.file(q=True, sceneName=True).split('/')[:-1])
            self.protect_path = os.path.join(self.scene_path, 'weight_protector')
            try:
                if not os.path.exists(self.protect_path):
                    os.makedirs(self.protect_path)
            except Exception as e:
                print e.message
                return
            self.filePath = self.protect_pat+'\\' + self.saveName
        self.fileName = os.path.join(self.filePath, self.saveName + '.json')
        self.apiName = os.path.join(self.filePath, self.saveName + '.skn')
        # コピーかペーストをそれぞれ呼び出し
        if mode == 'copy':
            self.weightCopy()
        if mode == 'paste':
            self.weightPaste()

    def weightPaste(self):
        dummy = cmds.spaceLocator()
        for skinMesh in self.skinMeshes:
            # 読みに行くセーブファイル名を指定、autoならメッシュ名
            if self.weightFile == 'auto':
                weightFile = skinMesh
            else:
                weightFile = self.weightFile
            dstSkinCluster = cmds.ls(cmds.listHistory(skinMesh), type='skinCluster')
            # スキンクラスタがない場合はあらかじめ取得しておいた情報をもとにバインドする
            if not dstSkinCluster:
                meshName = str(weightFile).replace('|', '__pipe__')
                if os.path.exists(self.fileName):
                    try:
                        with open(self.fileName, 'r') as f:  # ファイル開く'r'読み込みモード'w'書き込みモード
                            saveData = json.load(f)  # ロード
                            # self.visibility = saveData['visibility']#セーブデータ読み込み
                            skinningMethod = saveData[';skinningMethod']
                            dropoffRate = saveData[';dropoffRate']
                            maintainMaxInfluences = saveData[';maintainMaxInfluences']
                            maxInfluences = saveData[';maxInfluences']
                            bindMethod = saveData[';bindMethod']
                            normalizeWeights = saveData[';normalizeWeights']
                            influences = saveData[';influences']
                        # 子のノードがトランスフォームならダミーに親子付けして退避
                        common.TemporaryReparent().main(skinMesh, dummyParent=dummy, mode='cut')
                        influences = cmds.ls(influences, l=True, tr=True)
                        # バインド
                        dstSkinCluster = cmds.skinCluster(
                            skinMesh,
                            influences,
                            omi=maintainMaxInfluences,
                            mi=maxInfluences,
                            dr=dropoffRate,
                            sm=skinningMethod,
                            nw=normalizeWeights,
                            tsb=True,
                        )
                        dstSkinCluster = dstSkinCluster[0]
                        # 親子付けを戻す
                        common.TemporaryReparent().main(skinMesh, dummyParent=dummy, mode='parent')
                        tempSkinNode = skinMesh#親を取得するためスキンクラスタのあるノードを保存しておく
                    except Exception as e:
                        print e.message
                        print 'Error !! Skin bind failed : ' + skinMesh
                        continue
            else:
                dstSkinCluster = dstSkinCluster[0]
                tempSkinNode = skinMesh#親を取得するためスキンクラスタのあるノードを保存しておく
            if self.engine == 'maya':
                files = os.listdir(self.filePath)
                print files
                if len(files) == 2:
                    for file in files:
                        name, ext = os.path.splitext(file)
                        if ext == '.xml':
                            xml_name = file
                else:
                    # Pipeはファイル名に出来ないので変換しておく
                    meshName = str(weightFile).replace('|', '__pipe__')
                    # コロンはファイル名に出来ないので変換しておく
                    meshName = str(meshName).replace(':', '__colon__')
                    
                    xml_name = meshName + '.xml'
                    
                
                if os.path.isfile(self.filePath + '\\' + xml_name):
                    if self.method == 'index' or self.method == 'over':
                        cmds.deformerWeights(xml_name,
                                             im=True,
                                             method=self.method,
                                             deformer=dstSkinCluster,
                                             path=self.filePath + '\\')
                    else:
                        cmds.deformerWeights(xml_name,
                                             im=True,
                                             deformer=dstSkinCluster,
                                             method=self.method,
                                             worldSpace=True,
                                             positionTolerance=self.threshold,
                                             path=self.filePath + '\\')
                    cmds.skinCluster(dstSkinCluster, e=True, forceNormalizeWeights=True)
                    print 'Weight paste to : ' + str(skinMesh)
                else:
                    print 'Not exist seved weight XML file : ' + skinMesh
        # ダミー親削除
        cmds.delete(dummy)
        cmds.select(self.skinMeshes, r=True)
            
    # ウェイト情報を保存する関数
    def weightCopy(self):
        saveData = {}
        # 保存ディレクトリが無かったら作成
        if not os.path.exists(self.filePath):
            os.makedirs(os.path.dirname(self.filePath + '\\'))  # 末尾\\が必要なので注意
        else:  # ある場合は中身を削除
            files = os.listdir(self.filePath)
            if files is not None:
                for file in files:
                    os.remove(self.filePath + '\\' + file)
        skinFlag = False
        all_influences = []
        for skinMesh in self.skinMeshes:
            try:
                cmds.bakePartialHistory(skinMesh, ppt=True)
            except:
                pass
            # ノードの中からスキンクラスタを取得してくる#inMesh直上がSkinClusterとは限らないので修正
            srcSkinCluster = cmds.ls(cmds.listHistory(skinMesh), type='skinCluster')
            if not srcSkinCluster:
                continue  # スキンクラスタがなかったら次に移行
            tempSkinNode = skinMesh#親を取得するためスキンクラスタのあるノードを保存しておく
            # スキンクラスタのパラメータ色々を取得しておく
            srcSkinCluster = srcSkinCluster[0]
            skinningMethod = cmds.getAttr(srcSkinCluster + ' .skm')
            dropoffRate = cmds.getAttr(srcSkinCluster + ' .dr')
            maintainMaxInfluences = cmds.getAttr(srcSkinCluster + ' .mmi')
            maxInfluences = cmds.getAttr(srcSkinCluster + ' .mi')
            bindMethod = cmds.getAttr(srcSkinCluster + ' .bm')
            normalizeWeights = cmds.getAttr(srcSkinCluster + ' .nw')
            influences = cmds.skinCluster(srcSkinCluster, q=True, inf=True)
            saveData[';skinningMethod'] = skinningMethod
            saveData[';dropoffRate'] = dropoffRate
            saveData[';maintainMaxInfluences'] = maintainMaxInfluences
            saveData[';maxInfluences'] = maxInfluences
            saveData[';bindMethod'] = bindMethod
            saveData[';normalizeWeights'] = normalizeWeights
            all_influences += influences
            #saveData[';influences'] = influences
            skinFlag = True
        all_influences = list(set(all_influences))
        saveData[';influences'] = all_influences
        #インフルエンス数の変化に耐えられるようにあらかじめAddしてからコピーするS
        for skinMesh in self.skinMeshes:
            srcSkinCluster = cmds.ls(cmds.listHistory(skinMesh), type='skinCluster')
            if not srcSkinCluster:
                continue  # スキンクラスタがなかったらfor分の次に移行
            srcSkinCluster = srcSkinCluster[0]
            influences = cmds.skinCluster(srcSkinCluster, q=True, inf=True) 
            sub_influences = list(set(all_influences) - set(influences))
            if sub_influences:
                cmds.skinCluster(skinMesh, e=True, ai=sub_influences, lw=True, ug=True, wt=0, ps=0)
            if self.engine == 'maya':
                # 読みに行くセーブファイル名を指定、autoならメッシュ名
                if self.weightFile == 'auto':
                    weightFile = skinMesh
                else:
                    weightFile = self.weightFile
                # Pipeはファイル名に出来ないので変換しておく
                meshName = str(weightFile).replace('|', '__pipe__')
                # コロンはファイル名に出来ないので変換しておく
                meshName = str(meshName).replace(':', '__colon__')
                cmds.deformerWeights(meshName + '.xml', export=True, deformer=srcSkinCluster, path=self.filePath + '\\')
        with open(self.fileName, 'w') as f:  # ファイル開く'r'読み込みモード'w'書き込みモード
            json.dump(saveData, f)

def transfer_weight(skinMesh, transferedMesh, transferWeight=True, returnInfluences=False, logTransfer=True):
    '''
    スキンウェイトの転送関数
    転送先がバインドされていないオブジェクトの場合は転送元のバインド情報を元に自動バインド
    ・引数
    skinMesh→転送元メッシュ（1個,リスト形式でも可）
    transferedMesh(リスト形式,複数可、リストじゃなくても大丈夫)
    transferWeight→ウェイトを転送するかどうか。省略可能、デフォルトはTrue
    logTransfer→ログ表示するかどうか
    returnInfluences→バインドされているインフルエンス情報を戻り値として返すかどうか。省略可能、デフォルトはFalse
    '''

    massege01 = lang.Lang(
        en=': It does not perform the transfer of weight because it is not a skin mesh.',
        ja=u': スキンメッシュではないのでウェイトの転送を行いません'
    ).output()
    massege02 = lang.Lang(
        en='Transfer the weight:',
        ja=u'ウェイトを転送:'
    ).output()
    massege03 = lang.Lang(
        en='Transfer bind influences:',
        ja=u'バインド状態を転送:'
    ).output()

    if isinstance(skinMesh, list):  # 転送元がリストだった場合、最初のメッシュのみ取り出す
        skinMesh = skinMesh[0]  # リストを渡されたときのための保険
        
    # ノードの中からスキンクラスタを取得してくる#inMesh直上がSkinClusterとは限らないので修正
    srcSkinCluster = cmds.ls(cmds.listHistory(skinMesh), type='skinCluster')
    # srcSkinCluster = cmds.listConnections(skinMesh+'.inMesh', s=True, d=False)
    if not srcSkinCluster:
        if logTransfer:
            print skinMesh + massege01
        return False  # スキンクラスタがなかったら関数抜ける
    # スキンクラスタのパラメータ色々を取得しておく
    srcSkinCluster = srcSkinCluster[0]
    skinningMethod = cmds.getAttr(srcSkinCluster + ' .skm')
    dropoffRate = cmds.getAttr(srcSkinCluster + ' .dr')
    maintainMaxInfluences = cmds.getAttr(srcSkinCluster + ' .mmi')
    maxInfluences = cmds.getAttr(srcSkinCluster + ' .mi')
    bindMethod = cmds.getAttr(srcSkinCluster + ' .bm')
    normalizeWeights = cmds.getAttr(srcSkinCluster + ' .nw')
    influences = cmds.skinCluster(srcSkinCluster, q=True, inf=True)  # qフラグは照会モード、ちなみにeは編集モード

    # リストタイプじゃなかったらリストに変換する
    if not isinstance(transferedMesh, list):
        temp = transferedMesh
        transferedMesh = []
        transferedMesh.append(temp)

    for dst in transferedMesh:
        #子供のノード退避用ダミーペアレントを用意
        dummy = common.TemporaryReparent().main(mode='create')
        common.TemporaryReparent().main(dst,dummyParent=dummy, mode='cut')
        
        shapes = cmds.listRelatives(dst, s=True, pa=True, type='mesh')
        if not shapes:  # もしメッシュがなかったら
            continue  # 処理を中断して次のオブジェクトへ
        # スキンクラスタの有無を取得
        dstSkinCluster = cmds.ls(cmds.listHistory(shapes[0]), type='skinCluster')
        # スキンクラスタがない場合はあらかじめ取得しておいた情報をもとにバインドする
        if not dstSkinCluster:
            # バインド
            dstSkinCluster = cmds.skinCluster(
                dst,
                influences,
                omi=maintainMaxInfluences,
                mi=maxInfluences,
                dr=dropoffRate,
                sm=skinningMethod,
                nw=normalizeWeights,
                tsb=True,
            )
            if logTransfer:
                print massege03 + '[' + skinMesh + '] >>> [' + dst + ']'
        dstSkinCluster = dstSkinCluster[0]

        if transferWeight:
            cmds.copySkinWeights(
                ss=srcSkinCluster,
                ds=dstSkinCluster,
                surfaceAssociation='closestPoint',
                influenceAssociation=['name', 'closestJoint', 'oneToOne'],
                normalize=True,
                noMirror=True
            )
            if logTransfer:
                print massege02 + '[' + skinMesh + '] >>> [' + dst + ']'
        #親子付けを戻す
        common.TemporaryReparent().main(dst,dummyParent=dummy, mode='parent')
        #ダミーペアレントを削除
        common.TemporaryReparent().main(dummyParent=dummy, mode='delete')
    if returnInfluences:
        return influences
    else:
        return True
        
def symmetry_weight(srcNode=None, dstNode=None, symWeight=True):
    '''
    ウェイトシンメトリする関数
    srcNode→反転元
    dstNode→反転先
    symWeight→ウェイトミラーするかどうか
    '''
    # スキンクラスタを取得
    if srcNode is None:
        return
    srcShapes = cmds.listRelatives(srcNode, s=True, pa=True, type='mesh')
    if srcShapes:
        srcSkinCluster = cmds.ls(cmds.listHistory(srcNode), type='skinCluster')
        # スキンクラスタがあったらジョイントラベルを設定してウェイトミラー
        if srcSkinCluster:
            # バインド状態を転送する関数呼び出し
            skinJointAll = cmds.skinCluster(srcSkinCluster, q=True, inf=True) #ジョイントを取得
            for skinJoint in skinJointAll:
                # ジョイントラベル設定関数呼び出し
                joint_label(skinJoint, visibility=False)
            if symWeight is False or dstNode is None:
                return
            transfer_weight(srcNode, dstNode, transferWeight=False, returnInfluences=True)
            dstShapes = cmds.listRelatives(dstNode, s=True, pa=True, type='mesh')
            dstSkinCluster = cmds.listConnections(dstShapes[0] + '.inMesh', s=True, d=False)
            cmds.copySkinWeights(ss=srcSkinCluster[0], ds=dstSkinCluster[0],
                                 mirrorMode='YZ', surfaceAssociation='closestComponent',
                                 influenceAssociation='label', normalize=True)
                                 
def load_joint_label_rules():
    #ロードできなかった時の初期値
    start_l_list = ['L_', 'l_', 'Left_', 'left_']
    start_r_list = ['R_', 'r_', 'Right_', 'right_']
    mid_l_list = ['_L_', '_l_', '_Left_', '_left_']
    mid_r_list = ['_R_', '_r_', '_Right_', '_right_']
    end_l_list = ['_L', '_l', '_L.', '_l.', '_L..', '_l..', '_Left', '_left']
    end_r_list = ['_R', '_r', '_R.', '_r.', '_R..', '_r..', '_Right', '_right']
    def_left_list_list = [start_l_list, mid_l_list, end_l_list]
    def_right_list_list = [start_r_list, mid_r_list, end_r_list]
    #左右対称設定ファイルからルールをロードする
    dir_path = os.path.join(
                    os.getenv('MAYA_APP_dir'),
                    'Scripting_Files')
    start_file = dir_path+'/joint_rule_start.json'
    middle_file = dir_path+'/joint_rule_middle.json'
    end_file = dir_path+'/joint_rule_end.json'
    save_files = [start_file, middle_file, end_file]
    
    left_list_list = []
    right_list_list = []
    for i, save_file in enumerate(save_files):
        if os.path.exists(save_file):#保存ファイルが存在したら
            try:
                with open(save_file, 'r') as f:
                    save_data = json.load(f)
                    l_list = save_data.keys()
                    r_list = save_data.values()
                    left_list_list.append(l_list)
                    right_list_list.append(r_list)
            except Exception as e:
                print e.message
                left_list_list.append(def_left_list_list[i])
                right_list_list.append(def_right_list_list[i])
        else:
            left_list_list.append(def_left_list_list[i])
            right_list_list.append(def_right_list_list[i])
    return left_list_list, right_list_list
    
def joint_label(object, visibility=False):
    '''
    ジョイントラベル設定関数
    object→オブジェクト、リスト形式可
    visibility→ラベルの可視性、省略可能。デフォルトFalse。
    '''
    #ラベリングルールをロードしておく
    left_list_list, right_list_list = load_joint_label_rules()
    
    # リストタイプじゃなかったらリストに変換する
    if not isinstance(object, list):
        temp = object
        object = []
        object.append(temp)
    for skinJoint in object:
        objTypeName = cmds.objectType(skinJoint)
        
        if objTypeName == 'joint':
            split_name = skinJoint.split('|')[-1]
            
            # スケルトン名にLRが含まれているかどうかを判定
            side = 0
            side_name = ''
            for i, (l_list, r_list) in enumerate(zip(left_list_list, right_list_list)):
                for j, lr_list in enumerate([l_list, r_list]):
                    for k, lr in enumerate(lr_list):
                        if i == 0:
                            if re.match(lr, split_name):
                                side = j + 1
                        if i == 1:
                            if re.search(lr, split_name):
                                side = j + 1
                        if i == 2:
                            if re.match(lr[::-1], split_name[::-1]):
                                side = j + 1
                        if side:#対象が見つかってたら全部抜ける
                            side_name = lr
                            break
                    if side:
                        break
                if side:
                    break
            #print 'joint setting :', split_name, side, side_name
            # 左右のラベルを設定、どちらでもないときは中央
            cmds.setAttr(skinJoint + '.side', side)
            # ラベルタイプを”その他”に設定
            cmds.setAttr(skinJoint + '.type', 18)
            new_joint_name = split_name.replace(side_name.replace('.', ''), '')
                
            # スケルトン名設定
            cmds.setAttr(skinJoint + '.otherType', new_joint_name, type='string')
            # 可視性設定
            cmds.setAttr(skinJoint + '.drawLabel', visibility)
        else:
            print(str(skinJoint) + ' : ' + str(objTypeName) + ' Skip Command')
            
#ウェイトのミュートをトグル
def toggle_mute_skinning():
    msg01 = lang.Lang(
        en='No mesh selection.\nWould you like to process all of mesh in this scene?.',
        ja=u'選択メッシュがありません。\nシーン内のすべてのメッシュを処理しますか？').output()
    msg02 = lang.Lang(en='Yes', ja=u'はい').output()
    msg03 = lang.Lang(en='No', ja=u'いいえ').output()
    msg04 = lang.Lang(
        en='Skinning is disabled',
        ja=u'スキニングは無効になりました') .output()
    msg05 = lang.Lang(
        en='Skinning is enabled',
        ja=u'スキニングが有効になりました') .output()
    
    cmds.selectMode(o=True)
    objects = cmds.ls(sl=True, l=True)
    ad_node = []
    
    for node in objects:
        children = cmds.ls(cmds.listRelatives(node, ad=True, f=True), type ='transform')
        ad_node += [node]+children
    #print len(ad_node)
    objects = set(ad_node)
    #print len(objects)
    
    if not objects:
        all_mesh = cmds.confirmDialog(m=msg01, t='', b= [msg02, msg03], db=msg02, cb=msg03, icn='question',ds=msg03)
        if all_mesh == msg02:
            objects = cmds.ls(type='transform')
            
    if not objects:
        return
        
    mute_flag = 1
    skin_list = []
    for node in objects:
        skin = cmds.ls(cmds.listHistory(node), type='skinCluster')
        if not skin:
            continue
        skin_list.append(skin)
        if cmds.getAttr(skin[0]+'.envelope') > 0:
            mute_flag = 0
    for skin in skin_list:
        cmds.setAttr(skin[0]+'.envelope', mute_flag)
    if mute_flag == 0:
        cmds.confirmDialog(m=msg04)
    if mute_flag == 1:
        cmds.confirmDialog(m=msg05)