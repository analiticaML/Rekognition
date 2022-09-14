import logging
import json
import base64
from PIL import Image 
import io
import boto3


#Se define función principal de ejecución: Función Handler del evento de S3
def lambda_handler(event, context):
    # TODO implement

    #Se conecta con el servicio de Cloudwatch
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    cuerpo = event["body"]
    
    stringCuerpo = base64.b64decode(cuerpo).decode('utf-8')
    
    json_object = json.loads(stringCuerpo)
    
    print(json_object)
    
    imagen = json_object["capture"]
    
    nombre = json_object["date"]
    
    img_byte_arr = io.BytesIO()
    
    img_bytes = Image.open(io.BytesIO(base64.decodebytes(bytes(imagen, "utf-8"))))
    
    img_bytes.save(img_byte_arr, format="JPEG")
    img_byte_arr = img_byte_arr.getvalue()
    
    
    s3 = boto3.client("s3")
    
    s3.put_object(Body=img_byte_arr, Bucket="prueba-bucket-machine", Key = (nombre + ".jpg"))