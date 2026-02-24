from paddleocr import PaddleOCR

IMAGE_PATH = "data/tmp/pdf_images/page_1_img_1.png"

ocr = PaddleOCR(use_angle_cls=True, lang='en')

result = ocr.ocr(IMAGE_PATH, cls=True)

print("\n--- OCR RESULT ---\n")

for line in result[0]:
    text = line[1][0]
    print(text)