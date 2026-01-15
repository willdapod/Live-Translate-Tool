import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

try:
    # Create a small blank image
    image = Image.new('RGB', (100, 100), color = (255, 255, 255))
    text = pytesseract.image_to_string(image, lang='script/Japanese')
    print("Success: 'jpn' language loaded.")
except Exception as e:
    print(f"Error: {e}")
