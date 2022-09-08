from PIL import Image
from io import BytesIO
import base64

with open(r'C:\Users\user\Desktop\collection\Emanuel\Emanuel.jpg', "rb") as f:
    im_b64 = base64.b64encode(f.read())

print(im_b64))

