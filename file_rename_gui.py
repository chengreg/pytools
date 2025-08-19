#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Iterable

from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QFileDialog, QLabel, QCheckBox, QPlainTextEdit, QGroupBox, QRadioButton,
    QButtonGroup, QMessageBox
)

@dataclass
class RenameStats:
    scanned: int = 0
    renamed: int = 0
    skipped: int = 0
    errors: int = 0

class RenamerWorker(QObject):
    progress = Signal(str)
    finished = Signal(RenameStats)
    started = Signal()

    def __init__(self,
                 root_dir: str,
                 to_delete: str,
                 recursive: bool,
                 include_dirs: bool,
                 case_sensitive: bool,
                 include_extension: bool,
                 conflict_strategy: str):
        super().__init__()
        self.root_dir = root_dir
        self.to_delete = to_delete
        self.recursive = recursive
        self.include_dirs = include_dirs
        self.case_sensitive = case_sensitive
        self.include_extension = include_extension
        self.conflict_strategy = conflict_strategy
        self._abort = False

    @Slot()
    def run(self):
        self.started.emit()
        stats = RenameStats()

        if not self.to_delete:
            self.progress.emit("❗未提供要删除的字符串，任务结束。")
            self.finished.emit(stats)
            return

        try:
            if self.recursive:
                iterator: Iterable[Tuple[str, list, list]] = os.walk(self.root_dir)
            else:
                # 模拟非递归：只遍历一层
                def one_level(root):
                    dirs, files = [], []
                    with os.scandir(root) as it:
                        for e in it:
                            if e.is_dir():
                                dirs.append(e.name)
                            elif e.is_file():
                                files.append(e.name)
                    yield root, dirs, files
                iterator = one_level(self.root_dir)
        except Exception as e:
            self.progress.emit(f"❗遍历目录失败：{e}")
            self.finished.emit(stats)
            return

        # 准备匹配器
        if self.case_sensitive:
            flags = 0
        else:
            flags = re.IGNORECASE

        # 简单地对目标字符串做正则转义，按字面匹配
        pattern = re.compile(re.escape(self.to_delete), flags=flags)

        for root, dirs, files in iterator:
            if self._abort:
                self.progress.emit("⏹ 已中止。")
                break

            # 先处理文件夹名（可选）
            if self.include_dirs:
                for name in list(dirs):  # list() 防止迭代中修改影响
                    src_path = os.path.join(root, name)
                    new_name = self._rename_candidate(name, pattern, include_ext=True)  # 文件夹无扩展名概念
                    stats.scanned += 1
                    if new_name == name:
                        stats.skipped += 1
                        continue
                    dst_path = os.path.join(root, new_name)
                    ok = self._apply_rename(src_path, dst_path, stats)
                    if ok:
                        # 若文件夹改名成功，更新 dirs 列表，避免 os.walk 继续走旧路径（仅递归时有意义）
                        if self.recursive:
                            try:
                                idx = dirs.index(name)
                                dirs[idx] = new_name
                            except ValueError:
                                pass

            # 再处理文件
            for name in files:
                src_path = os.path.join(root, name)
                # 是否处理扩展名
                if self.include_extension:
                    new_name = self._rename_candidate(name, pattern, include_ext=True)
                else:
                    stem, dot, ext = name.partition(".")
                    if dot:  # 有扩展名
                        new_stem = self._rename_candidate(stem, pattern, include_ext=True)
                        new_name = f"{new_stem}.{ext}"
                    else:     # 无扩展名
                        new_name = self._rename_candidate(name, pattern, include_ext=True)

                stats.scanned += 1
                if new_name == name:
                    stats.skipped += 1
                    continue

                dst_path = os.path.join(root, new_name)
                self._apply_rename(src_path, dst_path, stats)

        self.finished.emit(stats)

    def abort(self):
        self._abort = True

    def _rename_candidate(self, name: str, pattern: re.Pattern, include_ext: bool) -> str:
        # 直接替换为“空字符串”以达到“删除”的效果
        new_name = pattern.sub("", name)
        # 清理可能出现的多余空格
        new_name = re.sub(r"\s{2,}", " ", new_name).strip()
        # 防止空名
        if not new_name:
            new_name = "_"
        return new_name

    def _apply_rename(self, src_path: str, dst_path: str, stats: RenameStats) -> bool:
        src = Path(src_path)
        dst = Path(dst_path)

        # 冲突处理
        if dst.exists():
            if self.conflict_strategy == "skip":
                self.progress.emit(f"⏭ 冲突跳过: {src.name} -> {dst.name}")
                stats.skipped += 1
                return False
            else:
                # 自动追加序号
                base = dst.stem
                suffix = dst.suffix
                parent = dst.parent
                i = 1
                while True:
                    cand = parent / f"{base}_{i}{suffix}"
                    if not cand.exists():
                        dst = cand
                        break
                    i += 1

        try:
            os.rename(src, dst)
            stats.renamed += 1
            self.progress.emit(f"✅ {src.name}  →  {dst.name}")
            return True
        except Exception as e:
            stats.errors += 1
            self.progress.emit(f"❌ 重命名失败: {src.name} -> {dst.name} | {e}")
            return False


class DropLineEdit(QLineEdit):
    """支持拖拽目录/文件路径的输入框"""
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.setText(path)
        else:
            super().dropEvent(event)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量文件改名（删除指定字符串） - PySide6")
        self.setMinimumWidth(720)

        # 路径选择
        self.edt_path = DropLineEdit()
        btn_browse = QPushButton("选择路径…")
        btn_browse.clicked.connect(self.on_browse)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("目标路径："))
        path_row.addWidget(self.edt_path, stretch=1)
        path_row.addWidget(btn_browse)

        # 删除字符串
        self.edt_delete = QLineEdit()
        self.edt_delete.setPlaceholderText("输入要从文件/文件夹名中删除的字符串…")

        delete_row = QHBoxLayout()
        delete_row.addWidget(QLabel("删除字符串："))
        delete_row.addWidget(self.edt_delete, stretch=1)

        # 选项
        self.chk_recursive = QCheckBox("递归子目录")
        self.chk_recursive.setChecked(True)
        self.chk_dirs = QCheckBox("包含文件夹改名")
        self.chk_dirs.setChecked(False)
        self.chk_case = QCheckBox("区分大小写")
        self.chk_case.setChecked(False)
        self.chk_ext = QCheckBox("处理扩展名")
        self.chk_ext.setChecked(False)

        opt_row = QHBoxLayout()
        opt_row.addWidget(self.chk_recursive)
        opt_row.addWidget(self.chk_dirs)
        opt_row.addWidget(self.chk_case)
        opt_row.addWidget(self.chk_ext)
        opt_row.addStretch(1)

        # 冲突策略
        grp_conflict = QGroupBox("命名冲突时")
        rdo_skip = QRadioButton("跳过")
        rdo_auto = QRadioButton("自动追加序号 (_1, _2, …)")
        rdo_auto.setChecked(True)
        self.conflict_group = QButtonGroup()
        self.conflict_group.addButton(rdo_skip, 0)
        self.conflict_group.addButton(rdo_auto, 1)

        lay_conf = QVBoxLayout()
        lay_conf.addWidget(rdo_auto)
        lay_conf.addWidget(rdo_skip)
        grp_conflict.setLayout(lay_conf)

        # 按钮
        self.btn_run = QPushButton("执行")
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_stop)

        # 日志输出
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("运行日志将显示在这里…")

        # 布局
        root = QVBoxLayout(self)
        root.addLayout(path_row)
        root.addLayout(delete_row)
        root.addLayout(opt_row)
        root.addWidget(grp_conflict)
        root.addLayout(btn_row)
        root.addWidget(QLabel("日志："))
        root.addWidget(self.log, stretch=1)

        # 线程相关
        self.thread: QThread | None = None
        self.worker: RenamerWorker | None = None

        # 信号
        self.btn_run.clicked.connect(self.on_run)
        self.btn_stop.clicked.connect(self.on_stop)

    @Slot()
    def on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if path:
            self.edt_path.setText(path)

    @Slot()
    def on_run(self):
        root_dir = self.edt_path.text().strip()
        to_delete = self.edt_delete.text()

        if not root_dir or not os.path.isdir(root_dir):
            QMessageBox.warning(self, "提示", "请选择一个有效的目录。")
            return
        if to_delete == "":
            ret = QMessageBox.question(
                self, "确认",
                "要删除的字符串为空，这将不会改变任何名称。\n仍要继续吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if ret != QMessageBox.Yes:
                return

        self.log.clear()
        self.append_log(f"📂 目标路径：{root_dir}")
        self.append_log(f"🧹 删除字符串：{repr(to_delete)}")
        self.append_log(f"🔧 选项：递归={self.chk_recursive.isChecked()}，"
                        f"包含文件夹={self.chk_dirs.isChecked()}，"
                        f"区分大小写={self.chk_case.isChecked()}，"
                        f"处理扩展名={self.chk_ext.isChecked()}")
        strategy = "auto" if self.conflict_group.checkedId() == 1 else "skip"
        self.append_log(f"⚖️ 冲突策略：{'自动追加序号' if strategy=='auto' else '跳过'}")
        self.append_log("-" * 60)

        # 启动线程
        self.thread = QThread(self)
        self.worker = RenamerWorker(
            root_dir=root_dir,
            to_delete=to_delete,
            recursive=self.chk_recursive.isChecked(),
            include_dirs=self.chk_dirs.isChecked(),
            case_sensitive=self.chk_case.isChecked(),
            include_extension=self.chk_ext.isChecked(),
            conflict_strategy=strategy
        )
        self.worker.moveToThread(self.thread)

        # 连接信号
        self.thread.started.connect(self.worker.run)
        self.worker.started.connect(self.on_started)
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    @Slot()
    def on_stop(self):
        if self.worker:
            self.worker.abort()
            self.append_log("⌛ 正在请求停止…")

    @Slot()
    def on_started(self):
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)

    @Slot(RenameStats)
    def on_finished(self, stats: RenameStats):
        self.append_log("-" * 60)
        self.append_log(f"📈 扫描项：{stats.scanned}")
        self.append_log(f"✅ 已改名：{stats.renamed}")
        self.append_log(f"⏭ 已跳过：{stats.skipped}")
        self.append_log(f"❌ 失败数：{stats.errors}")
        self.append_log("🎉 完成")
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)

    @Slot(str)
    def append_log(self, text: str):
        self.log.appendPlainText(text)
        self.log.ensureCursorVisible()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
