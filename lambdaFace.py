from distutils.command.clean import clean
from email.mime import image
import json
import os
import logging
import boto3
import urllib
import io
from PIL import Image, ImageDraw, ExifTags, ImageColor
import base64



def lambda_handler(event, context):
    # TODO implement

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    print('Llamada de crop')

    dictionary, num, image= detect_faces(bucket,key)

    print('\n Resultado final: \n')
    print(dictionary)
    print('número de personas: ' + '{0:.0f}'.format(num) + '\n')

    print('Llamada de crop')
    listaimg=cropFace(image,dictionary,num,key)

    for image in listaimg:

        #Se busca si la persona esta en una collection
        #Se recibe un booleano donde true indica que si pertence y false que no pertenece
        faceids=search_faces(image)

        #Se actualiza atributo (Status) en la base de datos en DynamoDB
        #de acuerdo al resultado de la función search_faces para cada una de las coincidencias en la collection
        for faceid in faceids:
            updateItemDB(faceid)



   

def detect_faces(bucket,key):

    client=boto3.client('rekognition', 'us-east-1')


    print(bucket)
    print(key)
    
    response = client.detect_faces(Image={'S3Object': {'Bucket': bucket, 'Name': key}},
        Attributes=['ALL'])

    print('Detected faces for ' + key)   

    for faceDetail in response['FaceDetails']:
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low']) 
            + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')

        # print('Here are the other attributes:')
        # print(json.dumps(faceDetail, indent=4, sort_keys=True))

        # Access predictions for individual face details and print them
        print("Gender: " + str(faceDetail['Gender']))
        # print("Smile: " + str(faceDetail['Smile']))
        # print("Eyeglasses: " + str(faceDetail['Eyeglasses']))
        # print("Emotions: " + str(faceDetail['Emotions'][0]))


    # Load image from S3 bucket
    s3_connection = boto3.resource('s3')
    s3_object = s3_connection.Object(bucket,key)
    s3_response = s3_object.get()

    

    stream = io.BytesIO(s3_response['Body'].read())

    print('Hasta aquí se ejecura sin PIL')
    image=Image.open(stream)

    imgWidth, imgHeight = image.size  

    print('Se va a imprimir imagen')

    # draw = ImageDraw.Draw(image)  
                
    dict={}


    count=1

    # calculate and display bounding boxes for each detected face       
    # print('Bounding boxes for ' + key)    
    for faceDetail in response['FaceDetails']:
    

        
        box = faceDetail['BoundingBox']
        left = imgWidth * box['Left']
        top = imgHeight * box['Top']
        width = imgWidth * box['Width']
        height = imgHeight * box['Height']

        dict['cara'+'{0:.0f}'.format(count)]=[left,top,left+width,top+height]
                
        count=count+1


        print('Left: ' + '{0:.0f}'.format(left))
        print('Top: ' + '{0:.0f}'.format(top))
        print('Face Width: ' + "{0:.0f}".format(width))
        print('Face Height: ' + "{0:.0f}".format(height))

        points = (
            (left,top),
            (left + width, top),
            (left + width, top + height),
            (left , top + height),
            (left, top)

        )
        # draw.line(points, fill='#00d400', width=2)

    print('número de caras')
    numCaras=len(response['FaceDetails'])


    # image.show()

    return dict, numCaras, image


def cropFace(image,dict,numCaras,key):

    client=boto3.client('s3')

    key=key[0:len(key)-4]

    listaimg=[]

    for i in range(1,numCaras+1):
        
        nombre=key+"{0:.0f}".format(i)

        dimensiones=dict['cara'+"{0:.0f}".format(i)]

        dim=(int(dimensiones[0]),int(dimensiones[1]),int(dimensiones[2]),int(dimensiones[3]))
        imagecrop=image.crop(dim)


        img_byte_arr = io.BytesIO()


        imagecrop.save(img_byte_arr, format="JPEG")

        # img_str = base64.b64encode(img_byte_arr.getvalue())

        # imagecrop.save(img_byte_arr, format='JPEG')

        image_file_size = img_byte_arr.tell()

        print('Tamaño (bytes)')
        print(image_file_size)

        img_byte_arr = img_byte_arr.getvalue()

        listaimg.append(img_byte_arr)

    #     print(nombre+'.jpeg')

    #     # client.upload_fileobj(img_str.read(), 'prueba-rekognition-analitica', nombre+'.jpeg')

    #     client.put_object(
    # Body=img_byte_arr,
    # Bucket='prueba-rekognition-analitica',
    # Key=nombre+'.jpeg',

# )

    print(len(listaimg))

    return listaimg

#Se define función para buscar caras en una imagen y relacionar con una collection
#Recibe el nombre del bucket y de la imagen a analizar 
#Retorna lista con los FaceId de las coincidencias en la colección
def search_faces(image):

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition', 'us-east-1')


    collectionId = 'CollectionAnalitica' #Nombre de la colección
    threshold = 80 #Umbral para similaridad entre caras
    maxFaces = 100 #Número máximo de caras que quiere reconocer de la colección
    
    #Función del SDK (boto3) de python para buscar coincidencia con caras de una colección


    response=client.search_faces_by_image(CollectionId=collectionId,
                                    Image={'Bytes': image},
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