'''
Función lambda: facerek 

    Función disparada con evento de S3 (subir imagen a un bucket asociado a la función) 
    Se toma del evento: el nombre del bucket y de la imagen subida. 
    Realiza reconocimiento de una persona de acuerdo a la coincidencia con las imagenes en una colección.
    Se actualiza el atributo status de una tabla en dynamodb con booleano indicando el resultado de la coincidencia.
    (True: La persona se encuentra en la colección, False: La persona no se encuentra en la colección).

'''


#Se importan librerias
from distutils.command.clean import clean
import json
import os
import logging
import boto3
import urllib

#Se define función principal de ejecución
def lambda_handler(event):

    #Se conecta con el servicio de Cloudwatch
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    #Con el evento de S3 (Subir imagen al bucket) se recibe el nombre del bucket y el nombre de la imagen que se subió 
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    #Se chequea si la variable bucket no está vacía
    if bucket != "":

        logger.info('Corriendo \n')

        #Se busca si la persona esta en una collection
        #Se recibe un booleano donde true indica que si pertence y false que no pertenece
        faceids=search_faces(bucket,key)

        #Se actualiza atributo (Status) en la base de datos en DynamoDB
        #de acuerdo al resultado de la función search_faces para cada una de las coincidencias en la collection
        for faceid in faceids:
            updateItemDB(faceid)

        return {
            'statusCode': 200,
            'body': json.dumps('Reconocimiento Exitoso')
        }

    else: 
        print('No se encontró la ubicación de la imagen en S3')


#Se define función para listar los objetos de un bucket 
#Recibe el nombre del bucket a anlizar
#Retorna lista con los nombres de la imagenes
def listBucketObjects(bucketName):

    #Recurso de S3
    s3 = boto3.resource('s3')

    #Cliente representando un servicio de S3
    client = boto3.client('s3')
    
    #Lista con nombres de los objetos del bucket
    keys=[] 

    #Se toman los nombres de los objetos del bucket
    try:
        response = client.list_objects(
            Bucket=bucketName,
            MaxKeys=123,
        )

        for key in response['Contents']:
            keys.append(key['Key'])
        
        return keys

    except Exception as msg:
        print(f"Oops, error en list_objects: {msg}")

            

#Se define función para buscar caras en una imagen y relacionar con una collection
#Recibe el nombre del bucket y de la imagen a analizar 
#Retorna lista con los FaceId de las coincidencias en la colección
def search_faces(bucket,key):

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition', 'us-east-1')


    collectionId = 'collection-rekognition' #Nombre de la colección
    threshold = 80 #Umbral para similaridad entre caras
    maxFaces = 100 #Número máximo de caras que quiere reconocer de la colección

    print('Nombre del bucket: ' + bucket)
    print('Nombre de la imagen: ' + key)
    
    #Función del SDK (boto3) de python para buscar coincidencia con caras de una colección
    response=client.search_faces_by_image(CollectionId=collectionId,
                                    Image={'S3Object':{'Bucket':bucket,'Name':key}},
                                    FaceMatchThreshold=threshold,
                                     MaxFaces=maxFaces)


    faceMatches = response['FaceMatches']

    #Lista con el FaceId de la cara de coincidencia en la colección
    listface=[]


    for match in faceMatches:
        print('FaceId:' + match['Face']['FaceId'])
        print('ImageId:' + match['Face']['ImageId'])
        print('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
        print('Confidence: ' + str(match['Face']['Confidence']))

        #Si la similaridad entre coincidencia es mayor a 80% se agrega el FaceId a la lista listface
        if match['Similarity'] > 80.0:
            listface.append( match['Face']['FaceId'])

    return listface

#Se define función para eliminar los tags de todos los objetos de un bucket
#Recibe el nombre del bucket y una lista con los nombres de los objetos del bucket
def deleteTagFromObject(bucketName, keys): 

    try:
        #Cliente representando servicio de S3
        client = boto3.client('s3')
    
        #Con la función delete_object_tagging de boto3 se borran las etiquetas de la imagenes
        for key in keys:
            response = client.delete_object_tagging(
                Bucket=bucketName,
                Key=key,
          )

    except: 
        
        print('Error al borrar las etiquetas')
        

#Se define función para actualizar un item de la base de datos de dynamodb
#Recibe el FaceId del item a actualizar
def updateItemDB(FaceId):

    #Cliente representando servicio dynamodb
    client = boto3.client('dynamodb')

    try:

        #Se actualiza la base de datos cambiando el atributo status con el valor booleano True
        response = client.update_item(
            TableName='dataset-collection-images',
            Key={
                'FaceID': {
                    'S': FaceId
                }
            },
            AttributeUpdates={
                'status': {
                    'Value': {
                        'BOOL': True
                    },
                    'Action': 'PUT'
                }
            },


        )   

        print('Actualizó DB')

    except Exception as msg:

        print(f"Oops, no se pudo actualizar el item: {msg}")