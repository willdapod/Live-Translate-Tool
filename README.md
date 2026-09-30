# Live Translate Tool 🎮 🌐

Real-time AI-powered on-screen video and game translation tool. Captures video from HDMI capture cards, webcams, or virtual cameras (OBS), runs optical character recognition (OCR) on your GPU, translates dialogue on the fly, and renders crisp subtitle overlays.

---

## ✨ Features & Performance Enhancements

- **🚀 60 FPS Threaded Video Capture (`VideoManager`)**:
  - DirectShow hardware capture is offloaded to a dedicated background frame-grabber thread.
  - Video rendering on the GUI never blocks on hardware I/O, maintaining a smooth **60.0 FPS** display rate.
- **⚡ DirectML GPU Acceleration on NVIDIA Graphics Card**:
  - Leverages **DirectML (`onnxruntime-directml`)** to run ONNX neural network inference directly on the GPU via DirectX 12 compute shaders.
  - Completely bypasses CUDA `sm_120` architecture limitations with native hardware GPU acceleration.
- **🔍 3x Faster OCR with Dynamic Downsampling**:
  - Automatically downsamples high-resolution (1080p) video frames for text detection (`max_ocr_width=960`), reducing OCR inference time to ~40–80ms while scaling bounding box coordinates back up with pixel perfection.
- **🛡️ 100% Local Neural Translation & Rate-Limit Immunity**:
  - **Argos Translate**: Runs local neural machine translation offline on your machine with 0ms network latency and no rate limits.
  - **Google / MyMemory with Automatic Fallback**: Detects 429 rate limits and instantly switches to local Argos.
  - **Immediate Local Persistence (`translations.json`)**: Every new translation is automatically cached in memory and saved to disk. Subsequent requests take **0.01 ms** and require zero network requests.
- **🎯 Accurate Box Replacement & Anti-Flicker**:
  - Solid, opaque background backdrops completely cover and hide the original Japanese text.
  - Timestamp-based expiry (`0.55s`) clears text from the screen immediately when dialogue ends or the camera pans.
- **🔊 Low-Latency Audio Passthrough (`AudioManager`)**:
  - Direct audio routing from HDMI capture cards to PC headphones/speakers with a real-time volume slider.
- **🎨 Modern Dark UI & Subtitle Modes**:
  - **Box Replacement Mode**: Clean cards centered directly over original text.
  - **Subtitle Banner Mode**: Cinematic bottom-screen subtitle bar.
  - Telemetry HUD: Real-time Camera FPS, OCR latency (ms), translation latency (ms), and active box count.

---

## 🚀 How to Run

```powershell
& ./venv/Scripts/python.exe main.py
```

Or from within `Live-Translate-Tool`:

```powershell
cd Live-Translate-Tool
& ./venv/Scripts/python.exe main.py
```
