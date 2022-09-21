'''
Función lambda: lambdaFace

    Función disparada con evento de S3 (subir imagen a un bucket asociado a la función) 
    Se toma del evento el nombre del bucket y de la imagen subida. 
    Realiza reconocimiento de una o varias persona de acuerdo a la coincidencia con las imagenes en una colección.
    Se actualiza el atributo status, fecha y hora de una tabla en mysql con valor binario indicando el resultado de la coincidencia.
    (1: La persona en la colección fue reconocida, 0: La persona en la colección no fue reconocida).

'''


#Se importan librerías
import logging
import boto3
import urllib
import json
from lambdaFaceFunctions import *
#Variables globales estáticas
#Cliente representando servicio de aws
lambda_client = boto3.client('lambda')

#Se define función principal de ejecución: Función Handler del evento de S3
def lambda_handler(event, context):
    # TODO implement

    #Se conecta con el servicio de Cloudwatch
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    #Con el evento de S3 (Subir imagen al bucket) se recibe el nombre del bucket y el nombre de la imagen que se subió
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    #Función para obtener la fecha y la horas de la modificación de un objeto en un bucket 
    date,time=objectDate(bucket,key)

    #Función para detectar caras:
    #Se obtiene de la función detec_faces un diccionario con los limites del bounding box de cada cara detectada
    #El número de caras detectadas y la imagen tipo PIL a analizar
    dictionary, num, image= detect_faces(bucket,key)

    #Número de personas identificadas en la imagen
    print('número de personas: ' + '{0:.0f}'.format(num) + '\n')

    #Función para recortar las caras de las personas en una imagen:
    #Se obtiene de la función una lista con las imagenes de las caras de cada una de las personas en la imagen
    listaimg=cropFace(image,dictionary,num,key)


    #Se recorren todas las caras de las personas identificadas en la captura.
    for image in listaimg:

        #Se busca si la persona esta en una collection
        #Retorna una lista con el ExternalImageId de las coincidencias en la colección,
        #lista con las similaridades y lista con las confianzas de las coincidencias. 
        imgsid, similarity, confidence = search_faces(image)

        #Si se encuentra una coincidencia con la colección
        #Se actualizan los atributos status, Fecha y Hora en la base de datos de mysql de acuerdo 
        #al resultado de la función search_faces para cada una de las coincidencias en la collection.
        #El valor del atributo Satus es un valor binario: 
        #1 indica que reconoció a una persona de la colección y 0 que no la reconoció                 
        if imgsid:

            lambda_payload = {"cedula":imgsid[0],"date":str(date),"time":str(time),
            "similarity":similarity[0],"confidence":confidence[0]}
            lambda_payload = json.dumps(lambda_payload)
            lambda_client.invoke(FunctionName='lambdaMysql', 
            InvocationType='Event',
            Payload=lambda_payload)

            #Si se identificó a la persona en la colección se elimina la imagen del bucket
            deleteObject(bucket,key)

