import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
from functools import partial, reduce
from pathlib import Path

from project_index import _usd

importlib.reload(_usd)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets


class TraceResetUI(QtWidgets.QMainWindow):
    """UI widget for editing published project components and files"""

    def __init__(self, parent=None):
        """
        Initialize the main window UI and load project data.

        Args:
            parent: Parent widget.
        """
        super(TraceResetUI, self).__init__(parent=parent)
        self.resize(1500, 900)
        self.setWindowTitle('Trace Reset v0.1.6')

        style_folder = os.environ.get("STYLE_PROJECT_INDEX")
        framework = os.getenv("PR_TRACEPATH_FRAMEWORK")
        if not framework:
            raise EnvironmentError("PR_TRACEPATH_FRAMEWORK is not set")

        self.project_index_path = os.path.join(framework, "config/trace_project_index.json")
        with open(self.project_index_path, "r") as read_file:
            self.pr_index_read = json.load(read_file)

        self.pr_projects_path = os.environ.get("PR_PROJECTS_PATH")
        if not self.pr_projects_path:
            raise EnvironmentError("PR_PROJECTS_PATH is not set")

        self.central_widget = QtWidgets.QWidget(self)
        self.central_layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.setContentsMargins(10, 10, 10, 10)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizes([3, 1])
        self.central_layout.addWidget(self.splitter)

        # DISPLAY WIDGETS ---------------------------------
        self.display_widget = QtWidgets.QWidget()
        self.display_widget.setMinimumHeight(200)
        self.splitter.addWidget(self.display_widget)
        self.display_layout = QtWidgets.QVBoxLayout()
        self.display_widget.setLayout(self.display_layout)

        # Project elements layout
        self.project_elements_layout = QtWidgets.QHBoxLayout()
        self.display_layout.addLayout(self.project_elements_layout)

        # Project List
        self.projects_layout = QtWidgets.QVBoxLayout()
        self.project_elements_layout.addLayout(self.projects_layout)

        self.projects_label = QtWidgets.QLabel("Projects")
        self.projects_layout.addWidget(self.projects_label)

        self.projects = QtWidgets.QListWidget(self)
        self.projects_layout.addWidget(self.projects)

        self.projects.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.projects.setMinimumHeight(300)

        # Group List
        self.groups_layout = QtWidgets.QVBoxLayout()
        self.project_elements_layout.addLayout(self.groups_layout)

        self.groups_label = QtWidgets.QLabel("Groups")
        self.groups_layout.addWidget(self.groups_label)

        self.groups = QtWidgets.QListWidget(self)
        self.groups_layout.addWidget(self.groups)

        # Item List
        self.items_layout = QtWidgets.QVBoxLayout()
        self.project_elements_layout.addLayout(self.items_layout)

        self.items_label = QtWidgets.QLabel("Items")
        self.items_layout.addWidget(self.items_label)

        self.items = QtWidgets.QListWidget(self)
        self.items_layout.addWidget(self.items)

        # Task List
        self.tasks_layout = QtWidgets.QVBoxLayout()
        self.project_elements_layout.addLayout(self.tasks_layout)

        self.tasks_label = QtWidgets.QLabel("Tasks")
        self.tasks_layout.addWidget(self.tasks_label)

        self.tasks = QtWidgets.QListWidget(self)
        self.tasks_layout.addWidget(self.tasks)

        # Main USD list
        self.usd_list_layout = QtWidgets.QVBoxLayout()
        self.project_elements_layout.addLayout(self.usd_list_layout)

        self.main_usd_label = QtWidgets.QLabel("Main Versions")
        self.usd_list_layout.addWidget(self.main_usd_label)
        self.main_usd = QtWidgets.QListWidget(self)
        self.usd_list_layout.addWidget(self.main_usd)

        # USD Layer Composition data info message:
        self.data_info = QtWidgets.QLabel("Warning: Data in USD Layer Composition is for informational purposes only."
                                          " You cannot edit the main USD file's component layers.")
        self.data_info.setObjectName("data_info")
        self.display_layout.addWidget(self.data_info)

        self.usd_data = QtWidgets.QTreeWidget()
        self.usd_data.setHeaderLabel("USD Layer Composition")
        self.display_layout.addWidget(self.usd_data)

        # DELETE WIDGETS ---------------------------------
        self.delete_widget = QtWidgets.QWidget()
        self.delete_widget.setMinimumHeight(150)
        self.splitter.addWidget(self.delete_widget)

        self.delete_layout = QtWidgets.QVBoxLayout()
        self.delete_widget.setLayout(self.delete_layout)

        # Marked to Delete List
        self.marked_to_del_label = QtWidgets.QLabel("Marked to Delete")
        self.delete_layout.addWidget(self.marked_to_del_label)

        self.marked_to_delete = QtWidgets.QListWidget(self)
        self.delete_layout.addWidget(self.marked_to_delete)

        # Delete Button
        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_layout.addWidget(self.delete_btn)

        # Resize Splitter
        self.splitter.setSizes([int(self.splitter.height() * 0.8), int(self.splitter.height() * 0.2)])

        # Load and set style
        style = ""
        if style_folder:
            style_file = os.path.join(style_folder, "style.qss")
            if os.path.isfile(style_file):
                with open(style_file, 'r') as f:
                    style = f.read()
        self.setStyleSheet(style)

        if self.parent():
            self.parent().setStyleSheet(self.parent().styleSheet())

        # FUNCTIONS EXECUTED ON INIT ---------------------------------
        self.populate_project_list()

        # SIGNALS ---------------------------------
        self.projects.itemSelectionChanged.connect(self.on_project_changed)
        self.groups.itemSelectionChanged.connect(self.on_group_changed)
        self.items.itemSelectionChanged.connect(self.on_pr_item_changed)
        self.main_usd.itemSelectionChanged.connect(self.on_main_usd_version_changed)

        for widget in (self.projects, self.groups, self.items, self.tasks):
            widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(partial(self.open_mark_to_del_menu, widget))

        self.main_usd.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.main_usd.customContextMenuRequested.connect(self.open_inspect_usd_file_menu)

        self.marked_to_delete.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.marked_to_delete.customContextMenuRequested.connect(self.open_restore_menu)

        self.delete_btn.clicked.connect(self.on_del_exec)

        # PROJECT COMPONENTS BROWSING ---------------------------------

    def get_selection(self, widget: QtWidgets.QListWidget) -> str | None:
        """
        Return the selected item text or None.

        Args:
            widget: List widget to get the selection from.
        """
        selected = widget.selectedItems()
        return selected[0].text() if selected else None

    def selected_project(self) -> str | None:
        """Return the selected project name."""
        return self.get_selection(self.projects)

    def selected_group(self) -> str | None:
        """Return the selected group name."""
        return self.get_selection(self.groups)

    def selected_item(self) -> str | None:
        """Return the selected item name."""
        return self.get_selection(self.items)

    def selected_task(self) -> str | None:
        """Return the selected task name."""
        return self.get_selection(self.tasks)

    def create_list_item(self, item_name: str, parent_widget: QtWidgets.QListWidget,
                         metadata: dict | None = None) -> None:
        """
        Create a list item, attach metadata, and add it to the parent widget.

        Args:
            item_name: Item name.
            parent_widget: Parent list widget.
            metadata: Optional metadata.
        """
        item = QtWidgets.QListWidgetItem(item_name)
        if metadata:
            metadata["item_name"] = item_name
            metadata["parent"] = parent_widget
            item.setData(QtCore.Qt.UserRole, metadata)
        parent_widget.addItem(item)

    def populate_project_list(self) -> None:
        """Populate the project list from the index data."""
        for i in self.pr_index_read.keys():
            meta = {"preview_path": i, "project": i, "type": "project"}
            self.create_list_item(i, self.projects, meta)

    def get_nested_data(self, data: dict, data_keys: list[str]) -> dict or None:
        """
        Return nested data from a dictionary using a list of keys.

        Args:
            data: Source data.
            data_keys: Keys to traverse.
        """
        if not isinstance(data, dict):
            logging.warning("Invalid data provided; data must be a dictionary.")
            return None
        result = reduce(lambda df, data_key: df.get(data_key) if isinstance(df, dict) else None, data_keys,
                        data)
        return result

    def on_project_changed(self) -> None:
        """Update groups based on the selected project."""
        self.main_usd.clear()
        self.tasks.clear()
        self.items.clear()
        self.groups.clear()
        project = self.selected_project()
        if not project:
            return
        data_keys = [project, "groups"]

        groups = self.get_nested_data(self.pr_index_read, data_keys)
        if not groups:
            logging.warning(f"No 'groups' data found in the index for project: '{project}'. Skipping population.")
            return
        for group, meta in groups.items():
            meta = {"preview_path": f"{project}/{group}", "project": project, "type": "group"}
            self.create_list_item(group, self.groups, meta)

    def on_group_changed(self) -> None:
        """Update items based on the selected group."""
        self.main_usd.clear()
        self.tasks.clear()
        self.items.clear()
        project = self.selected_project()
        group = self.selected_group()
        if not group or not project:
            return

        data_keys = [project, "groups", group, "items"]

        pr_items = self.get_nested_data(self.pr_index_read, data_keys)
        if not pr_items:
            logging.warning(
                f"No 'items' data found in the index for project: '{project}', group: '{group}'. Skipping population.")
            return
        for pr_item, meta in pr_items.items():
            meta = {"preview_path": f"{project}/{group}/{pr_item}", "project": project, "type": "item"}
            self.create_list_item(pr_item, self.items, meta)

    def read_published_data(self, show_data: str) -> dict | None:
        """
        Load published project data from disk.

        Args:
            show_data: Path to the global show metadata JSON file.
        """
        try:
            with open(show_data, "r") as data_read:
                published_data = json.load(data_read)
            return published_data
        except FileNotFoundError:
            logging.error(f"Show data file \n{show_data} is not found")
            return None

    def on_pr_item_changed(self) -> None:
        """Update tasks and main USD versions for the selected item."""
        self.main_usd.clear()
        self.tasks.clear()
        project = self.selected_project()
        group = self.selected_group()
        pr_item = self.selected_item()
        if not pr_item or not group or not project:
            return

        data_keys = [project, "groups", group, "items", pr_item, "tasks"]
        pr_tasks = self.get_nested_data(self.pr_index_read, data_keys)
        if pr_tasks:
            for pr_task, meta in pr_tasks.items():
                meta = {"preview_path": f"{project}/{group}/{pr_item}/{pr_task}",
                        "project": project, "type": "task"}
                self.create_list_item(pr_task, self.tasks, meta)
        else:
            logging.warning(
                f"No 'tasks' data found in the index for project: '{project}', group: '{group}', "
                f"item: '{pr_item}'. Skipping population.")

        show_data = os.path.join(self.pr_projects_path, project, "show_data/published_data.json")

        published_data = self.read_published_data(show_data)

        if not published_data:
            logging.warning(f"Failed to read published data file for project: '{project}'. Skipping version load.")
            return

        data_key = f"{group}_{pr_item}"
        if not data_key in published_data.keys():
            logging.warning(f"No published versions found for key '{group}_{pr_item}' in project data.")
            return

        for version in published_data[data_key].keys():
            ver_preview_name = version.split("/")[-1]

            meta = {"preview_path": version,
                    "project": project, "type": "main_usd"}
            self.create_list_item(ver_preview_name, self.main_usd, meta)

    def on_main_usd_version_changed(self) -> None:
        """Display layer composition for the selected USD file."""
        self.usd_data.clear()
        selected = self.main_usd.selectedItems()
        if not selected:
            return
        selected_main = selected[0]
        if not selected_main:
            return
        usd_file_path = selected_main.data(QtCore.Qt.UserRole)["preview_path"]
        if not os.path.isfile(usd_file_path):
            logging.error(f"Published USD file '{usd_file_path}' was not found. Skipping loading process.")
            return
        self.display_usd_layer_composition(usd_file_path)

    def display_usd_layer_composition(self, usd_file_path: str) -> None:
        """
        Populate the layer composition tree for a USD file.

        Args:
            usd_file_path: USD scene file to create a layer composition breakdown.
        """
        root_usd_layer = _usd.find_usd_layer(usd_file_path)
        comp = _usd.walk_layer_stack(root_usd_layer)
        root = self.usd_data.invisibleRootItem()
        visited = set()
        self.populate_tree_recursive(comp, usd_file_path, root, visited)
        self.usd_data.expandAll()

    def populate_tree_recursive(self, tree_dict: dict[str, list[str]], node_id: str,
                                parent_item: QtWidgets.QTreeWidgetItem, visited: set[str]) -> None:
        """
        Render a node and its children recursively into a tree widget.

        Args:
            tree_dict: dictionary (parent -> children)
            node_id: current usd layer identifier
            parent_item: Parent UI item.
            visited: visited nodes
        """
        if node_id in visited:
            return
        visited.add(node_id)

        item = self._tree_item(node_id, parent_item)

        for child in tree_dict.get(node_id, []):
            self.populate_tree_recursive(tree_dict, child, item, visited)

    def _tree_item(self, name: str, parent: QtWidgets.QTreeWidgetItem) -> QtWidgets.QTreeWidgetItem:
        """
        Create a tree item and attach it to the parent.

        Args:
            name: Tree item name
            parent: Parent tree widget.
        """
        item = QtWidgets.QTreeWidgetItem(parent)
        item.setText(0, name)
        return item

    # PROJECT FOLDERS AND DATA MODIFICATION ---------------------------------
    def open_context_menu(self, widget: QtWidgets.QListWidget, position: QtCore.QPoint, functions: dict) -> None:
        """Open a context menu with the given actions.

        Args:
            widget: The widget from which the context menu is created.
            position: The position of the mouse clicks within the widget.
            functions: Dictionary where keys are action labels (menu text) and values are functions to execute.
        """
        item = widget.itemAt(position)
        menu = QtWidgets.QMenu(self)
        if item:
            for action_text, func_to_execute in functions.items():
                mark_to_delete = menu.addAction(action_text)
                mark_to_delete.triggered.connect(partial(func_to_execute, item))

        menu.exec(widget.viewport().mapToGlobal(position))

    def open_mark_to_del_menu(self, widget: QtWidgets.QListWidget, position: QtCore.QPoint) -> None:
        """
        Open menu to mark items for deletion.

        Args:
            widget: QListWidget from which to create a context menu.
            position: Menu position.
        """
        functions = {"Mark to delete": self.add_to_delete_list}
        self.open_context_menu(widget, position, functions)

    def add_to_delete_list(self, orig_item: QtWidgets.QListWidgetItem) -> None:
        """
        Add an item to the deletion list and hide it in the UI.

        Args:
            orig_item: List widget item to stage for deletion.
        """
        metadata = orig_item.data(QtCore.Qt.UserRole)
        if not metadata or "preview_path" not in metadata or "parent" not in metadata:
            logging.warning("No/invalid metadata; cannot stage for deletion.")
            return
        orig_item.setHidden(True)
        preview_path = metadata["preview_path"]
        parent_widget = metadata["parent"]

        item = QtWidgets.QListWidgetItem(preview_path)
        item.setData(QtCore.Qt.UserRole + 1, metadata)
        self.marked_to_delete.addItem(item)
        parent_widget.clearSelection()

    def open_restore_menu(self, position: QtCore.QPoint) -> None:
        """
        Open menu to restore items from the deletion list.

        Args:
            position: Context menu position.
        """
        functions = {"Restore item": self.restore_item_from_del_list}
        self.open_context_menu(self.marked_to_delete, position, functions)

    def _find_item_by_name(self, item_name: str,
                           parent_widget: QtWidgets.QListWidget) -> QtWidgets.QListWidgetItem | None:
        """
        Return the QListWidgetItem matching the given text, or None if not found.

        Args:
            item_name: List widget item name.
            parent_widget: Parent list widget.
        """
        for i in range(parent_widget.count()):
            item = parent_widget.item(i)
            if item and item.text() == item_name:
                return item
        return None

    def restore_item_from_del_list(self, item: QtWidgets.QListWidgetItem) -> None:
        """
        Removes an item from the deletion list and restores its visibility
        in the original project context QListWidget.

        Args:
            item: List widget item to restore.
        """
        self.marked_to_delete.takeItem(self.marked_to_delete.row(item))
        item_name = item.data(QtCore.Qt.UserRole + 1)["item_name"]
        parent_widget = item.data(QtCore.Qt.UserRole + 1)["parent"]
        found_item = self._find_item_by_name(item_name, parent_widget)
        if not found_item:
            logging.warning(f"Could not find '{item_name}' in parent to restore")
            return
        if found_item.isHidden():
            found_item.setHidden(False)
            parent_widget.clearSelection()
            parent_widget.setCurrentItem(found_item)

    def _restore_selection(self, prev_selection: str, parent_widget: QtWidgets.QListWidget) -> None:
        """
        Restore the previous selection in the given widget.

        Args:
            prev_selection: List widget item to restore.
            parent_widget: Parent list widget.
        """
        found_item = self._find_item_by_name(prev_selection, parent_widget)
        if found_item:
            parent_widget.setCurrentItem(found_item)
        else:
            parent_widget.setCurrentRow(0)

    def open_inspect_usd_file_menu(self, position: QtCore.QPoint) -> None:
        """
        Open menu for USD inspection actions.

        Args:
            position: Context menu position.
        """
        functions = {"Open in USD View": self.open_in_usd_view, "Mark to delete": self.add_to_delete_list}
        self.open_context_menu(self.main_usd, position, functions)

    def open_in_usd_view(self, item: QtWidgets.QListWidgetItem) -> None:
        """
        Open the selected USD file in usdview.

        Args:
            item: List widget item containing the USD file to open in usdview.
        """
        usd_file_path = item.data(QtCore.Qt.UserRole)["preview_path"]
        cmd = ["usdview", usd_file_path]
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Launch failed", f"Failed to open usdview:\n{e}")

    def clean_up_ui(self) -> None:
        """Reset UI state after deletion and restore selections."""
        if self.marked_to_delete.count() == 0:
            QtWidgets.QMessageBox.information(
                self,
                "Information",
                f"No staged items found — skipping deletion."
            )
            return
        self.marked_to_delete.clear()

        _cur_pr = self.selected_project()
        _cur_gr = self.selected_group()
        _cur_itm = self.selected_item()  # Use standard Python casing

        self.main_usd.clear()
        self.tasks.clear()
        self.items.clear()
        self.groups.clear()

        self.projects.clear()

        self.populate_project_list()

        self._restore_selection(_cur_pr, self.projects)
        self._restore_selection(_cur_gr, self.groups)
        self._restore_selection(_cur_itm, self.items)

    def on_del_exec(self) -> None:
        """Execute deletion of staged items and update data."""
        items_to_process = [self.marked_to_delete.item(i) for i in range(self.marked_to_delete.count())]
        if not items_to_process:
            logging.info("No staged items found — skipping deletion.")
            return
        if QtWidgets.QMessageBox.question(
                self, "Confirm deletion", "Permanently delete staged items?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) != QtWidgets.QMessageBox.Yes:
            return
        removed, failed = [], []
        for item in items_to_process:
            marked_item_meta = item.data(QtCore.Qt.UserRole + 1)

            path_to_remove = Path(self.pr_projects_path) / item.text()
            try:
                if marked_item_meta["type"] == "main_usd":
                    show_data = os.path.join(self.pr_projects_path, marked_item_meta["project"],
                                             "show_data/published_data.json")
                    published_data = self.read_published_data(show_data) or {}
                    self.remove_meta_key_recursive(published_data, item.text())
                    with open(show_data, "w") as write_file:
                        json.dump(published_data, write_file, indent=4)

                self.remove_filesystem_item(path_to_remove)

                self.remove_meta_key_recursive(self.pr_index_read, marked_item_meta["item_name"])
                removed.append(str(path_to_remove))
            except Exception as e:
                failed.append(str(path_to_remove))
                logging.error(f"Failed to delete {path_to_remove} or update index: {e}")
                continue  # Move to the next item
        with open(self.project_index_path, "w") as write_file:
            json.dump(self.pr_index_read, write_file, indent=4)

        self.clean_up_ui()

        msg = []
        if removed:
            msg.append(f"Removed:\n- " + "\n- ".join(removed))
            logging.info(f"Items to remove: {msg}")
        if failed:
            msg.append(f"Failed:\n- " + "\n- ".join(failed))
        message = f"\n\n".join(msg) if msg else "No elements were modified."
        QtWidgets.QMessageBox.information(
            self,
            "Deletion results",
            message
        )
        logging.info(f"All message: {msg}")

    def remove_filesystem_item(self, path_to_remove: Path) -> None:
        """
        Remove a file or directory from disk.

        Args:
            path_to_remove: Filesystem path of the file or directory to remove.
        """
        if not path_to_remove.exists():
            logging.error(f"File not found: {path_to_remove}")
            raise FileNotFoundError(f"File not found: {path_to_remove}")
        try:
            if path_to_remove.is_file():
                parent = path_to_remove.parent
                path_to_remove.unlink()
                if not any(parent.iterdir()):
                    parent.rmdir()
                logging.info(f"Successfully removed file: {path_to_remove}")
            elif path_to_remove.is_dir():
                shutil.rmtree(path_to_remove)
                logging.info(f"Successfully removed folder: {path_to_remove}")
            else:
                logging.info(f"Skipped removal as it is not folder or file\n: {path_to_remove}")

        except PermissionError as e:
            logging.error(f"Permission denied while removing {path_to_remove}\n{e}")

    def remove_meta_key_recursive(self, meta: dict, key_to_delete: str) -> None:
        """
        Remove a key recursively from a nested dictionary.

        Args:
            meta: Metadata dictionary.
            key_to_delete: Key to remove.
        """
        if isinstance(meta, dict):
            # Attempt to delete the key, returns None if the key is not found in the first step of the iteration
            meta.pop(key_to_delete, None)
            # Iterate over the remaining items to continue the recursion.
            # Iterates over a copy of the keys (list(meta.items()))
            for key, value in list(meta.items()):
                # Recurse into the value if it is another dictionary
                if isinstance(value, dict):
                    self.remove_meta_key_recursive(value, key_to_delete)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = TraceResetUI()
    w.show()
    sys.exit(app.exec())
