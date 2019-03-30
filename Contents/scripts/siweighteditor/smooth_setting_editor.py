# -*- coding: utf-8 -*-
from . import qt
from . import lang
import os
import json
import imp
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
try:
    imp.find_module('PySide2')
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from PySide2.QtCore import *
except ImportError:
    from PySide.QtGui import *
    from PySide.QtCore import *
    

class Option():
    def __init__(self):
        global WINDOW
        try:
            WINDOW.closeEvent(None)
            WINDOW.close()
        except Exception as e:
            #print e.message
            pass
        WINDOW = SubWindow()
        WINDOW.resize(300, 150)
        pos = QCursor.pos()
        WINDOW.move(pos.x(), pos.y())
        WINDOW.show()
    
    
class SubWindow(qt.SubWindow):
    def __init__(self, parent = None, init_pos=False):
        super(self.__class__, self).__init__(parent)
        self.loaded_data = self.load_data()
        self._init_ui()
        
    def _init_ui(self):
        sq_widget = QScrollArea(self)
        sq_widget.setWidgetResizable(True)#リサイズに中身が追従するかどうか
        sq_widget.setFocusPolicy(Qt.NoFocus)#スクロールエリアをフォーカスできるかどうか
        sq_widget.setMinimumHeight(1)#ウィンドウの最小サイズ
        self.setWindowTitle(u'- Smooth Setting-')
        self.setCentralWidget(sq_widget)
        
        self.main_layout = QVBoxLayout()
        sq_widget.setLayout(self.main_layout)
        
        sub_layout = QHBoxLayout()
        msg = lang.Lang(en='Required Weight Difference:', ja=u'必要なウェイト差:').output()
        label = QLabel(msg)
        sub_layout.addWidget(label)
        self.main_layout.addLayout(sub_layout)
        self.tolerance = qt.EditorDoubleSpinbox()
        self.tolerance.setDecimals(4)
        self.tolerance.setRange(0, 1.0)
        sub_layout.addWidget(self.tolerance)
        #スライダバーを設定
        self.tolerance_sld = QSlider(Qt.Horizontal)
        self.tolerance_sld.setRange(0, 10000)
        sub_layout.addWidget(self.tolerance_sld)
        #コネクト
        self.tolerance_sld.valueChanged[int].connect(lambda:self.tolerance.setValue(self.tolerance_sld.value()/10000.0))
        self.tolerance.editingFinished.connect(lambda:self.tolerance_sld.setValue(self.tolerance.value()*10000))
        self.tolerance_sld.setValue(self.loaded_data['weight_difference']*10000.0)
        self.tolerance.valueChanged.connect(self.save_data)
        
        self.main_layout.addWidget(qt.make_h_line())
        
        sub_layout = QHBoxLayout()
        msg = lang.Lang(en='Smoothing Iterations:', ja=u'スムージングの反復:').output()
        label = QLabel(msg)
        sub_layout.addWidget(label)
        self.main_layout.addLayout(sub_layout)
        self.iterations = QSpinBox()
        self.iterations.setRange(0, 100)
        sub_layout.addWidget(self.iterations)
        #スライダバーを設定
        self.iterations_sld = QSlider(Qt.Horizontal)
        self.iterations_sld.setRange(0, 100)
        sub_layout.addWidget(self.iterations_sld)
        #コネクト
        self.iterations_sld.valueChanged[int].connect(lambda:self.iterations.setValue(self.iterations_sld.value()))
        self.iterations.editingFinished.connect(lambda:self.iterations_sld.setValue(self.iterations.value()))
        self.iterations_sld.setValue(self.loaded_data['smoothing_iterations'])
        self.iterations.valueChanged.connect(self.save_data)
        
        self.main_layout.addWidget(qt.make_h_line())
        
        sub_layout = QHBoxLayout()
        msg = lang.Lang(en='Obey Max Influences:', ja=u'最大インフルエンス数に従う:').output()
        label = QLabel(msg)
        sub_layout.addWidget(label)
        self.main_layout.addLayout(sub_layout)
        
        self.obey_max_inf =  QCheckBox()
        self.obey_max_inf.setChecked(self.loaded_data['obey_max_inf'])
        self.obey_max_inf.stateChanged.connect(self.save_data)
        sub_layout.addWidget(self.obey_max_inf)
        
    @classmethod
    def load_data(self):
        self.dir_path = os.path.join(
            os.getenv('MAYA_APP_DIR'),
            'Scripting_Files')
        self.save_file = self.dir_path+'/siweighteditor_smooth_setting.json'
        #セーブデータが無いかエラーした場合はデフォファイルを作成
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    save_data = json.load(f)
            except Exception as e:
                print e.message
                save_data = self.save_default()
        else:
            save_data = self.save_default()
        return save_data
        
    @classmethod
    def save_default(self):
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)
        save_data = {}
        save_data['weight_difference'] = 0.0
        save_data['smoothing_iterations'] = 5
        save_data['obey_max_inf'] = True
        with open(self.save_file, 'w') as f:
            json.dump(save_data, f)
        return save_data
            
    def save_data(self):
        #print 'save smooth setting :'
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)
        save_data = {}
        save_data['weight_difference'] = self.tolerance.value()
        save_data['smoothing_iterations'] = self.iterations.value()
        save_data['obey_max_inf'] = self.obey_max_inf.isChecked()
        with open(self.save_file, 'w') as f:
            json.dump(save_data, f)
        
    def closeEvent(self, e):
        self.save_data()
        self.deleteLater()
