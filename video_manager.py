import cv2
import threading
import time
from pygrabber.dshow_graph import FilterGraph

class VideoManager:
    """
    High-performance video capture manager.
    Runs a dedicated background thread to read frames from DirectShow hardware,
    ensuring the GUI rendering loop never blocks on camera I/O and runs at a smooth 60 FPS.
    """
    def __init__(self):
        self.cap = None
        self.current_device_index = -1
        self.target_resolution = (1280, 720) # Default 720p
        self.target_fps = 60

        # Threaded capture state
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.thread_active = False
        self.capture_thread = None

    def get_devices(self):
        try:
            graph = FilterGraph()
            devices = graph.get_input_devices()
            return devices if devices else []
        except Exception as e:
            print(f"[VideoManager] Device enumeration error: {e}")
            return []

    def set_target_resolution(self, width, height):
        self.target_resolution = (int(width), int(height))
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_resolution[1])

    def start_capture(self, device_index):
        self.stop_capture()

        # Open device with DirectShow (standard Windows API for HDMI capture cards)
        self.cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(device_index)

        if not self.cap.isOpened():
            self.cap = None
            return False

        self.current_device_index = device_index

        # Request MJPG stream from capture device to unlock hardware 60 FPS on USB capture cards
        try:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        except Exception:
            pass

        # Set buffer size to 1 to eliminate frame latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        w, h = self.target_resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        # Launch dedicated background frame grabber thread
        self.thread_active = True
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.capture_thread.start()

        return True

    def _capture_worker(self):
        """
        Continuously reads frames from hardware in the background.
        Main GUI thread grabs latest_frame without any blocking.
        """
        while self.thread_active:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.frame_lock:
                        self.latest_frame = frame
                else:
                    time.sleep(0.001)
            else:
                time.sleep(0.01)

    def stop_capture(self):
        self.thread_active = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=0.3)
        self.capture_thread = None

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        with self.frame_lock:
            self.latest_frame = None
        self.current_device_index = -1

    def get_frame(self):
        """
        Instantaneous non-blocking frame retrieval. Returns in <0.01ms.
        """
        with self.frame_lock:
            if self.latest_frame is not None:
                return True, self.latest_frame
        return False, None

    def get_actual_resolution(self):
        with self.frame_lock:
            if self.latest_frame is not None:
                h, w = self.latest_frame.shape[:2]
                return w, h
        return 0, 0
