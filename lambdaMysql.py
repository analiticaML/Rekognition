'''
Función lambda: lambdaMysql

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
import mysql.connector
from datetime import datetime as dt

#Variables globales estáticas
#Cliente representando servicio de aws
s3_client=boto3.client('s3')
rekognition_client=boto3.client('rekognition', 'us-east-1')
lambda_client = boto3.client('lambda')

#Se define función principal de ejecución: Función Handler del evento de S3
def lambda_handler(event, context):
    # TODO implement

    #Se conecta con el servicio de Cloudwatch
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    nombre = event["nombre"]
    date = event["date"]
    time = event["time"]
    similarity = event["similarity"]
    confidence = event["confidence"]

    #Se llama la función para establecer conexión con la base de datos en mysql   
    conexion = mysql_start_connection("analitica","analitica123" , 
    "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", "reconocimiento", 3306)

    #Se llama la función para actualizar un item de la base de datos
    updateItemDB(nombre,date,time,conexion,similarity,confidence)

    #Se llama la función para obtener diferencia de tiempos entre capturas para una misma persona
    delta = timeDifference(conexion,time,nombre,date)

    #Si la diferencia entre capturas es mayor a cinco segundo se crea un registro
    if delta > 5:

        #Se llama función para crear un item en la tabla de registro de la base de datos de mysql
        createRegister(conexion,nombre,str(date),str(time))

    #Se llama función para desplegar en pantalla una tabla de la base de datos de mysql
    #mysql_display(conexion)

    #Se llama función para terminar la conexión
    mysql_end_connection(conexion)


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
def timeDifference(conexion, endTime,nombre,fechaActual):
    
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
        fecha = records[numberRow-1][0]
        startTime = records[numberRow-1][1]

        if fecha != fechaActual:
            return 6

        #Se convierte la hora de string a formate datetime
        t1 = dt.strptime(startTime[0], "%H:%M:%S")
        t2 = dt.strptime(endTime, "%H:%M:%S")

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