import os
import re
from pathlib import Path

import hou

try:
    from PySide2 import QtWidgets, QtCore  # type: ignore
except ImportError:
    from PySide6 import QtWidgets, QtCore

from tracepath import core_utils


class OpenFileDialog(QtWidgets.QDialog):
    """
    Dialog for browsing and opening scene files from the current task context.

    Displays a tree of available scene files and loads the selected file into Houdini.
    """

    def __init__(self, dcc, parent=None):
        """
        Initialize the dialog UI, populate the file tree.

        Args:
            dcc: DCC identifier, used to resolve the context path.
            parent: Parent widget.
        """
        super(OpenFileDialog, self).__init__(parent=parent)
        self.setObjectName('OpenDialog')
        self.resize(800, 500)
        self.setWindowTitle("Open File - TRACE")

        self.central_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.central_layout)

        self.root_label = QtWidgets.QLabel("Context:")
        self.user_data = os.path.join(core_utils.get_task_context(), f"{dcc}/scenes")
        self.central_layout.addWidget(self.root_label)

        self.tree_widget = QtWidgets.QTreeWidget(self)
        self.tree_widget.setHeaderLabels([self.user_data])
        self.central_layout.addWidget(self.tree_widget)

        self.open_button = QtWidgets.QPushButton("Open")
        self.central_layout.addWidget(self.open_button)

        # Run on init
        self.populate_tree()

        # Signal connections
        self.open_button.clicked.connect(self.on_open)
        self.tree_widget.itemDoubleClicked.connect(self.on_open)

        # Style
        style_folder = os.environ.get("STYLE_TRACEPATH")
        style = ""
        if style_folder:
            style_file = os.path.join(style_folder, "style.qss")
            if os.path.isfile(style_file):
                with open(style_file, 'r') as f:
                    style = f.read()
        self.setStyleSheet(style)

    def populate_tree(self) -> None:
        """Populate the tree widget with scene folders and files from the context directory."""
        root = self.tree_widget.invisibleRootItem()
        hip_folders = [i for i in sorted(os.listdir(self.user_data)) if not i.startswith(".")]

        for hip_folder in hip_folders:
            hip_folder_item = QtWidgets.QTreeWidgetItem(root)
            hip_folder_item.setText(0, hip_folder)

            folder_path = os.path.join(self.user_data, hip_folder)
            hip_files = [i for i in sorted(os.listdir(folder_path)) if not i.startswith(".")]
            for hip_file in hip_files:
                hip_file_path = os.path.join(folder_path, hip_file)
                display_name = hip_file.split("/")[-1]
                if Path(hip_file_path).is_file():
                    hip_file_item = QtWidgets.QTreeWidgetItem(hip_folder_item)
                    hip_file_item.setText(0, display_name)

                    if re.search(r"\.hip\w*$", hip_file, re.IGNORECASE):
                        hip_file_item.setData(0, QtCore.Qt.UserRole, hip_file_path)
                        hip_file_item.setText(0, hip_file)

    def on_open(self) -> None:
        """Load the selected scene file into Houdini"""
        item = self.tree_widget.selectedItems()[0]
        scene_path = item.data(0, QtCore.Qt.UserRole)
        hou.hipFile.load(scene_path)
        self.close()


dialog = None


def show_houdini() -> OpenFileDialog:
    """
    Create and show the Open File dialog in Houdini.

    Returns:
        OpenFileDialog: The created dialog instance.
    """
    import hou
    global dialog
    dialog = OpenFileDialog("houdini", parent=hou.qt.mainWindow())
    dialog.show()
    return dialog
