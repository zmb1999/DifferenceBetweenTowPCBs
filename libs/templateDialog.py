try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from libs.lib import newIcon, labelValidator

BB = QDialogButtonBox


class TemplateDialog(QDialog):

    def __init__(self, text="Enter object label", parent=None, listItem=None):
        super(TemplateDialog, self).__init__(parent)
        self.listItem = listItem
        self.removeItems = []
        self.edit = QLineEdit()
        self.edit.setText(text)
        self.edit.setValidator(labelValidator())
        self.edit.editingFinished.connect(self.postProcess)
        self.edit.setEnabled(False)
        self.edit.setFocusPolicy(Qt.NoFocus)

        model = QStringListModel()
        model.setStringList(listItem)
        completer = QCompleter()
        completer.setModel(model)
        self.edit.setCompleter(completer)

        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        buttonDelete = QPushButton("&Delete")
        self.buttonBox = bb = BB(BB.Ok | BB.Cancel, Qt.Horizontal, self)
        bb.button(BB.Ok).setIcon(newIcon('done'))
        bb.button(BB.Cancel).setIcon(newIcon('undo'))
        bb.addButton(buttonDelete, QDialogButtonBox.ActionRole)
        # bb.button(BB.Apply)
        buttonDelete.clicked.connect(self.delete)
        bb.accepted.connect(self.validate)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

        if listItem is not None and len(listItem) > 0:
            self.listWidget = QListWidget(self)
            for item in listItem:
                self.listWidget.addItem(item)
            self.listWidget.itemClicked.connect(self.listItemClick)
            self.listWidget.itemDoubleClicked.connect(self.listItemDoubleClick)
            layout.addWidget(self.listWidget)

        self.setLayout(layout)

    def currentItem(self):
        items = self.listWidget.selectedItems()
        if items:
            return items[0]
        return None

    def delete(self):
        item = self.currentItem()
        if item:
            text = self.edit.text()
            self.listItem.remove(text)
            self.removeItems.append(text)
            self.listWidget.takeItem(self.listWidget.row(item))
            if len(self.listItem) > 0:
                self.edit.setText(self.listItem[0])
            else:
                self.edit.setText('')

    def validate(self):
        try:
            if self.edit.text().trimmed() or self.removeItems:
                self.accept()
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            if self.edit.text().strip() or self.removeItems:
                self.accept()

    def postProcess(self):
        try:
            self.edit.setText(self.edit.text().trimmed())
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            self.edit.setText(self.edit.text())

    def popUp(self, text='', move=True):
        if self.listItem:
            self.edit.setText(self.listItem[0])
        else:
            self.edit.setText(text)
        if move:
            self.move(QCursor.pos())
        return [self.edit.text(),self.removeItems] if self.exec_() else [None, None]

    def listItemClick(self, tQListWidgetItem):
        try:
            text = tQListWidgetItem.text().trimmed()
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            text = tQListWidgetItem.text().strip()
        self.edit.setText(text)
        
    def listItemDoubleClick(self, tQListWidgetItem):
        self.listItemClick(tQListWidgetItem)
        self.validate()
