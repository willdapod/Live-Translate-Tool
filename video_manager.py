import cv2
from pygrabber.dshow_graph import FilterGraph

class VideoManager:
    def __init__(self):
        self.cap = None
        self.current_device_index = -1

    def get_devices(self):
        try:
            graph = FilterGraph()
            devices = graph.get_input_devices()
            return devices
        except Exception:
            return []

    def start_capture(self, device_index):
        if self.cap is not None:
            self.stop_capture()

        self.cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            return False
            
        self.current_device_index = device_index
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        return True

    def stop_capture(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_frame(self):
        if self.cap and self.cap.isOpened():
            return self.cap.read()
        return False, None
