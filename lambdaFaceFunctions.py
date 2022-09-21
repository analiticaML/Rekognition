#Se importan librerías
import boto3
import io
from PIL import Image
import datetime 
import mysql.connector
import json
import base64
from PIL import ExifTags

s3_client=boto3.client('s3')
rekognition_client=boto3.client('rekognition', 'us-east-1')
lambda_client = boto3.client('lambda')


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


#Función para terminar la conexión con la base de datos de mysql
#Recibe la conexión inicial con la base de datos de mysql
def mysql_end_connection(conexion):    
    conexion.close()


#Función para obtener la fecha y la horas de la modificación de un objeto en un bucket 
#Recibe como parámetro el nombre del bucket y de la imagen
def objectDate(bucket,key):

    #Función del SDK (boto3) de python para obtener información de un objeto de un bucket en s3
    response = s3_client.head_object(Bucket=bucket, Key=key)
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

    
     #Se carga imagen de un bucket S3
    s3_connection = boto3.resource('s3')
    s3_object = s3_connection.Object(bucket,key)
    s3_response = s3_object.get()

    
    #Se convierte el objeto de S3 en una imagen en bytes
    stream = io.BytesIO(s3_response['Body'].read())

    #Se convierte imagen a una imagen tipo PIL
    image=Image.open(stream)

    #Se llama la función de cambio de ortientación a la imagen
    image = setOrientationImage(image)
    
    #Función del SDK (boto3) de python para detectar caras en una colección
    response = rekognition_client.detect_faces(Image={'S3Object': {'Bucket': bucket, 'Name': key}},
        Attributes=['ALL'])

    print('Detected faces for ' + key)   

    for faceDetail in response['FaceDetails']:

        #Se muestra detalle de la cara de la persona detectada: rango de edad
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low']) 
            + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')


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


    collectionId = 'collection-telemetrik' #Nombre de la colección
    threshold = 80 #Umbral para similaridad entre caras
    maxFaces = 100 #Número máximo de caras que quiere reconocer de la colección
    
    listface = [] 
    similarity = []
    confidence = []
    
    try:
        #Función del SDK (boto3) de python para buscar coincidencia con caras de una colección
        response=rekognition_client.search_faces_by_image(CollectionId=collectionId,
                                        Image={'Bytes': image},
                                        FaceMatchThreshold=threshold,
                                         MaxFaces=maxFaces)
                
        faceMatches = response['FaceMatches']     
    
        
    
        if not faceMatches:
    
            conexion = mysql_start_connection("analitica","analitica123" , 
            "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", "reconocimiento", 3306)
    
            imagen = base64.b64encode(image)
            #Establecer conexión con mysql
            cursorUpdate = conexion.cursor()
    
            #query para actualización de la tabla de unknown
            query = """ UPDATE unknown set imagen = %s where persona = %s"""
    
            try:
                #Se ejecuta la actualización
                cursorUpdate.execute(query, ( imagen,"PersonaDesconocida")) #Se realiza la actualización
        
            except Exception as msg:
    
                print(f"Oops, no se pudo actualizar el item: {msg}")
    
            #Se termina la actualización
            conexion.commit()
            cursorUpdate.close()
            
    
            mysql_end_connection(conexion)
    
    
            lambda_payload = {"nombre":"nombre"}
            lambda_payload = json.dumps(lambda_payload)
            lambda_client.invoke(FunctionName='lambdaSNS', 
            InvocationType='Event',
            Payload=lambda_payload)
    
        
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

#Función para eliminar objetos del bucket
#La función recibe como parámetros el nombre del bucket y de la imagen
def deleteObject(bucket, key):

    #Cliente representando servicio de s3
    s3 = boto3.resource('s3')
    s3.Object(bucket, key).delete()


#Función para corregir la orientación de la imagen
#Recibe la imagen en bytes
def setOrientationImage(image):
    
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
        return imagen
        