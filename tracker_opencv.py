import sys
import cv2
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                           QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
                           QMenuBar, QMenu, QAction, QStatusBar, QFrame, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QPoint, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QCursor

TRACKER_TYPES = {
    'CSRT': cv2.legacy.TrackerCSRT_create if hasattr(cv2, 'legacy') else cv2.TrackerCSRT_create,
    'KCF': cv2.legacy.TrackerKCF_create if hasattr(cv2, 'legacy') else cv2.TrackerKCF_create,
    'Boosting': cv2.legacy.TrackerBoosting_create if hasattr(cv2, 'legacy') else cv2.TrackerBoosting_create,
    'MIL': cv2.legacy.TrackerMIL_create if hasattr(cv2, 'legacy') else cv2.TrackerMIL_create,
}

TRACKER_COLORS = {
    'CSRT': (0, 255, 0),      # Green
    'KCF': (255, 0, 0),      # Blue
    'Boosting': (0, 255, 255), # Yellow
    'MIL': (255, 0, 255),    # Magenta
}

class VideoDisplay(QLabel):
    def __init__(self, tracker_app):
        super().__init__()
        self.tracker_app = tracker_app
        self.setMinimumSize(800, 600)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel { background-color: #181818; border: 2px solid #444; }")
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.bbox = None
        self.temp_bbox = None
        self.drawing_enabled = False  
        self.display_scale = 1.0
        self.display_offset_x = 0
        self.display_offset_y = 0
        self.frame_shape = None  
        self.mouse_pos = None

    def set_frame(self, frame):
        self.frame_shape = frame.shape[:2]
        self.update()

    def map_to_image(self, x, y):
        img_x = int((x - self.display_offset_x) / self.display_scale)
        img_y = int((y - self.display_offset_y) / self.display_scale)
        if self.frame_shape:
            img_x = max(0, min(self.frame_shape[1] - 1, img_x))
            img_y = max(0, min(self.frame_shape[0] - 1, img_y))
        return img_x, img_y

    def map_to_widget(self, x, y):
        wx = int(x * self.display_scale + self.display_offset_x)
        wy = int(y * self.display_scale + self.display_offset_y)
        return wx, wy

    def mousePressEvent(self, event):
        if self.drawing_enabled:
            self.drawing = True
            self.ix, self.iy = self.map_to_image(event.x(), event.y())
            self.temp_bbox = None
            self.setCursor(QCursor(Qt.CrossCursor))
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing and self.drawing_enabled:
            x, y = self.map_to_image(event.x(), event.y())
            self.temp_bbox = (
                min(self.ix, x),
                min(self.iy, y),
                abs(x - self.ix),
                abs(y - self.iy)
            )
            self.mouse_pos = (event.x(), event.y())
            self.update()
        elif self.drawing_enabled:
            self.mouse_pos = (event.x(), event.y())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drawing and self.drawing_enabled:
            self.drawing = False
            x, y = self.map_to_image(event.x(), event.y())
            w = abs(x - self.ix)
            h = abs(y - self.iy)
            if w > 10 and h > 10:
                self.bbox = (
                    min(self.ix, x),
                    min(self.iy, y),
                    w, h
                )
            self.temp_bbox = None
            self.drawing_enabled = False
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.tracker_app.on_roi_selected()
            self.update()

    def enterEvent(self, event):
        if self.drawing_enabled:
            self.setCursor(QCursor(Qt.CrossCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.mouse_pos = None
        self.update()

    def paintEvent(self, event):
        if self.tracker_app.frame is not None:
            frame = self.tracker_app.frame.copy()
            self.tracker_app.draw_boxes(frame)
            if not self.tracker_app.paused:
                cv2.putText(frame, f'FPS: {self.tracker_app.fps:.2f}', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            label_w, label_h = self.width(), self.height()
            scale = min(label_w / w, label_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            offset_x = (label_w - new_w) // 2
            offset_y = (label_h - new_h) // 2
            self.display_scale = scale
            self.display_offset_x = offset_x
            self.display_offset_y = offset_y
            qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image).scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(24, 24, 24))
            painter.drawPixmap(offset_x, offset_y, pixmap)
            if (self.drawing and self.temp_bbox) or (self.drawing_enabled and self.mouse_pos):
                if self.temp_bbox:
                    x, y, w_box, h_box = self.temp_bbox
                    wx, wy = self.map_to_widget(x, y)
                    wx2, wy2 = self.map_to_widget(x + w_box, y + h_box)
                    rect = QRect(QPoint(wx, wy), QPoint(wx2, wy2))
                    overlay_color = QColor(255, 255, 0, 60)
                    painter.setBrush(overlay_color)
                    pen = QPen(QColor(255, 255, 0), 2, Qt.DashLine)
                    painter.setPen(pen)
                    painter.drawRect(rect)
                if self.mouse_pos:
                    mx, my = self.mouse_pos
                    painter.setPen(QPen(QColor(255, 255, 255, 180), 1, Qt.SolidLine))
                    painter.drawLine(mx - 10, my, mx + 10, my)
                    painter.drawLine(mx, my - 10, mx, my + 10)
            painter.end()
        else:
            super().paintEvent(event)

class TrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.cap = None
        self.frame = None
        self.paused = True
        self.trackers = {}
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        self.target_width = 1280
        self.target_height = 720
        self.video_writer = None  
        self.output_video_path = None
        self.saving_video = False
        self.show_reference_bbox = False  
        self.reference_bbox_timer = None
        self.reference_frame = None
        self.reference_pause_written = False  
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.instruction_label = QLabel('Load a video to begin.')
        self.instruction_label.setStyleSheet('font-size: 16px; color: #2e9fff; padding: 8px;')
        main_layout.addWidget(self.instruction_label, alignment=Qt.AlignCenter)
        video_group = QGroupBox()
        video_group.setStyleSheet('QGroupBox { border: 2px solid #2e9fff; border-radius: 8px; margin-top: 8px; }')
        video_layout = QVBoxLayout(video_group)
        self.video_display = VideoDisplay(self)
        video_layout.addWidget(self.video_display)
        main_layout.addWidget(video_group)
        button_layout = QHBoxLayout()
        self.load_btn = QPushButton('Load Video')
        self.draw_btn = QPushButton('Draw Box')
        self.play_btn = QPushButton('Play')
        self.reset_btn = QPushButton('Reset')
        self.load_btn.clicked.connect(self.load_video)
        self.draw_btn.clicked.connect(self.start_drawing)
        self.play_btn.clicked.connect(self.toggle_play)
        self.reset_btn.clicked.connect(self.reset)
        for btn in [self.load_btn, self.draw_btn, self.play_btn, self.reset_btn]:
            btn.setMinimumWidth(100)
            btn.setStyleSheet('font-size: 15px; padding: 6px 12px;')
        button_layout.addStretch(1)
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.draw_btn)
        button_layout.addWidget(self.play_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch(1)
        main_layout.addLayout(button_layout)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        open_action = QAction('Open Video', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.load_video)
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(open_action)
        file_menu.addAction(exit_action)
        self.setWindowTitle('Multi-Tracker Comparison')
        self.setGeometry(100, 100, 1100, 900)
        self.draw_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

    def load_video(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm)"
        )
        if file_name:
            self.video_path = file_name
            self.cap = cv2.VideoCapture(self.video_path)
            self.frame_count = 0
            self.paused = True
            self.trackers = {}
            self.fps = 0
            self.last_time = time.time()
            self.read_first_frame()
            self.draw_btn.setEnabled(True)
            self.play_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)
            self.instruction_label.setText('Click "Draw Box" and drag to select ROI.')

    def read_first_frame(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.frame = self.resize_frame(frame)
                self.video_display.set_frame(self.frame)
                self.video_display.update()
                self.instruction_label.setText('Click "Draw Box" and drag to select ROI.')
                self.statusBar.showMessage('Draw ROI by clicking "Draw Box" and dragging on the video')
            else:
                self.statusBar.showMessage('Failed to read video')
                self.instruction_label.setText('Failed to read video.')

    def resize_frame(self, frame):
        height, width = frame.shape[:2]
        scale_width = self.target_width / width
        scale_height = self.target_height / height
        scale = min(scale_width, scale_height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    def update_display(self):
        self.video_display.set_frame(self.frame)
        self.video_display.update()

    def draw_boxes(self, frame):
        for name in TRACKER_TYPES.keys():
            bbox = self.trackers.get(name + '_bbox', None)
            color = TRACKER_COLORS[name]
            if bbox is not None:
                x, y, w, h = [int(v) for v in bbox]
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, name, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        if self.show_reference_bbox and self.video_display and self.video_display.bbox:
            x, y, w, h = [int(v) for v in self.video_display.bbox]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
            cv2.putText(frame, 'Reference', (x, y + h + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        self.draw_legend(frame)

    def draw_legend(self, frame):
        legend_items = list(TRACKER_TYPES.keys())
        box_w, box_h = 22, 22
        pad = 10
        font_scale = 0.7
        thickness = 2
        x0 = frame.shape[1] - 180  
        y0 = 20
        for i, name in enumerate(legend_items):
            color = TRACKER_COLORS[name]
            y = y0 + i * (box_h + 8)
            cv2.rectangle(frame, (x0, y), (x0 + box_w, y + box_h), color, -1)
            cv2.rectangle(frame, (x0, y), (x0 + box_w, y + box_h), (255,255,255), 1)
            cv2.putText(frame, name, (x0 + box_w + 8, y + box_h - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255,255,255), thickness)

    def start_drawing(self):
        if self.frame is not None:
            self.video_display.drawing_enabled = True
            self.video_display.bbox = None
            self.video_display.temp_bbox = None
            self.video_display.setCursor(QCursor(Qt.CrossCursor))
            self.update_display()
            self.statusBar.showMessage('Draw ROI by clicking and dragging on the video')
            self.instruction_label.setText('Draw ROI: Click and drag on the video.')
            self.play_btn.setEnabled(False)

    def on_roi_selected(self):
        if self.video_display.bbox:
            self.reference_frame = self.frame.copy()
            x, y, w, h = [int(v) for v in self.video_display.bbox]
            cv2.rectangle(self.reference_frame, (x, y), (x + w, y + h), (0, 255, 255), 3)
            cv2.putText(self.reference_frame, 'Reference Box Selected', (x, y - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3, cv2.LINE_AA)
            self.show_reference_bbox = True
            self.reference_pause_written = False  
            if self.reference_bbox_timer is not None:
                self.reference_bbox_timer.stop()
            self.reference_bbox_timer = QTimer(self)
            self.reference_bbox_timer.setSingleShot(True)
            self.reference_bbox_timer.timeout.connect(self.hide_reference_bbox)
            self.reference_bbox_timer.start(1000)
            self.update_display()
            self.init_trackers()
            self.statusBar.showMessage('ROI selected. Press Play to start tracking')
            self.instruction_label.setText('ROI selected. Press Play to start tracking.')
            self.play_btn.setEnabled(True)

    def hide_reference_bbox(self):
        self.show_reference_bbox = False
        self.update_display()

    def init_trackers(self):
        self.trackers = {}
        for name, ctor in TRACKER_TYPES.items():
            tracker = ctor()
            tracker.init(self.frame, self.video_display.bbox)
            self.trackers[name] = tracker

    def update_trackers(self):
        tracker_items = [(name, tracker) for name, tracker in self.trackers.items() if not name.endswith('_bbox')]
        for name, tracker in tracker_items:
            success, bbox = tracker.update(self.frame)
            if success:
                self.trackers[name + '_bbox'] = bbox
            else:
                self.trackers[name + '_bbox'] = None
        now = time.time()
        self.fps = 1.0 / (now - self.last_time)
        self.last_time = now

    def toggle_play(self):
        if self.cap is None:
            self.statusBar.showMessage('No video loaded')
            return
        if not self.saving_video and self.play_btn.text() == 'Play':
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Save Result Video As",
                "result.avi",
                "AVI Files (*.avi);;MP4 Files (*.mp4)"
            )
            if file_name:
                self.output_video_path = file_name
                self.init_video_writer()
                self.saving_video = True
        if self.saving_video and hasattr(self, 'reference_frame') and self.reference_frame is not None and (not hasattr(self, 'reference_pause_written') or not self.reference_pause_written):
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps < 1:
                fps = 30
            for _ in range(int(fps)):
                self.video_writer.write(self.reference_frame)
            self.reference_pause_written = True
        self.paused = not self.paused
        self.play_btn.setText('Pause' if not self.paused else 'Play')
        if not self.paused:
            self.timer.start(30)  
            self.draw_btn.setEnabled(False)
            self.instruction_label.setText('Tracking...')
        else:
            self.timer.stop()
            self.draw_btn.setEnabled(True)
            self.instruction_label.setText('Paused. Press Play to resume.')

    def init_video_writer(self):
        # Initialize the video writer with the correct size and FPS
        if self.frame is not None and self.output_video_path:
            height, width = self.frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'XVID') if self.output_video_path.endswith('.avi') else cv2.VideoWriter_fourcc(*'mp4v')
            # Try to get FPS from video file, fallback to 30
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps < 1:
                fps = 30
            self.video_writer = cv2.VideoWriter(self.output_video_path, fourcc, fps, (width, height))

    def update_frame(self):
        if self.cap and not self.paused:
            ret, frame = self.cap.read()
            if ret:
                self.frame = self.resize_frame(frame)
                self.frame_count = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.update_trackers()
                out_frame = self.frame.copy()
                self.draw_boxes(out_frame)
                if not self.paused:
                    cv2.putText(out_frame, f'FPS: {self.fps:.2f}', (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                if self.saving_video and self.video_writer is not None:
                    self.video_writer.write(out_frame)
                self.update_display()
            else:
                self.paused = True
                self.play_btn.setText('Play')
                self.timer.stop()
                self.statusBar.showMessage('End of video')
                self.instruction_label.setText('End of video.')
                if self.saving_video and self.video_writer is not None:
                    self.video_writer.release()
                    self.video_writer = None
                    self.saving_video = False

    def reset(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)
            ret, frame = self.cap.read()
            if ret:
                self.frame = self.resize_frame(frame)
                self.video_display.bbox = None
                self.trackers = {}
                self.update_display()
                self.statusBar.showMessage('Draw new ROI')
                self.instruction_label.setText('Draw new ROI: Click "Draw Box" and drag.')
                self.play_btn.setEnabled(False)
                self.draw_btn.setEnabled(True)
                self.show_reference_bbox = False
                if self.reference_bbox_timer is not None:
                    self.reference_bbox_timer.stop()
                    self.reference_bbox_timer = None
                self.reference_pause_written = False  

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        if self.saving_video and self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            self.saving_video = False
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  
    window = TrackerApp()
    window.show()
    sys.exit(app.exec_())
