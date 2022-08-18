'''
Función lambda: detectFace

    Función disparada con evento de S3 (subir imagen a un bucket asociado a la función) 
    Se toma del evento el nombre del bucket y de la imagen subida. 
    Detecta las caras de las personas en una imagen y 
    se guarda en un bucket las imagenes de cada una de las caras

'''

#Se importan librerías
from distutils.command.clean import clean
import logging
import boto3
import urllib
import io
from PIL import Image


#Se define función principal de ejecución: Función Handler del evento de S3
def lambda_handler(event, context):
    # TODO implement

    #Se conecta con el servicio de Cloudwatch
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    #Con el evento de S3 (Subir imagen al bucket) se recibe el nombre del bucket y el nombre de la imagen que se subió
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    #Función para detectar caras:
    #Se obtiene de la función detec_faces un diccionario con los limites del bounding box de cada cara detectada
    #El número de caras detectadas y la imagen tipo PIL a analizar
    dictionary, num, image= detect_faces(bucket,key)

    #Función para recortar las caras de las personas en una imagen y guardar en un bucket de s3
    cropFace(image,dictionary,num,key)



#Función para detectar las caras de las personas presentes en una imagen.
#La función recibe como parámetros el nombre del bucket y de la imagen.
def detect_faces(bucket,key):

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition', 'us-east-1')

    #Función del SDK (boto3) de python para detectar caras en una colección
    response = client.detect_faces(Image={'S3Object': {'Bucket': bucket, 'Name': key}},
        Attributes=['ALL'])


    print('Detected faces for ' + key)   

    for faceDetail in response['FaceDetails']:
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low']) 
            + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')

        # Detaller adicionales de las caras
        # print("Gender: " + str(faceDetail['Gender']))
        # print("Smile: " + str(faceDetail['Smile']))
        # print("Eyeglasses: " + str(faceDetail['Eyeglasses']))
        # print("Emotions: " + str(faceDetail['Emotions'][0]))


    # Se carga imagen de un bucket S3
    s3_connection = boto3.resource('s3')
    s3_object = s3_connection.Object(bucket,key)
    s3_response = s3_object.get()

    #Se convierte el objeto de S3 en una imagen en bytes
    stream = io.BytesIO(s3_response['Body'].read())

    #Se convierte imagen a una imagen tipo PIL
    image=Image.open(stream)

    #Tamaño de la imagen en pixeles
    imgWidth, imgHeight = image.size  

    #Diccionario que almacena para cada una de las caras los límites del bounding box           
    dict={}

    #Contador para actualizar el número de  la cara
    count=1

    # Calcula los límites del bounding box para cada una de las caras detectadas     
    for faceDetail in response['FaceDetails']:
    
        box = faceDetail['BoundingBox']
        left = imgWidth * box['Left']
        top = imgHeight * box['Top']
        width = imgWidth * box['Width']
        height = imgHeight * box['Height']

        #Se agrega al diccionario los límites del bounding box correspondientes a cada cara
        dict['cara'+'{0:.0f}'.format(count)]=[left,top,left+width,top+height]
                
        count=count+1

    #Número de caras detectadas en la imagen
    numCaras=len(response['FaceDetails'])

    #Retorna diccionario con los límites del bounding box para cada cara, el número de caras detectadas
    #y la imagen tipo PIL
    return dict, numCaras, image

#Función para recortar las caras de las personas detectadas en una imagen.
#La función recibe como parámetros la imagen tipo PIL a analizar, diccionario con los límites del bounding box
#correspondiente a la cara de cada persona, el número de caras en la imagen y el nombre de la imagen.
def cropFace(image,dict,numCaras,key):

    #Cliente representando servicio de s3
    client=boto3.client('s3')

    #Se elimina del nombre de la imagen la extension (ie. jpg)
    key=key[0:len(key)-4]

     #Se realiza el recorte para cada una de las caras en la imagen
    for i in range(1,numCaras+1):
        
        #Se actualiza el nombre de la imagen recortada de acuerdo al número de la cara
        nombre=key+"{0:.0f}".format(i)

        #Se toman los límites del bounding box de una cara
        dimensiones=dict['cara'+"{0:.0f}".format(i)]
        dim=(int(dimensiones[0]),int(dimensiones[1]),int(dimensiones[2]),int(dimensiones[3]))

        #Se rocarte la imagen de acuerdo a las dimensiones del bounding box
        imagecrop=image.crop(dim)

        #Se convierte la imagen recortada tipo PIL a una imagen en bytes con extensión JPEG 
        img_byte_arr = io.BytesIO()
        imagecrop.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        #Se sube imagen al bucket
        client.put_object(
                            Body=img_byte_arr,
                            Bucket='prueba-rekognition-analitica',
                            Key=nombre+'.jpeg',
                        )



