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
            print e.message
        WINDOW = SubWindow()
        #WINDOW.init_flag=False
        WINDOW.resize(800, 500)
        #WINDOW.move(WINDOW.pw-8, WINDOW.ph-31)
        WINDOW.show()
    
    
class SubWindow(qt.SubWindow):
    
    def __init__(self, parent = None, init_pos=False):
        super(self.__class__, self).__init__(parent)
        self.init_save()
        self._init_ui()
    
    def init_save(self):
        self.dir_path = os.path.join(
            os.getenv('MAYA_APP_DIR'),
            'Scripting_Files')
        self.start_file = self.dir_path+'/joint_rule_start.json'
        self.middle_file = self.dir_path+'/joint_rule_middle.json'
        self.end_file = self.dir_path+'/joint_rule_end.json'
        self.save_files = [self.start_file, self.middle_file, self.end_file]
    
    def _init_ui(self):
        sq_widget = QScrollArea(self)
        sq_widget.setWidgetResizable(True)#リサイズに中身が追従するかどうか
        sq_widget.setFocusPolicy(Qt.NoFocus)#スクロールエリアをフォーカスできるかどうか
        sq_widget.setMinimumHeight(1)#ウィンドウの最小サイズ
        self.setWindowTitle(u'- Joint Label Rules Editor-')
        self.setCentralWidget(sq_widget)
        
        self.main_layout = QVBoxLayout()
        sq_widget.setLayout(self.main_layout)
        
        second_layout = QHBoxLayout()
        self.main_layout.addLayout(second_layout)
        
        start_layout = QVBoxLayout()
        second_layout.addLayout(start_layout)
        msg = lang.Lang(en='- Prefixed LR naming convention -', ja=u'- 先頭のLR命名規則 -').output()
        start_layout.addWidget(QLabel(msg))
        self.start_list_widget = QTableWidget(self)
        start_layout.addWidget(self.start_list_widget)
        
        middle_layout = QVBoxLayout()
        second_layout.addLayout(middle_layout)
        msg = lang.Lang(en='- between LR naming conventions -', ja=u'- 中間のLR命名規則 -').output()
        middle_layout.addWidget(QLabel(msg))
        self.middle_list_widget = QTableWidget(self)
        middle_layout.addWidget(self.middle_list_widget)

        end_layout = QVBoxLayout()
        second_layout.addLayout(end_layout)
        msg = lang.Lang(en='- Suffixed LR naming convention -', ja=u'- 末尾のLR命名規則 -').output()
        end_layout.addWidget(QLabel(msg))
        self.end_list_widget = QTableWidget(self)
        end_layout.addWidget(self.end_list_widget)
        
        self.rule_table_list = [self.start_list_widget, self.middle_list_widget, self.end_list_widget]
        
        self.main_layout.addWidget(qt.make_h_line())
        
        button_layout = QHBoxLayout()
        self.main_layout.addLayout(button_layout)
        
        tip = lang.Lang(en='Reset table to initial state', 
                            ja=u'テーブルを初期状態にリセット').output()
        self.reset_but = qt.make_flat_btton(name='- Reset Joint Label Rules -', border_col=180, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        self.reset_but.clicked.connect(self.table_reset)
        button_layout.addWidget(self.reset_but)
        
        tip = lang.Lang(en='Clear table data', 
                            ja=u'テーブルのデータをクリア').output()
        self.clear_but = qt.make_flat_btton(name='- Clear Joint Label Rules -', border_col=180, 
                                                    flat=True, hover=True, checkable=False, destroy_flag=True, tip=tip)
        self.clear_but.clicked.connect(self.table_clear)
        button_layout.addWidget(self.clear_but)
        
        self.load_data()
        self.set_rule_data()
        self.table_setup()
        
    def table_setup(self):
        for table in self.rule_table_list:
            table.verticalHeader().setDefaultSectionSize(20)
            table.setSortingEnabled(True)
            table.setAlternatingRowColors(True)
            
    def set_rule_data(self):
        for table, lr_list in zip(self.rule_table_list, self.all_lr_list):
            self.set_table_data(table,  lr_list)
            table.setHorizontalHeaderLabels(self.header_labels)
        
    def table_clear(self):
        for table in self.rule_table_list:
            table.clear()
            table.setHorizontalHeaderLabels(self.header_labels)
            
    def table_reset(self):
        for table, lr_list in zip(self.rule_table_list, self.def_all_lr_list):
            table.clear()
            self.set_table_data(table,  lr_list)
            table.setHorizontalHeaderLabels(self.header_labels)
            
    
    def set_table_data(self, table, data_list):
        table.setColumnCount(2)
        table.setRowCount(100)
        for i, lr_list in enumerate(data_list):
            for j, lr in enumerate(lr_list):
                #print 'set rule :', lr
                item = QTableWidgetItem(lr)
                table.setItem(j, i, item)
                
    
    
    #初期値
    header_labels = ['Left', 'Right']
    start_l_list = ['L_', 'l_', 'Left_', 'left_']
    start_r_list = ['R_', 'r_', 'Right_', 'right_']
    mid_l_list = ['_L_', '_l_', '_Left_', '_left_']
    mid_r_list = ['_R_', '_r_', '_Right_', '_right_']
    end_l_list = ['_L', '_l', '_L.', '_l.', '_L..', '_l..', '_Left', '_left']
    end_r_list = ['_R', '_r', '_R.', '_r.', '_R..', '_r..', '_Right', '_right']
    
    start_lr_list = [start_l_list, start_r_list]
    mid_lr_list = [mid_l_list, mid_r_list]
    end_lr_list = [end_l_list, end_r_list]
    def_all_lr_list = [start_lr_list, mid_lr_list, end_lr_list]
    
    def load_data(self):
        #セーブデータが無いかエラーした場合はデフォファイルを作成
        self.all_lr_list = []
        for i, save_file in enumerate(self.save_files):
            if os.path.exists(save_file):#保存ファイルが存在したら
                try:
                    with open(save_file, 'r') as f:
                        save_data = json.load(f)
                        l_list = save_data.keys()
                        r_list = save_data.values()
                        self.all_lr_list.append([l_list, r_list])
                except Exception as e:
                    print e.message
                    self.all_lr_list.append(self.def_all_lr_list[i])
            else:
                self.all_lr_list.append(self.def_all_lr_list[i])
            
    def save_data(self):
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)
            
        for table, save_file in zip(self.rule_table_list, self.save_files):
            save_data = {}
            for row in range(100):
                left_data = table.item(row, 0)
                right_data = table.item(row, 1)
                if left_data and right_data:
                    if not left_data.text() or not right_data.text():
                        continue
                    #print 'save data :', left_data.text(), right_data.text()
                    save_data[left_data.text()] = right_data.text()
                    
            with open(save_file, 'w') as f:
                json.dump(save_data, f)
        
    def closeEvent(self, e):
        self.save_data()
        self.deleteLater()
