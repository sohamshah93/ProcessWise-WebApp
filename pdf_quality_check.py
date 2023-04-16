import cv2
import pytesseract
import os
from pytesseract import Output
from pdf2image import convert_from_path


def is_scanned_pdf(file_path):
    if file_path.lower().endswith('.pdf'):
        images = convert_from_path(file_path)
        img = images[0]
        img.save('temp_image.png', 'PNG')
        file_path = 'temp_image.png'

    return os.path.splitext(file_path)[1].lower() in {'.png', '.jpg', '.jpeg', '.tiff'}


def check_pdf_image_quality(file_path):
    if file_path.lower().endswith('.pdf'):
        images = convert_from_path(file_path)
        img = images[0]
        img.save('temp_image.png', 'PNG')
        file_path = 'temp_image.png'

    img = cv2.imread(file_path, 0)
    d = pytesseract.image_to_data(img, output_type=Output.DICT)
    text = ' '.join(d['text'])
    quality_score = sum(d['conf']) / len(d['conf'])

    if os.path.exists('temp_image.png'):
        os.remove('temp_image.png')

    return quality_score
