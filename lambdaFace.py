'''
Función lambda: lambdaFace

    Función disparada con evento de S3 (subir imagen a un bucket asociado a la función) 
    Se toma del evento el nombre del bucket y de la imagen subida. 
    Realiza reconocimiento de una o varias persona de acuerdo a la coincidencia con las imagenes en una colección.
    Se actualiza el atributo status, fecha y hora de una tabla en mysql con valor binario indicando el resultado de la coincidencia.
    (1: La persona en la colección fue reconocida, 0: La persona en la colección no fue reconocida).

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
import time
from datetime import datetime as dt


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

            #Se llama la función para establecer conexión con la base de datos en mysql   
            conexion = mysql_start_connection("analitica","analitica123" , 
            "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", "reconocimiento", 3306)

            #Se llama la función para actualizar un item de la base de datos
            updateItemDB(imgsid[0],str(date),str(time),conexion,similarity[0],confidence[0])

            #Se llama la función para obtener diferencia de tiempos entre capturas para una misma persona
            delta = timeDifference(conexion,time,imgsid[0])
            print(delta)

            #Si la diferencia entre capturas es mayor a cinco segundo se crea un registro
            if delta > 5:

                #Se llama función para crear un item en la tabla de registro de la base de datos de mysql
                createRegister(conexion,imgsid[0],str(date),str(time))

            #Se llama función para desplegar en pantalla una tabla de la base de datos de mysql
            #mysql_display(conexion)

            #Se llama función para terminar la conexión
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
    #String con fecha,hora e identificador de zona horaria de la última modificación del objeto en s3
    datetime_value = str(response["LastModified"]) 

    #Se elimina del string el identificador de la zona horaria (UTC)
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

    #Se selecciona la fecha del string completo 
    fecha=result_utc_datetime[0:len(result_utc_datetime)-9]
    #Se selecciona la hora del string completo
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


    #Se carga imagen de un bucket S3
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

        #Se recorta la imagen de acuerdo a las dimensiones del bounding box
        imagecrop=image.crop(dim)

        #Se convierte la imagen recortada tipo PIL a una imagen en bytes con extensión JPEG
        img_byte_arr = io.BytesIO()
        imagecrop.save(img_byte_arr, format="JPEG")
        img_byte_arr = img_byte_arr.getvalue()
        
        #Se agrega a la lista la imagen recortada en bytes
        listaimg.append(img_byte_arr)

    #Retorna una lista con las imagenes de la cara de cada una de las personas en la imagen
    return listaimg

#Se define función para buscar caras en una imagen y relacionar con una colección
#Recibe como parámetros la imagen de cada una de las caras presentes en la imagen
def search_faces(image):

    #Cliente representando servicio de rekognition
    client=boto3.client('rekognition', 'us-east-1')


    collectionId = 'collection-telemetrik' #Nombre de la colección
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
        
        for match in faceMatches:
            print('--------------------\n')
            print('ImageId:' + match['Face']['ImageId'])
            print('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
            print('Confidence: ' + str(match['Face']['Confidence']))
        
            #Si la similaridad entre coincidencia es mayor a 80% se agrega el ExternalImageId a la lista listface,
            #se agrega a la lista similarity la similaridad de la coincidencia y a la lista  confidence la 
            #confianza con la que se hizo la coincidencia
            if match['Similarity'] > 80.0:
                listface.append(match['Face']['ExternalImageId'])
                similarity.append(match['Similarity'])
                confidence.append(match['Face']['Confidence'])
                    
        
        #Retorna lista con el ExternalImageId de las coincidencias en la colección
        #lista con las similaridades y con las confianzas de las coincidencias para cada imagen de la colección
        return listface, similarity, confidence
        
    except:
        #Retorna listas vacías
        return listface, similarity, confidence


#Se define función para actualizar un item de la base de datos de mysql
#Recibe como parámetros el ExternalImageId, la fecha, la hora, la similaridad y la confianza del item a actualizar
def updateItemDB(imgId,date,time,conexion,similarity,confidence):
    similarity = round(similarity,2)
    confidence = round(confidence,2)

    #Establecer conexión con mysql
    cursorUpdate = conexion.cursor()
    
    #query para actualización de la tabla de control para las columnas
    #fecha, hora, estado = 1, similaridad y confianza de la persona identificada, 
    #indicando que la persona a sido identificada.
    consultaUpdate = "UPDATE control set fecha= '{0}',hora ='{1}',estado='{2}',similaridad='{3}',confianza='{4}' where nombre= '{5}';".format(date,time,1,similarity,confidence,imgId)

    try:
        #Se ejecuta la actualización
        cursorUpdate.execute(consultaUpdate) #Se realiza la actualización
        
    except Exception as msg:

        print(f"Oops, no se pudo actualizar el item: {msg}")

    #Se termina la actualización
    conexion.commit()
    cursorUpdate.close()

#Función para conectar con una base de datos de mysql
#Recibe como parámetros el usuario, la contraseña, el host, el nombre de la base de datos
#y el puerto de la base de datos de mysql
def mysql_start_connection(user, password, host, database, port):
    try:
        #Se establece la conexión ingresando los parámetros de la base de datos de mysql
        conexion = mysql.connector.connect(user = user, password=password, host = host, database = database, port =port)
        print("conexion exitosa")
    except:
        print("falla en la conexion ")
    #Retorna la conexión establecida con la base de datos
    return conexion



#Función para desplegar la tabla en terminal
#Recibe la conexión inicial con la base de datos de mysql
def mysql_display(conexion):

    #Se seleccionan todos los items de la tabla
    cursor = conexion.cursor()
    cursor.execute("Select * from control;")

    #Se crea una lista con las filas de la tabla
    personas = cursor.fetchall()
    for i in personas:
        print(i)

    cursor.close()

#Función para terminar la conexión con la base de datos de mysql
#Recibe la conexión inicial con la base de datos de mysql
def mysql_end_connection(conexion):    
    conexion.close()

#Función para eliminar objetos del bucket
#La función recibe como parámetros el nombre del bucket y de la imagen
def deleteObject(bucket, key):

    #Cliente representando servicio de s3
    s3 = boto3.resource('s3')
    s3.Object(bucket, key).delete()

#Función para crear un nuevo item en la tabla de registro en mysql
def createRegister(conexion,imgsid,date,time):

                    cursorInsert = conexion.cursor()

                    nombre = imgsid #nombre de la persona identificada en la collection
                    fecha = date #Fecha de la última actualización de la imagen
                    hora = time #hora de la última actualización de la 

                    #Query para inserta item con nombre, fecha y hora en la tabla registro.
                    consulta = "INSERT  INTO  registro(nombre, fecha, hora) VALUES('{0}', '{1}', '{2}');".format(nombre,
                     fecha, hora)

                    #Realizar insert
                    cursorInsert.execute(consulta)

                    conexion.commit()
                    cursorInsert.close()

#Función  para obtener la diferencia de tiempo entre dos captura de una misma persona
#La función recibe como parámetros la conexión con la base de datos de mysql, el tiempo de la captura actual
#y el nombre de la persona detectada en la captura
def timeDifference(conexion, endTime,nombre):
    
    try:
        #Se selecciona de la tabla de registro los registros de la persona seleccionada
        sql_select_Query = "select hora from registro where nombre = '{0}'".format(nombre)

        cursor = conexion.cursor()
        cursor.execute(sql_select_Query)

        #Se guardan todos los registros en una lista
        records = cursor.fetchall()

        #Número de registro de la persona
        numberRow = cursor.rowcount
     
        #Se obtiene la hora del  último registro de la persona
        startTime = records[numberRow-1]

        #Se convierte la hora de string a formate datetime
        t1 = dt.strptime(startTime[0], "%H:%M:%S")
        t2 = dt.strptime(endTime, "%H:%M:%S")
        print(t1)
        print(t2)

        #Se obtiene la diferencia de los dos tiempos
        delta = t2 - t1
        
        cursor.close()

        dif = delta.total_seconds() #Se pasa la diferencia a segundos

        #La función retorna la diferencia de los dos tiempos en segundos
        return dif

    except:
        #Se retorna un valor de 6 para que si la persona no tiene aún ningún resgistro en la tabla registros
        #Se agrege el registro como registro inicial
        return 6 
