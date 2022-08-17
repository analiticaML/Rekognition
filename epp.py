from distutils.command.clean import clean
from itertools import count
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

    dictionary, num, image,listaepp= detect_ppe(bucket, key)

    print('\n Resultado final: \n')
    print(dictionary)
    print('número de personas: ' + '{0:.0f}'.format(num) + '\n')

    print('Llamada de crop')
    listaimg=cropFace(image,dictionary,num,key)

    count=0

    for image in listaimg:

        #Se busca si la persona esta en una collection
        #Se recibe un booleano donde true indica que si pertence y false que no pertenece
        faceids=search_faces(image)

        # #Se actualiza atributo (Status) en la base de datos en DynamoDB
        # #de acuerdo al resultado de la función search_faces para cada una de las coincidencias en la collection
        # for faceid in faceids:
        updateItemDB(faceids[0],listaepp[count])

        count=count+1


  
def detect_ppe(bucket,key):

    fill_green='#00d400'
    fill_red='#ff0000'
    fill_yellow='#ffff00'
    line_width=3

    #open image and get image data from stream.
    # Load image from S3 bucket
    s3_connection = boto3.resource('s3')
    s3_object = s3_connection.Object(bucket,key)
    s3_response = s3_object.get()

    

    stream = io.BytesIO(s3_response['Body'].read())

    print('Hasta aquí se ejecura sin PIL')
    image=Image.open(stream)

    imgWidth, imgHeight = image.size  

    client=boto3.client('rekognition')

    response = client.detect_protective_equipment(Image={'S3Object':{'Bucket':bucket,'Name':key}},SummarizationAttributes={
        'MinConfidence': 80,
        'RequiredEquipmentTypes': [
            'FACE_COVER','HAND_COVER','HEAD_COVER'
        ]
    })


    print('Detected PPE for people in image ' + key) 
    print('\nDetected people\n---------------')   

    dict={}


    count=1

    for person in response['Persons']:

        print('---#---------#---------#------')
        print('Person ID: ' + str(person['Id']))

        box = person['BoundingBox']

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


        print ('Body Parts\n----------')
        body_parts = person['BodyParts']

        listaEPP=[]

        if len(body_parts) == 0:
                print ('No body parts found')
        else:
            for body_part in body_parts:
                print('\t'+ body_part['Name'] + '\n\t\tConfidence: ' + str(body_part['Confidence']))
                print('\n\t\tDetected PPE\n\t\t------------')
                ppe_items = body_part['EquipmentDetections']
                if len(ppe_items) ==0:
                    print ('\t\tNo PPE detected on ' + body_part['Name'])
                else:    
                    for ppe_item in ppe_items:
                        print('\t\t' + ppe_item['Type'] + '\n\t\t\tConfidence: ' + str(ppe_item['Confidence'])) 
                        print('\t\tCovers body part: ' + str(ppe_item['CoversBodyPart']['Value']) + '\n\t\t\tConfidence: ' + str(ppe_item['CoversBodyPart']['Confidence']))
       
                        
                        listaEPP.append({[ppe_item['Type']]:ppe_item['CoversBodyPart']['Value']})

                        
       
                        # print('\t\tBounding Box:')
                        # print ('\t\t\tTop: ' + str(ppe_item['BoundingBox']['Top']))
                        # print ('\t\t\tLeft: ' + str(ppe_item['BoundingBox']['Left']))
                        # print ('\t\t\tWidth: ' +  str(ppe_item['BoundingBox']['Width']))
                        # print ('\t\t\tHeight: ' +  str(ppe_item['BoundingBox']['Height']))
                        # print ('\t\t\tConfidence: ' + str(ppe_item['Confidence']))

            

    print('Person ID Summary\n----------------')

    display_summary('With required equipment',response['Summary']['PersonsWithRequiredEquipment'] )
    display_summary('Without required equipment',response['Summary']['PersonsWithoutRequiredEquipment'] )
    display_summary('Indeterminate',response['Summary']['PersonsIndeterminate'] )

    numPersonas=len(response['Persons'])

    return dict, numPersonas, image, listaEPP

#Display summary information for supplied summary.
def display_summary(summary_type, summary):
    print (summary_type + '\n\tIDs: ',end='')
    if (len(summary)==0):
        print('None')
    else:
        for num, id in enumerate(summary, start=0):
            if num==len(summary)-1:
                print (id)
            else:
                print (str(id) + ', ' , end='')


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


        # imagecrop.save(img_byte_arr, format="JPEG")

        # img_str = base64.b64encode(img_byte_arr.getvalue())

        imagecrop.save(img_byte_arr, format='JPEG')

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
        

def search_faces(image):

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition', 'us-east-1')


    collectionId = 'collection-epp' #Nombre de la colección
    threshold = 80 #Umbral para similaridad entre caras
    maxFaces = 100 #Número máximo de caras que quiere reconocer de la colección
    
    #Función del SDK (boto3) de python para buscar coincidencia con caras de una colección



    print('problemas para buscar en la collection')

    response=client.search_faces_by_image(CollectionId=collectionId,
                                    Image={'Bytes': image},
                                    FaceMatchThreshold=threshold,
                                     MaxFaces=maxFaces)


    faceMatches = response['FaceMatches']


    print('funcionó hasta la collection')
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
def updateItemDB(imgId,date,time,itemsepp):

    #Cliente representando servicio dynamodb
    client = boto3.client('dynamodb')

    try:

        #Se actualiza la base de datos cambiando el atributo status con el valor booleano True
        response = client.update_item(
            TableName='dataset-collection-epp',
            Key={
                'faceId': {
                    'S': imgId
                }
            },
            AttributeUpdates={
                'Fecha':{
                    'Value':{
                        'S': date
                    },
                    'Action':'PUT'
                },
                'Hora':{
                    'Value':{
                        'S':time
                    },
                    'Action':'PUT'
                },
                'Casco':{
                    'Value':{
                        'BOOL': itemsepp['HEAD_COVER']
                    }
                },
                'Guantes':{
                    'Value':{
                        'BOOL': itemsepp['HAND_COVER']
                    }
                },
                'TapaBocas':{
                    'Value':{
                        'BOOL': itemsepp['FACE_COVER']
                    }
                },

            },


        )   

        print('Actualizó DB')

    except Exception as msg:

        print(f"Oops, no se pudo actualizar el item: {msg}")