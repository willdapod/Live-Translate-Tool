import tkinter as tk
from gui import LiveTranslateApp
import pytesseract

def main():
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    root = tk.Tk()
    app = LiveTranslateApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
