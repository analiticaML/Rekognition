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

    cedula = event["cedula"]
    date = event["date"]
    time = event["time"]
    similarity = event["similarity"]
    confidence = event["confidence"]
    

    #Se llama la función para establecer conexión con la base de datos en mysql   
    conexion = mysql_start_connection("analitica","analitica123" , 
    "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", "reconocimiento", 3306)

    listaPersonas = mysql_members(conexion)

    for person in listaPersonas:
        
        print(person[0])
        
        if int(person[0])==int(cedula):

            nombre = person[1]
            apellido = person[2]
            
            break
    #Se llama la función para actualizar un item de la base de datos
    updateItemDB(cedula,date,time,conexion,similarity,confidence)

    #Se llama la función para obtener diferencia de tiempos entre capturas para una misma persona
    delta = timeDifference(conexion,time,cedula,date)

    #Si la diferencia entre capturas es mayor a cinco segundo se crea un registro
    if delta > 5:

        #Se llama función para crear un item en la tabla de registro de la base de datos de mysql
        createRegister(conexion,nombre,str(date),str(time),apellido,cedula)

    #Se llama función para desplegar en pantalla una tabla de la base de datos de mysql
    #mysql_display(conexion)

    #Se llama función para terminar la conexión
    mysql_end_connection(conexion)


    #Se define función para actualizar un item de la base de datos de mysql
#Recibe como parámetros el ExternalImageId, la fecha, la hora, la similaridad y la confianza del item a actualizar
def updateItemDB(cedula,date,time,conexion,similarity,confidence):
    similarity = round(similarity,2)
    confidence = round(confidence,2)

    #Establecer conexión con mysql
    cursorUpdate = conexion.cursor()
    
    #query para actualización de la tabla de control para las columnas
    #fecha, hora, estado = 1, similaridad y confianza de la persona identificada, 
    #indicando que la persona a sido identificada.
    consultaUpdate = "UPDATE control set fecha= '{0}',hora ='{1}',estado='{2}',similaridad='{3}',confianza='{4}' where cedula= '{5}';".format(date,time,1,similarity,confidence,cedula)

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
def createRegister(conexion,nombre,date,time,apellido,cedula):

                    cursorInsert = conexion.cursor()

                    nombre = nombre #nombre de la persona identificada en la collection
                    apellido = apellido
                    fecha = date #Fecha de la última actualización de la imagen
                    hora = time #hora de la última actualización de la 

                    #Query para inserta item con nombre, fecha y hora en la tabla registro.
                    consulta = "INSERT  INTO  registro(cedula,nombre,apellido, fecha, hora) VALUES('{0}', '{1}', '{2}','{3}','{4}');".format(cedula,nombre,
                    apellido, fecha, hora)

                    #Realizar insert
                    cursorInsert.execute(consulta)

                    conexion.commit()
                    cursorInsert.close()

#Función  para obtener la diferencia de tiempo entre dos captura de una misma persona
#La función recibe como parámetros la conexión con la base de datos de mysql, el tiempo de la captura actual
#y el nombre de la persona detectada en la captura
def timeDifference(conexion, endTime,cedula,fechaActual):
    
    try:
        #Se selecciona de la tabla de registro los registros de la persona seleccionada
        sql_select_Query = "select fecha,hora from registro where cedula = '{0}'".format(cedula)
    
        cursor = conexion.cursor()
        cursor.execute(sql_select_Query)
    
        #Se guardan todos los registros en una lista
        records = cursor.fetchall()
    
        print(records)
    
        #Número de registro de la persona
        numberRow = cursor.rowcount
     
        #Se obtiene la hora del  último registro de la persona
        fecha = records[numberRow-1][0]
        startTime = records[numberRow-1][1]
    
        if fecha != fechaActual:
            return 6
    
        #Se convierte la hora de string a formate datetime
        t1 = dt.strptime(startTime, "%H:%M:%S")
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


def mysql_members(conexion):
    lista =[]
    cursor = conexion.cursor()

    cursor.execute("Select * from control;")

    personas = cursor.fetchall()
    for i in personas:
        lista.append(i)
    cursor.close()
    
    print("obtuvo la lista de control")

    return(lista)