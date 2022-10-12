#Se importan librerías
import boto3
import io
from PIL import Image
import numpy as np
import cv2
from facenet_pytorch import MTCNN
import datetime
import json
import base64
import requests

#Variables globales estáticas
#Cliente representando servicio de aws
sqs_client = boto3.client('sqs')
s3_client=boto3.client('s3')

#Se define función principal de ejecución: Función Handler del evento de S3
def main():
    while(True):
        response = sqs_client.receive_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/853702706419/kinesis_sqs',
            AttributeNames=[
                'All'
            ],
    
            MaxNumberOfMessages=1
        )

        try:
            body = response["Messages"][0]["Body"]
            json_object = json.loads(body)

            print(json_object)

            bucket =  json_object["Records"][0]["s3"]["bucket"]["name"]
            key    =  json_object["Records"][0]["s3"]["object"]["key"]

            #Se carga imagen de un bucket S3
            s3_connection = boto3.resource('s3')
            s3_object = s3_connection.Object(bucket,key)
            s3_response = s3_object.get()

            
            #Se convierte el objeto de S3 en una imagen en bytes
            stream = io.BytesIO(s3_response['Body'].read())

            #Se convierte imagen a una imagen tipo PIL
            image=Image.open(stream)

            #Se llama la función de cambio de ortientación a la imagen
            #image = setOrientationImage(image)


            #Se guarda la fecha de hoy y se convierte a string 
            UTC_OFFSET_TIMEDELTA = 5
            now = datetime.datetime.utcnow()
            now = now - datetime.timedelta(hours=UTC_OFFSET_TIMEDELTA)
            date=str(now.year)+str(now.month)+str(now.day)+str(now.hour)+str(now.minute)+str(now.second)+str(now.microsecond)

            #objetos= persondetector.detectObjects(path)
            caras = facedetector(image)                  
                    
            if caras.size != 0:
                print("Se detectó una cara")

                img_byte_arr = io.BytesIO()
            
                image.save(img_byte_arr, format="JPEG")
                img_byte_arr = img_byte_arr.getvalue()

                image = base64.b64encode(img_byte_arr).decode('utf-8')
            
                post("https://u3biagxped.execute-api.us-east-1.amazonaws.com/default/lambdaAPI", image, date, 1)
                #s3_client.put_object(Body=img_byte_arr, Bucket="bucket-filtered-captures", Key = (date + ".jpg"))



            print("################### FINAL DEL LOOP :)")
            # sqs_client.delete_message(
            #     'https://sqs.us-east-1.amazonaws.com/853702706419/kinesis_sqs',
            #     response["Messages"]["ReceiptHandle"]
            # )

        except:
            print("No message")    


   
#Función para corregir la orientación de la imagen
#Recibe la imagen en bytes
'''def setOrientationImage(image):
    
    imagen = image

    #Se cambia el nombre clave de la orientación de los metadatos de la imagen a Orientation
    for orientation in ExifTags.TAGS.keys():
        if ExifTags.TAGS[orientation]=='Orientation':
            break
        
    
    try:
        #Se toman los metadatos de la imagen
        exif = imagen._getexif()
    
        #Se hacen la rotaciones necesarias para que la imagen quede orientada 0°
        if exif[orientation] == 3:
            imagen=imagen.rotate(180, expand=True)
        elif exif[orientation] == 6:
            imagen=imagen.rotate(270, expand=True)
        elif exif[orientation] == 8:
            imagen=imagen.rotate(90, expand=True)
    
        #Se retorna la imagen rotada
        return imagen
    
    except:
        return imagen'''


def facedetector(Image):

        imagen = cv2.cvtColor(np.array(Image), cv2.COLOR_BGR2RGB)


        # Detector MTCNN
        mtcnn = MTCNN(
                    select_largest = True,
                    min_face_size  = 15,
                    thresholds     = [0.6, 0.7, 0.7],
                    post_process   = False,
                    image_size     = 160
                )
      

        # Detección de bounding box y landmarks
        boxes, probs, landmarks = mtcnn.detect(imagen, landmarks=True)
    
        
        try:
            for box, landmark in zip(boxes, landmarks):
            
                xy  = (box[0], box[1])
                width  = box[2] - box[0]
                height = box[3] - box[1]
    
            return boxes

        except:
            return np.array([])

#método para realizar post
def post(url, bytes_image, date, timeout):

    body = {
        'account': "analitica@telemetrik.com.co",
        'capture': bytes_image,
        'date': date,
        'producer': "camara1Telemetrik",
        'secret': "analitica"
    }
    response = requests.post(url, data=json.dumps(body), timeout=timeout)
    print(' [x] Request respose', response.status_code)

main()