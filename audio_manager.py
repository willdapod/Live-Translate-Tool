import sounddevice as sd
import numpy as np

class AudioManager:
    """
    Manages low-latency audio passthrough from HDMI capture cards to PC speakers/headphones.
    """
    def __init__(self):
        self.stream = None
        self.input_device = None
        self.output_device = None
        self.sample_rate = 48000
        self.block_size = 1024
        self.volume = 1.0 # 0.0 to 1.5

    def get_devices(self):
        try:
            devices = sd.query_devices()
            inputs = []
            outputs = []
            for i, dev in enumerate(devices):
                if dev.get('max_input_channels', 0) > 0:
                    inputs.append({'index': i, 'name': dev['name']})
                if dev.get('max_output_channels', 0) > 0:
                    outputs.append({'index': i, 'name': dev['name']})
            return inputs, outputs
        except Exception as e:
            print(f"[AudioManager] Failed to query audio devices: {e}")
            return [], []

    def set_volume(self, vol_float):
        self.volume = max(0.0, min(1.5, float(vol_float)))

    def is_active(self):
        return self.stream is not None and self.stream.active

    def start_passthrough(self, input_idx, output_idx):
        self.stop_passthrough()
        try:
            self.input_device = input_idx
            self.output_device = output_idx

            # Try to determine compatible sample rate
            in_info = sd.query_devices(input_idx)
            out_info = sd.query_devices(output_idx)
            rate = int(in_info.get('default_samplerate', 48000))
            if not rate or rate < 8000:
                rate = int(out_info.get('default_samplerate', 48000))
            self.sample_rate = rate

            channels = min(
                int(in_info.get('max_input_channels', 2)),
                int(out_info.get('max_output_channels', 2)),
                2
            )
            if channels < 1:
                channels = 2

            def audio_callback(indata, outdata, frames, time_info, status):
                if status:
                    pass
                if self.volume != 1.0:
                    outdata[:] = indata * self.volume
                else:
                    outdata[:] = indata

            self.stream = sd.Stream(
                device=(input_idx, output_idx),
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=channels,
                callback=audio_callback
            )
            self.stream.start()
            msg = f"Passthrough active ({self.sample_rate}Hz, {channels}ch)"
            print(f"[AudioManager] {msg}")
            return True, msg
        except Exception as e:
            err = str(e)
            print(f"[AudioManager] Failed to start audio passthrough: {err}")
            self.stop_passthrough()
            return False, err

    def stop_passthrough(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            print("[AudioManager] Audio passthrough stopped.")
