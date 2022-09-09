'''
Función lambda: lambdaFace

    Función disparada con evento de S3 (subir imagen a un bucket asociado a la función) 
    Se toma del evento el nombre del bucket y de la imagen subida. 
    Realiza reconocimiento de una o varias persona de acuerdo a la coincidencia con las imagenes en una colección.
    Se actualiza el atributo status de una tabla en dynamodb con booleano indicando el resultado de la coincidencia.
    (True: La persona en la colección fue reconocida, False: La persona en la colección no fue reconocida).

'''


#Se importan librerías
from distutils.command.clean import clean
from email.mime import image
import logging
import boto3
import urllib
import io
from PIL import Image
import datetime
import mysql.connector
import math


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

    print('número de personas: ' + '{0:.0f}'.format(num) + '\n')

    #Función para recortar las caras de las personas en una imagen:
    #Se obtiene de la función una lista con las imagenes de las caras de cada una de las personas en la imagen
    listaimg=cropFace(image,dictionary,num,key)

    #Función para obtener la fecha y la horas de la modificación de un objeto en un bucket 
    date,time=objectDate(bucket,key)


    for image in listaimg:

        #Se busca si la persona esta en una collection
        #Retorna una lista con el ExternalImageId de las coincidencias en la colección
        imgsid, similarity, confidence = search_faces(image)

        # Si se encuentra una persona de la base de datos
        #Se actualizan los atributos status, Fecha y Hora en la base de datos en DynamoDB de acuerdo 
        #al resultado de la función search_faces para cada una de las coincidencias en la collection
        # El valor del atributo Satus es un booleano: 
        # true indica que reconoció a una persona de la colección y false que no la reconoció                 
        if imgsid:   
            conexion = mysql_start_connection("analitica","analitica123" , 
    "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", "reconocimiento", 3306)

            updateItemDB(imgsid[0],str(date),str(time),conexion,similarity[0],confidence[0])

            createRegister(conexion,imgsid[0],str(date),str(time))

            mysql_display(conexion)

            mysql_end_connection(conexion)

            #Si se identificó a la persona en la colección se elimina la imagen del bucket
            deleteObject(bucket,key)


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

        #Se muestra detalle de la cara de la persona detectada: rango de edad
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low']) 
            + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')



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
        left = imgWidth* box['Left']
        top =   imgHeight * box['Top']
        width =  imgWidth * box['Width']
        height =  imgHeight * box['Height']

        #Se agrega al diccionario los límites del bounding box correspondientes a cada cara
        dict['cara'+'{0:.0f}'.format(count)]=[left,top,left+width,top+height]
                
        #Se actualiza contador       
        count=count+1

    #Número de caras detectadas en la imagen
    numCaras=len(response['FaceDetails'])

    #Si no se encuentra ninguna cara en la imagen, se borra la imagen del bucket.
    if numCaras==0:
        deleteObject(bucket,key)
  
    #Retorna diccionario con los límites del bounding box para cada cara, el número de caras detectadas
    #y la imagen tipo PIL
    return dict, numCaras, image


#Función para recortar las caras de las personas detectadas en una imagen.
#La función recibe como parámetros la imagen tipo PIL a analizar, diccionario con los límites del bounding box
#correspondiente a la cara de cada persona, el número de caras en la imagen y el nombre de la imagen.
def cropFace(image,dict,numCaras,key):

    #Se elimina del nombre de la imagen la extension (ie. jpg)
    key=key[0:len(key)-4]

    #Lista que almacena las imagenes de la cara de cada una de las personas detectadas en la imagen
    #con base en el bounding box
    listaimg=[]

    #Se realiza el recorte para cada una de las caras en la imagen
    for i in range(1,numCaras+1):
        
        #Se toman los límites del bounding box de una cara
        dimensiones=dict['cara'+"{0:.0f}".format(i)]
        dim=(int(dimensiones[0]),int(dimensiones[1]),int(dimensiones[2]),int(dimensiones[3]))

        #Se rocarte la imagen de acuerdo a las dimensiones del bounding box
        imagecrop=image.crop(dim)

        #Se convierte la imagen recortada tipo PIL a una imagen en bytes con extensión JPEG
        img_byte_arr = io.BytesIO()
        imagecrop.save(img_byte_arr, format="JPEG")
        img_byte_arr = img_byte_arr.getvalue()
        
        prueba = boto3.client("s3")
        prueba.put_object(Body = img_byte_arr, Key = key +str(i)+".jpg", Bucket ="bucket-prueba-lambda")

        #Se agrega a la lista la imagen recortada en bytes
        listaimg.append(img_byte_arr)

    #Retorna una lista con las imagenes de la cara de cada una de las personas en la imagen
    return listaimg

#Se define función para buscar caras en una imagen y relacionar con una colección
#Recibe como parámetros la imagen de cada una de las caras presentes en la imagen
def search_faces(image):

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition', 'us-east-1')


    collectionId = 'collection-rekognition' #Nombre de la colección
    threshold = 80 #Umbral para similaridad entre caras
    maxFaces = 100 #Número máximo de caras que quiere reconocer de la colección
    
    listface = []
    similarity = []
    confidence = []
    
    try:
        #Función del SDK (boto3) de python para buscar coincidencia con caras de una colección
        response=client.search_faces_by_image(CollectionId=collectionId,
                                        Image={'Bytes': image},
                                        FaceMatchThreshold=threshold,
                                         MaxFaces=maxFaces)
        
        
        faceMatches = response['FaceMatches']
        
            #Lista con el ExternaImageId de la cara en la colección
            
        
        for match in faceMatches:
            print('--------------------\n')
            print('ImageId:' + match['Face']['ImageId'])
            print('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
            print('Confidence: ' + str(match['Face']['Confidence']))
        
            #Si la similaridad entre coincidencia es mayor a 80% se agrega el ExternalImageId a la lista listface
            if match['Similarity'] > 80.0:
                listface.append(match['Face']['ExternalImageId'])
                similarity.append(match['Similarity'])
                confidence.append(match['Face']['Confidence'])
                    
        
            #Retorna lista con el ExternalImageId de las coincidencias en la colección
        return listface, similarity, confidence
        
    except:
        return listface, similarity, confidence


#Se define función para actualizar un item de la base de datos de dynamodb
#Recibe como parámetros el ExternalImageId, la fecha y la hora del item a actualizar
def updateItemDB(imgId,date,time,conexion,similarity,confidence):
    similarity = round(similarity,2)
    confidence = round(confidence,2)

    print(type(imgId))
    print(imgId)
    # actualizar datos en la tabla
    cursorUpdate = conexion.cursor()
    
    consultaUpdate = "UPDATE control set fecha= '{0}',hora ='{1}',estado='{2}',similaridad='{3}',confianza='{4}' where nombre= '{5}';".format(date,time,1,similarity,confidence,imgId)

    
    # Mock values for face ID, image ID, and confidence - replace them with actual values from your collection results
    #try:
    cursorUpdate.execute(consultaUpdate)
        

    #except Exception as msg:

    #    print(f"Oops, no se pudo actualizar el item: {msg}")

    conexion.commit()
    cursorUpdate.close()


def mysql_start_connection(user, password, host, database, port):
    try:
        conexion = mysql.connector.connect(user = user, password=password, host = host, database = database, port =port)
        print("conexion exitosa")
    except:
        print("falla en la conexion ")

    return conexion




def mysql_display(conexion):
    cursor = conexion.cursor()
    cursor.execute("Select * from control;")

    personas = cursor.fetchall()
    for i in personas:
        print(i)

    cursor.close()

def mysql_end_connection(conexion):    
    conexion.close()

#Función para eliminar objetos del bucket
#La función recibe como parámetros el nombre del bucket y de la imagen
def deleteObject(bucket, key):

    #Cliente representando servicio dynamodb
    s3 = boto3.resource('s3')
    s3.Object(bucket, key).delete()

def createRegister(conexion,imgsid,date,time):
                    # insertar datos en la tabla
                    cursorInsert = conexion.cursor()

                    nombre = imgsid
                    fecha = date
                    hora = time

                    consulta = "INSERT  INTO  registro(nombre, fecha, hora) VALUES('{0}', '{1}', '{2}');".format(nombre,
                     fecha, hora)

                    
                    cursorInsert.execute(consulta)

                    conexion.commit()
                    cursorInsert.close()

