import sys
import pyautogui
import keyboard
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QHBoxLayout, QKeySequenceEdit, QDateEdit, QTimeEdit, QMessageBox, QListWidget,
    QListWidgetItem, QAbstractItemView, QFileDialog, QSpinBox, QDialog, QScrollArea
)
from PyQt5.QtCore import Qt, QDateTime, QThread, pyqtSignal, QTime, QEvent
from PyQt5.QtGui import QFont, QIcon

import threading
from datetime import datetime
import json  # JSON 파일로 매크로를 저장하기 위해 추가

class MacroThread(QThread):
    def __init__(self, macro_actions):
        super().__init__()
        self.macro_actions = macro_actions
        self._is_running = True  # 스레드 동작 여부 플래그

    def run(self):
        for action in self.macro_actions:
            if not self._is_running:
                break
            if action['type'] == 'mouse':
                x, y = action['x'], action['y']
                pyautogui.click(x, y)
            elif action['type'] == 'keyboard':
                keys = action['keys']
                pyautogui.hotkey(*keys)

            total_delay = action['delay']
            delay_hours = total_delay // 3600
            delay_minutes = (total_delay % 3600) // 60
            delay_seconds = total_delay % 60
            delay_time = delay_hours * 3600 + delay_minutes * 60 + delay_seconds

            for _ in range(int(delay_time * 10)):
                if not self._is_running:
                    break
                self.msleep(100)  # 0.1초마다 체크
            if not self._is_running:
                break

    def stop(self):
        self._is_running = False

class MousePositionThread(QThread):
    position_changed = pyqtSignal(int, int)

    def run(self):
        while True:
            x, y = pyautogui.position()
            self.position_changed.emit(x, y)
            self.msleep(100)

# QTimeEdit를 상속하여 키 입력 이벤트를 수정하는 클래스
class CustomTimeEdit(QTimeEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace:
            if self.hasSelectedText():
                # 전체 텍스트 선택 후 백스페이스를 누른 경우
                cursor = self.lineEdit().cursor()
                selected_text = cursor.selectedText()
                if selected_text == self.text():
                    self.setTime(QTime(0, 0, 0))
                    self.setCurrentSection(QDateTimeEdit.HourSection)
                    return  # 이벤트 소비하여 기본 동작 막기
        super().keyPressEvent(event)

# 시간 선택을 위한 커스텀 다이얼로그 클래스
class TimePickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("시간 선택")
        self.setFixedSize(400, 200)
        layout = QVBoxLayout()

        # 현재 시간 가져오기
        now = QTime.currentTime()
        current_hour = now.hour()
        current_minute = now.minute()
        current_second = now.second()

        # 오전/오후 리스트
        self.am_pm_list = QListWidget()
        self.am_pm_list.addItems(["오전", "오후"])
        self.am_pm_list.setFixedWidth(60)
        self.am_pm_list.setFixedHeight(100)
        self.am_pm_list.setCurrentRow(0 if current_hour < 12 else 1)
        self.am_pm_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 시간 리스트 (1~12)
        self.hour_list = QListWidget()
        self.hour_list.addItems([str(i) for i in range(1, 13)])
        self.hour_list.setFixedWidth(60)
        self.hour_list.setFixedHeight(100)
        display_hour = current_hour % 12
        display_hour = 12 if display_hour == 0 else display_hour
        self.hour_list.setCurrentRow(display_hour - 1)
        self.hour_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 분 리스트 (0~59)
        self.minute_list = QListWidget()
        self.minute_list.addItems(["{:02}".format(i) for i in range(0, 60)])
        self.minute_list.setFixedWidth(60)
        self.minute_list.setFixedHeight(100)
        self.minute_list.setCurrentRow(current_minute)
        self.minute_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 초 리스트 (0~59)
        self.second_list = QListWidget()
        self.second_list.addItems(["{:02}".format(i) for i in range(0, 60)])
        self.second_list.setFixedWidth(60)
        self.second_list.setFixedHeight(100)
        self.second_list.setCurrentRow(current_second)
        self.second_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 각 리스트를 스크롤 영역으로 추가하여 휠 피커 효과를 냅니다.
        list_layout = QHBoxLayout()

        am_pm_layout = QVBoxLayout()
        am_pm_layout.addWidget(QLabel("오전/오후"))
        am_pm_layout.addWidget(self.am_pm_list)
        list_layout.addLayout(am_pm_layout)

        hour_layout = QVBoxLayout()
        hour_layout.addWidget(QLabel("시"))
        hour_layout.addWidget(self.hour_list)
        list_layout.addLayout(hour_layout)

        minute_layout = QVBoxLayout()
        minute_layout.addWidget(QLabel("분"))
        minute_layout.addWidget(self.minute_list)
        list_layout.addLayout(minute_layout)

        second_layout = QVBoxLayout()
        second_layout.addWidget(QLabel("초"))
        second_layout.addWidget(self.second_list)
        list_layout.addLayout(second_layout)

        layout.addLayout(list_layout)

        # 확인 및 취소 버튼
        button_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        cancel_button = QPushButton("취소")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 버튼 연결
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def get_selected_time(self):
        am_pm = self.am_pm_list.currentItem().text()
        hour = int(self.hour_list.currentItem().text())
        if am_pm == "오후" and hour != 12:
            hour += 12
        elif am_pm == "오전" and hour == 12:
            hour = 0
        minute = int(self.minute_list.currentItem().text())
        second = int(self.second_list.currentItem().text())
        return QTime(hour, minute, second)

class MacroApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.macro_actions = []
        self.macro_thread = None  # 현재 실행 중인 매크로 스레드
        self.schedule_thread = None  # 예약 스레드
        self.scheduled = False  # 매크로 예약 여부

    def initUI(self):
        self.setWindowTitle('매크로 made by Ramge132')
        self.setWindowIcon(QIcon('macro_icon.png'))  # 아이콘 파일을 지정하세요
        self.setGeometry(100, 100, 500, 700)
        font = QFont('Arial', 10)

        # 스타일시트 적용
        self.setStyleSheet("""
        QWidget { background-color: #f0f0f0; }
        QLabel { font-size: 14px; }
        QPushButton { background-color: #ADD8E6; /* 연한 하늘색 */ color: black; border-radius: 6px; padding: 8px; font-size: 12px; }
        QPushButton:hover { background-color: #1E90FF; /* 진한 파란색 */ color: white; }
        QTextEdit { background-color: #ffffff; }
        QLineEdit, QDateEdit, QTimeEdit, QKeySequenceEdit { background-color: #ffffff; }
        QListWidget { background-color: #ffffff; }
        """)

        layout = QVBoxLayout()

        # 마우스 좌표 표시
        self.coord_label = QLabel('마우스 위치: (0, 0)')
        self.coord_label.setFont(font)
        layout.addWidget(self.coord_label)

        # 매크로 상태 표시
        self.status_label = QLabel('매크로 상태: 대기 중')
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)

        # 예약 시간 선택
        datetime_layout = QHBoxLayout()
        self.time_edit = CustomTimeEdit(self)
        self.time_edit.setTime(QTime.currentTime())
        self.time_edit.setDisplayFormat('AP hh:mm:ss')  # AM/PM 표시 형식
        self.time_edit.setKeyboardTracking(True)  # 키보드로 시간 변경 가능
        datetime_layout.addWidget(QLabel('예약 시간:'))
        datetime_layout.addWidget(self.time_edit)

        # 시간 피커 버튼 추가
        self.time_picker_button = QPushButton('🕒')  # 아이콘을 사용하거나 이모지를 사용할 수 있습니다.
        self.time_picker_button.setFixedSize(30, 30)
        datetime_layout.addWidget(self.time_picker_button)
        layout.addLayout(datetime_layout)

        # 키보드 입력
        keyboard_layout = QHBoxLayout()
        self.keyboard_input = QKeySequenceEdit(self)
        keyboard_layout.addWidget(QLabel('키보드 입력:'))
        keyboard_layout.addWidget(self.keyboard_input)
        layout.addLayout(keyboard_layout)

        # 딜레이 설정 (시, 분, 초 분리)
        delay_layout = QHBoxLayout()
        self.delay_hours_spinbox = QSpinBox(self)
        self.delay_hours_spinbox.setRange(0, 23)
        self.delay_hours_spinbox.setPrefix('시: ')

        self.delay_minutes_spinbox = QSpinBox(self)
        self.delay_minutes_spinbox.setRange(0, 59)
        self.delay_minutes_spinbox.setPrefix('분: ')

        self.delay_seconds_spinbox = QSpinBox(self)
        self.delay_seconds_spinbox.setRange(0, 59)
        self.delay_seconds_spinbox.setPrefix('초: ')
        self.delay_seconds_spinbox.setValue(1)  # 기본값 1초

        delay_layout.addWidget(QLabel('동작 후 딜레이:'))
        delay_layout.addWidget(self.delay_hours_spinbox)
        delay_layout.addWidget(self.delay_minutes_spinbox)
        delay_layout.addWidget(self.delay_seconds_spinbox)
        layout.addLayout(delay_layout)

        # 버튼들
        button_layout = QHBoxLayout()
        self.add_mouse_action_btn = QPushButton('마우스 위치 추가 (Ctrl+F3)')
        button_layout.addWidget(self.add_mouse_action_btn)
        self.add_keyboard_action_btn = QPushButton('키보드 입력 추가')
        button_layout.addWidget(self.add_keyboard_action_btn)
        layout.addLayout(button_layout)

        # 매크로 시작 및 중지 버튼들
        macro_control_layout = QHBoxLayout()
        self.start_macro_now_btn = QPushButton('매크로 즉시 시작 (Ctrl+F1)')
        macro_control_layout.addWidget(self.start_macro_now_btn)
        self.stop_macro_btn = QPushButton('매크로 중지 (Ctrl+F2)')
        macro_control_layout.addWidget(self.stop_macro_btn)
        layout.addLayout(macro_control_layout)

        # 매크로 예약 시작 버튼
        self.schedule_macro_btn = QPushButton('매크로 예약 시작')
        layout.addWidget(self.schedule_macro_btn)

        # 저장 및 불러오기 버튼들
        file_button_layout = QHBoxLayout()
        self.save_macro_btn = QPushButton('저장')
        file_button_layout.addWidget(self.save_macro_btn)
        self.load_macro_btn = QPushButton('불러오기')
        file_button_layout.addWidget(self.load_macro_btn)
        layout.addLayout(file_button_layout)

        # 매크로 동작 리스트
        self.macro_list = QListWidget(self)
        self.macro_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.macro_list.setDragDropMode(QAbstractItemView.InternalMove)  # 드래그 앤 드롭 활성화
        layout.addWidget(self.macro_list)

        # 동작 삭제 버튼 추가
        self.delete_action_btn = QPushButton('동작 삭제')
        layout.addWidget(self.delete_action_btn)

        self.setLayout(layout)

        # 시그널 연결
        self.add_mouse_action_btn.clicked.connect(self.add_mouse_action)
        self.add_keyboard_action_btn.clicked.connect(self.add_keyboard_action)
        self.start_macro_now_btn.clicked.connect(self.run_macro_now)
        self.stop_macro_btn.clicked.connect(self.stop_macro)
        self.schedule_macro_btn.clicked.connect(self.schedule_macro_start)
        self.save_macro_btn.clicked.connect(self.save_macro)
        self.load_macro_btn.clicked.connect(self.load_macro)
        self.delete_action_btn.clicked.connect(self.delete_selected_action)

        # 시간 피커 버튼 클릭 시 다이얼로그 표시
        self.time_picker_button.clicked.connect(self.open_time_picker_dialog)

        # 마우스 위치 스레드 시작
        self.mouse_thread = MousePositionThread()
        self.mouse_thread.position_changed.connect(self.update_mouse_position)
        self.mouse_thread.start()

        # 단축키 설정
        keyboard.add_hotkey('ctrl+f1', self.run_macro_now)
        keyboard.add_hotkey('ctrl+f2', self.stop_macro)
        keyboard.add_hotkey('ctrl+f3', self.add_mouse_action)

    def update_mouse_position(self, x, y):
        self.coord_label.setText(f'마우스 위치: ({x}, {y})')

    def get_delay_in_seconds(self):
        hours = self.delay_hours_spinbox.value()
        minutes = self.delay_minutes_spinbox.value()
        seconds = self.delay_seconds_spinbox.value()
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds

    def format_delay(self, total_seconds):
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f'{hours}시 {minutes}분 {seconds}초'

    def add_mouse_action(self):
        x, y = pyautogui.position()
        delay = self.get_delay_in_seconds()
        action = {'type': 'mouse', 'x': x, 'y': y, 'delay': delay}
        self.macro_actions.append(action)
        formatted_delay = self.format_delay(delay)
        item_text = f'마우스 클릭 at ({x}, {y}) - 딜레이: {formatted_delay}'
        self.add_action_to_list(item_text)

    def add_keyboard_action(self):
        key_sequence = self.keyboard_input.keySequence()
        if not key_sequence.isEmpty():
            keys = key_sequence.toString().lower().split('+')
            keys = [key.strip() for key in keys]
            delay = self.get_delay_in_seconds()
            action = {'type': 'keyboard', 'keys': keys, 'delay': delay}
            self.macro_actions.append(action)
            formatted_delay = self.format_delay(delay)
            item_text = f'키보드 입력: {" + ".join(keys)} - 딜레이: {formatted_delay}'
            self.add_action_to_list(item_text)
            self.keyboard_input.clear()
        else:
            QMessageBox.warning(self, '경고', '올바른 키 시퀀스를 입력하세요.')

    def add_action_to_list(self, text):
        item = QListWidgetItem(text)
        self.macro_list.addItem(item)

    def run_macro_now(self):
        if self.macro_list.count() > 0:
            # 이미 매크로가 실행 중인 경우
            if self.macro_thread and self.macro_thread.isRunning():
                QMessageBox.warning(self, '경고', '매크로가 이미 실행 중입니다.')
                return
            # 순서를 사용자 정의 순서로 설정
            self.update_macro_actions_order()
            self.macro_thread = MacroThread(self.macro_actions)
            self.macro_thread.start()
            self.status_label.setText('매크로 상태: 실행 중')
            self.macro_thread.finished.connect(self.on_macro_finished)
        else:
            QMessageBox.information(self, '정보', '수행할 매크로 동작이 없습니다.')

    def stop_macro(self):
        if self.macro_thread and self.macro_thread.isRunning():
            self.macro_thread.stop()
            self.status_label.setText('매크로 상태: 정지됨')
        else:
            QMessageBox.information(self, '정보', '실행 중인 매크로가 없습니다.')

    def on_macro_finished(self):
        self.status_label.setText('매크로 상태: 대기 중')

    def schedule_macro_start(self):
        scheduled_time = self.time_edit.time()
        now = QTime.currentTime()
        seconds_until_execution = now.secsTo(scheduled_time)
        if seconds_until_execution < 0:
            seconds_until_execution += 86400  # 다음 날로 설정
        if seconds_until_execution == 0:
            QMessageBox.warning(self, '경고', '미래의 시간을 선택하세요.')
            return
        self.status_label.setText(f'매크로 상태: 예약됨 - {scheduled_time.toString("AP hh:mm:ss")}에 실행 예정')
        self.scheduled = True
        self.schedule_thread = threading.Timer(seconds_until_execution, self.run_macro_now)
        self.schedule_thread.start()

    def update_macro_actions_order(self):
        items = []
        for index in range(self.macro_list.count()):
            items.append(self.macro_list.item(index).text())

        # 매크로 동작 리스트를 재정렬
        new_macro_actions = []
        for text in items:
            for action in self.macro_actions:
                delay_formatted = self.format_delay(action['delay'])
                if action['type'] == 'mouse':
                    action_text = f'마우스 클릭 at ({action["x"]}, {action["y"]}) - 딜레이: {delay_formatted}'
                else:
                    keys_joined = " + ".join(action['keys'])
                    action_text = f'키보드 입력: {keys_joined} - 딜레이: {delay_formatted}'

                if action_text == text and action not in new_macro_actions:
                    new_macro_actions.append(action)
                    break
        self.macro_actions = new_macro_actions

    def save_macro(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "매크로 저장", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(self.macro_actions, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, '성공', '매크로가 성공적으로 저장되었습니다.')
            except Exception as e:
                QMessageBox.warning(self, '오류', f'매크로 저장 중 오류가 발생했습니다:\n{e}')

    def load_macro(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "매크로 불러오기", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    self.macro_actions = json.load(f)
                self.update_macro_list()
                QMessageBox.information(self, '성공', '매크로가 성공적으로 불러와졌습니다.')
            except Exception as e:
                QMessageBox.warning(self, '오류', f'매크로 불러오기 중 오류가 발생했습니다:\n{e}')

    def update_macro_list(self):
        self.macro_list.clear()
        for action in self.macro_actions:
            delay_formatted = self.format_delay(action['delay'])
            if action['type'] == 'mouse':
                item_text = f'마우스 클릭 at ({action["x"]}, {action["y"]}) - 딜레이: {delay_formatted}'
            elif action['type'] == 'keyboard':
                keys_joined = " + ".join(action['keys'])
                item_text = f'키보드 입력: {keys_joined} - 딜레이: {delay_formatted}'
            self.add_action_to_list(item_text)

    # 시간 피커 다이얼로그 표시 함수 추가
    def open_time_picker_dialog(self):
        dialog = TimePickerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            selected_time = dialog.get_selected_time()
            self.time_edit.setTime(selected_time)

    # 동작 삭제 함수 추가
    def delete_selected_action(self):
        selected_items = self.macro_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, '정보', '삭제할 동작을 선택하세요.')
            return
        for item in selected_items:
            row = self.macro_list.row(item)
            self.macro_list.takeItem(row)
            del self.macro_actions[row]  # 해당 매크로 동작도 삭제

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MacroApp()
    ex.show()
    sys.exit(app.exec_())