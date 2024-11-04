# test.py
import cv2
import dlib
import mediapipe as mp
import numpy as np
from PyQt5.QtCore import QObject, QThread, pyqtSignal

# Initialize Mediapipe Face Mesh and Dlib
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

class EyeTracker(QThread):
    # Define signals to emit eye direction and eye status
    eye_direction_signal = pyqtSignal(str)
    eye_status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.square_size = 30  # Size of the squares for gaze tracking
        self.padding = 30  # Padding between squares
        self.left_square_top_left = (100, 200)
        self.right_square_top_left = (100 + self.square_size + self.padding, 200)
        self.running = True  # Control variable for the thread

    def calculate_ear(self, eye):
        d1 = np.linalg.norm(eye[1] - eye[5])
        d2 = np.linalg.norm(eye[2] - eye[4])
        d3 = np.linalg.norm(eye[0] - eye[3])
        ear = (d1 + d2) / (2.0 * d3)
        return ear

    def run(self):
        cap = cv2.VideoCapture(0)
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            frame = cv2.flip(frame, 1)  # Lật khung hình theo chiều ngang

            if not ret:
                break
            
            # Process frame
            self.process_frame(frame)

            # Display the processed frame
            cv2.imshow("Eye Tracking and Blink Detection", frame)
            
            # Kiểm tra phím nhấn để thay đổi kích thước ô vuông
            key = cv2.waitKey(1)
            if key == ord('+'):
                self.square_size += 10  # Tăng kích thước ô vuông
            elif key == ord('-'):
                self.square_size = max(20, self.square_size - 10)  # Giảm kích thước, với kích thước tối thiểu là 20
            elif key == ord('q'):
                self.running = False  # Dừng chương trình khi nhấn 'q'
            cv2.namedWindow("Eye Tracking and Blink Detection")
            cv2.setMouseCallback("Eye Tracking and Blink Detection", self.mouse_callback)

        cap.release()
        cv2.destroyAllWindows()
    def mouse_callback(self, event, x, y, flags, param):
        # Kiểm tra và xử lý khi chuột được nhấn vào các ô vuông
        if event == cv2.EVENT_LBUTTONDOWN:
            # Kiểm tra vị trí chuột trong ô vuông bên trái
            if (self.left_square_top_left[0] <= x <= self.left_square_top_left[0] + self.square_size and
                self.left_square_top_left[1] <= y <= self.left_square_top_left[1] + self.square_size):
                if x >= self.left_square_top_left[0] + self.square_size - 10 and y >= self.left_square_top_left[1] + self.square_size - 10:
                    self.resizing_left = True  # Bắt đầu thay đổi kích thước
                else:
                    self.dragging_left = True  # Bắt đầu kéo ô vuông

            # Kiểm tra vị trí chuột trong ô vuông bên phải
            elif (self.right_square_top_left[0] <= x <= self.right_square_top_left[0] + self.square_size and
                self.right_square_top_left[1] <= y <= self.right_square_top_left[1] + self.square_size):
                if x >= self.right_square_top_left[0] + self.square_size - 10 and y >= self.right_square_top_left[1] + self.square_size - 10:
                    self.resizing_right = True  # Bắt đầu thay đổi kích thước
                else:
                    self.dragging_right = True  # Bắt đầu kéo ô vuông

        # Xử lý khi chuột di chuyển
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.dragging_left:
                self.left_square_top_left = (x - self.square_size // 2, y - self.square_size // 2)
            elif self.dragging_right:
                self.right_square_top_left = (x - self.square_size // 2, y - self.square_size // 2)
            elif self.resizing_left:
                self.square_size = max(20, x - self.left_square_top_left[0])  # Thay đổi kích thước, giới hạn kích thước tối thiểu là 20
            elif self.resizing_right:
                self.square_size = max(20, x - self.right_square_top_left[0])

        # Khi thả chuột ra, dừng kéo hoặc thay đổi kích thước
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging_left = False
            self.dragging_right = False
            self.resizing_left = False
            self.resizing_right = False

    def process_frame(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray_frame)

        # Draw squares for gaze tracking
        self.draw_square_grid(frame, self.left_square_top_left)
        self.draw_square_grid(frame, self.right_square_top_left)

        for face in faces:
            landmarks = predictor(gray_frame, face)
            left_eye = np.array([[landmarks.part(i).x, landmarks.part(i).y] for i in range(36, 42)])
            right_eye = np.array([[landmarks.part(i).x, landmarks.part(i).y] for i in range(42, 48)])
            
            # Calculate EAR for blink detection
            ear_left = self.calculate_ear(left_eye)
            ear_right = self.calculate_ear(right_eye)

            # Determine eye status based on EAR values
            if ear_left < 0.2 or ear_right < 0.2:
                eye_status = "closed"
            else:
                eye_status = "open"

            # Emit eye status
            self.eye_status_signal.emit(eye_status)

            # Detect pupil position more accurately
            left_eye_center = self.detect_pupil_position(gray_frame, left_eye)
            right_eye_center = self.detect_pupil_position(gray_frame, right_eye)

            # Draw circles at the center points of each eye to indicate pupil location
            if left_eye_center is not None:
                cv2.circle(frame, tuple(left_eye_center), 5, (0, 255, 0), -1)  # Left eye center in green
            if right_eye_center is not None:
                cv2.circle(frame, tuple(right_eye_center), 5, (0, 255, 0), -1)  # Right eye center in green

            eye_centers = [left_eye_center, right_eye_center]
            gaze_directions = []

            # Determine gaze direction for each eye based on square sections
            for i, eye_center in enumerate(eye_centers):
                if eye_center is None:
                    continue  # Skip if pupil detection failed

                square_top_left = self.left_square_top_left if i == 0 else self.right_square_top_left
                if (square_top_left[0] <= eye_center[0] <= square_top_left[0] + self.square_size and
                    square_top_left[1] <= eye_center[1] <= square_top_left[1] + self.square_size):
                    
                    # Calculate which part of the 3x3 grid the eye center falls into
                    section_x = (eye_center[0] - square_top_left[0]) // (self.square_size // 3)
                    section_y = (eye_center[1] - square_top_left[1]) // (self.square_size // 3)
                    if section_x < 3 and section_y < 3:
                        section_index = section_y * 3 + section_x
                        gaze_directions.append(section_index)

            # Define mapping from grid position to gaze direction
            direction_map = {
                0: "Top", 1: "Top", 2: "Top",
                3: "Left", 4: "Center", 5: "Right",
                6: "Bottom", 7: "Bottom", 8: "Bottom"
            }

            # Determine the dominant gaze direction for each eye
            dominant_directions = []
            for gaze in gaze_directions:
                gaze_direction = direction_map.get(gaze, "Center")
                dominant_directions.append(gaze_direction)

            # Calculate overall eye direction based on both eyes
            if len(dominant_directions) == 2 and dominant_directions[0] == dominant_directions[1]:
                eye_direction = dominant_directions[0]  # Both eyes agree on direction
            else:
                eye_direction = "Center"  # Default to center if directions differ or not detected

            # Emit eye direction
            self.eye_direction_signal.emit(eye_direction)

            # Optional: Display debug information on the frame
            cv2.putText(frame, f"Eye Status: {eye_status}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if eye_status == "open" else (0, 0, 255), 2)
            cv2.putText(frame, f"Eye Direction: {eye_direction}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    def detect_pupil_position(self, gray_frame, eye_region):
        # Crop the eye region
        x_min, y_min = np.min(eye_region, axis=0)
        x_max, y_max = np.max(eye_region, axis=0)
        eye_roi = gray_frame[y_min:y_max, x_min:x_max]

        # Apply histogram equalization to enhance contrast
        eye_roi = cv2.equalizeHist(eye_roi)

        # Apply GaussianBlur to reduce noise
        eye_roi = cv2.GaussianBlur(eye_roi, (5, 5), 0)

        # Apply binary threshold with a fixed threshold value
        threshold_value = 50  # Adjust this value based on lighting and contrast conditions
        _, thresholded_eye = cv2.threshold(eye_roi, threshold_value, 255, cv2.THRESH_BINARY_INV)

        # Find contours in the thresholded image
        contours, _ = cv2.findContours(thresholded_eye, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Filter contours by area to avoid noise (assume pupil is within a reasonable size range)
            min_area = 5
            max_area = 500  # Adjust based on typical pupil size in your setup
            valid_contours = [cnt for cnt in contours if min_area < cv2.contourArea(cnt) < max_area]

            if valid_contours:
                # Find the largest valid contour, assuming it's the pupil
                largest_contour = max(valid_contours, key=cv2.contourArea)
                (x, y), radius = cv2.minEnclosingCircle(largest_contour)
                if radius > 1:
                    # Return the pupil center in the original frame coordinates
                    return np.array([int(x + x_min), int(y + y_min)])

        return None  # Return None if no valid pupil is detected


    
    def draw_square_grid(self, frame, top_left):
        """Draws a 3x3 grid inside a square for gaze tracking."""
        x, y = top_left
        # Draw the outer square
        cv2.rectangle(frame, (x, y), (x + self.square_size, y + self.square_size), (255, 0, 0), 2)
        # Draw the grid lines
        grid_size = self.square_size // 3
        for i in range(1, 3):
            # Vertical grid lines
            cv2.line(frame, (x + i * grid_size, y), (x + i * grid_size, y + self.square_size), (0, 255, 255), 1)
            # Horizontal grid lines
            cv2.line(frame, (x, y + i * grid_size), (x + self.square_size, y + i * grid_size), (0, 255, 255), 1)

    def stop(self):
        self.running = False