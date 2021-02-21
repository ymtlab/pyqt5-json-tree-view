import json
import sys
from PyQt5 import QtWidgets, QtCore

class JsonTreeView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(JsonTreeView, self).__init__(parent)

        self.view = QtWidgets.QTreeView(self)
        self.model = Model(self)
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.delegate = Delegate()
        self.lineEdit = QtWidgets.QLineEdit(self)
        self.button_expand_all = QtWidgets.QToolButton(self)
        self.button_collapse_all = QtWidgets.QToolButton(self)
        self.button_load = QtWidgets.QToolButton(self)
        self.button_save = QtWidgets.QToolButton(self)
        self.button_save_as = QtWidgets.QToolButton(self)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout2 = QtWidgets.QHBoxLayout()
        self.verticalLayout = QtWidgets.QVBoxLayout(self)

        self.proxy.setSourceModel(self.model)
        self.button_load.setText('Load')
        self.button_load.clicked.connect(self.load_json)
        self.button_save.setText('Save')
        self.button_save.clicked.connect(self.save_json)
        self.button_save_as.setText('Save As')
        self.button_save_as.clicked.connect(self.save_as_json)
        self.button_expand_all.setText('Expand all')
        self.button_expand_all.clicked.connect( lambda : self.view.expandAll() )
        self.button_collapse_all.setText('Collapse all')
        self.button_collapse_all.clicked.connect( lambda : self.view.collapseAll() )
        self.lineEdit.textChanged.connect(self.text_changed)

        self.horizontalLayout.addWidget(QtWidgets.QLabel('Filter', self))
        self.horizontalLayout.addWidget(self.lineEdit)

        self.horizontalLayout2.addWidget(self.button_load)
        self.horizontalLayout2.addWidget(self.button_save)
        self.horizontalLayout2.addWidget(self.button_save_as)
        self.horizontalLayout2.addWidget(self.button_expand_all)
        self.horizontalLayout2.addWidget(self.button_collapse_all)
        self.horizontalLayout2.addItem( QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum) )

        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout.addLayout(self.horizontalLayout2)
        self.verticalLayout.addWidget(self.view)

        self.view.setModel(self.proxy)
        self.view.setItemDelegate(self.delegate)
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.contextMenu)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        self.header = self.view.header()
        self.header.setSectionsClickable(True)
        self.header.sectionClicked.connect(self.header_clicked)

    def text_changed(self, text):
        self.proxy.setFilterRegExp( QtCore.QRegExp( text, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.RegExp ) )
        self.proxy.setFilterKeyColumn(-1)

    def header_clicked(self, logicalIndex):
        self.header_menu = HeaderMenu( self, list(set( self.model.datas(logicalIndex)[1:] )), logicalIndex )
        self.header_menu.filtered.connect(self.filtered_clicked)

        headerPos = self.view.mapToGlobal(self.header.pos())

        self.header_menu.exec(
            QtCore.QPoint(
                headerPos.x() + self.header.sectionPosition(self.header_menu.logicalIndex), 
                headerPos.y() + self.header.height()
            )
        )

    def filtered_clicked(self, text):
        self.proxy.setFilterRegExp( QtCore.QRegExp( text, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.RegExp ) )
        self.proxy.setFilterKeyColumn(self.header_menu.logicalIndex)

    def contextMenu(self, point):
        self.menu = QtWidgets.QMenu(self)
        self.menu.addAction('Insert', self.insertRow)
        self.menu.addAction('Delete', self.delItem)
        self.menu.exec( self.focusWidget().mapToGlobal(point) )
 
    def insertRow(self):
        indexes = self.view.selectedIndexes()
        if len(indexes) == 0:
            self.model.insertRow( self.model.rowCount() )
        items = []
        for index in indexes:
            index = self.proxy.mapToSource(index)
            if index.internalPointer() in items:
                continue
            self.model.insertRow( self.model.rowCount(index), index )
            items.append(index.internalPointer())

    def delItem(self):

        def is_select_parent(item, items):
            if item in items:
                return True
            if item == self.model.root:
                return False
            return is_select_parent(item.parent(), items)

        selected_indexes = [ self.proxy.mapToSource(index) for index in self.view.selectedIndexes() ]

        if len(selected_indexes) == 0:
            if not self.model.rowCount() == 0:
                self.model.removeRow( self.model.rowCount() - 1 )
            return

        selected_items = list(set([ index.internalPointer() for index in selected_indexes ]))

        delete_list = {'items':[], 'indexes':[]}
        for index in selected_indexes:
            item = index.internalPointer()
            if item in delete_list['items']:
                continue
            if is_select_parent(item.parent(), selected_items):
                continue
            delete_list['items'].append(item)
            delete_list['indexes'].append(index)

        for index in delete_list['indexes'][::-1]:
            self.model.removeRow(index.row(), index.parent())

    def load_json(self, filepath=None):
        
        if type(filepath) is bool:
            filepath = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', '', 'JSON File (*.json)')
            filepath = filepath[0]
            if not filepath:
                return

        def set_item(json_item, parent):
            self.model.insertRow(self.model.rowCount(parent), parent)
            parent_item = self.model.item(parent)
            insert_item = parent_item.child(-1)
            for key in json_item:
                if key == 'children':
                    continue
                insert_item.data(key, json_item[key])
            if 'children' in json_item:
                index = self.model.index(insert_item.row(), 0, parent)
                for child in json_item['children']:
                    set_item(child, index)

        with open(filepath) as f:
            self.json = json.load(f)

        columns = self.json['columns']
        if self.model.columnCount() > 0:
            self.model.removeColumns(0, self.model.columnCount())
        self.model.insertColumns(0, len(columns))

        if self.model.rowCount() > 0:
            self.model.removeRows(0, self.model.rowCount())

        for i, column in enumerate(columns):
            self.model.setHeaderData(i, QtCore.Qt.Horizontal, column)
        
        for item in self.json['items']:
            set_item( item, QtCore.QModelIndex() )
        
        self.filepath = filepath

    def save_json(self, filepath=None):

        def recursion(item):
            data = item.data()
            children = []
            for child in item.children():
                children.append( recursion(child) )
            if children:
                data['children'] = children
            return data
        
        if type(filepath) is bool:
            filepath = QtWidgets.QFileDialog.getSaveFileName(self, 'Open file', '', 'JSON File (*.json)')
            filepath = filepath[0]
            if not filepath:
                return
        
        self.json['columns'] = self.model.columns

        items = []
        for item in self.model.root.children():
            items.append( recursion(item) )

        self.json['items'] = items

        with open(filepath, 'w') as f:
            json.dump(self.json, f, indent=4)

    def save_as_json(self):
        self.save_json(self.filepath)

class HeaderMenu(QtWidgets.QMenu):

    filtered = QtCore.pyqtSignal(str)

    def __init__(self, parent, values, logicalIndex=-1):
        super(HeaderMenu, self).__init__(parent)
        
        self.logicalIndex = logicalIndex
        actionAll = QtWidgets.QAction("All", self)
        actionAll.triggered.connect(self.emitWithText)
        self.addAction(actionAll)
        self.addSeparator()

        for actionName in sorted(values):              
            action = QtWidgets.QAction(actionName, self)
            action.triggered.connect(self.emitWithText)
            self.addAction(action)
        
    def emitWithText(self):
        action = self.sender()
        text = action.text()
        if text == 'All':
            self.filtered.emit('')
        else:
            self.filtered.emit( action.text() )

class Model(QtCore.QAbstractItemModel):
    def __init__(self, parent):
        super(Model, self).__init__(parent)
        self.root = Item()
        self.columns = []

    def column(self, index):
        return self.columns[ index.column() ]

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        data = self.item(index).data( self.column(index) )
        if role == QtCore.Qt.EditRole:
            if data is None:
                return ''
            return data
        if role == QtCore.Qt.DisplayRole:
            if data is None:
                return 'None'
            return data
        return QtCore.QVariant()

    def datas(self, column, index=QtCore.QModelIndex(), role=QtCore.Qt.DisplayRole):
        datas = [ self.data(index, role) ]
        for child in self.item(index).children():
            child_index = self.index(child.row(), column, index)
            datas.extend( self.datas(column, child_index, role) )
        return datas

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled
        return QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.columns[section]
        
        if orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return section + 1

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if parent == QtCore.QModelIndex():
            return self.createIndex( row, column, self.root.child(row) )

        if parent.isValid():
            return self.createIndex( row, column, self.item(parent).child(row) )

        return QtCore.QModelIndex()

    def insertColumn(self, column, parent=QtCore.QModelIndex()):
        self.insertColumns(column, 1, parent)

    def insertColumns(self, column, count, parent=QtCore.QModelIndex()):
        self.beginInsertColumns(parent, column, column + count - 1)
        self.columns[column:column] = [ '' for i in range(count) ]
        self.endInsertColumns()

    def insertRow(self, row, parent=QtCore.QModelIndex()):
        self.insertRows(row, 1, parent)

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        self.beginInsertRows(parent, row, row + count - 1)
        self.item(parent).insert(row, count)
        self.endInsertRows()

    def item(self, index):
        if index == QtCore.QModelIndex() or index is None:
            return self.root
        if index.isValid():
            return index.internalPointer()
        return QtCore.QModelIndex()
        
    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        item = self.item(index)
        if item.parent() == self.root:
            return QtCore.QModelIndex()
        return self.createIndex(index.row(), 0, self.item(index).parent())

    def removeColumn(self, column, parent=QtCore.QModelIndex()):
        self.removeColumns(column, 1, parent)

    def removeColumns(self, column, count, parent=QtCore.QModelIndex()):
        self.beginRemoveColumns(parent, column, column + count - 1)
        del self.columns[column:column+count]
        self.endRemoveColumns()

    def removeRow(self, row, parent=QtCore.QModelIndex()):
        self.removeRows(row, 1, parent)

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        self.beginRemoveRows(parent, row, row + count - 1)
        self.item(parent).remove(row, count)
        self.endRemoveRows()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len( self.item(parent).children() )

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            self.item(index).data( self.columns[index.column()], value )
            return True
        return False

    def setHeaderData(self, section, orientation, value, role=QtCore.Qt.EditRole):
        if orientation==QtCore.Qt.Horizontal and role==QtCore.Qt.EditRole:
            self.columns[section] = value
        return True

class Delegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None, setModelDataEvent=None):
        super(Delegate, self).__init__(parent)
        self.setModelDataEvent = setModelDataEvent
 
    def createEditor(self, parent, option, index):
        return QtWidgets.QLineEdit(parent)
 
    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        editor.setText(str(value))
 
    def setModelData(self, editor, model, index):
        model.setData(index, editor.text())
        if not self.setModelDataEvent is None:
            self.setModelDataEvent()

class Item(object):
    def __init__(self, parent=None):
        self._data = {}
        self._parent = parent
        self._children = []

    def append(self):
        self._children.append( Item(self) )

    def child(self, row):
        return self._children[row]

    def children(self):
        return self._children

    def data(self, key=None, value=None):
        if key is None:
            return self._data
        if type(key) is dict:
            self._data = key
            return
        if value is None:
            return self._data.get(key)
        self._data[key] = value

    def insert(self, row, count=1):
        self._children[row:row] = [ Item(self) for i in range(count) ]

    def parent(self, item=None):
        if item is None:
            return self._parent
        self._parent = item

    def pop(self, row, count=1):
        d = self._children[row:row+count]
        del self._children[row:row+count]
        return d

    def remove(self, row, count=1):
        del self._children[row:row+count]

    def row(self):
        if not self._parent is None:
            if self in self._parent._children:
                return self._parent._children.index(self)
        return -1

def main():
    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super(MainWindow, self).__init__()
            self.wg = JsonTreeView(self)
            self.setCentralWidget(self.wg)

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()

    w.wg.load_json('settings.json')

    w.show()
    app.exec()

if __name__ == '__main__':
    main()