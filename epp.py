'''
Función lambda: epp

    Función disparada con evento de S3 (subir imagen a un bucket asociado a la función) 
    Se toma del evento el nombre del bucket y de la imagen subida. 
    Detecta las caras de las personas en una imagen y 
    Realiza reconocimiento de una o varias persona de acuerdo a la coincidencia con las imagenes en una colección.
    Se actualiza los atributos de una tabla en dynamodb con booleano indicando si la persona lleva correctamente
    el equipo de protección.
    (Los equipos de protección a identificar son casco, guantes y tapabocas)

'''

#Se importan librerías
import logging
import boto3
import urllib
import io
from PIL import Image
import datetime


#Se define función principal de ejecución: Función Handler del evento de S3
def lambda_handler(event, context):
    # TODO implement

    #Se conecta con el servicio de Cloudwatch
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    #Con el evento de S3 (Subir imagen al bucket) se recibe el nombre del bucket y el nombre de la imagen que se subió
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    #Función para detectar caras y equipos de protección:
    #Se obtiene de la función un diccionario con los limites del bounding box de cada cara detectada
    #El número de caras detectadas, la imagen tipo PIL a analizar y una lista de diccionarios con 
    #los elementos de protección econtrados para cada cara
    dictionary, num, image,listaepp= detect_ppe(bucket, key)

    #Función para recortar las caras de las personas en una imagen:
    #Se obtiene de la función una lista con las imagenes de las caras de cada una de las personas en la imagen
    listaimg=cropFace(image,dictionary,num,key)

    #Función para obtener la fecha y la horas de la modificación de un objeto en un bucket 
    date,time=objectDate(bucket,key)

    #Contador para actualizar el diccionario correspondiente a cada cara
    count=0

    for image in listaimg:

        #Se busca si la persona esta en una collection
        #Retorna una lista con el ExternalImageId de las coincidencias en la colección
        faceids=search_faces(image)

        # Si se encuentra una persona de la base de datos
        # Se actualizan atributos de la base de datos en DynamoDB:
        # FaceId, fecha, hora y equipos de protección(Booleano indicando si se usa correctamente el equipo
        # Aplica para el caso de casco, guantes y tapabocas
        if faceids:
            updateItemDB(faceids[0],date,time,listaepp[count])

        count=count+1


#Función para obtener la fecha y la horas de la modificación de un objeto en un bucket 
#Recibe como parámetro el nombre del bucket y de la imagen
def objectDate(bucket,key):

    #Cliente representando servicio de s3
    client=boto3.client('s3')

    #Función del SDK (boto3) de python para obtener información de un objeto de un bucket en s3
    response = client.head_object(Bucket=bucket, Key=key)
    datetime_value = str(response["LastModified"])

    #Se elimina la zona horaria (UTC)
    time=datetime_value[0:len(datetime_value)-6]

    #Se convierte string en formato datetime y se actualiza la hora de acuerdo a la zona horaria
    utc_datetime = datetime.datetime.utcnow()
    utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
    UTC_OFFSET_TIMEDELTA = 5
    local_datetime = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    result_utc_datetime = local_datetime - datetime.timedelta(hours=UTC_OFFSET_TIMEDELTA)
    result_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
    #Se convierte nuevamente a string
    result_utc_datetime=str(result_utc_datetime)

    fecha=result_utc_datetime[0:len(result_utc_datetime)-9]
    hora=result_utc_datetime[11:len(result_utc_datetime)]

    #Retorna strings con la fecha y la hora de la última modificación del objeto en s3
    return fecha,hora

#Función para detectar las personas presentes en una imagen y los elementos de protección usados.
#(casco, guantes y tapabocas)
#La función recibe como parámetros el nombre del bucket y de la imagen.  
def detect_ppe(bucket,key):

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

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition')

    #Función del SDK (boto3) de python para detectar equipos de protección personal de rekognition
    response = client.detect_protective_equipment(Image={'S3Object':{'Bucket':bucket,'Name':key}},SummarizationAttributes={
        'MinConfidence': 80,
        'RequiredEquipmentTypes': [
            'FACE_COVER','HAND_COVER','HEAD_COVER'
        ]
    })


    print('Detected PPE for people in image ' + key)  

    #Diccionario que almacena para cada una de las personas los límites del bounding box 
    dict={}

    #Contador para actualizar el número de personas
    count=1

    #Lista de diccionarios con los elementos de protección econtrados para cada persona 
    listaEPP=[]

    #Para cada persona detectada en la imagen
    for person in response['Persons']:

        print('---#---------#---------#------')
        print('Person ID: ' + str(person['Id']))

        # Calcula los límites del bounding box para cada una de las personas detectadas
        box = person['BoundingBox']
        left = imgWidth * box['Left']
        top = imgHeight * box['Top']
        width = imgWidth * box['Width']
        height = imgHeight * box['Height']

        #Se agrega al diccionario los límites del bounding box correspondientes a cada persona
        dict['cara'+'{0:.0f}'.format(count)]=[left,top,left+width,top+height]
                
        count=count+1

        body_parts = person['BodyParts']
        
        #Diccionario que almacena un booleano indicando si se hace un correcto uso del elemento de protección
        #Para casco, guantes y tapabocas        
        dictepp = {}
        dictepp={'FACE_COVER':False,'HAND_COVER':False,'HEAD_COVER':False}

        if len(body_parts) == 0:
                print ('No body parts found')
        else:
            for body_part in body_parts:
                print ('Parte del cuerpo:\n')
                print('\t'+ body_part['Name'] + '\n\t\tConfidence: ' + str(body_part['Confidence']))
                print('\nEPP encontrado\n')
                ppe_items = body_part['EquipmentDetections']
                if len(ppe_items) ==0:
                    print ('\t\tNo se encontró epp en: ' + body_part['Name'])
                else:    
                    for ppe_item in ppe_items:
                        print('\t\t' + ppe_item['Type'] + '\n\t\t\tConfidence: ' + str(ppe_item['Confidence'])) 
                        print('\t\tCovers body part: ' + str(ppe_item['CoversBodyPart']['Value']) + '\n\t\t\tConfidence: ' + str(ppe_item['CoversBodyPart']['Confidence']))

                        #Se actualiza en el diccionario el booleano del elemento encontrado
                        dictepp[ppe_item['Type']]=ppe_item['CoversBodyPart']['Value']

        #Se agrega a la lista los diccionarios con los equipos de protección para cada persona                
        listaEPP.append(dictepp)

    #Número de personas detectadas
    numPersonas=len(response['Persons'])

    #Retorna diccionario con los límites del bounding box para cada persona, el número de personas detectadas
    #la imagen tipo PIL y la lista de diccionarios con los elementos de protección econtrados para cada persona
    return dict, numPersonas, image, listaEPP

#Función para recortar de la iamgen las personas detectadas.
#La función recibe como parámetros la imagen tipo PIL a analizar, diccionario con los límites del bounding box
#correspondiente a cada persona, el número de personas en la imagen y el nombre de la imagen.
def cropFace(image,dict,numCaras,key):

    #Se elimina del nombre de la imagen la extension (ie. jpg)
    key=key[0:len(key)-4]

    #Lista que almacena las imagenes de cada una de las personas detectadas en la imagen
    #con base en el bounding box
    listaimg=[]

    #Se realiza el recorte para cada una de las personas en la imagen
    for i in range(1,numCaras+1):
        
        #Se toman los límites del bounding box de una cara
        dimensiones=dict['cara'+"{0:.0f}".format(i)]
        dim=(int(dimensiones[0]),int(dimensiones[1]),int(dimensiones[2]),int(dimensiones[3]))
        
        #Se rocarte la imagen de acuerdo a las dimensiones del bounding box
        imagecrop=image.crop(dim)

        #Se convierte la imagen recortada tipo PIL a una imagen en bytes con extensión JPEG
        img_byte_arr = io.BytesIO()
        imagecrop.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        #Se agrega a la lista la imagen recortada en bytes
        listaimg.append(img_byte_arr)

    #Retorna una lista con las imagenes de cada una de las personas en la imagen
    return listaimg
        
#Se define función para buscar caras en una imagen y relacionar con una colección
#Recibe como parámetros la imagen de cada una de las caras presentes en la imagen
def search_faces(image):

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition', 'us-east-1')


    collectionId = 'collection-epp' #Nombre de la colección
    threshold = 80 #Umbral para similaridad entre caras
    maxFaces = 100 #Número máximo de caras que quiere reconocer de la colección
    
    try:
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
            if match['Similarity'] > 80.:
                listface.append( match['Face']['FaceId'])
    except:
        listface = []

    #Retorna lista con el ExternalImageId de las coincidencias en la colección
    return listface


#Se define función para actualizar un item de la base de datos de dynamodb
#Recibe como parámetros el ExternalImageId, la fecha, la hora del item a actualizar
#y el diccionario con los epp
def updateItemDB(imgId,date,time,itemsepp):

    #Cliente representando servicio dynamodb
    client = boto3.client('dynamodb')

    try:

        #Se actualiza la base de datos cambiando los atributos fecha, hora y valor booleano de cada uno de los epp
        #casco, guantes y tapabocas
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
                    },
                    'Action':'PUT'
                },
                'Guantes':{
                    'Value':{
                        'BOOL': itemsepp['HAND_COVER']
                    },
                    'Action':'PUT'
                },
                'TapaBocas':{
                    'Value':{
                        'BOOL': itemsepp['FACE_COVER']
                    },
                    'Action':'PUT'
                },

            },


        )   

    except Exception as msg:

        print(f"Oops, no se pudo actualizar el item: {msg}")