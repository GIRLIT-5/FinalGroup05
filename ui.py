# ui.py

import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QGridLayout, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

from eye_tracking import EyeTracker  # Import the EyeTracker class


class VirtualKeyboard(QWidget):
    def __init__(self, eye_tracker):
        super().__init__()
        self.setWindowTitle("Virtual Keyboard")
        self.setFixedSize(600, 600)

        # Initialize variables
        self.eye_direction = None
        self.eye_status = "open"
        self.current_button_index = 0
        self.button_list = []
        self.input_text = ""

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.display_label = QLabel(self.input_text)
        self.display_label.setFixedHeight(50)
        self.display_label.setStyleSheet("font-size: 18px; border: 1px solid black; padding: 5px;")
        self.display_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        main_layout.addWidget(self.display_label)

        keyboard_layout = QGridLayout()
        main_layout.addLayout(keyboard_layout)

        buttons = [
            'A', 'B', 'C', 'D', 'E', 'F', 'G',
            'H', 'I', 'J', 'K', 'L', 'M', 'N',
            'O', 'P', 'Q', 'R', 'S', 'T', 'U',
            'V', 'W', 'X', 'Y', 'Z', '0', '1',
            '2', '3', '4', '5', '6', '7', '8',
            '9', 'Space', 'Backspace', 'Remove All'
        ]

        row_col_positions = [
            (0, 0, 7), (1, 0, 7), (2, 0, 7),
            (3, 0, 6), (4, 0, 6), (5, 0, 6)
        ]

        idx = 0
        for row, col, num_buttons in row_col_positions:
            for i in range(num_buttons):
                button = QPushButton(buttons[idx])
                button.setFixedSize(80, 50)
                keyboard_layout.addWidget(button, row, col + i)
                self.button_list.append(button)
                idx += 1

        self.update_button_selection()

        # Connect signals from EyeTracker
        eye_tracker.eye_direction_signal.connect(self.update_eye_direction)
        eye_tracker.eye_status_signal.connect(self.update_eye_status)

        # Timer for eye_status 'closed' duration detection
        self.closed_timer = QTimer()
        self.closed_timer.timeout.connect(self.activate_selected_button)
        self.closed_timer.setSingleShot(True)  # Only activate after 2 seconds of closed status

        # Timer for gaze direction holding time, to move every 1 second if direction is stable
        self.gaze_timer = QTimer()
        self.gaze_timer.timeout.connect(self.move_selection_based_on_gaze)

    def update_button_selection(self):
        for button in self.button_list:
            button.setStyleSheet("")
        self.button_list[self.current_button_index].setStyleSheet("background-color: yellow;")

    def update_eye_direction(self, direction):
        # Check if the direction has changed
        if self.eye_direction != direction:
            self.eye_direction = direction
            self.gaze_timer.stop()  # Stop the timer if the direction changes
            self.gaze_timer.start(500)  # Start the timer for 1-second interval if direction is stable

    def update_eye_status(self, status):
        # Update eye status and start timer if eye is closed and direction is "Center"
        self.eye_status = status
        if self.eye_status == 'closed' and self.eye_direction == "Center":
            if not self.closed_timer.isActive():  # Start timer only if not already active
                self.closed_timer.start(1500)  # Start 1.5-second timer
        else:
            self.closed_timer.stop()  # Stop the timer if eyes are open or direction is not Center

    def move_selection_based_on_gaze(self):
        """Move the selection based on stable eye direction every 1 second."""
        if self.eye_direction == 'Left':
            self.current_button_index = max(0, self.current_button_index - 1)
        elif self.eye_direction == 'Right':
            self.current_button_index = min(len(self.button_list) - 1, self.current_button_index + 1)
        elif self.eye_direction == 'Top':
            self.current_button_index = max(0, self.current_button_index - 7)
        elif self.eye_direction == 'Bottom':
            self.current_button_index = min(len(self.button_list) - 1, self.current_button_index + 7)

        self.update_button_selection()

    def activate_selected_button(self):
        """Activate the currently selected button when the eyes are closed for 2 seconds."""
        selected_button = self.button_list[self.current_button_index]
        text = selected_button.text()

        # Handle button actions
        if text == "Space":
            self.input_text += " "
        elif text == "Backspace":
            self.input_text = self.input_text[:-1]
        elif text == "Remove All":
            self.input_text = ""
        else:
            self.input_text += text

        # Update the display label
        self.display_label.setText(self.input_text)
        print(f"Button '{text}' activated!")  # Debug print for activated button


if __name__ == "__main__":
    app = QApplication(sys.argv)
    eye_tracker = EyeTracker()  # Initialize EyeTracker
    eye_tracker.start()  # Start the EyeTracker thread

    keyboard = VirtualKeyboard(eye_tracker)
    keyboard.show()

    # Graceful exit handling
    app.aboutToQuit.connect(eye_tracker.stop)
    sys.exit(app.exec_())
