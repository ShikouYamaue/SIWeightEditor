# -*- coding: utf-8 -*-
from maya import cmds
from maya import mel
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
import maya.OpenMaya as om
import maya.OpenMayaAnim as oma
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
import pymel.core as pm

from collections import defaultdict
from collections import OrderedDict
import datetime as dt
import copy
import time
import itertools
import re
import os
import locale
import json
import webbrowser

from . import common
from . import lang
from . import qt
from . import freeze
from . import weight
from . import weight_transfer_multiple
from . import modeling
from . import symmetrize
from . import joint_rule_editor
from . import go
from . import prof
reload(prof)

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

VERSION = 'r1.1.9'
    
#桁数をとりあえずグローバルで指定しておく、後で設定可変にするつもり
FLOAT_DECIMALS = 4
#0-1か0-100かを切り替えられるように変数指定
MAXIMUM_WEIGHT = 100

MAXIMUM_INFLUENCE_COUNT = 3

ZERO_CELL_DARKEN = 60

WIDGET_HEIGHT = 32
BUTTON_HEIGHT = 22

#トランスファークラスをインスタンス化しておく
WEIGHT_TRANSFER_MULTIPLE = weight_transfer_multiple.WeightTransferMultiple()

#速度計測結果を表示するかどうか
COUNTER_PRINT = True
COUNTER_PRINT = False

#GitHub
HELP_PATH = 'https://github.com/ShikouYamaue/SIWeightEditor/blob/master/README.md'
#リリースページ
REREASE_PATH = 'https://github.com/ShikouYamaue/SIWeightEditor/releases'

#焼きこみプラグインをロードしておく
def load_plugin():
    try:
        check = cmds.pluginInfo('bake_skin_weight.py', query=True, l=True)
        if not check:
            cmds.loadPlugin('bake_skin_weight.py', qt=True)
            cmds.pluginInfo('bake_skin_weight.py', e=True, autoload=True)
    except Exception as e:
        e.message
    #ツールチップもついでに有効か
    cmds.help(popupMode=True)

    
def timer(func):
    #戻す用関数を定義
    def wrapper(*args, **kwargs):
        start = time.time()#開始時間
        func(*args, **kwargs)#関数実行
        end = time.time()#終了時間
        print '-'*50
        print 'Execution time :', func.__name__, end - start
        print '-'*50
    return wrapper
    
def timer(func):
    return func
    
        
#イベント追加したカスタムスピンボックス
class EditorDoubleSpinbox(QDoubleSpinBox):
    wheeled = Signal()
    focused = Signal()
    keypressed = Signal()
    mousepressed = Signal()
    
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.installEventFilter(self)
        
    #ホイールイベントをのっとる
    def wheelEvent(self,e):
        pass
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            self.sel_all_input()
            self.focused.emit()
        if event.type() == QEvent.Wheel:
            delta = event.delta()
            delta /= abs(delta)#120単位を1単位に直す
            shift_mod = self.check_shift_modifiers()
            ctrl_mod = self.check_ctrl_modifiers()
            if shift_mod:
                self.setValue(self.value()+delta*0.001*MAXIMUM_WEIGHT)
            elif ctrl_mod:
                self.setValue(self.value()+delta*0.1*MAXIMUM_WEIGHT)
            else:
                self.setValue(self.value()+delta*0.01*MAXIMUM_WEIGHT)
            cmds.scriptJob(ro=True, e=("idle", self.emit_wheel_event), protected=True)
        if event.type() == QEvent.KeyPress:
            self.keypressed.emit()
        if event.type() == QEvent.MouseButtonPress:
            self.mousepressed.emit()
        return False
        
    def emit_wheel_event(self):
        self.wheeled.emit()
        
    #入力窓を選択するジョブ
    def sel_all_input(self):
        cmds.scriptJob(ro=True, e=("idle", self.select_box_all), protected=True)
        
    #スピンボックスの数値を全選択する
    def select_box_all(self):
        try:
            self.selectAll()
        except:
            pass
            
    def check_shift_modifiers(self):
        mods = QApplication.keyboardModifiers()
        isShiftPressed =  mods & Qt.ShiftModifier
        shift_mod = bool(isShiftPressed)
        return shift_mod
        
    def check_ctrl_modifiers(self):
        mods = QApplication.keyboardModifiers()
        isCtrlPressed =  mods & Qt.ControlModifier
        ctrl_mod = bool(isCtrlPressed)
        return ctrl_mod
        
class EditorSpinbox(QSpinBox):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            self.sel_all_input()
        return False
    #ウェイト入力窓を選択するジョブ
    def sel_all_input(self):
        cmds.scriptJob(ro=True, e=("idle", self.select_box_all), protected=True)
    #スピンボックスの数値を全選択する
    def select_box_all(self):
        try:
            self.selectAll()
        except:
            pass
        
class PopInputBox(qt.SubWindow):
    closed = Signal()
    def __init__(self, parent = None, value=0.0, mode=0, direct=False, pos=None):
        super(self.__class__, self).__init__(parent)
        #↓ウインドウ枠消す設定
        self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint)
        
        #ラインエディットを作成、フォーカスが外れたら消えるイベントを設定
        if direct:
            self.input = qt.LineEdit(self)
            self.setCentralWidget(self.input)
            self.input.setText(value)
            #pos = pos
        else:
            #self.input = EditorDoubleSpinbox(self)
            self.input = QDoubleSpinBox(self)
            self.input.setButtonSymbols(QAbstractSpinBox.NoButtons)
            
            self.setCentralWidget(self.input)
            
            if mode == 0:
                self.input.setDecimals(FLOAT_DECIMALS)
                self.input.setRange(0, MAXIMUM_WEIGHT*10)
                self.input.setValue(value)
            elif mode == 1:
                self.input.setDecimals(FLOAT_DECIMALS)
                self.input.setRange(-1*MAXIMUM_WEIGHT*10 , MAXIMUM_WEIGHT*10)
                self.input.setValue(value)
            elif mode == 2:
                self.input.setDecimals(1)
                self.input.setRange(-999, 999)
            #行を全選択
            self.input.selectAll()
        pos = QCursor.pos()
        
        #位置とサイズ調整
        self.resize(50, 24)
        self.move(pos.x()-20, pos.y()-12)
            
        self.input.editingFinished.connect(self.close)
        self.show()
        
        #ウィンドウを最前面にしてフォーカスを取る
        self.activateWindow()
        self.raise_()
        self.input.setFocus()
        
    def closeEvent(self, e):
        self.closed.emit()
        
#右クリックウィジェットクラスの作成
class RightClickTableView(QTableView):
    rightClicked = Signal()
    keyPressed = Signal(str)
    ignore_key_input = False
    def mouseReleaseEvent(self, e):
        self.mouse_pos = QCursor.pos()
        #print 'view mouse release event :', self.mouse_pos
        if e.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            super(self.__class__, self).mouseReleaseEvent(e)
            
    def keyPressEvent(self, e):
        self.keyPressed.emit(e.text())
        #スーパークラスに行かないとキー入力無効になっちゃうので注意
        if self.ignore_key_input:
            return
        super(self.__class__, self).keyPressEvent(e)
        
#Horizontal_Headerを縦書きにするカスタムHeader_View
class MyHeaderView(QHeaderView):
    doubleClicked = Signal(int)
    rightClicked = Signal()
    active_section_list = []
    def __init__(self, parent=None):
        super(MyHeaderView, self).__init__(Qt.Horizontal, parent)
        self._font = QFont("helvetica", 9)
        self._actived_font = QFont("helvetica", 9)
        self._actived_font.setWeight(63)#太くする
        self._metrics = QFontMetrics(self._font)
        self._descent = self._metrics.descent()
        self._margin = 5
        try:
            #PySide
            self.setClickable(True)
        except:
            #PySide2
            self.setSectionsClickable(True)
        self.setHighlightSections(True)
        
        #self.sectionEntered.connect(self.section_enter)
        #self.sectionClicked.connect(self.clicked_section)
        self.sectionDoubleClicked.connect(self.double_clicked_section)
        
    def mouseReleaseEvent(self, e):
        WINDOW.view_widget.mouse_pos = QCursor.pos()
        if e.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            super(self.__class__, self).mouseReleaseEvent(e)
            
    #セクションがクリックされた時のスロット
    def double_clicked_section(self, e):
        #print 'double clicked section', e
        self.doubleClicked.emit(e)
        
    #セクションがクリックされた時のスロット
    def clicked_section(self, e):
        print ' clicked_section', e
        
    #セクションが範囲選択された時のスロット
    def section_enter(self, e):
        print 'section_enter',e

    #@prof.profileFunction()
    def paintSection(self, painter, rect, index):
        painter.rotate(-90)#90度回転
        data = self._get_data(index)#インフルエンス名
        #data = 'test'
        data = data.split(':')[-1]
        is_active = self.check_section_is_active(index)#セクションがアクティブかどうか
        
        if is_active:
            font = self._actived_font
        else:
            font = self._font
        painter.setFont(font)
        
        color = self.model().headerData(index, Qt.Horizontal, Qt.BackgroundRole)#HeaderDataで設定する色を取る
        dark_color = QColor(*map(lambda c:c-42, color.getRgb()[:3]))#暗めの色つくる
        #ベースの色を塗る
        draw_rect = self.rotate_rect(index, rect)
        painter.fillRect(draw_rect , color)
        
        #Penで色を設定して線を描く
        painter.setPen(QPen(dark_color))
        painter.drawRect(draw_rect)
        
        #文字の色を指定して描く
        painter.setPen(QColor(*[230]*3))
        
        tx = - rect.height() + self._margin
        ty = rect.left() + (rect.width() + self._descent) / 2 
        painter.drawText(tx, ty, data)
        
        
    #現在のセクションがアクティブかどうかを判定する
    def check_section_is_active(self, index):
        sel_model = self.selectionModel()#ビューに設定されている選択モデルを取得する
        selected_item = sel_model.currentIndex()
        is_active = sel_model.columnIntersectsSelection(index, selected_item)
        #print 'header is active :', is_active
        return is_active
        
        
    #90°回転したRectのリストとオフセットを補正する。
    def rotate_rect(self,index, rect):
        #最初の1カラム目だけ1ピクセル補正
        if index == 0:
            offset = 1
        else:
            offset = 0
        rect = rect.getRect()
        rect = [rect[1]-rect[3]+1, rect[0]-1+offset, rect[3]-1, rect[2]-offset]
        rect = QRect(*rect)
        return rect
        
    def sizeHint(self):
        return QSize(0, self._get_text_width() + 2 * self._margin)

    def _get_text_width(self):
        width_list = [self._metrics.width(self._get_data(i)) for i in range(0, self.model().columnCount())] or [0]
        max_width = max(width_list) *1.1
        return max_width

    def _get_data(self, index):
        return self.model().headerData(index, self.orientation(), 0)
        
#QTableView用ヘッダー設定
def set_table_header_width(view, model, index=None, space=55, max=55, add=0):
    max += add
    if hasattr(view.horizontalHeader(), 'setResizeMode'):
        resize_mode = view.horizontalHeader().setResizeMode  # PySide
    else:
        resize_mode = view.horizontalHeader().setSectionResizeMode # PySide2

    def __resize_main(index):
        width = space + add
        if MAXIMUM_WEIGHT == 1.0:
            width -= 7
        if width > max:
            width = max
        view.setColumnWidth(index, width)

    if index is None:
        count = model.columnCount()
        for i in range(count):
            __resize_main(i)
    else:
        __resize_main(index)
        
class TableModel(QAbstractTableModel):
    norm = False
    #reset_flag = False
    def __init__(self, data, parent=None, mesh_rows=[], influences=[], 
                        v_header_list=[], header_color_list=[]):
        super(TableModel, self).__init__(parent)
        
        self.under_weight_rows = set()#合計値が1.0以下の行リスト
        self.over_weight_rows = set()#合計値が1.0以上の行のリスト
        self.over_influence_limit_dict = {}#行の使用中インフルエンス数格納辞書row:インフル数
        self.over_influence_limit_rows = set()#インフルオーバーリストを後付けで作る、show_bad参照用
        self.none_cells = []#インフルエンスの対応のないセルを格納する
        self.v_header_list = v_header_list
        self.mesh_rows = mesh_rows
        self.weight_lock_cells = set()
        self.header_list = influences
        self.header_color_list = header_color_list
        self._data = data
    
    #ヘッダーを設定する関数をオーバーライド
    def headerData(self, id, orientation, role):
        u"""見出しを返す"""
        if orientation == Qt.Horizontal:
            if id >= len(self.header_list):
                return None
            if role == Qt.DisplayRole:
                return self.header_list[id].split('|')[-1]
            elif role == Qt.BackgroundRole:#バックグラウンドロールなら色変更する
                color_id = self.header_color_list[id]
                return QColor(*self.joint_color_list[color_id])
                
        if orientation == Qt.Vertical:
            if role == Qt.DisplayRole:
                return self.v_header_list[id]
            elif role == Qt.BackgroundRole:#バックグラウンドロールなら色変更する
                #メッシュ行なら含む行を比較して順番に色を変えるか判断する
                #ほぼ処理負荷なし
                if id in self.mesh_rows:
                    end_of_mesh_rows = self.mesh_rows[self.mesh_rows.index(id)+1] 
                    mesh_rows = set(range(id+1,end_of_mesh_rows))
                    if mesh_rows & self.under_weight_rows:
                        return QColor(*self.under_weight_color)
                    if mesh_rows & self.over_weight_rows:
                        return QColor(*self.over_weight_color)
                    for mrow in mesh_rows:
                        if self.over_influence_limit_dict[mrow] > MAXIMUM_INFLUENCE_COUNT > 0:
                            return QColor(*self.over_influence_color)
                            
                if id in self.under_weight_rows:
                    return QColor(*self.under_weight_color)
                if id in self.over_weight_rows:
                    return QColor(*self.over_weight_color)
                try:
                    if self.over_influence_limit_dict[id] > MAXIMUM_INFLUENCE_COUNT > 0:
                        return QColor(*self.over_influence_color)
                except:
                    pass
                return QColor(*self.v_header_bg)
            elif role == Qt.TextAlignmentRole:
                return Qt.AlignRight
        return None
        
    def rowCount(self, parent=None):
        return len(self._data)
    
    def columnCount(self, parent=None):
        return len(self._data[0])-1 if self.rowCount() else 0
        
    joint_color_list = [
                        [161, 105,  48],
                        [159, 161,  48],
                        [104, 161,  48],
                        [ 48, 161,  93],
                        [ 48, 161, 161],
                        [ 48, 103, 161],
                        [111,  48, 161],
                        [161,  48, 105]
                        ]
    v_header_text = [220]*3
    v_header_bg = [100]*3
    under_weight_color = [230,54,54]
    over_weight_color = [210,116,32]
    over_influence_color = [210,190,40]
    lock_weight_bg_color = [100]*3
    lock_weight_text_color = [160]*3
    
    #データ設定関数をオーバーライド流れてくるロールに応じて処理
    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        column = index.column()
        if role == Qt.DisplayRole:
            try:
                #抜けカラムを考慮したインフルエンスIDを取得
                node = WINDOW.vtx_row_dict[row][6]
                inf_id_list = WINDOW.node_influence_id_list_dict[node]
                local_column = inf_id_list[column]
                weight = self._data[row][local_column]*MAXIMUM_WEIGHT
                #指定桁数にまとめる、formatで自動的に桁数そろえてくれるみたい
                return FLOAT_FORMAT.format(weight)
            except Exception as e:
                #print e.message
                return None
        elif role == Qt.BackgroundRole:#バックグラウンドロールなら色変更する
            if row in self.mesh_rows:
                color_id = self.header_color_list[column]
                return QColor(*self.joint_color_list[color_id])
            if (row, column) in self.weight_lock_cells:
                return QColor(*self.lock_weight_bg_color)
        elif role == Qt.ForegroundRole:
            zero_flag = False
            color = [210]*3
            try:
                node = WINDOW.vtx_row_dict[row][6]
                inf_id_list = WINDOW.node_influence_id_list_dict[node]
                local_column = inf_id_list[column]
                weight = self._data[row][local_column]*MAXIMUM_WEIGHT
                if weight == 0.0:
                    zero_flag=True
            except:
                pass
                
            if (row, column) in self.weight_lock_cells:
                color = self.lock_weight_text_color
            else:
                if row in self.under_weight_rows:
                    color = self.under_weight_color
                elif row in self.over_weight_rows:
                    color = self.over_weight_color
                else:
                    try:
                        if self.over_influence_limit_dict[row] > MAXIMUM_INFLUENCE_COUNT > 0:
                            color = self.over_influence_color
                    except:
                        pass
                if zero_flag:
                    color = [min([c - ZERO_CELL_DARKEN, 255]) if c - ZERO_CELL_DARKEN > 43 else 43 for c in color]
                    
            return QColor(*color)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignRight
                
    def get_data(self, index=None, row=0, column=0):
        try:
            if index:
                row = index.row()
                column = index.column()
            node = WINDOW.vtx_row_dict[row][6]
            inf_id_list = WINDOW.node_influence_id_list_dict[node]
            local_column = inf_id_list[column]
            value  = self._data[row][local_column]
        except Exception as e:
            print 'get data error :', e
            value = None
        return value
        
    #データセットする関数をオーバライド
    def setData(self, index, value, role=Qt.EditRole):
        if not isinstance(index, tuple):
            if not index.isValid() or not 0 <= index.row() < len(self._data):
                print 'can not set data : retrun'
                return
            row = index.row()
            column = index.column()
        else:
            row = index[0]
            column = index[1]
        if role == Qt.EditRole and value != "":
            #抜けカラムを考慮したインフルエンスIDを取得
            node = WINDOW.vtx_row_dict[row][6]
            inf_id_list = WINDOW.node_influence_id_list_dict[node]
            local_column = inf_id_list[column]#空白セルを考慮したローカルカラム取得
            
            self._data[row][local_column] = value
            self.dataChanged.emit((row, column), (row, column))#データをアップデート
            return True
        else:
            return False
            
    # 各セルのインタラクション
    def flags(self, index):
        row = index.row()
        column = index.column()
        try:
            node = WINDOW.vtx_row_dict[row][6]
            inf_id_list = WINDOW.node_influence_id_list_dict[node]
            local_column = inf_id_list[column]
            value = self._data[row][local_column]
        except:
            value = None
        if row in self.mesh_rows or value is None:
            return Qt.ItemIsEnabled
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
      
#モデルのアイテムインデックスを全部返してくれる。便利。
def model_iter(model, parent_index=QModelIndex(), col_iter=True):
    """ モデルのイテレータ
    :rtype: generator(QModelIndex)
    :type col_iter: bool
    :type parent_index: QModelIndex
    :type model: QAbstractItemModel
    """
    index = model.index(0, 0, parent_index)

    while True:
        if col_iter:
            for col in range(0, model.columnCount(parent_index)):
                yield index.sibling(index.row(), col)
        else:
            yield index

        if model.rowCount(index) > 0:
            for _ in model_iter(model, index, col_iter):
                yield _

        index = index.sibling(index.row() + 1, index.column())
        if not index.isValid():
            break
            
class Option():
    def __init__(self):
        global WINDOW
        try:
            WINDOW.closeEvent(None)
            WINDOW.close()
        except Exception as e:
            print e.message
        WINDOW = MainWindow()
        WINDOW.init_flag=False
        WINDOW.move(WINDOW.pw-8, WINDOW.ph-31)
        #ウィンドウ幅が狭くても正しくボタン再配置できるように大きいサイズから縮めておく
        for i in range(0, 800, 50):
            WINDOW.resize(1000 - i, 800)
        WINDOW.resize(WINDOW.sw, WINDOW.sh)
        WINDOW.show()
        #WINDOW.get_set_skin_weight()
        #起動時に取得実行
        #cmds.scriptJob(ro=True, e=("idle", lambda : WINDOW.get_set_skin_weight()), protected=True)
        
class MainWindow(qt.MainWindow):
    selection_mode = 'tree'
    filter_type = 'scene'
    icon_path = os.path.join(os.path.dirname(__file__), 'icon/')
    
    def init_save(self):
        temp = __name__.split('.')
        self.dir_path = os.path.join(
            os.getenv('MAYA_APP_dir'),
            'Scripting_Files')
        self.w_file = self.dir_path+'/'+temp[-1]+'_window.json'
    
    #セーブファイルを読み込んで返す　   
    def load_window_data(self, init_pos=False):
        global MAXIMUM_WEIGHT
        #セーブデータが無いかエラーした場合はデフォファイルを作成
        if init_pos:
            self.init_save_data()
            return
        #読み込み処理
        if os.path.exists(self.w_file):#保存ファイルが存在したら
            try:
                with open(self.w_file, 'r') as f:
                    save_data = json.load(f)
                    self.pw = save_data['pw']
                    self.ph = save_data['ph']
                    self.sw = save_data['sw']
                    self.sh = save_data['sh']
                    self.hilite_vtx = save_data['hilite']
                    self.lock = save_data['lock'] 
                    self.mesh = True#メッシュ選択変更切り替え反映機能はいったんなしに
                    self.focus = save_data['focus']
                    self.mode = save_data['mode']
                    self.norm = save_data['norm']
                    self.limit = save_data['limit']
                    self.filter = save_data['filter']
                    self.no_limit = save_data['no_limit']
                    self.digit = save_data['digit']
                    self.round = save_data['round']
                    self.under_wt = save_data['under_wt']
                    self.over_wt = save_data['over_wt']
                    self.over_inf = save_data['over_inf']
                    self.max_wt = save_data['max']
                    self.joint_tool = save_data['joint_tool']
                    self.joint_hilite = save_data['joint_hilite']
                    self.search_mode = save_data['search_mode']
                    self.darken_value = save_data['darken_value']
                    self.interactive = save_data['interactive']
            except Exception as e:
                self.init_save_data()
        else:
            self.init_save_data()
            
    def init_save_data(self):
        self.area = None
        self.pw = 200
        self.ph = 200
        self.sw = 440
        self.sh = 700
        self.digit = 1
        self.round = 1
        self.hilite_vtx = False
        self.lock = False
        self.focus = True
        self.mode = 0
        self.norm = True
        self.limit = 0
        self.filter = False
        self.no_limit = False
        self.over_wt = False
        self.under_wt = False
        self.over_inf = False
        self.joint_tool = 0
        self.joint_hilite = False
        self.max_wt = 100
        self.search_mode = 0
        self.darken_value = 150
        self.interactive = False
    
    def save_window_data(self, display=True):
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)
        save_data = {}
        dock_dtrl = self.parent()
        pos = self.pos()
        size = self.size()
        save_data['pw'] = pos.x()+8
        save_data['ph'] = pos.y()+31
        save_data['sw'] = size.width()
        save_data['sh'] = size.height()
        save_data['hilite'] = self.highlite_but.isChecked()
        save_data['lock'] = self.lock_but.isChecked()
        save_data['focus'] = self.focus_but.isChecked()
        save_data['mode'] = self.mode_but_group.checkedId()
        save_data['norm'] = self.norm_but.isChecked()
        save_data['limit'] = self.limit_box.value()
        save_data['filter'] = self.filter_but.isChecked()
        save_data['no_limit'] = self.no_limit
        save_data['max'] = self.max_wt
        save_data['digit'] = self.digit_box.value()
        save_data['round'] = self.round_box.value()
        save_data['under_wt'] = self.under_wt_but.isChecked()
        save_data['over_wt'] = self.over_wt_but.isChecked()
        save_data['over_inf'] = self.over_inf_but.isChecked()
        save_data['joint_tool'] = self.joint_tool
        save_data['joint_hilite'] = self.joint_hl_but.isChecked()
        save_data['search_mode'] = self.search_but_group.checkedId()
        save_data['darken_value'] = self.zero_darken.value()
        save_data['interactive'] = self.interactive_but.isChecked()
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)
        with open(self.w_file, 'w') as f:
            json.dump(save_data, f)
        
    pre_selection_node = []
    def __init__(self, parent = None, init_pos=False):
        super(self.__class__, self).__init__(parent)
        load_plugin()#プラグインロード
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.init_save()
        self.wdata = self.load_window_data()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.icon_path = os.path.join(os.path.dirname(__file__), 'icons/')
        #OpenMayaでウェイト取得するクラスを実態化しておく
        self.store_skin_weight = store_skin_weight.StoreSkinWeight()
        #self.setAcceptDrops(True)#ドロップ可能にしておく
        self._init_ui()
    
    show_flag = False    
    def _init_ui(self, job_create=True):
        self.counter = prof.LapCounter()#ラップタイム計測クラス
        self.init_flag=True
        sq_widget = QScrollArea(self)
        sq_widget.setWidgetResizable(True)#リサイズに中身が追従するかどうか
        sq_widget.setFocusPolicy(Qt.NoFocus)#スクロールエリアをフォーカスできるかどうか
        sq_widget.setMinimumHeight(1)#ウィンドウの最小サイズ
        self.setWindowTitle(u'- SI Weight Editor / ver_'+VERSION+' -')
        self.setCentralWidget(sq_widget)
        
        self.main_layout = QVBoxLayout()
        sq_widget.setLayout(self.main_layout)
        
        self.unique_layout = QGridLayout()
        self.unique_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        self.main_layout.addLayout(self.unique_layout)
        
        self.but_list = []
        
        self.ui_color = 68
        self.hilite = 114
        self.lock_col = [180, 60, 60]
        self.red = [150, 60, 60]
        self.orange = [150,96,32]
        self.yellow = [150,125,20]
        but_h = BUTTON_HEIGHT
        
        #表示ボタンをはめる
        show_widget = QWidget()
        show_widget.setGeometry(QRect(0, 0, 0 ,0))
        show_layout = QHBoxLayout()
        show_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        show_widget.setLayout(show_layout)
        but_w = 60
        norm_w =75
        space = 13
        show_widget.setMinimumWidth(but_w*5+space)
        show_widget.setMaximumWidth(but_w*5+space)
        show_widget.setMaximumHeight(WIDGET_HEIGHT)
        tip = lang.Lang(en='Show only selected cells', ja=u'選択セルのみ表示').output()
        self.show_but = qt.make_flat_btton(name='Show', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Show all cells', ja=u'全てのセルを表示').output()
        self.show_all_but = qt.make_flat_btton(name='Show All', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Reflect component selection change in UI', ja=u'コンポーネント選択変更をUIに反映する').output()
        self.focus_but = qt.make_flat_btton(name='Focus', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.focus_but.setChecked(self.focus)
        #self.focus_but.setDisabled(True)#無効化
        tip = lang.Lang(en='Toggle display / non-display of Influence with all zero weights being displayed', ja=u'表示中のウェイトがすべてゼロのインフルエンスの表示/非表示を切り替える').output()
        self.filter_but = qt.make_flat_btton(name='Filter', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.filter_but.setChecked(self.filter)
        #self.filter_but.setDisabled(True)#無効化
        tip = lang.Lang(en='Highlite points in 3D view to reflect the weight editor selection', ja=u'ウェイトエディタの選択をポイントハイライトに反映').output()
        self.highlite_but = qt.make_flat_btton(name='Highlite', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.highlite_but.setChecked(self.hilite_vtx)
        self.show_but.clicked.connect(self.show_selected_cells)
        self.show_all_but.clicked.connect(self.show_all_cells)
        self.highlite_but.clicked.connect(self.reset_hilite)
        self.filter_but.clicked.connect(lambda : self.get_set_skin_weight(filter=True))
        show_layout.addWidget(self.show_but)
        show_layout.addWidget(self.show_all_but)
        show_layout.addWidget(self.focus_but)
        show_layout.addWidget(self.filter_but)
        show_layout.addWidget(self.highlite_but)
        
        #不具合行にフォーカスするボタン
        show_bad_widget = QWidget()
        show_bad_layout = QHBoxLayout()
        show_bad_layout.setSpacing(0)
        show_bad_widget.setLayout(show_bad_layout)
        but_w = 70
        space = 14
        show_bad_widget.setMinimumWidth(but_w*4+space)
        show_bad_widget.setMaximumWidth(but_w*4+space)
        show_bad_widget.setMaximumHeight(WIDGET_HEIGHT)
        tip = lang.Lang(en='Focus on the vertex of an incorrect weight value',  ja=u'不正なウェイト値の頂点にフォーカスする').output()
        self.show_bad_but = qt.make_flat_btton(name='Show Bad', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Incorrect display setting: Vertex weight of total less than 1.0',  ja=u'不正表示設定 ： 合計1.0未満の頂点ウェイト').output()
        self.under_wt_but = qt.make_flat_btton(name='Under Wt', bg=self.red, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Incorrect display setting: Vertex weight larger than 1.0 in total',  ja=u'不正表示設定 ： 合計1.0より大きい頂点ウェイト').output()
        self.over_wt_but = qt.make_flat_btton(name='Over Wt', bg=self.orange, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Incorrect display setting: vertices larger than the specified influence number',  ja=u'不正表示設定 ： 指定インフルエンス数以上の頂点').output()
        self.over_inf_but = qt.make_flat_btton(name='Influences', bg=self.yellow, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.show_bad_but.clicked.connect(self.show_bad_rows)
        self.under_wt_but.setChecked(self.under_wt)
        self.over_wt_but.setChecked(self.over_wt)
        self.over_inf_but.setChecked(self.over_inf)
        show_bad_layout.addWidget(self.show_bad_but)
        show_bad_layout.addWidget(self.under_wt_but)
        show_bad_layout.addWidget(self.over_wt_but)
        show_bad_layout.addWidget(self.over_inf_but)
        
        #アイコンボタン群
        icon_widget = QWidget()
        icon_layout = QHBoxLayout()
        icon_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        icon_widget.setLayout(icon_layout)
        but_w = BUTTON_HEIGHT#常に正方形になるように高さと合わせる
        space = 10
        wid_a = but_w*4+space
        tip = lang.Lang(en='Lock display mesh', ja=u'表示メッシュのロック').output()
        self.lock_but = qt.make_flat_btton(name='', bg=self.lock_col, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=True, destroy_flag=True, icon=self.icon_path+'lock.png', tip=tip)
        tip = lang.Lang(en='Update the view based on object selection', ja=u'オブジェクト選択に基づきビューを更新').output()
        self.cycle_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'cycle.png', tip=tip)
        tip = lang.Lang(en='Clear the view', ja=u'ビューのクリア').output()
        self.clear_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'clear.png', tip=tip)
        tip = lang.Lang(en='Select vertices from cell selection', ja=u'セル選択から頂点を選択').output()
        self.adjust_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'adjust.png', tip=tip)
        self.lock_but.setChecked(self.lock)
        self.lock_but.clicked.connect(self.check_unlock)
        self.cycle_but.clicked.connect(lambda : self.get_set_skin_weight(cycle=True))
        self.clear_but.clicked.connect(lambda : self.get_set_skin_weight(clear=True))
        self.adjust_but.clicked.connect(self.select_vertex_from_cells)
        
        but_w = 40
        space = 8
        wid_b = but_w*2+space
        
        self.max_value_but_group = QButtonGroup()
        tip = lang.Lang(en='Displaying the weight value from 0.0 to 1.0', ja=u'0.0～1.0でウェイト値を表示する').output()
        self.w1_but = qt.make_flat_btton(name='0-1', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Displaying the weight value from 0 to 100', ja=u'0～100でウェイト値を表示する').output()
        self.w100_but = qt.make_flat_btton(name='0-100', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.max_value_but_group.addButton(self.w1_but, 0)
        self.max_value_but_group.addButton(self.w100_but, 1)
        self.pre_max_id = round(self.max_wt/100, 1)
        self.max_value_but_group.button(self.pre_max_id).setChecked(True)
        self.max_value_but_group.buttonClicked[int].connect(self.change_maximum_weight)
        self.max_value_but_group.buttonClicked[int].connect(self.change_max_decimal_digit)
        
        global MAXIMUM_WEIGHT
        MAXIMUM_WEIGHT = self.max_wt
        
        icon_widget.setMinimumWidth(wid_a+wid_b)
        icon_widget.setMaximumWidth(wid_a+wid_b)
        icon_widget.setMaximumHeight(WIDGET_HEIGHT)
        
        icon_layout.addWidget(self.lock_but)
        icon_layout.addWidget(self.cycle_but)
        icon_layout.addWidget(self.clear_but)
        icon_layout.addWidget(self.adjust_but)
        icon_layout.addWidget(self.w1_but)
        icon_layout.addWidget(self.w100_but)
        
        
        #enforce_limitを設定する
        enforce_widget = QWidget()
        enforce_layout = QHBoxLayout()
        enforce_layout.setSpacing(4)
        enforce_widget.setLayout(enforce_layout)
        but_w = 85
        spin_w = 40
        space = 24
        enforce_widget.setMinimumWidth(but_w+spin_w+space)
        enforce_widget.setMaximumWidth(but_w+spin_w+space)
        enforce_widget.setMaximumHeight(WIDGET_HEIGHT)
        tip = lang.Lang(en='Enforce the limit on the number of deformers that can affect a given vertex\n* Apply to all vertices by executing without selecting a cell', 
                        ja=u'指定された頂点に影響を与えるデフォーマの数に制限を設定\n※セルを選択せずに実行で全頂点に適用').output()
        self.enforce_but = qt.make_flat_btton(name='Enforce Limit', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        self.enforce_but.clicked.connect(self.enforce_limit_and_normalize)
        self.limit_box = EditorSpinbox()
        #self.limit_box.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.limit_box.setRange(0, 16)
        self.limit_box.setValue(self.limit)
        self.limit_box.setMaximumWidth(spin_w)
        self.limit_box.setMinimumWidth(spin_w)
        self.limit_box.setMinimumHeight(BUTTON_HEIGHT)
        self.limit_box.valueChanged.connect(self.change_limit_box_color)
        self.limit_box.valueChanged.connect(self.change_limit)
        enforce_layout.addWidget(self.enforce_but)
        enforce_layout.addWidget(self.limit_box)
        self.change_limit_box_color()#0の時は何も入力されてないように見えるようにする
        
        global MAXIMUM_INFLUENCE_COUNT
        MAXIMUM_INFLUENCE_COUNT = self.limit
        
        #桁数設定ウィジェット
        decimal_widget = QWidget()
        decimal_layout = QHBoxLayout()
        decimal_layout.setSpacing(4)
        decimal_widget.setLayout(decimal_layout)
        but_w = 85
        spin_w = 40
        space = 28
        decimal_widget.setMinimumWidth(but_w*2+spin_w*2+space)
        decimal_widget.setMaximumWidth(but_w+spin_w+space)
        decimal_widget.setMaximumHeight(WIDGET_HEIGHT)
        tip = lang.Lang(en='Set the number of decimal places to be displayed', 
                        ja=u'表示される小数点以下の桁数を設定').output()
        self.decimal_but = qt.make_flat_btton(name='Display Digit', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        self.digit_box = EditorSpinbox()
        offset = (1 - self.max_value_but_group.checkedId()) * 2
        self.digit_box.setRange(offset, 7 + offset)
        self.digit_box.setValue(self.digit)
        self.digit_box.setMaximumWidth(spin_w)
        self.digit_box.setMinimumWidth(spin_w)
        self.digit_box.setMinimumHeight(BUTTON_HEIGHT)
        self.digit_box.valueChanged.connect(self.change_decimal_digits)
        
        #フォーマット設定と桁数をグローバルに設定しておく
        global FLOAT_DECIMALS
        FLOAT_DECIMALS = self.digit
        global FLOAT_FORMAT
        FLOAT_FORMAT = '{:.'+str(FLOAT_DECIMALS)+'f}'
        
        but_w = 70
        tip = lang.Lang(en='Round off the decimal point with the specified number of digits\n* Apply to all vertices by executing without selecting a celｌ', 
                        ja=u'小数点以下を指定桁数で丸める\n※セルを選択せずに実行で全頂点に適用').output()
        self.round_but = qt.make_flat_btton(name='Round Off', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        self.round_but.clicked.connect(self.round_off)
        self.round_box = EditorSpinbox()
        #self.digit_box.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        offset = (1 - self.max_value_but_group.checkedId()) * 2
        self.round_box.setRange(offset, 7 + offset)
        self.round_box.setValue(self.round)
        self.round_box.setMaximumWidth(spin_w)
        self.round_box.setMinimumWidth(spin_w)
        self.round_box.setMinimumHeight(BUTTON_HEIGHT)
        
        decimal_layout.addWidget(self.decimal_but)
        decimal_layout.addWidget(self.digit_box)
        
        decimal_layout.addWidget(QLabel('  '))
        decimal_layout.addWidget(self.round_but)
        decimal_layout.addWidget(self.round_box)
        
        #Weightロックボタン
        lock_widget = QWidget()
        lock_layout = QHBoxLayout()
        lock_layout.setSpacing(0)
        lock_widget.setLayout(lock_layout)
        but_w = 73
        space = 14
        lock_widget.setMinimumWidth(but_w*3+space)
        lock_widget.setMaximumWidth(but_w*3+space)
        lock_widget.setMaximumHeight(WIDGET_HEIGHT)
        tip = lang.Lang(en='Lock selected weights\nRight click to lock influence of all vertices', 
                                ja=u'選択ウェイトのロック\n右クリックで全頂点のインフルエンスロック').output()
        self.weight_lock_but = qt.make_flat_btton(name='Lock Wt', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Unlock selected weights\nRight click to unlock influence of all vertices',  
                                ja=u'選択ウェイトのロック解除\n右クリックで全頂点のインフルエンスアンロック').output()
        self.weight_unlock_but = qt.make_flat_btton(name='Unlock Wt', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Unlock selected weights',  
                                ja=u'すべてのウェイトロックの解除').output()
        self.weight_lock_clear_but = qt.make_flat_btton(name='Clear locks', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        self.weight_lock_but.clicked.connect(self.lock_weight)
        self.weight_lock_but.rightClicked.connect(self.lock_all_rows)
        self.weight_unlock_but.clicked.connect(self.unlock_weight)
        self.weight_unlock_but.rightClicked.connect(lambda : self.lock_all_rows(lock=False))
        self.weight_lock_clear_but.clicked.connect(self.clear_lock_weight)
        lock_layout.addWidget(self.weight_lock_but)
        lock_layout.addWidget(self.weight_unlock_but)
        lock_layout.addWidget(self.weight_lock_clear_but)
        
        #計算モードボタンをはめる
        mode_widget = QWidget()
        mode_widget.setGeometry(QRect(0, 0, 0 ,0))
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        mode_widget.setLayout(mode_layout)
        but_w = 38
        norm_w =68
        space = 26
        mode_widget.setMinimumWidth(but_w*3+norm_w*2+space)
        mode_widget.setMaximumWidth(but_w*3+norm_w*2+space)
        mode_widget.setMaximumHeight(WIDGET_HEIGHT)
        self.mode_but_group = QButtonGroup()
        tip = lang.Lang(en='Values entered represent absolute values', ja=u'絶対値で再入力').output()
        self.abs_but = qt.make_flat_btton(name='Abs', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Values entered are added to exisiting values', ja=u'既存値への加算入力').output()
        self.add_but = qt.make_flat_btton(name='Add', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Values entered are percentages added to exisiting values', ja=u'既存値への率加算入力').output()
        self.add_par_but = qt.make_flat_btton(name='Add%', bg=self.hilite, border_col=180, w_max=but_w+8, w_min=but_w+8, h_max=but_h, h_min=but_h, 
                                                                flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Normalize new weights\n\nRight-click forced normalization execution\n*If you execute without selecting a cell, it will be applied to all cells', 
                                ja=u'新規ウェイトの正規化\n\n右クリックで強制正規化実行\n※セルを選択せずに実行すると全てのセルに適用されます').output()
        self.norm_but = qt.make_flat_btton(name='Normalize', bg=self.hilite, border_col=180, w_max=norm_w, w_min=norm_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Accept weight values ​​greater than 1.0 or 100 in total', ja=u'合計1.0もしくは100以上のウェイト値を許容する').output()
        self.no_limit_but = qt.make_flat_btton(name='Unlimited', bg=self.hilite, border_col=180, w_max=norm_w, w_min=norm_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.norm_but.clicked.connect(self.toggle_no_limit_but_enable)
        self.norm_but.rightClicked.connect(lambda : self.enforce_limit_and_normalize(force_norm=True))
        self.no_limit_but.clicked.connect(self.keep_no_limit_flag)
        self.mode_but_group.buttonClicked[int].connect(self.change_add_mode)
        
        self.norm_but.setChecked(self.norm)
        self.no_limit_but.setChecked(self.no_limit)
        self.toggle_no_limit_but_enable()
        
        self.mode_but_group.addButton(self.abs_but, 0)
        self.mode_but_group.addButton(self.add_but, 1)
        self.mode_but_group.addButton(self.add_par_but, 2)
        self.mode_but_group.button(self.mode).setChecked(True)
        mode_layout.addWidget(self.abs_but)
        mode_layout.addWidget(self.add_but)
        mode_layout.addWidget(self.add_par_but)
        mode_layout.addWidget(self.norm_but)
        mode_layout.addWidget(self.no_limit_but)
        
        #ジョイント選択ツールタイプ
        sel_joint_widget = QWidget()
        sel_joint_widget.setGeometry(QRect(0, 0, 0 ,0))
        sel_joint_layout = QHBoxLayout()
        sel_joint_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        sel_joint_widget.setLayout(sel_joint_layout)
        but_w = 22
        j_hl_w = 75
        space = 9
        sel_joint_widget.setMinimumWidth(but_w*4+j_hl_w+space)
        sel_joint_widget.setMaximumWidth(but_w*4+j_hl_w+space)
        sel_joint_widget.setMaximumHeight(WIDGET_HEIGHT)
        self.sel_joint_but_group = QButtonGroup()
        tip = lang.Lang(en='Do not change the tool when selecting the joint by right clicking on the header', 
                            ja=u'ヘッダー右クリックでジョイント選択するときにツール変更しない').output()
        self.n_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, icon=self.icon_path+'n.png', tip=tip)
        tip = lang.Lang(en='Change tool to scaling when joint selection by header right click', 
                            ja=u'ヘッダー右クリックでジョイント選択するときにツールをスケールにする').output()
        self.s_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, icon=self.icon_path+'s.png', tip=tip)
        tip = lang.Lang(en='Change tool to rotation when joint selection by header right click', 
                            ja=u'ヘッダー右クリックでジョイント選択するときにツールをローテーションにする').output()
        self.r_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, icon=self.icon_path+'r.png', tip=tip)
        tip = lang.Lang(en='Change tool to translation when joint selection by header right click', 
                            ja=u'ヘッダー右クリックでジョイント選択するときにツールをトランスレーションにする').output()
        self.t_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=but_w, w_min=but_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, icon=self.icon_path+'t.png', tip=tip)
        tip = lang.Lang(en='Highlight cell selected joint', 
                            ja=u'セル選択されたジョイントをハイライトする').output()
        self.joint_hl_but = qt.make_flat_btton(name='Joint Hilite', bg=self.hilite, border_col=180, w_max=j_hl_w, w_min=j_hl_w, h_max=but_h, h_min=but_h, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.sel_joint_but_group.buttonClicked[int].connect(self.change_joint_tool_mode)
        self.joint_hl_but.setChecked(self.joint_hilite)
        self.joint_hl_but.clicked.connect(self.reset_joint_hl)
        self.sel_joint_but_group.addButton(self.n_but, 0)
        self.sel_joint_but_group.addButton(self.s_but, 1)
        self.sel_joint_but_group.addButton(self.r_but, 2)
        self.sel_joint_but_group.addButton(self.t_but, 3)
        self.sel_joint_but_group.button(self.joint_tool).setChecked(True)
        sel_joint_layout.addWidget(self.n_but)
        sel_joint_layout.addWidget(self.s_but)
        sel_joint_layout.addWidget(self.r_but)
        sel_joint_layout.addWidget(self.t_but)
        sel_joint_layout.addWidget(self.joint_hl_but)
        
        
        #-----------------------------------------------------------------------------------------------------
        #サブツール群を配置
        sub_tool_widget = QWidget()
        sub_tool_widget.setGeometry(QRect(0, 0, 0 ,0))
        sub_tool_layout = QHBoxLayout()
        sub_tool_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        sub_tool_widget.setLayout(sub_tool_layout)
        if MAYA_VER >= 2016:
            size = 212
        else:
            size = 190
        sub_tool_widget.setMinimumWidth(size)
        sub_tool_widget.setMaximumWidth(size)
        sub_tool_widget.setMaximumHeight(WIDGET_HEIGHT)
        
        #サブツール類のレイアウト
        #label = QLabel('Sub Tools :')
        #sub_tool_layout.addWidget(label)
        
        #ウェイトハンマー
        tip = lang.Lang(en='*Weight Hummer\n\nExecute a weight hammer at the vertex of the selected cell', 
                            ja=u'・Weight Hummer\n\n選択セルの頂点にウェイトハンマーを実行する').output()
        self.hummer_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'hummer.png', tip=tip)
        self.hummer_but.clicked.connect(self.hummer_weight)
        sub_tool_layout.addWidget(self.hummer_but)
        
        sub_tool_layout.addWidget(QLabel('  '))
        
        #フリーズ
        tip = lang.Lang(en='*Freeze\n\nDelete all history and write back deformer cluster and blend shape\nEasy history cleanup function', 
                            ja=u'・Freeze\n\nヒストリを全削除したあとデフォーマクラスタとブレンドシェイプを書き戻します\nヒストリの簡単クリーンアップ機能').output()
        self.freeze_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'freeze.png', tip=tip)
        self.freeze_but.clicked.connect(qt.Callback(self.freeze))
        sub_tool_layout.addWidget(self.freeze_but)
        
        #フリーズM
        tip = lang.Lang(en='*Freeze_M\n\nAfter deleting all history, write back skin weight, deformer cluster, blend shape \n'+\
                                'Function to clean up history while keeping skinning \n'+\
                                'You can also bake lattice while skinning', 
                            ja=u'・Freeze_M\n\nヒストリを全削除したあと、スキンウェイト、デフォーマクラスタ、ブレンドシェイプを書き戻します\n'+\
                                u'スキニングを保持したままヒストリをきれいにする機能\n'+\
                                u'スキニングしたままラティスをベイクしたりもできます').output()
        self.freeze_m_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'freeze_m.png', tip=tip)
        self.freeze_m_but.clicked.connect(qt.Callback(self.freeze_m))
        sub_tool_layout.addWidget(self.freeze_m_but)
        
        sub_tool_layout.addWidget(QLabel('  '))
       
        #ウェイトコピー
        tip = lang.Lang(en='*Simple_Weight_Copy\n\nCopy the mesh weight \nWrite it out externally as a temporary file', 
                            ja=u'・Simple_Weight_Copy\n\nメッシュのウェイトをコピーします\n一時ファイルとして外部に書き出し').output()
        self.simple_copy_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'simple_copy.png', tip=tip)
        self.simple_copy_but.clicked.connect(qt.Callback(self.weight_copy))
        sub_tool_layout.addWidget(self.simple_copy_but)

        #ウェイトペースト
        tip = lang.Lang(en='*Simple_Weight_Paste(Name / Index)\n\nPaste the weight of the mesh from the copy information \nWrite back with mesh name and vertex number', 
                            ja=u'・Simple_Weight_Paste(Name / Index)\n\nメッシュのウェイトをコピー情報からペーストします\nメッシュ名と頂点番号で書き戻し').output()
        self.simple_paste_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'simple_topology.png', tip=tip)
        self.simple_paste_but.clicked.connect(qt.Callback(self.weight_paste))
        sub_tool_layout.addWidget(self.simple_paste_but)
        
        #ウェイトペーストポジション
        if MAYA_VER >= 2016:#Maya2016以上はNearestが使える
            tip = lang.Lang(en='*Simple_Weight_Paste(Name / Position)\n\nPaste the weight of mesh from copy information \nWrite back in mesh name and neighborhood coordinates of vertex', 
                                ja=u'・Simple_Weight_Paste(Name / Position)\n\nメッシュのウェイトをコピー情報からペーストします\nメッシュ名と頂点の近傍座標で書き戻し').output()
            self.simple_paste_position_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                        flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'simple_position.png', tip=tip)
            self.simple_paste_position_but.clicked.connect(qt.Callback(lambda : self.weight_paste(method='nearest', threshold=2.0)))
            sub_tool_layout.addWidget(self.simple_paste_position_but)
        
        sub_tool_layout.addWidget(QLabel('  '))
        
        #ウェイトトランスファー
        tip = lang.Lang(en='*Transfer_Weight_Multiple / Copy\n\nWeight Specify the transfer source mesh \nMultiple meshes can be specified', 
                            ja=u'・Transfer_Weight_Multiple / Copy\n\nウェイト転送元のメッシュを指定します\n複数メッシュ指定可能').output()
        self.transfer_copy_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'transfer_copy.png', tip=tip)
        self.transfer_copy_but.clicked.connect(qt.Callback(self.weight_transfer_copy))
        sub_tool_layout.addWidget(self.transfer_copy_but)
        
        #ウェイトトランスファー
        tip = lang.Lang(en='*Transfer_Weight_Multiple / Transfer\n\nWait transfer source Weight is transferred from the specified mesh to the selected mesh \nMultiple mesh can be specified', 
                            ja=u'・Transfer_Weight_Multiple / Transfer\n\nウェイト転送元指定したメッシュから選択メッシュにウェイトを転送します\n複数メッシュ指定可能').output()
        self.transfer_paste_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'transfer_paste.png', tip=tip)
        self.transfer_paste_but.clicked.connect(qt.Callback(self.weight_transfer_paste))
        sub_tool_layout.addWidget(self.transfer_paste_but)
        
        #-----------------------------------------------------------------------------------------------------
        #サブツール群を配置
        sub_tool2_widget = QWidget()
        sub_tool2_widget.setGeometry(QRect(0, 0, 0 ,0))
        sub_tool2_layout = QHBoxLayout()
        sub_tool2_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        sub_tool2_widget.setLayout(sub_tool2_layout)
        size = 180
        sub_tool2_widget.setMinimumWidth(size)
        sub_tool2_widget.setMaximumWidth(size)
        sub_tool2_widget.setMaximumHeight(WIDGET_HEIGHT)
        #ウェイトシンメトリ
        tip = lang.Lang(en='*Weight_Symmetrize\n\n'+\
                            'Mirror weights of selected objects and components\n'+\
                            'Joint label is automatically generated from setting\n\n'+\
                            'Right click to open label setting rule editor', 
                            ja=u'・Weight_Symmetrize\n\n'+\
                            u'選択したオブジェクト、コンポーネントのウェイトをミラーリングします\n'+\
                            u'ジョイントラベルは設定から自動生成されます\n\n'+\
                            u'右クリックでラベル設定ルールエディタを開きます').output()
        self.sym_weight_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'sym_weight.png', tip=tip)
        self.sym_weight_but.clicked.connect(qt.Callback(symmetrize.WeightSymmetrize))
        self.sym_weight_but.rightClicked.connect(self.open_joint_rule_editor)
        sub_tool2_layout.addWidget(self.sym_weight_but)
        
        #メッシュとウェイトをセットでシンメトリ
        tip = lang.Lang(en='*Auto_Symmetry\n\n'+\
                            'Copy selected objects in reverse\n'+\
                            'In case of skin meshes, we also mirror the weight automatically\n\n'+\
                            'Right click to open label setting rule editor', 
                            ja=u'・Auto_Symmetry\n\n'+\
                            u'選択オブジェクトを反転コピー\n'+\
                            u'スキンメッシュの場合はウェイトも自動でミラーリングします\n\n'+\
                            u'右クリックでラベル設定ルールエディタを開きます').output()
        self.auto_symmetry_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'auto_symmetry.png', tip=tip)
        self.auto_symmetry_but.clicked.connect(qt.Callback(symmetrize.mesh_weight_symmetrize))
        self.auto_symmetry_but.rightClicked.connect(self.open_joint_rule_editor)
        sub_tool2_layout.addWidget(self.auto_symmetry_but)
        
        #メッシュマージ
        tip = lang.Lang(en='*Mesh Marge with Skinning\n\n'+\
                            'Conbine the selected mesh with keeping skinning\n'+\
                            'With standard functions, data can not be broken or can not be undone , so original implementation\n\n'+\
                            'It is convenient to merge after Auto Symmetry', 
                            ja=u'・Mesh Marge with Skinning\n\n'+\
                            u'選択メッシュをスキニングを保持したまま結合します\n'+\
                            u'標準機能ではデータが壊れたりアンドゥできない（Mayaごと落ちる）ことが多いので独自実装\n\n'+\
                            u'Auto Symmetry後にマージしたりとか便利です').output()
        self.marge_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'marge.png', tip=tip)
        self.marge_but.clicked.connect(qt.Callback(lambda : modeling.MeshMarge().main(cmds.ls(sl=True, l=True))))
        sub_tool2_layout.addWidget(self.marge_but)
        
        sub_tool2_layout.addWidget(QLabel('  '))
        
        #ウェイトのミュート
        tip = lang.Lang(en='*Toggle_Mute_Skinning \n\nToggle the muting state of the selected mesh skinning \n If you do not select anything, apply it to all skin meshes', 
                            ja=u'・Toggle_Mute_Skinning \n\n選択メッシュのスキニングのミュート状態をトグル\n何も選択せずに実行すると全てのスキンメッシュに適用').output()
        self.toggle_mute_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'mute.png', tip=tip)
        self.toggle_mute_but.clicked.connect(weight.toggle_mute_skinning)
        sub_tool2_layout.addWidget(self.toggle_mute_but)
        
        #バインドポーズ
        tip = lang.Lang(en='*Go_to_Bind_Pose \n\nReturn to bind pose', 
                            ja=u'・Go_to_Bind_Pose \n\nバインドポーズにもどります').output()
        self.bind_pose_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'bind_pose.png', tip=tip)
        self.bind_pose_but.clicked.connect(lambda : mel.eval('gotoBindPose;'))
        sub_tool2_layout.addWidget(self.bind_pose_but)
        
        sub_tool2_layout.addWidget(QLabel('  '))
        
        #Go Maya Exoport
        tip = lang.Lang(en='*Go_Maya_Export\n\n'+\
                            'Export the selected object as a temporary file\n'+\
                            'The last output is overwritten\n\n'+\
                            'Object passing tool between maya scenes\n'+\
                            'It is compatible with the same function of SI Side Bar',
                            ja=u'・Go_Maya_Export\n\n'+\
                            u'選択したオブジェクトを一時ファイルとして書き出します\n'+\
                            u'前回出力分は上書きされます\n\n'+\
                            u'シーン間のオブジェクト受け渡しツール\n'+\
                            u'SI Side Bar の同機能とも互換性があります').output()
        self.go_export_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'go_export.png', tip=tip)
        self.go_export_but.clicked.connect(go.maya_export)
        sub_tool2_layout.addWidget(self.go_export_but)
        
        #Go Maya Import
        tip = lang.Lang(en='*Go_Maya_Import\n\n'+\
                            'Receive objects output by Go_Maya_Export\n\n'+\
                            'Object passing tool between maya scenes\n'+\
                            'It is compatible with the same function of SI Side Bar',
                            ja=u'・Go_Maya_Import\n\n'+\
                            u'Go_Maya_Export で出力したオブジェクトを受け取ります\n\n'+\
                            u'シーン間のオブジェクト受け渡しツール\n'+\
                            u'SI Side Bar の同機能とも互換性があります').output()
        self.go_import_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'go_import.png', tip=tip)
        self.go_import_but.clicked.connect(go.maya_import)
        sub_tool2_layout.addWidget(self.go_import_but)
        
        #sub_tool_layout.addStretch(0)
        
        #ボタン軍の並びを一括設定
        self.but_list.append(show_widget)
        self.but_list.append(sel_joint_widget)
        self.but_list.append(show_bad_widget)
        self.but_list.append(icon_widget)
        self.but_list.append(enforce_widget)
        self.but_list.append(decimal_widget)
        self.but_list.append(lock_widget)
        self.but_list.append(mode_widget)
        self.but_list.append(sub_tool_widget)
        self.but_list.append(sub_tool2_widget)
        
        self.set_column_stretch()#ボタン間隔が伸びないようにする
        #self.init_but_width_list(but_list=self.but_list)#配置実行
        
        self.main_layout.addWidget(qt.make_h_line())
        
        #---------------------------------------------------------------------------------------------------
                
        #スライダー作成
        sld_layout = QHBoxLayout()
        self.main_layout.addLayout(sld_layout)
        self.weight_input = EditorDoubleSpinbox()#スピンボックス
        self.weight_input.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.weight_input.setRange(0, 255)
        self.weight_input.setValue(0.0)#値を設定
        self.weight_input.setDecimals(1)#値を設定
        sld_layout.addWidget(self.weight_input)
        #スライダバーを設定
        self.weight_input_sld = QSlider(Qt.Horizontal)
        self.weight_input_sld.setRange(0, 255)
        sld_layout.addWidget(self.weight_input_sld)
        #スライダーとボックスの値をコネクト。連動するように設定。
        self.weight_input.valueChanged.connect(self.change_from_spinbox)
        self.weight_input.wheeled.connect(lambda : self.store_keypress(True))
        self.weight_input.wheeled.connect(lambda : self.calc_cell_value(from_spinbox=True))
        self.weight_input.editingFinished.connect(lambda : self.calc_cell_value(from_spinbox=True))
        self.weight_input.focused.connect(lambda : self.store_keypress(False))
        self.weight_input.keypressed.connect(lambda : self.store_keypress(True))
        self.weight_input_sld.valueChanged.connect(self.change_from_sld)
        self.weight_input_sld.sliderPressed.connect(self.sld_pressed)
        self.weight_input_sld.valueChanged.connect(lambda : self.calc_cell_value(from_slider=True))
        self.weight_input_sld.sliderReleased.connect(self.sld_released)
        
        tip = lang.Lang(en='Clear cell selection and spin box value', 
                            ja=u'セル選択とスピンボックスの値をクリア').output()
        self.clear_search_but = qt.make_flat_btton(name='C', bg=self.hilite, border_col=180, w_max=18, w_min=18, h_max=18, h_min=18, 
                                                            flat=True, hover=True, checkable=False, destroy_flag=True, icon=None, tip=tip)
        self.clear_search_but.clicked.connect(self.clear_selection)
        sld_layout.addWidget(self.clear_search_but)
        
        self.main_layout.addWidget(qt.make_h_line())
        
        #-------------------------------------------------------------------------------------------
        seach_layout = QHBoxLayout()
        self.main_layout.addLayout(seach_layout)
        
        label = QLabel('Search: ')
        seach_layout.addWidget(label)
        seach_layout.setSpacing(0)#ウェジェットどうしの間隔を設定する
        
        self.search_but_group = QButtonGroup()
        tip = lang.Lang(en='Refine joints search by specified character string', 
                            ja=u'表示中のジョイントを指定文字列で絞り込み検索').output()
        self.refine_but = qt.make_flat_btton(name='Refine', bg=self.hilite, border_col=180, w_max=45, w_min=45, h_max=18, h_min=18, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        tip = lang.Lang(en='Add the joint containing the specified character string to the current display', 
                            ja=u'指定文字列を含むジョイントを現在の表示に加える').output()
        self.add_but = qt.make_flat_btton(name='Add', bg=self.hilite, border_col=180, w_max=35, w_min=35, h_max=18, h_min=18, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, tip=tip)
        self.search_but_group.addButton(self.refine_but , 0)
        self.search_but_group.addButton(self.add_but , 1)
        self.search_but_group.button(self.search_mode).setChecked(True)
        self.search_but_group.buttonClicked.connect(lambda : self.get_set_skin_weight())
        seach_layout.addWidget(self.refine_but)
        seach_layout.addWidget(self.add_but)
        
        seach_layout.addWidget(QLabel(' '))
        
        tip = lang.Lang(en='Clear Search Window', 
                            ja=u'検索窓をクリア').output()
        self.clear_search_but = qt.make_flat_btton(name='C', bg=self.hilite, border_col=180, w_max=18, w_min=18, h_max=18, h_min=18, 
                                                            flat=True, hover=True, checkable=False, destroy_flag=True, icon=None, tip=tip)
        self.clear_search_but.clicked.connect(self.clear_search)
        seach_layout.addWidget(self.clear_search_but)
        
        seach_layout.addWidget(QLabel(' '))
        
        self.search_line = qt.LineEdit()
        self.search_line.editingFinished.connect(lambda : self.search_joint(as_interractive=False))
        self.search_line.textChanged.connect(lambda : self.search_joint(as_interractive=True))
        seach_layout.addWidget(self.search_line)
        
        seach_layout.addWidget(QLabel(' '))
        
        tip = lang.Lang(en='Interactive search', 
                            ja=u'インタラクティブ検索').output()
        self.interactive_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=18, w_min=18, h_max=18, h_min=18, 
                                                            flat=True, hover=True, checkable=True, destroy_flag=True, icon=self.icon_path+'i.png', tip=tip)
        seach_layout.addWidget(self.interactive_but)
        self.interactive_but.setChecked(self.interactive)
        
        #----------------------------------------------------------------------------------------------------
        
        #HorizontalHeaderを縦書きにするカスタムクラス
        headerView = MyHeaderView()
        headerView.doubleClicked.connect(self.toggle_lock_weight)
        headerView.rightClicked.connect(self.select_joint_from_header)
        
        #テーブル作成
        self.view_widget = RightClickTableView(self)
        self.view_widget.setHorizontalHeader(headerView)
        self.view_widget.verticalHeader().setDefaultSectionSize(20)
        self.view_widget.rightClicked.connect(self.get_clicke_item_value)
        self.view_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)#編集スタート不可能にする
        self.view_widget.setAlternatingRowColors(True)
        #self.view_widget.setEditTriggers(QAbstractItemView.AllEditTriggers)#全ての方式で編集スタート可能にする
        self.view_widget.keyPressed .connect(self.direct_cell_input)
        self.main_layout.addWidget(self.view_widget)
        
        #--------------------------------------------------------------------------------------------
        msg_layout = QHBoxLayout()
        
        tip = lang.Lang(en='Set the brightness of the cell character whose value is zero', 
                            ja=u'値がゼロのセル文字の明るさを設定').output()
        label = QLabel('')
        label.setPixmap(QPixmap(self.icon_path+'value.png'))
        label.setToolTip(tip)
        label.setMaximumWidth(20)
        label.setMinimumWidth(20)
        msg_layout.addWidget(label)
        self.zero_darken = EditorDoubleSpinbox()#スピンボックス
        self.zero_darken.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.zero_darken.setRange(0, 999)
        self.zero_darken.setValue(self.darken_value)#値を設定
        self.zero_darken.setDecimals(0)#値を設定
        self.zero_darken.editingFinished.connect(self.zero_cell_darken)#値を設定
        self.zero_darken.setToolTip(tip)
        self.zero_darken.setMaximumWidth(35)
        self.zero_darken.setMinimumWidth(35)
        msg_layout.addWidget(self.zero_darken)
        
        msg_layout.addWidget(qt.make_v_line())
        
        tip = lang.Lang(en='Show latest release page', ja=u'最新リリースページを表示').output()
        self.release_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'release.png', tip=tip)
        self.release_but.clicked.connect(lambda : webbrowser.open(REREASE_PATH))
        msg_layout.addWidget(self.release_but)
        
        tip = lang.Lang(en='Display help page', ja=u'ヘルプページの表示').output()
        self.help_but = qt.make_flat_btton(name='', bg=self.hilite, border_col=180, w_max=BUTTON_HEIGHT, w_min=BUTTON_HEIGHT, h_max=but_h, h_min=but_h, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, icon=self.icon_path+'help.png', tip=tip)
        self.help_but.clicked.connect(lambda : webbrowser.open(HELP_PATH))
        msg_layout.addWidget(self.help_but)
        
        msg_layout.addWidget(qt.make_v_line())
        
        #実行時間のお知らせ
        self.main_layout.addLayout(msg_layout)
        self.time_label = QLabel('- Calculation Time - 0.00000 sec')
        self.time_label.setMaximumWidth(200)
        self.time_label.setMinimumWidth(200)
        msg_layout.addWidget(self.time_label)
        
        msg_layout.addWidget(qt.make_v_line())
        
        #ウェイトエディタからの通知
        self.msg_label = QLabel('')
        msg_layout.addWidget(self.msg_label)
        
        msg_layout.setSpacing(6)#ウェジェットどうしの間隔を設定する
        
        self.create_job()
        self.change_add_mode(id=self.mode)
        self.change_decimal_digits()
        self.zero_cell_darken()
        self.get_set_skin_weight()
        
        
    def open_joint_rule_editor(self):
        joint_rule_editor.Option()
        
    #サブツールコマンド群-----------------------------------------------------------
    def freeze(self):
        freeze.freeze()
    
    def freeze_m(self):
        freeze.main(pop_zero_poly=True)
    
    def weight_copy(self, method='index', engin='maya', saveName='simple.copypaste'):
        selection = cmds.ls(sl=True)
        skin_meshes = common.search_polygon_mesh(selection, serchChildeNode=True)
        if skin_meshes is not None:
            weight.WeightCopyPaste().main(skin_meshes, 
                                            mode = 'copy', 
                                            saveName = saveName, 
                                            engine = engin,
                                            viewmsg = True)
                                                
    def weight_paste(self, method='index', threshold=0.2, engin='maya', saveName='simple.copypaste'):
        selection = cmds.ls(sl=True)
        skin_meshes = common.search_polygon_mesh(selection, serchChildeNode=True)
        if skin_meshes is not None:
            weight.WeightCopyPaste().main(skin_meshes, 
                                            mode = 'paste', 
                                            saveName = saveName, 
                                            method = method, 
                                            threshold = threshold,
                                            engine = engin,
                                            viewmsg = True)
                                            
    def weight_transfer_copy(self):
        msg = WEIGHT_TRANSFER_MULTIPLE.stock_copy_mesh()
        print msg
        self.set_message(msg=msg, error=False)
        
    def weight_transfer_paste(self):
        msg = WEIGHT_TRANSFER_MULTIPLE.transfer_weight_multiple()
        
        cmds.scriptJob(ro=True, e=("idle", lambda : self.set_message(msg=msg, error=False)), protected=True)
        
    #ウェイトハンマーの実行、後でちゃんとする
    def hummer_weight(self):
        current_selection = cmds.ls(sl=True, l=True)
        self.setup_update_row_data()#焼きこみ対象の行を設定する
        target_vertices = []
        for row in self.update_rows:
            target_vertices.append(self.vtx_row_dict[row][5])
        
        cmds.undoInfo(swf=False)
        self.hilite_flag = True
        cmds.select(target_vertices, r=True)
        cmds.undoInfo(swf=True)
        
        mel.eval('weightHammerVerts;')
        
        cmds.undoInfo(swf=False)
        self.hilite_flag = True
        cmds.select(current_selection, r=True)
        cmds.undoInfo(swf=True)
        
        self.get_set_skin_weight(node_vtx_dict=self.node_vtx_dict)
    
    #-----------------------------------------------------------
    def clear_selection(self):
        self.sel_model.clearSelection()
        self.weight_input.setValue(0.0)
    
    numeric_list = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '.']
    def direct_cell_input(self, string):
        if not self.sel_model.selectedIndexes():
            return
        if string in self.numeric_list:
            self.view_widget.ignore_key_input = True#一時的にテーブルへのキー入力無効
            self.input_box = PopInputBox(value=string, 
                                        mode=self.mode_but_group.checkedId(),
                                        direct=True)
            self.input_box.closed.connect(lambda : self.apply_input_box_value(direct=True))
        
    #ゼロセルの文字の色を変える
    def zero_cell_darken(self):
        global ZERO_CELL_DARKEN
        ZERO_CELL_DARKEN = 210 - self.zero_darken.value()
        self.refresh_table_view()
    
    #お知らせをUIに表示する
    def set_message(self, msg='', error=True):
        self.msg_label.setText(msg)
        if error:
            qt.change_button_color(self.msg_label, textColor=[250, 128, 64])
        else:
            qt.change_button_color(self.msg_label, textColor=200)
            
    #お知らせを消す
    def reset_message(self):
        self.msg_label.setText('')
        
    search_joint_list = []
    def search_joint(self, as_interractive=False):
        if not self.interactive_but.isChecked() and as_interractive:
            return
        if self.interactive_but.isChecked() and not as_interractive:
            return
        if len(self.search_line.text()) == 0:
            self.search_joint_list = []
        else:
            self.search_joint_list = self.search_line.text().split(' ')
            self.search_joint_list  = [name for name in self.search_joint_list if name != '']
        self.get_set_skin_weight()
        
    def clear_search(self):
        self.search_line.setText('')
        self.get_set_skin_weight()
        
    #エンフォース、ラウンド、ノーマライズなど強制焼きこみの時は事前に行データを設定する
    def setup_update_row_data(self):
        self.update_rows = set()
        if not  self.selected_items:
            self.update_rows = self.all_editable_rows
        else:
            for cell_id in self.selected_items:
                row = cell_id.row()
                self.update_rows.add(row)
        self.row_column_dict = {}
        #行に対するカラムの選択はないことにする
        for row in self.update_rows:
            self.row_column_dict[row] = []
            
    #エンフォースリミットと強制ノーマライズ実行
    def enforce_limit_and_normalize(self, force_norm=False):
        if not force_norm:#エンフォース
            limit = self.limit_box.value()
            if limit == 0:
                return
        else:#強制正規化
            limit = -1
        self.setup_update_row_data()#焼きこみ対象の行を設定する
        self.precalculate_bake_weights(enforce=limit)
        
    #してい桁数で丸める
    def round_off(self):
        id = self.max_value_but_group.checkedId()
        offset =  id * 2
        round_digit = self.round_box.value()+offset
        self.setup_update_row_data()#焼きこみ対象の行を設定する
        self.precalculate_bake_weights(round_digit=round_digit)
        
    def keep_no_limit_flag(self):
        self.no_limit = self.no_limit_but.isChecked()
        
    def toggle_no_limit_but_enable(self):
        if self.norm_but.isChecked():
            self.no_limit_but.setDisabled(True)#無効化
            self.no_limit_but.setChecked(False)
            qt.change_button_color(self.no_limit_but, textColor=128, bgColor=68, hiColor=68, hiText=128, hiBg=64, dsColor=160,
                                        mode='button', toggle=False, hover=False, destroy=True, dsWidth=1)
        else:
            self.no_limit_but.setDisabled(False)
            self.no_limit_but.setChecked(self.no_limit)
            qt.change_button_color(self.no_limit_but, textColor=200, bgColor=68, hiColor=120, hiText=200, hiBg=120, dsColor=160,
                                        mode='button', toggle=True, hover=False, destroy=True, dsWidth=1)
            
    #小数点以下の最大表示桁数を100と1の時で切り替える
    def change_max_decimal_digit(self, id):
        if self.pre_max_id == id:
            return
        self.pre_max_id = id
        offset = (1 - id) * 2
        value = self.digit_box.value()
        if id == 0:
            self.digit_box.setRange(offset , 9)
            self.digit_box.setValue(value + 2 )
            self.round_box.setRange(offset , 9)
            self.round_box.setValue(value + 2 )
        else:
            self.digit_box.setRange(offset , 7)
            self.digit_box.setValue(value- 2 )
            self.round_box.setRange(offset , 7)
            self.round_box.setValue(value- 2 )
            
    #表示桁数を変える
    def change_decimal_digits(self):
        global FLOAT_DECIMALS
        FLOAT_DECIMALS = self.digit_box.value()
        
        self.weight_input.setDecimals(FLOAT_DECIMALS)
        self.weight_input_sld.setRange(0, 10**FLOAT_DECIMALS*MAXIMUM_WEIGHT)
        
        #テーブルビューでゼロ埋めするためのフォーマットを作っておく
        global FLOAT_FORMAT
        FLOAT_FORMAT = '{:.'+str(FLOAT_DECIMALS)+'f}'
        try:
            set_table_header_width(self.view_widget, self.weight_model, add=(FLOAT_DECIMALS-2)*7-10)
            self.refresh_table_view()
        except:
            pass
        
    def change_maximum_weight(self, id):
        global MAXIMUM_WEIGHT
        if id == 0:
            MAXIMUM_WEIGHT = 1.0
            self.max_wt = 1.0
        else:
            MAXIMUM_WEIGHT = 100.0
            self.max_wt = 100.0
        self.refresh_table_view()
        
    @timer
    def change_limit(self, e):
        global MAXIMUM_INFLUENCE_COUNT
        MAXIMUM_INFLUENCE_COUNT = self.limit_box.value()
        self.refresh_table_view()
        
    #リミットゼロの時は入力されてないように見せる
    def change_limit_box_color(self):
        if self.limit_box.value() == 0:
            qt.change_widget_color(self.limit_box, textColor=42, hitxColor=42, hibgColor=42)
        else:
            qt.change_widget_color(self.limit_box, textColor=200, hitxColor=255)
        
    def check_unlock(self):
        if not self.lock_but.isChecked():
            self.get_set_skin_weight()
            
    #ヘッダーをダブルクリックしてロックをトグルする
    @Slot(int)#シグナルから整数を引数として受け取る
    def toggle_lock_weight(self,section_id):
        for lock_data in self.weight_lock_data:
            if lock_data[1] == section_id:
                #print 'unlock wt'
                self.unlock_weight(all_lock=True, section_ids=[section_id])
                break
        else:
            #print 'lock wt'
            self.lock_weight(all_lock=True, section_ids=[section_id])
        self.sel_model.clearSelection()
            
    def lock_all_vtx_weight(self, section_ids=[], add=True):
        for node in self.hl_nodes:
            skin_cluster = self.all_skin_clusters[node]
            vertices = self.node_vtx_dict[node]
            #print len(vertices)
            lock_influences = [self.all_influences[section_id] for section_id in section_ids]
            pre_lock_data_dict = self.decode_lock_data(skin_cluster)
            for vtx in vertices:
                after_lock_influences = []
                try:#キーの有無を比較すると重かったので例外処理で乗り切る
                    pre_lock_influences = pre_lock_data_dict[vtx]
                except Exception as e:
                    pre_lock_influences = []
                    pass
                if add:
                    after_lock_influences = list(set(pre_lock_influences+lock_influences))
                else:
                    after_lock_influences = list(set(pre_lock_influences)-set(lock_influences))
                pre_lock_data_dict[vtx] = after_lock_influences
            new_lock_data_list = self.encode_lock_data(pre_lock_data_dict)
            if not new_lock_data_list:
                try:
                    cmds.deleteAttr(skin_cluster+'.'+self.lock_attr_name)
                except Exception as e:
                    print 'clear lock error :', skin_cluster, e.message
                    pass
            else:
                cmds.setAttr(skin_cluster+'.'+self.lock_attr_name, 
                            type='stringArray', 
                            *([len(new_lock_data_list)] + new_lock_data_list) )
            
    def lock_all_rows(self, lock=True):
        column_count = self.weight_model.columnCount()
        selected_item = self.sel_model.currentIndex()
        new_indexes = []
        section_ids = []
        for index in range(column_count):
            if self.sel_model.columnIntersectsSelection(index, selected_item):
                section_ids.append(index)
                column_indexes = [[row, index] for row in self.all_editable_rows]
                new_indexes += column_indexes
        if lock:
            self.lock_weight(all_lock=True, section_ids=section_ids, indexes=new_indexes)
        else:
            self.unlock_weight(all_lock=True, section_ids=section_ids, indexes=new_indexes)
        self.refresh_table_view()
        
    def unlock_all_rows(self):
        column_count = self.weight_model.columnCount()
        selected_item = self.sel_model.currentIndex()
        new_indexes = []
        for index in range(column_count):
            if self.sel_model.columnIntersectsSelection(index, selected_item):
                column_indexes = [[row, index] for row in self.all_editable_rows]
                new_indexes += column_indexes
        self.unlock_weight(all_lock=False, section_ids=index, indexes=new_indexes)
        self.refresh_table_view()
        
    #ウェイトロック
    #@prof.profileFunction()
    @timer
    def lock_weight(self, all_lock=False, section_ids=None, indexes=None):
        self.counter.reset()
        
        skin_vtx_dict = defaultdict(lambda : [])
        vtx_lock_dict = defaultdict(lambda : [])
        if not indexes:
            target_cells = self.selected_items
        else:
            target_cells = indexes
        for cell_id in target_cells:
            #セルの色替え
            if not indexes:
                row = cell_id.row()
                column = cell_id.column()
            else:
                row = cell_id[0]
                column = cell_id[1]
            index = (row, column)
            self.weight_lock_data.add(index)
            self.weight_model.weight_lock_cells.add(index)
            
            #事前に格納しておいた行のデータを引き出す
            row_data = self.vtx_row_dict[row]
            vtx = row_data[0]
            skin_cluster = row_data[1]
            influences =  row_data[2]
            vtx_name = row_data[5]
            node = row_data[6]
            node_influence_id_list = self.node_influence_id_list_dict[node]
            rock_id = node_influence_id_list[column]#ロックするインフルエンスのID
            try:
                rock_influence = influences[rock_id]#ロックするインフルエンス
            except:
                continue
            self.vtx_lock_data_dict[vtx_name].add(rock_id)#ロックインフルエンス辞書に追加
            
            #まとめて処理するためにいろいろ情報を整理して格納
            skin_vtx_dict[skin_cluster] += [vtx]
            vtx_lock_dict[vtx] += [rock_influence]
            
        self.counter.count(string='lock cell :')
        
        if all_lock:
            self.lock_all_vtx_weight(section_ids=section_ids, add=True)
        else:
            #ロック情報を文字配列としてスキンクラスタのカスタムアトリビュートに格納
            for skin_cluster, vertices in skin_vtx_dict.items():
                new_lock_data_list = []
                pre_lock_data_dict = self.decode_lock_data(skin_cluster)
                
                for vtx in vertices:
                    lock_influences = vtx_lock_dict[vtx]
                    try:#キーの有無を比較すると重かったので例外処理で乗り切る
                        pre_lock_influences = pre_lock_data_dict[vtx]
                        lock_influences = list(set(lock_influences+pre_lock_influences))
                    except:
                        pass
                    pre_lock_data_dict[vtx] = lock_influences
                new_lock_data_list = self.encode_lock_data(pre_lock_data_dict)
                cmds.setAttr(skin_cluster+'.'+self.lock_attr_name, type='stringArray', *([len(new_lock_data_list)] + new_lock_data_list) )
                
        self.counter.count(string='set lock attr to skin_node :')
        self.counter.lap_print(print_flag=COUNTER_PRINT)
            
    #ウェイトアンロック
    #@prof.profileFunction()
    @timer
    def unlock_weight(self, all_lock=False, section_ids=None, indexes=None):
        skin_vtx_dict = defaultdict(lambda : [])
        vtx_lock_dict = defaultdict(lambda : [])
        if not indexes:
            target_cells = self.selected_items
        else:
            target_cells = indexes
        for cell_id in target_cells:
            #セルの色替え
            if not indexes:
                row = cell_id.row()
                column = cell_id.column()
            else:
                row = cell_id[0]
                column = cell_id[1]
            index = (row, column)
            try:
                self.weight_lock_data.remove(index)
            except:
                pass
            try:
                self.weight_model.weight_lock_cells.remove(index)
            except:
                pass
            #事前に格納しておいた行のデータを引き出す
            row_data = self.vtx_row_dict[row]
            vtx = row_data[0]
            skin_cluster = row_data[1]
            influences =  row_data[2]
            vtx_name = row_data[5]
            node = row_data[6]
            try:
                rock_influence = influences[rock_id]#ロックするインフルエンス
            except:
                continue
            node_influence_id_list = self.node_influence_id_list_dict[node]
            if rock_id in self.vtx_lock_data_dict[vtx_name]:
                self.vtx_lock_data_dict[vtx_name].remove(rock_id)#ロックインフルエンス辞書から削除
            rock_influence = influences[rock_id]#ロックするインフルエンス
            #まとめて処理するためにいろいろ情報を整理して格納
            skin_vtx_dict[skin_cluster] += [vtx]
            vtx_lock_dict[vtx] += [rock_influence]
        if all_lock:
            self.lock_all_vtx_weight(section_ids=section_ids, add=False)
        else:
            #ロック情報を文字配列としてスキンクラスタのカスタムアトリビュートに格納
            for skin_cluster, vertices in skin_vtx_dict.items():
                new_lock_data_list = []
                pre_lock_data_dict = self.decode_lock_data(skin_cluster)
                for vtx in vertices:
                    lock_influences = vtx_lock_dict[vtx]
                    try:
                        pre_lock_influences = pre_lock_data_dict[vtx]
                        lock_influences = list(set(pre_lock_influences)-set(lock_influences))
                    except:
                        pass
                    pre_lock_data_dict[vtx] = lock_influences
                new_lock_data_list = self.encode_lock_data(pre_lock_data_dict)
                if not new_lock_data_list:
                    try:
                        cmds.deleteAttr(skin_cluster+'.'+self.lock_attr_name)
                    except Exception as e:
                        print 'clear lock error :', skin_cluster, e.message
                        pass
                else:
                    cmds.setAttr(skin_cluster+'.'+self.lock_attr_name, type='stringArray', *([len(new_lock_data_list)] + new_lock_data_list) )
                
            
    #アトリビュートに格納する形式にロックデータをエンコードする
    def encode_lock_data(self, lock_dict):
        return [str(v)+self.spliter+','.join(influences) for v, influences in lock_dict.items() if len(influences) != 0]
        
    #アトリビュートのロック情報を翻訳する
    lock_attr_name = 'SI_Weight_Lock_Data'
    spliter = '-|-'#アトリビュートに格納するときのインフルエンスつなぎ文字
    #@prof.profileFunction()
    def decode_lock_data(self, skin_cluster):
        try:
            lock_data_dict = {}
            attrs = cmds.listAttr(skin_cluster)
            if not self.lock_attr_name in attrs:
                cmds.addAttr(skin_cluster, longName=self.lock_attr_name, dataType='stringArray')
            else:
                lock_list = cmds.getAttr(skin_cluster+'.'+self.lock_attr_name) or []
                for lock_data in lock_list:
                    split_lock_data = lock_data.split(self.spliter)
                    lock_inf_str = split_lock_data[1]
                    if lock_inf_str:
                        lock_data_dict[int(split_lock_data[0])] = lock_inf_str.split(',')
            return lock_data_dict
        except Exception as e:#読み込み失敗したらクリアする
            print e.message
            return {}
                
    #ロック状態のクリア
    def clear_lock_weight(self):
        self.vtx_lock_data_dict = defaultdict(lambda : set())
        self.weight_model.weight_lock_cells = set()
        self.weight_lock_data = set()
        self.refresh_table_view()#ビューの更新
        for skin_cluster in self.all_skin_clusters.values():
            attrs = cmds.listAttr(skin_cluster)
            if self.lock_attr_name in attrs:
                try:
                    cmds.deleteAttr(skin_cluster+'.'+self.lock_attr_name)
                except Exception as e:
                    print 'clear lock error :', skin_cluster, e.message
                    pass
            
    #右クリックしたときの小窓を反映する。
    def get_clicke_item_value(self):
        #ヘッダーの幅を取得してカラム位置をオフセットする
        v_header = self.view_widget.verticalHeader()
        v_header_width = v_header.sizeHint().width()
        h_header = self.view_widget.horizontalHeader()
        h_header_height = h_header.sizeHint().height()
        
        pos = self.view_widget.mapFromGlobal(QCursor.pos())
        pos_x = pos.x() - v_header_width - 2#誤差補正
        pos_y = pos.y() - h_header_height -2 #誤差補正
        row = self.view_widget.rowAt(pos_y)
        column = self.view_widget.columnAt(pos_x)
        if column == -1:
            column = len(self.all_influences)
        text = self.weight_model.get_data(row=row, column=column)
        if text is None:
            return
        else:
            text = text*MAXIMUM_WEIGHT
        value = float(text)
        self.input_box = PopInputBox(value=value, mode=self.mode_but_group.checkedId())
        self.input_box.closed.connect(self.apply_input_box_value)
    
    #右クリック入力を確定して反映する
    def apply_input_box_value(self, direct=True):
        if direct:
            try:
                self.input_box_value = float(self.input_box.input.text())
            except:
                return
        else:
            self.input_box_value = self.input_box.input.value()
        self.calc_cell_value(from_spinbox=False, from_input_box=True)
        
        #フォーカスを取る
        self.activateWindow()
        self.raise_()
        #Pyside1だとなぜか繰り返さないとフォーカス取れない
        self.view_widget.setFocus()
        self.weight_input.clearFocus()
        self.view_widget.setFocus()
        #キー入力受付をもとに戻す
        self.view_widget.ignore_key_input = False
        
    #加算モードが変更されたらスライダー反映式を変える
    add_mode = 0
    def change_from_sld(self):
        div_num = 10.0**FLOAT_DECIMALS
        self.weight_input.setValue(self.weight_input_sld.value()/div_num)
        
    def change_from_spinbox(self):
        mul_num = 10.0**FLOAT_DECIMALS
        self.weight_input_sld.setValue(self.weight_input.value()*mul_num)
    
    #加算モード変更時、最大最小と小数点以下桁数を変更する
    #@timer
    def change_add_mode(self, id, change_only=False):
        self.add_mode = id
        if id == 0:
            if not self.selected_items:
                return
            pre_sel_value = self.weight_model.get_data(self.selected_items[0])
            
            #選択した値がすべて同じ値ならスピンボックスに同値を入れる
            for item in self.selected_items:
                #print 'check abs value :', item.row(), item.column()
                sel_value = self.weight_model.get_data(item)
                #値が0.0が混じる場合は確認する必要ないので逃げる
                if sel_value == 0.0:
                    self.weight_input_sld.setValue(0.0)
                    return
                if pre_sel_value == sel_value:
                    pre_sel_value = sel_value
                    continue
                else:
                    break
            else:
                value = self.weight_model.get_data(self.selected_items[0])
                if value is None:
                    return
                value *= MAXIMUM_WEIGHT
                value = round(value, FLOAT_DECIMALS)
                #print 'get single abs value :', value
                self.weight_input_sld.setValue(value* 10**FLOAT_DECIMALS)
                if change_only:
                    return
        if id == 0:
            self.weight_input.setRange(0, MAXIMUM_WEIGHT)
            self.weight_input.setDecimals(FLOAT_DECIMALS)
            self.weight_input_sld.setRange(0, 10**FLOAT_DECIMALS*MAXIMUM_WEIGHT)
        if id == 2 or id == 1:
            self.weight_input.setRange(-1*MAXIMUM_WEIGHT, MAXIMUM_WEIGHT)
            self.weight_input.setDecimals(3)
            self.weight_input_sld.setRange(-1*10**FLOAT_DECIMALS*MAXIMUM_WEIGHT, 10**FLOAT_DECIMALS*MAXIMUM_WEIGHT)
            self.weight_input_sld.setValue(0)
        self.pre_add_value = 0.0
        self.weight_input.setValue(0)
        self.weight_input_sld.setValue(0)
            
    #ボタンが左詰めになるように調整
    def set_column_stretch(self):
        self.def_but_width_list = self.init_but_width_list(self.but_list)
        for i in range(self.def_but_width_list[-1]):
            self.unique_layout.setColumnStretch(i, 0)
        self.unique_layout.setColumnStretch(i+1, 1)
        
    def init_but_width_list(self, but_list):
        but_width_list = [0]
        sum_width = 0
        for but in but_list:
            sum_width += but.width()
            but_width_list.append(sum_width)
        return but_width_list
        
    def resizeEvent(self, event):
        if self.init_flag:
            return
        win_x = event.size().width()
        self.re_arrangement_but(win_x=win_x, grid_v=0, but_list=self.but_list, loop=0)
        
    check_window_dict = defaultdict(lambda: -1)
    def check_window_size(self, win_x, but_width_list):
        self.def_but_width_list
        for i, but_width in enumerate(self.def_but_width_list[::-1][:-1]):
            if win_x > but_width+40:#ウィンドウの幅がボタン幅より広かったら配置して次の再帰へ
                self.window_size_id = i
                break
        if self.window_size_id == self.check_window_dict[str(but_width_list)]:
            #print 'same id return', self.window_size_id, str(but_width_list)
            return False
        self.check_window_dict[str(but_width_list)] = self.window_size_id
        return True
        
    pre_row_count = 0
    def re_arrangement_but(self, win_x, grid_v, but_list, loop):
        if loop >100:
            return
        if not but_list:
            return
        but_width_list = self.init_but_width_list(but_list)
        arrangement_list = [0]
        for i, but_width in enumerate(but_width_list[::-1][:-1]):
            if win_x > but_width+40:#ウィンドウの幅がボタン幅より広かったら配置して次の再帰へ
                if i != 0:
                    set_but_list = but_list[:-i]
                else:
                    set_but_list = but_list[:]
                for j, but in enumerate(set_but_list):
                    self.unique_layout.addWidget(but, grid_v, but_width_list[j], 1, but.width())
                break
        but_num = len(but_list)-i
        new_but_list = but_list[but_num:]
        self.re_arrangement_but(win_x=win_x, grid_v=grid_v+1, but_list=new_but_list, loop=loop+1)
        
    #UIに選択コンポーネントのバーテックスカラーを反映
    weight_list = []
    pre_hl_nodes = []
    hl_nodes = None
    pre_sel = None
    pre_vtx_id_list = []
    temp_vf_face_dict = {}
    temp_vf_vtx_dict = {}
    node_vertex_dict_dict = {}#頂点とIDの対応辞書のノードごとの辞書
    pre_node_vtx_dict ={}
    hilite_flag = False
    all_influences = []
    pre_current_vtx_dict = {}
    #@timer
    #@prof.profileFunction()
    def get_set_skin_weight(self, node_vtx_dict={}, cycle=False, clear=False, filter=False, 
                                        show_dict={}, show_all=False, show_bad=False, undo=False):
        self.reset_message()#メッセージ初期化
        '''機能上整合性とれなくなるのでオミット
        #選択変更時に何も選択されてなかったら表示キープ
        if self.no_sel_lock_but.isChecked():
            if not cmds.ls(sl=True, l=True) and not filter and not clear and not cycle and self.pre_hl_nodes:
                if not show_bad:
                    return
                else:
                    node_vtx_dict = self.pre_node_vtx_dict
                    self.hl_nodes = self.pre_hl_nodes
        '''
        try:
            if cmds.selectMode(q=True, co=True) and not self.focus_but.isChecked():
                return
        except Exception as e:
            #print e.message
            #print 'UI Allready Closed :'
            return
        if self.hilite_flag:
            self.hilite_flag = False
            return
            
        self.node_vtx_dict = node_vtx_dict
        
        if self.joint_hl_but.isChecked():
            self.disable_joint_override()
        
        self.counter.reset()
        
        self.original_selection = cmds.ls(sl=True, l=True)#ハイライトの時にまとめて選択する元の選択
        self.show_dict = show_dict
        
        #クリアボタン押されたときは全部初期化
        if clear:
            self.hl_nodes = []
            self.node_vtx_dict = {}
            self.show_dict = defaultdict(lambda : [])
            self.show_dict['clear'] = []#クリア用に初期値を与えたデフォルトディクトを作る
        #インフルエンスフィルター更新の時は頂点変更しない
        elif filter:
            self.node_vtx_dict = {}
            if self.pre_node_vtx_dict:
                self.node_vtx_dict = self.pre_node_vtx_dict
            #フィルター解除されたら全インフルエンス情報をもとに戻す
            if not self.filter_but.isChecked():
                self.all_influences = copy.copy(self.store_skin_weight.all_influences)
        #ロックボタンが押されているときの挙動
        elif self.lock_but.isChecked()  and self.pre_hl_nodes and not cycle and not show_bad:
            self.hl_nodes = self.pre_hl_nodes
            if cmds.selectMode(q=True, o=True):
                return
            else:
                self.node_vtx_dict = {node : self.store_skin_weight.om_selected_mesh_vertex(node) for node in self.pre_hl_nodes}
                if not any(self.node_vtx_dict.values()):#全てのリストが空だったら何もせず戻る
                    return
        else:#ロックされてないとき
            pass
        
        self.counter.count(string='get mesh vtx :')
        
        #頂点ID、ウェイト、インフルエンスを格納したインスタンスから各種データをとりだしておく
        
        if not self.node_vtx_dict:
            self.store_skin_weight.run_store()
            self.hl_nodes = list(set(self.store_skin_weight.mesh_node_list))
            self.all_influences = copy.copy(self.store_skin_weight.all_influences)
            self.all_skin_clusters = self.store_skin_weight.all_skin_clusters#ロック全解除のためにスキンクラスタ全部入りリスト作っておく
            self.influences_dict  = self.store_skin_weight.influences_dict#メッシュごとのインフルエンス一覧
            self.node_vtx_dict  = self.store_skin_weight.node_vtx_dict#メッシュごとの頂点ID一覧
            self.node_weight_dict  = self.store_skin_weight.node_weight_dict#メッシュごとのウェイト一覧
            self.node_skinFn_dict = self.store_skin_weight.node_skinFn_dict
        else:
            pass

        if not self.show_dict:
            self.show_dict = self.store_skin_weight.show_dict
        
        self.pre_node_vtx_dict = self.node_vtx_dict#選択状態を保持するために前回分を取っておく
                    
        self.counter.count(string='get vtx weight :')
        
        #ジョイント選択機能が働いていたらツールを戻す
        if self.pre_tool:
            cmds.setToolTo(self.pre_tool)
            self.pre_tool = None
        
        self.header_selection = []#ヘッダーからのジョイント選択復元リストを初期化
        self.all_rows = 0#右クリックウィンドウ補正用サイズを出すため全行の桁数を数える
        self.v_header_list = []#縦ヘッダーの表示リスト
        self._data = []#全体のテーブルデータを格納する
        self.mesh_rows = []#メッシュ表示している行リスト
        self.vtx_row_dict = {}#行と頂点の対応辞書
        self.under_weight_rows = set()#ウェイト合計が1.0未満の行
        self.over_weight_rows = set()#ウェイト合計が1.0より大きい行
        self.over_influence_limit_dict = {}#行と使用中のインフルエンス数の対応辞書,model内で表示を変えるときに参照する
        self.over_influence_limit_rows = set()#インフルエンス数がオーバーしている行
        self.all_editable_rows = set()#編集可能な行のIDを格納
        self.weight_lock_data = set()#テーブルモデルに追加するようのロック状態格納セット
        self.vtx_lock_data_dict = defaultdict(lambda : set())#頂点のロックインフルエンスIDを格納する
        self.node_id_dict = {}#ノード名からノードIDを引く辞書
        self.mesh_model_items_dict = {}#後でメッシュ行に空セルを設定するための辞書
        self.filter_weight_dict = defaultdict(lambda : 0.0)#ウェイト0のインフルエンスの表示、非表示切り替えのためのすべての合計値辞書
        self.vtx_weight_dict = {}#焼きこみ時、正規化ウェイトをUIに反映するための辞書
        self.lock_data_dict = {}#ロック情報を格納する。全頂点捜査後、インフルエンスとセルのロック情報対応を作るための事前データ。
        for node_id, node in enumerate(self.hl_nodes):
            self.node_id_dict[node] = node_id
            skin_cluster = self.all_skin_clusters[node]
            influences = self.influences_dict[node]
            
            node_influence_id_dict =  {inf:influences.index(inf)  for inf in influences}#インフルエンスとウェイトIDの対応辞書
            all_influences_count = len(influences)#インフルエンスの総数
            inf_id_list = range(len( influences))#インフルエンスの連番IDリスト
            
            #ロック情報を取得する
            lock_data_dict = self.decode_lock_data(skin_cluster)
            
            self.v_header_list.append(node.split('|')[-1].split(':')[-1])
            self.mesh_rows.append(self.all_rows)
            self.all_rows += 1
            
            #メッシュ行にアイテムを設定、とりあえずメッシュ名だけ入れる
            #他の空セルは後ほどゼロカラム計算後に入れる
            items = defaultdict(lambda: None)
            self.mesh_model_items_dict[node] = items
            items[0] = node.split('|')[-1]
            self._data.append(items)
            
            if show_all:#全照会するときはノード全体のIDリストを取りに行く
                current_vtx = self.node_vtx_dict[node]
            elif undo:
                current_vtx = self.pre_current_vtx_dict[node]
            else:#通常取得
                current_vtx = self.store_skin_weight.om_selected_mesh_vertex(node, show_bad=show_bad)#表示用頂点
            self.pre_current_vtx_dict[node] = current_vtx
            if not current_vtx:#現在の頂点がなければ次へ
                continue
            filter_vtx = self.show_dict[node]
            target_vertices = sorted(list(set(current_vtx) & set(filter_vtx)))
            if target_vertices:
                vertex_dict = self.node_vtx_dict[node]
                node_weight_list = self.node_weight_dict[node]
                sel_weight_list = []#選択頂点のリストをまとめる
                
                items = []#各行のカラムを格納するアイテムリスト
                for v in target_vertices:
                    vtx_name = "{0:}.vtx[{1:}]".format(node, v)#IDを頂点名に変換しておく
                    #頂点のロック情報を取得しておく
                    # try:#if v in keys比較が重いので例外処理で高速化
                        # self.lock_data_dict[self.all_rows] = [vtx_name, lock_data_dict[v]]
                    # except:
                        # pass
                        
                    #if v in lock_data_dict.keys():#比較遅い
                        #self.lock_data_dict[self.all_rows] = [vtx_name, lock_data_dict[v]]
                        
                    #例外補足とあまり変わらないかちょっと早い
                    lock_data = lock_data_dict.get(v, None)
                    if lock_data:
                        self.lock_data_dict[self.all_rows] = [vtx_name, lock_data]
                        
                    self.all_editable_rows.add(self.all_rows)
                    self.v_header_list.append(v)
                    
                    weight_list = node_weight_list[v][:]#頂点ウェイトを取得、アンドゥできるように参照ではなくコピー
                    sel_weight_list.append(weight_list)
                    self.vtx_weight_dict[vtx_name] = weight_list#UI更新用
                    self._data.append(weight_list)#モデル用データに入れておく
                    
                    #ウェイトの合計、使用インフルエンス数が不正かどうかを格納しておく
                    weight_sum = round(sum(weight_list), 12)#合計値
                    #print 'sum weights :', weight_sum
                    influence_count = all_influences_count - weight_list.count(0.0)
                    self.over_influence_limit_dict[self.all_rows] = influence_count
                    if weight_sum < 1.0:
                        self.under_weight_rows.add(self.all_rows)
                    if weight_sum > 1.0:
                        self.over_weight_rows.add(self.all_rows)
                    if influence_count > MAXIMUM_INFLUENCE_COUNT > 0:
                        self.over_influence_limit_rows.add(self.all_rows)
                        
                    #データ編集用に行をキーに頂点とスキンクラスタを格納しておく
                    self.vtx_row_dict[self.all_rows] = [v, skin_cluster, influences, [], 
                                                                    inf_id_list, vtx_name, node, node_id]
                    self.all_rows += 1#全体の行数を数えておく
                    
                #0フィルター用にインフルエンスごとのウェイト合計値を出す
                if self.filter_but.isChecked():
                    rot_weight_list = map(list, zip(*sel_weight_list))
                    for j, inf_weight in enumerate(rot_weight_list):
                        inf_weight_sum = sum(inf_weight)
                        self.filter_weight_dict[influences[j]] += inf_weight_sum
    
        self.mesh_rows.append(self.all_rows)#最後のメッシュの末尾探索のためにもう一個分メッシュ行を追加しておく
        
        self.counter.count('adjust weight data :')
        
        #表示中のインフルエンスの合計が0ならフィルターする
        if self.filter_but.isChecked():
            for inf, value in self.filter_weight_dict.items():
                if inf in self.all_influences:
                    #フィルター対象でもサーチに含まれている場合はスキップする
                    if self.search_joint_list and self.search_but_group.checkedId() == 1:
                        if any([True if s.upper() in inf.split('|')[-1].upper() else False for s in self.search_joint_list]):
                            continue
                    if value == 0.0:
                        self.all_influences.remove(inf)
                        
        #サーチ文字リストがあればフィルターする
        if self.search_joint_list and self.search_but_group.checkedId() == 0:
            self.all_influences = [inf for inf in self.all_influences if any([True if s.upper() in inf.split('|')[-1].upper() else False for s in self.search_joint_list])]
        #print 'all_influences :',self.all_influences
        #オーバーライドカラーを取得しておく
        self.store_infulence_override_color()
        
        self.node_influence_id_list_dict = {}#カラム抜けを回避するためのノードごとのリスト辞書
        for node in self.hl_nodes:          
            #未バインドのカラム抜け対策のためインフルエンスとカラムの対応リストを作っておく
            influences = self.influences_dict[node]
            node_influence_id_list = [influences.index(inf)  if inf in influences else None for inf in self.all_influences]       
            self.node_influence_id_list_dict[node] = node_influence_id_list
            
            #メッシュ行にフィルタリング後のインフルエンス数分の空データを設定しておく
            items = self.mesh_model_items_dict[node]
            for inf in self.all_influences:
                items[inf] = None
                
        #インフルエンスのカラーを取得してモデルに渡す
        self.inf_color_list = [cmds.getAttr(j+'.objectColor') for j in self.all_influences]
        #インフルエンス名とカラムの対応辞書を作る
        self.inf_column_dict = {inf:i for i,inf in enumerate(self.all_influences)}
        
        #事前に集めたロック情報をもとにロック設定する
        inf_column_dict_keys = self.inf_column_dict.keys()
        for row, lock_data in self.lock_data_dict.items():
            vtx_name = lock_data[0]
            lock_influences = lock_data[1]
            for influence in lock_influences:
                if influence in inf_column_dict_keys:
                    column = self.inf_column_dict[influence]
                    self.weight_lock_data.add((row, column))
                #ロックされているインフルエンスIDをすべて格納する
                try:
                    self.vtx_lock_data_dict[vtx_name].add(node_influence_id_dict[influence])
                except Exception as e:
                    #print 'lock setting error :', e.message
                    pass
                   
        try:#都度メモリをきれいに
            del self.weight_model._data
            self.weight_model._data = {}
        except Exception as e:
            print e.message, 'in get set' 
        try:#都度メモリをきれいに
            self.weight_model.deleteLater()
            del self.weight_model
        except Exception as e:
            print e.message, 'in get set'
            pass
        try:
            self.sel_model.deleteLater()
            del self.sel_model
        except Exception as e:
            print e.message, 'in get set'
            
        self.weight_model = TableModel(self._data, self.view_widget, self.mesh_rows, 
                                        self.all_influences, self.v_header_list, self.inf_color_list)
        self.weight_model.over_influence_limit_dict = self.over_influence_limit_dict
        self.weight_model.under_weight_rows = self.under_weight_rows
        self.weight_model.over_weight_rows = self.over_weight_rows
        self.weight_model.over_influence_limit_rows = self.over_influence_limit_rows
        self.weight_model.norm = self.norm_but.isChecked()#ノーマル状態かどうかを渡しておく
        self.weight_model.weight_lock_cells = self.weight_lock_data#ロック状態を渡す
        
        self.counter.count('setup ui model :')
            
        self.sel_model = QItemSelectionModel(self.weight_model)#選択モデルをつくる
        self.sel_model.selectionChanged.connect(self.cell_changed)#シグナルをつなげておく
        self.view_widget.setModel(self.weight_model)#表示用モデル設定
        self.view_widget.setSelectionModel(self.sel_model)#選択用モデルを設定
        self.selected_items = []
        
        if not self.show_flag:
            self.show_flag = True
            self.show()
        
        self.counter.count('ui data finalaize :')
        
        #↓もういらない？
        #self.model_index = self.weight_model.indexes#モデルのインデックス番号をあらかじめ取得
        #self.model_id_dict = {cell_id:i for i, cell_id in enumerate(self.model_index)}
        
        #前回の選択を格納
        self.pre_hl_nodes = self.hl_nodes
        
        #ヘッダーのサイズを整える
        set_table_header_width(self.view_widget, self.weight_model, add=(FLOAT_DECIMALS-2)*7-10)
        
        self.counter.count('ui create model list dict :')
        
        self.counter.lap_print(print_flag=COUNTER_PRINT, window=self)
        
        
    #セルの選択変更があった場合に現在の選択セルを格納する
    #@timer
    #@prof.profileFunction()
    def cell_changed(self, selected, deselected):
        #ジョイントハイライトは選択状態の格納に依存しない形に独立
        if self.joint_hl_but.isChecked():
            self.hilite_joints()
            
        self.reset_message()#メッセージ初期化
        if self.pre_tool:
            self.hilite_flag = True#get_setしないためのフラグ
            #print 'hl nodes :', self.hl_nodes
            if self.pre_comp_mode:
                cmds.selectMode(co=True)
                #cmds.hilite(self.hl_nodes, r=True)
            else:
                cmds.selectMode(o=True)
            if self.pre_tool:
                cmds.setToolTo(self.pre_tool)
            #print 'header selection :', self.header_selection
            if self.header_selection:
                cmds.hilite(self.hl_nodes, r=True)
                cmds.select(self.header_selection, r=True)
            self.pre_tool = None
            self.header_selection = None
        self.select_change_flag = True
        #ここめっちゃ重い↓対応要件等
        self.selected_items =  self.sel_model.selectedIndexes()
        #self.selected_items =  []
        
        if not self.selected_items:
            self.weight_input_sld.setValue(0.0)
        else:
            self.change_add_mode(self.add_mode, change_only=True)#スピンボックスの値を更新するためにAddMode関数にいく
        self.pre_add_value = 0.0#加算量を初期化
        self.sel_rows = list(set([item.row() for item in self.selected_items]))
        
        
        if self.highlite_but.isChecked():
            self.hilite_vertices()
        
    @timer
    def hilite_vertices(self):
        cmds.undoInfo(swf=False)#不要なヒストリを残さないようにオフる
        
        self.counter.reset()
         
        vertices = []
        row_count =  self.weight_model.rowCount()
        selected_item = self.sel_model.currentIndex()
        if not selected_item:
            return
        '''
        if MAYA_VER <= 2016:#2016以前はIntersectsで正しくとれる
            rows = [id for id in xrange(row_count) if self.sel_model.rowIntersectsSelection(id, selected_item)]
        else:#PySide2ではなぜかrowIntersectsSelectionが正しく機能しない問題
            rows = list(set([item.row() for item in self.sel_model.selectedIndexes()]))
        '''
        rows = list(set([item.row() for item in self.selected_items]))
        #print rows
        if rows:
            #高速選択するために頂点情報をつながり形式にしてまとめるvtx[0:5000]みたいな
            #全選択だと展開時より20倍くらい早い
            mesh_vtx_dict = defaultdict(lambda : [])
            pre_vid = None
            pre_node = None
            vtx_connection = []
            row_count = len(rows) - 1
            for i, r in enumerate(rows+[rows[0]]):
                node = self.vtx_row_dict[r][6]
                vid = self.vtx_row_dict[r][0]
                if pre_node == node or pre_node is None:
                    if pre_vid == vid-1 or pre_vid is None:
                        pre_node = node
                        pre_vid = vid
                        vtx_connection.append(vid)
                        continue
                if pre_node != node:
                    sel_node = pre_node
                else:
                    sel_node = node
                vertices.append(sel_node+'.vtx['+str(vtx_connection[0])+':'+str(vtx_connection[-1])+']')
                pre_node = node
                vtx_connection = [vid]
        self.hilite_flag = True#get_setしないためのフラグ
        self.counter.count(string='get cell vtx :')
        
        ##選択場合分け、コンポーネントモードが微妙なので要件等
        if not vertices:
            cmds.select(self.original_selection, r=True)
        else:
            if cmds.selectMode(q=True, o=True):
                cmds.select(vertices+self.original_selection, r=True)
            else:
                cmds.select(vertices, r=True)
            
        self.counter.count(string='select vtx :')
        self.counter.lap_print(print_flag=COUNTER_PRINT)
        
        cmds.undoInfo(swf=True)#ヒストリを再度有効か
        
    #ハイライトボタン押された時に選択反映するスロット
    def reset_hilite(self):
        if not self.highlite_but.isChecked():
            self.hilite_flag = True
            cmds.select(cl=True)
            cmds.select(self.original_selection, r=True)
        else:
            self.cell_changed(self.selected_items, None)
            
    def store_infulence_override_color(self):
        self.joint_override_dict = {}
        self.joint_override_mode_dict = {}
        self.joint_override_color_dict = {}
        for inf in self.all_influences:
            self.joint_override_dict[inf] = cmds.getAttr(inf + '.overrideEnabled')
            #オーバライドをインデクス指定かRGB指定か
            self.joint_override_mode_dict[inf] = cmds.getAttr(inf + '.overrideRGBColors')
            #オーバーライドカラー設定
            self.joint_override_color_dict[inf] = cmds.getAttr(inf + '.overrideColor')
            
    def hilite_joints(self):
        cmds.undoInfo(swf=False)#不要なヒストリを残さないようにオフる
        column_count =  self.weight_model.columnCount()
        selected_item = self.sel_model.currentIndex()
        if not selected_item:
            return
        self.sel_columns = [id for id in xrange(column_count) if self.sel_model.columnIntersectsSelection(id, selected_item)]
        for i, influence in enumerate(self.all_influences):
            try:
                if i in self.sel_columns:
                    if MAYA_VER >= 2016:
                        cmds.setAttr(influence+'.useObjectColor', 2)
                        cmds.setAttr(influence+'.wireColorR', 1)
                        cmds.setAttr(influence+'.wireColorG', 1)
                        cmds.setAttr(influence+'.wireColorB', 0.9)
                    else:
                        cmds.setAttr(influence + '.overrideEnabled', 1)
                        cmds.setAttr(influence + '.overrideRGBColors', 0)
                        cmds.setAttr(influence + '.overrideColor', 16)
                else:
                    if MAYA_VER >= 2016:
                        cmds.setAttr(influence+'.useObjectColor', 1)
                    else:
                        cmds.setAttr(influence + '.overrideColor', 0)
            except:
                pass
            try:
                if MAYA_VER >= 2016:
                    cmds.setAttr(influence + '.overrideEnabled', 0)
            except Exception as e:
                #print e.message
                self.set_message(msg='- Joint Hilite Error : Override attr still locked -', error=True)
                pass
        cmds.undoInfo(swf=True)#ヒストリを再度有効か
        
    def reset_joint_hl(self):
        if not self.joint_hl_but.isChecked():
            self.disable_joint_override()
        else:
            self.cell_changed(self.selected_items, None)
            
    #全ての骨ハイライトをおふ
    def disable_joint_override(self):
        cmds.undoInfo(swf=False)#不要なヒストリを残さないようにオフる
        for influence in self.all_influences:
            try:#オブジェクトカラー設定を戻す
                if MAYA_VER >= 2016:
                    cmds.setAttr(influence+'.useObjectColor', 1)
                    cmds.setAttr(influence+'.wireColorR', 0.5)
                    cmds.setAttr(influence+'.wireColorG', 0.5)
                    cmds.setAttr(influence+'.wireColorB', 0.5)
            except:
                pass
            try:#オーバーライド設定を戻す
                cmds.setAttr(influence + '.overrideEnabled', self.joint_override_dict[influence])
            except Exception as e:
                #print e.message
                self.set_message(msg='- Joint Unhilite Error : Override attr still locked -', error=True)
                pass
            if MAYA_VER <= 2015:#2015以下はオーバーライドカラー設定も戻す
                try:#オーバーライド設定を戻す
                    cmds.setAttr(influence + '.overrideRGBColors', self.joint_override_mode_dict[influence])
                    cmds.setAttr(influence + '.overrideColor', self.joint_override_color_dict[influence])
                except:
                    pass
        cmds.undoInfo(swf=True)#ヒストリを再度有効か
        
    joint_tool = 0
    def change_joint_tool_mode(self, id):
        self.joint_tool = id
        
    #ヘッダーからジョイントを選択しに行く
    pre_tool = None
    header_selection = None
    pre_comp_mode = None
    target_tool_list = [None, 'scaleSuperContext', 'RotateSuperContext', 'moveSuperContext']
    def select_joint_from_header(self):
        cmds.undoInfo(swf=False)#不要なヒストリを残さないようにオフる
        self.pre_tool = cmds.currentCtx()#ツールを復旧するために取得
        self.header_selection = self.original_selection[:]
        self.pre_comp_mode = cmds.selectMode(q=True, co=True)
        v_header = self.view_widget.verticalHeader()
        v_header_width = v_header.sizeHint().width()
        h_header = self.view_widget.horizontalHeader()
        h_header_height = h_header.sizeHint().height()
        pos = self.view_widget.mapFromGlobal(QCursor.pos())
        pos_x = pos.x() - v_header_width - 2#誤差補正
        pos_y = pos.y() - h_header_height -2 #誤差補正
        row = self.view_widget.rowAt(pos_y)
        column = self.view_widget.columnAt(pos_x)
        influence = self.all_influences[column]
        self.hilite_flag = True#get_setしないためのフラグ
        cmds.select(influence)
        if self.target_tool_list[self.joint_tool]:
            cmds.setToolTo(self.target_tool_list[self.joint_tool])
        cmds.undoInfo(swf=True)#ヒストリを再度有効か
        
    #Adjustボタン押したとき、頂点選択しにいく
    def select_vertex_from_cells(self):
        rows = list(set([item.row() for item in self.selected_items]))
        vertices = [self.vtx_row_dict[r][5] for r in rows]
        if vertices:
            cmds.selectMode(co=True)
            cmds.select(vertices, r=True)
            
    #選択されているセルの行のみの表示に絞る
    def show_selected_cells(self):
        rows = list(set([item.row() for item in self.selected_items]))
        self.show_dict = defaultdict(lambda : [])
        self.show_dict['clear'] = []#何も選択されてなかったときのために初期値与える
        for r in rows:
            vtx_row_dict = self.vtx_row_dict[r]
            node = vtx_row_dict[6]
            self.show_dict[node]  += [vtx_row_dict[0]]
        self.get_set_skin_weight(show_dict=self.show_dict)
                
    def show_all_cells(self):
        self.get_set_skin_weight(cycle=True, show_all=True)
            
    def show_bad_rows(self):
        self.get_set_skin_weight(show_all=True)
        rows = set()
        self.show_dict = defaultdict(lambda : [])
        self.show_dict['clear'] = []#何も見つからなかった時のために初期値与える
        if self.under_wt_but.isChecked():
            rows = rows | self.weight_model.under_weight_rows
        if self.over_wt_but.isChecked():
            rows = rows | self.weight_model.over_weight_rows
        if self.over_inf_but.isChecked():
            rows = rows | self.weight_model.over_influence_limit_rows
        for r in rows:
            vtx_row_dict = self.vtx_row_dict[r]
            node = vtx_row_dict[6]
            self.show_dict[node]  += [vtx_row_dict[0]]
        self.get_set_skin_weight(show_dict=self.show_dict, show_bad=True)
        
            
    #スピンボックスがフォーカス持ってからきーが押されたかどうかを格納しておく
    key_pressed = None
    def store_keypress(self, pressed):
        self.key_pressed = pressed
        self.editing_count = 0
        self.re_forcus_flag = False
        
        
    pre_new_value = 0.0
    selected_items = []
    select_change_flag = True
    from_spinbox =False
    #入力値をモードに合わせてセルの値と合算、セルに値を戻す
    caluc_times = 0
    editing_count = 0
    @timer
    def calc_cell_value(self, from_spinbox=False, from_input_box=False, from_slider=False):
        self.from_spinbox = from_spinbox
        
        if self.closed_flag:#ウィンドウ閉じた後は何もしない
            #print 'allready closed return :'
            return
            
        if self.from_spinbox:
            #print 'from spin box !!:'
            self.from_spinbox = False
            if not self.weight_input.hasFocus():
                #print 'from spin box and not focus return:'
                if self.re_forcus_flag:
                    self.weight_input.setFocus()
                return
            #return
            
        if not self.change_flag and from_slider:
            #print 'not change return :'
            self.from_spinbox = False
            return
            
        if not self.selected_items:
            #print 'no selection return :'
            self.from_spinbox = False
            return
            
        #Editing_Finishedが二回走らないように予防
        if from_spinbox:
            if self.editing_count == 1:
                #print 'from spin box 2nd return :'
                self.editing_count = 0
                self.weight_input.setFocus()
                return
            else:
                #print 'from spin box 1st go :'
                self.re_forcus_flag = True
            self.editing_count += 1
        
        #絶対値モードでフォーカス外したときに0だった時の場合分け
        '''
        if from_spinbox and not self.key_pressed and not from_input_box:
            #print 'focus error :'
            print 'from spin and no key and not input box return :'
            self.from_spinbox = False
            return
        '''
        #print 'calc Cell value *+*+**+*+*+*+**+*:', self.caluc_times
        #入力重複回避ここまで------------------------------------------------------------
        self.counter.reset()
        self.text_value_list = []
        self.locked_cells = self.weight_model.weight_lock_cells#ロック情報を取得
        
        #0-1表示なら割り算省略、ちょっとは早くなる？？
        if MAXIMUM_WEIGHT == 100.0:
            if not from_input_box:
                new_value = self.weight_input.value()/100
            else:
                new_value = self.input_box_value/100.0
        else:
            if not from_input_box:
                new_value = self.weight_input.value()
            else:
                new_value = self.input_box_value
            
        #print 'calc cell value :', self.caluc_times, 'val :', new_value
        self.caluc_times += 1
        #絶対値の時の処理
        self.update_rows = set()
        self.row_column_dict = defaultdict(lambda : [])
        if self.add_mode == 0:#abs
            new_value = max(0.0, min(new_value, 1.0))
            #まとめてデータ反映
            for cell_id in self.selected_items:
                row = cell_id.row()
                column = cell_id.column() 
                #ロックされてたらスキップ
                if (row, column) in self.locked_cells:
                    continue
                ##ここはsetDataしにいくより直接辞書更新した方がはやいので後ほど修正
                self.weight_model.setData(cell_id, new_value)
                #焼き込みようリストを更新しておく
                self.update_rows.add(row)
                self.row_column_dict[row].append(column)#行に対応する選択カラムを記録する
            after_value = new_value
            #print 'new_abs_value',new_value, from_spinbox, from_input_box
        else:
            #加算モードで0なら変化なしなので逃げる
            if new_value == 0.0:
                return
            #最大最小を設定しておく
            min_value = 0.0
            max_value = 1.0
            #加算の時の処理
            sub_value = new_value - self.pre_new_value
            for cell_id in self.selected_items:
                row = cell_id.row()
                column = cell_id.column() 
                #ロックされてたらスキップ
                if (row, column) in self.locked_cells:
                    continue
                #焼き込みようリストを更新しておく
                self.update_rows.add(row)
                self.row_column_dict[row].append(column)#行に対応する選択カラムを記録する
                org_value = self.weight_model.get_data(row=row, column=column)#もとの値
                
                if self.add_mode == 1:#add
                    added_value = org_value + sub_value
                    
                if self.add_mode == 2:#add%
                    added_value = org_value * (1.0 + new_value)
                        
                if not self.no_limit_but.isChecked():
                    if added_value > 1.0:
                        added_value = 1.0
                if added_value < 0.0:
                    added_value = 0.0
                    
                self.weight_model.setData(cell_id, added_value)
                #print 'calc 2 num :', org_value, new_value
                #print 'new_add_value',added_value, 'spin :', from_spinbox, 'input :', from_input_box
                    
            #処理後のスピンボックスの値を設定
            if from_spinbox or from_input_box:
                after_value = 0.0
                self.pre_new_value = 0.0
            else:
                self.pre_new_value = new_value
                after_value = new_value
                
        self.counter.count(string='Cell Value Calculation :')
                
        #ベイク計算に入る
        self.precalculate_bake_weights()
        
        #インプットボックスの値を変更すると以前のキャッシュデータに影響があるのでベイク後に変更する
        self.weight_input.setValue(after_value*MAXIMUM_WEIGHT)#UIのスピンボックスに数値反映
        
        self.counter.lap_print(print_flag=COUNTER_PRINT, window=self)
        
    #変更されたウェイト事前計算する
    #@prof.profileFunction()
    @timer
    def precalculate_bake_weights(self, realbake=True, ignoreundo=False, enforce=0, round_digit=None):
        #print 'precalculate_bake_weights : '
        #self.counter.reset()
        #enforce-1は強制正規化フラッグ扱い
        if round_digit:#丸めの時は正規化しない
            norm_flag = False
        else:
            norm_flag = self.norm_but.isChecked()
        new_data = self.weight_model._data
        #print 'get new_data :', new_data
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
        node_weight_list = []
        org_node_weight_list = []
        pre_node = None
        pre_row_inf_id_list = None
        self.update_rows = sorted(list(self.update_rows))
        if not self.update_rows:
            return
        last_row = list(self.update_rows)[-1]
        for row in self.update_rows:
            force_norm_flag = False
            bake_with_norm = False
            bake_weight_flag = True
            #事前に格納しておいた行のデータを引き出す
            row_data = self.vtx_row_dict[row]
            vtx = row_data[0]
            skin_cluster = row_data[1]
            influences =  row_data[2]
            all_influences_count = len(influences)#バインドされているインフルエンスの総数
            row_inf_id_list = row_data[4]
            vtx_name = row_data[5]
            node = row_data[6]
            node_id = row_data[7]
            node_influence_id_list = self.node_influence_id_list_dict[node]
            
            #アンドゥと不正計算防止のために元の値を取得
            org_weight = self.node_weight_dict[node][vtx]
            
            new_weight = new_data[row]
            
            #ロックされたセル情報からロックインフルエンスのIDリストを作る
            locked_inf_id_list = self.vtx_lock_data_dict[vtx_name]
            
            #エンフォースリミットを実行
            if enforce >= 1:
                #ロックされてるものは無限大にしておいてあとで数値戻す
                lock_sign_count = 0#ロックされているもののうち有効数字が入っているものの数
                if locked_inf_id_list:
                    org_weight_list = new_weight[:]
                    for i in locked_inf_id_list:
                        if new_weight[i]:#ウェイト値が0でなければ無限に
                            lock_sign_count += 1
                            new_weight[i] = float('inf')
                #ロック有効数字がエンフォースリミットより多い時は有効数+1でまとめる
                if enforce <= lock_sign_count:
                    temp_enforce = lock_sign_count+1
                else:
                    temp_enforce = enforce
                influence_count = all_influences_count - new_weight.count(0.0)
                if influence_count <= temp_enforce:#エンフォース数を下回っているときは元の値
                    new_weight = org_weight
                else:
                    enforce_list = sorted([[i, w]for i, w in enumerate(new_weight)], key=lambda x:x[1], reverse=True)
                    enforce_list = [iw if i < temp_enforce else [iw[0], 0.0] for i, iw in enumerate(enforce_list)]
                    new_weight = [iw[1] for iw in sorted(enforce_list, key=lambda x:x[0])]
                    for i in locked_inf_id_list:
                        new_weight[i] = org_weight_list[i]
                    self.row_column_dict[row] = []
                    force_norm_flag = True
                    
            #桁数丸めを実行
            elif round_digit is not None:
                pre_round_sum = round(sum(new_weight), 10)
                round_weight = map(lambda w:round(w, round_digit), new_weight)
                after_round_sum = round(sum(round_weight), 10)
                sub_value = pre_round_sum - after_round_sum
                if sub_value == 0.0:
                    new_weight = round_weight
                else:
                    for i, w in enumerate(round_weight):
                        if w > abs(sub_value):
                            round_weight[i] = round(w + sub_value, round_digit)
                            break
                    new_weight = round_weight
                force_norm_flag = False#丸めの時は平均化しない
                norm_flag = False
                
            elif enforce == 0:
                force_norm_flag = False
            else:
                force_norm_flag = True
            
            #ウェイト合計を出す0.2sec
            all_weight_sum = sum(new_weight)
            #if all_weight_sum == 1.0 and enforce == -1 and round_digit:
                #norm_flag = False
                #force_norm_flag =  False
                #new_weight = org_weight
            #合計が1.0より大きければ強制的に正規化する
            if all_weight_sum > 1.0 and not self.no_limit_but.isChecked():
                force_norm_flag = True
            elif force_norm_flag == True:
                pass
            else:
                force_norm_flag = False
            
            #ウェイト正規化処理0.2sec
            if norm_flag or force_norm_flag:
                norm_weight = []#正規化格納用
                #ロックされているウェイトの合計を出しておく
                locked_sum = sum([new_weight[i] for i in locked_inf_id_list])
                #ロック合計が1.0以上なら他は0.0に
                if locked_sum >= 1.0:
                    for i, w in  enumerate(new_weight):
                        if i in locked_inf_id_list:
                            norm_weight.append(w)
                        else:
                            norm_weight.append(0.0)
                else:
                    bake_with_norm = True
                    column_list = self.row_column_dict[row]#行のうち選択されているカラムのリスト
                    column_inf_id_list = [node_influence_id_list[i] for i in column_list]#選択カラムに対応するインフルエンスのリスト
                    
                    #スライダ中は値が振り切っても戻れるように選択外の値はプレス直後のものを使う
                    if self.change_flag:
                        pressed_weight = self.press_start_data[row]
                        for inf_id in column_inf_id_list:
                            pressed_weight[inf_id] = new_weight[inf_id]
                        new_weight = pressed_weight
                        #print 'use pressed weight :', pressed_weight
                    
                    select_sum = sum([new_weight[i] for i in column_inf_id_list if i is not None])#選択してるカラムの合計値
                    other_inf_id_list = list(set(row_inf_id_list) - set(column_inf_id_list))
                    other_sum = sum([new_weight[i] for i in other_inf_id_list]) - locked_sum
                    
                    ##ロックセル以外の合計が0.0の場合は正規化できないので変更前の値にもどす
                    if other_sum + select_sum == 0.0:
                        new_weight = org_weight
                        select_sum = sum([new_weight[i] for i in column_inf_id_list if i is not None])#選択してるカラムの合計値
                    #選択セルの合計1以上の時のノーマライズ処理
                    if select_sum + locked_sum >= 1.0:
                        for i, w in  enumerate(new_weight):
                            if i in locked_inf_id_list:
                                norm_weight.append(w)
                            elif  i in column_inf_id_list:
                                norm_weight.append(w/select_sum*(1.0-locked_sum))
                            else:
                                norm_weight.append(0.0)
                                
                    #1より小さい時のノーマライズ処理
                    elif select_sum < 1.0:
                        all_sum = select_sum + locked_sum
                        if all_sum >= 1.0 or other_sum == 0.0:
                            if other_sum == select_sum == 0.0:
                                if not enforce:
                                    bake_weight_flag = False
                            other_ratio = 0.0
                            if select_sum != 0.0:
                                ratio = (1 - locked_sum) / select_sum
                            else:
                                ratio = 0.0
                        else:
                            new_other_sum = 1.0 - all_sum
                            other_ratio = new_other_sum / other_sum
                            ratio = 1.0
                        for i, w in  enumerate(new_weight):
                            if i in locked_inf_id_list:
                                norm_weight.append(w)
                            elif i in column_inf_id_list:
                                norm_weight.append(new_weight[i]  * ratio)
                            else:
                                norm_weight.append(new_weight[i]  * other_ratio)
                new_weight = norm_weight[:]
                #print 'normalaized weight :', new_weight
                
            if bake_weight_flag:#焼きこみフラグ有効なら焼きこみ辞書に追加する
                #メッシュが変わったらベイク用辞書をまとめて更新する
                #都度MDoubleArrayにキャストすると重いのでノードごとにまとめて
                #まとめると早くなった0.2sec
                if node != pre_node and pre_node is not None:
                    self.bake_node_weight_dict[pre_node] += node_weight_list
                    self.org_node_weight_dict[pre_node] += org_node_weight_list
                    node_weight_list = []
                    org_node_weight_list = []
                    if MAYA_VER >= 2016:
                        self.bake_node_inf_dict[pre_node] = om2.MIntArray() + pre_row_inf_id_list
                    else:
                        self.bake_node_inf_dict[pre_node] = om.MIntArray() + pre_row_inf_id_list
                if row == last_row:
                    node_weight_list += new_weight
                    org_node_weight_list += org_weight
                    self.bake_node_weight_dict[node] += node_weight_list
                    self.org_node_weight_dict[node] += org_node_weight_list
                    if MAYA_VER >= 2016:
                        self.bake_node_inf_dict[node] = om2.MIntArray() + row_inf_id_list
                    else:
                        self.bake_node_inf_dict[node] = om.MIntArray() + row_inf_id_list
                node_weight_list += new_weight
                org_node_weight_list += org_weight
                #ここはそんなに重くない0.2sec
                self.bake_node_id_dict[node] += [vtx] 
                #アンドゥ・リドゥ用に2次元配列ウェイトもつくる
                self.redo_node_weight_dict[node].append(new_weight)
                self.undo_node_weight_dict[node].append(org_weight)
            pre_node = node
            pre_row_inf_id_list = row_inf_id_list
            
            #選択ノーマライズフラグが立っている場合はテーブルを更新する（コストは低い）
            if norm_flag or force_norm_flag or round is not None:
                weight_list = self.vtx_weight_dict[vtx_name] 
                #参照されているリストを更新するだけでUIに反映されるっぽい、、すごいぞ！！！
                for i, w in enumerate(new_weight):
                    weight_list[i] = w
                    
            #表示切替のためにテーブルの不正ウェイトセットを更新する
            after_weight_sum = round(sum(new_weight), 10)#丸めないと精度誤差で判定がずれる
            if after_weight_sum < 1.0:
                self.weight_model.under_weight_rows.add(row)
                try:
                    self.weight_model.over_weight_rows.remove(row)
                except:
                    pass
            elif after_weight_sum > 1.0:
                self.weight_model.over_weight_rows.add(row)
                try:
                    self.weight_model.under_weight_rows.remove(row)
                except:
                    pass
            else:
                try:
                    self.weight_model.under_weight_rows.remove(row)
                except:
                    pass
                try:
                    self.weight_model.over_weight_rows.remove(row)
                except:
                    pass
            influence_count = all_influences_count - new_weight.count(0.0)
            self.weight_model.over_influence_limit_dict[row] = influence_count
            
        self.counter.count(string='Weight Calculation :')
        
        #実際の焼きこみ
        try:
            self.om_bake_skin_weight(realbake=True, ignoreundo=self.change_flag)
        except Exception as e:
            try:
                print 'Bake Skin Weight Failure :', e.message
                #プラグインをリロードしてリトライする
                cmds.loadPlugin('bake_skin_weight.py', qt=True)
                cmds.pluginInfo('bake_skin_weight.py', e=True, autoload=True)
                self.om_bake_skin_weight(realbake=True, ignoreundo=self.change_flag)
            except:
                #ダメだったら通知
                msg = lang.Lang(en='Failed to write weights. Please check the plugin manager\nbake_skin_weight.py',
                                        ja='書き込みに失敗しました。プラグインマネージャを確認してください\nbake_skin_weight.py').output()
                self.set_message(msg=msg, error=True)
                
        self.counter.count(string='Bake Skin Weight :')
        #最後に表示状態の更新
        self.refresh_table_view()
        self.counter.count(string='Refresh UI :')
        self.counter.lap_print(print_flag=COUNTER_PRINT)
        
    def om_bake_skin_weight(self, realbake=True, ignoreundo=False):
        #焼きこみデータをグローバルに展開
        set_current_data(self.bake_node_id_dict, self.bake_node_weight_dict, 
                                self.bake_node_inf_dict, self.node_skinFn_dict, 
                                self.undo_node_weight_dict, self.redo_node_weight_dict,
                                self.org_node_weight_dict)#最後はアンドゥようにオリジナル渡す
        #焼きこみコマンド実行
        cmds.bakeSkinWeight(rb=realbake, iu=ignoreundo)
        
    #ビューの状態を更新する
    def refresh_table_view(self):
        #フォーカス移してテーブルの状態を更新する
        self.view_widget.setFocus()
        self.view_widget.clearFocus()
        #縦ヘッダーを取得
        header = self.view_widget.verticalHeader()
        #ヘッダーの数だけセクション（行の頭）の状態をアップデートする
        for i in range(header.count()):
            header.updateSection(i)
        '''
        try:
            self.weight_model.reset()
        except:
            pass
        '''
                
    change_flag = False
    def sld_pressed(self):
        cmds.undoInfo(openChunk=True)
        #マウスプレス直後に履歴を残す焼き込みする。実際のベイクはしない。
        self.press_start_data = copy.deepcopy(self.weight_model._data)
        self.setup_update_row_data()
        self.precalculate_bake_weights(realbake=False, ignoreundo=False)
        self.change_flag = True#スライダー操作中のみ値の変更を許可するフラグ
        #print 'sld mouse pressed'
            
    #パーセントの特殊処理、値をリリースして初期値に戻る
    def sld_released(self):
        self.change_flag = False
        self.calc_cell_value()
        if self.add_mode == 1 or self.add_mode == 2:
            self.weight_input.setValue(0.0)
            self.change_from_spinbox()
            self.pre_new_value = 0.0
        cmds.undoInfo(closeChunk=True)
                
    def create_job(self):
        global select_job
        if 'select_job' in globals():
            if select_job is not None:
                cmds.scriptJob(k=select_job)
        select_job = cmds.scriptJob(cu=True, e=("SelectionChanged", self.get_set_skin_weight))
        
    def remove_job(self):
        global select_job
        if select_job:
            #print 'remove job :', select_job
            cmds.scriptJob(k=select_job, f=True)
            select_job = None
            
    closed_flag = False
    def closeEvent(self, e):
        print 'window closed :'
        self.disable_joint_override()
        self.erase_func_data()
        self.closed_flag=True
        self.remove_job()
        self.save_window_data()
        self.deleteLater()
        
    #メモリ解放しっかり
    #ちゃんと消さないと莫大なUIデータがメモリに残り続けるので注意
    def erase_func_data(self):
        #print self.weight_model._data
        try:
            del self.weight_model._data#一番でかいっぽい
            self.weight_model._data = {}
        except Exception as e:
            print e.message, 'in close'
        try:
            self.weight_model.deleteLater()
            del self.weight_model
        except Exception as e:
            print e.message, 'in close'
        try:
            self.sel_model.deleteLater()
            del self.sel_model
        except Exception as e:
            print e.message, 'in close'
        try:
            self.view_widget.deleteLater()
            del self.view_widget
        except Exception as e:
            print e.message, 'in close'
        
        try:
            del self._data
            del self.hl_nodes
            del self.all_influences
            del self.all_skin_clusters
            del self.influences_dict 
            del self.node_vtx_dict 
            del self.node_weight_dict
            del self.node_skinFn_dict 
            
            del self.header_selection
            del self.all_rows
            del self.v_header_list
            del self.mesh_rows
            del self.vtx_row_dict
            del self.under_weight_rows
            del self.over_weight_rows
            del self.over_influence_limit_dict
            del self.over_influence_limit_rows
            del self.all_editable_rows
            del self.weight_lock_data
            del self.vtx_lock_data_dict
            del self.node_id_dict
            del self.mesh_model_items_dict
            del self.filter_weight_dict
            del self.vtx_weight_dict
            del self.lock_data_dict
        except Exception as e:
            print e.message, 'in close'
        print 'erase func data :'
            
        
#アンドゥ時に辞書を更新しておく。
def update_dict(node_weight_dict, node_id_dict):
    for node, new_weight_list in node_weight_dict.items():
        node_v_id_list = node_id_dict[node]#ノードごとの選択頂点リスト
        org_weight_list = WINDOW.node_weight_dict[node]#元のウェイトリストを引く
        for vid, new_weight in zip(node_v_id_list, new_weight_list):#頂点番号ループ
            WINDOW.node_weight_dict[node][vid] = new_weight#指定頂点のウェイトリストを置き換え
            
def reverse_dict(node_weight_dict, node_id_dict):
    for node, old_weight_list in node_weight_dict.items():
        WINDOW.node_weight_dict[node] = old_weight_list#元のウェイトリストを引く
    
#アンドゥの時に読み直す
def refresh_window():
    global WINDOW
    WINDOW.get_set_skin_weight(undo=True)
    WINDOW.weight_input.setValue(0.0)#値を設定
        
#焼き込みコマンドに渡すためにグローバルに要素を展開
def set_current_data(node_id, node_weight, node_inf, node_skin, undo_node_dict, redo_node_dict, org_node_dict):
    global BAKE_NODE_ID_DICT
    global BAKE_NODE_WEIGHT_DICT
    global BAKE_NODE_INF_DICT
    global NODE_SKINFN_DICT
    global UNDO_NODE_WEIGHT_DICT
    global REDO_NODE_WEIGHT_DICT
    global ORG_NODE_WEIGHT_DICT
    BAKE_NODE_ID_DICT = node_id
    BAKE_NODE_WEIGHT_DICT = node_weight
    BAKE_NODE_INF_DICT = node_inf
    NODE_SKINFN_DICT = node_skin
    UNDO_NODE_WEIGHT_DICT = undo_node_dict
    REDO_NODE_WEIGHT_DICT = redo_node_dict
    ORG_NODE_WEIGHT_DICT = org_node_dict

def get_current_data():
    global BAKE_NODE_ID_DICT
    global BAKE_NODE_WEIGHT_DICT
    global BAKE_NODE_INF_DICT
    global NODE_SKINFN_DICT
    global UNDO_NODE_WEIGHT_DICT
    global REDO_NODE_WEIGHT_DICT
    global ORG_NODE_WEIGHT_DICT
    return BAKE_NODE_ID_DICT, BAKE_NODE_WEIGHT_DICT, \
            BAKE_NODE_INF_DICT, NODE_SKINFN_DICT, \
            UNDO_NODE_WEIGHT_DICT, REDO_NODE_WEIGHT_DICT, \
            ORG_NODE_WEIGHT_DICT
    
        
