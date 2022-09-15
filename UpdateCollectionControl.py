import boto3
import os
from botocore.exceptions import ClientError
import logging
import mysql.connector 
import pandas as pd


#from mysql import mysql_start_connection, create_initial_collection_mysql_db, mysql_display,mysql_end_connection


#la funcion  add_faces_to_collection añade una cara a la collection
#recibe como parametro la imagen, el nombre de la imagen, la collection_id 
#donde se desea agregar la cara y la region de aws

def read_csv(path_csv):
    lista = []
    df = pd.read_excel (path_csv)
    for row in df.itertuples():
        tulple = (row.Cedula,row.Nombre,row.Apellido,row.Cargo)
        lista.append(tulple)
    return lista

def add_faces_to_collection(collection_id, region,path,control):

    fpath = os.listdir(path)
    # se crea una dos ciclos for para recorrer el path del local y cada directorio en el, donde se encuentran las imagenes
    for folder in fpath:
        path_folders =  path +'\\' + folder
        fpath_folders = os.listdir(path_folders)
        if folder not in control:
            for images in fpath_folders:

                file_image = r''+path + '\\'+ folder + '\\'+ images
                cedula = folder
            
                # Se llama al cliente de rekognition en la region indicada 
                client = boto3.client('rekognition', region_name=region)

                #Abrimos la imagen 
                imageTarget = open(file_image, 'rb')
                
                # con la funcion index_faces agregamos la imagen en bytes a la collection indicada
                client.index_faces(CollectionId=collection_id,
                    Image={'Bytes': imageTarget.read()},
                    ExternalImageId=cedula,
                    MaxFaces=1,
                    QualityFilter="AUTO")
        print("Se agrego correctamente "+folder + " en la collection")
                
                #Creamos un diccionario con el FaceId de la persona indexada y valor de path de imagen
           
    


# la funcion list_faces_in_collection retorna una lista con la información de cada
# cara en la collection
#  
def list_faces_in_collection(collection_id):
    lista = []
    maxResults=1
    tokens=True

    # se invoca el cliente de amazon rekognition
    client=boto3.client('rekognition')
    
    # la funcion list_faces retorna una lista de todos los json de las caras en la collection
    response=client.list_faces(CollectionId=collection_id,
                               MaxResults=maxResults)

    # creamos un ciclo para recorrer la lista de los json 
    while tokens:

        list1 = []
        faces=response['Faces']

        # A cada face en la collection, extraeremos los datos de FaceId, ImageId
        # ExternalImageId y los agregamos a una lista 
        for face in faces:
            list1.append(face['FaceId'])
            list1.append(face['ImageId'])
            list1.append(face['ExternalImageId'])
            lista.append(list1)
            list1.clear

        if 'NextToken' in response:
            nextToken=response['NextToken']

            response=client.list_faces(CollectionId=collection_id,
                                       NextToken=nextToken,MaxResults=maxResults)
        else:
            tokens=False
    return lista
# se recorre el path del local y los directorios donde estan las imagenes en dos ciclos 
# para subir imagen por imagen al bucket de s3
def put_folder_s3(region,path,bucket,control):
    fpath = os.listdir(path)
    # se crea una dos ciclos for para recorrer el path del local y cada directorio en el, donde se encuentran las imagenes
    for folder in fpath:
        path_folders =  path +'\\' + folder
        fpath_folders = os.listdir(path_folders)
        if folder not in control:
            for images in fpath_folders:
                file_image = r''+path + '\\'+ folder + '\\'+ images
                key_name = folder+'/'+ images
                # se llama al cliente de s3 
                s3 = boto3.client('s3', region_name=region)
                # Upload the file
                try:
                    #La función upload_file actualiza y sube la imagen al bucket
                    s3.upload_file(file_image, bucket, key_name)
                except ClientError as e:
                    logging.error(e)

def list_Objects_from_Bucket(bucketName):
    # se invoca el servicio de amazon s3
    client = boto3.client('s3')

    keys = []

    # la funcion list_objects retorna un json con todos los objetos en el bucket
    response = client.list_objects(
                Bucket=bucketName,
                MaxKeys=123,
            )
    # recorremos cada uno de estos paths y los agregamos a una lista
    for key in response['Contents']:
        keys.append(key['Key'])

    print("Se agregaron los paths de los objetos a una lista")
    return keys

def mysql_start_connection(user, password, host, database, port):
    
    try:
        conexion = mysql.connector.connect(user = user, password=password, host = host, database = database, port =port)
        print("conexion exitosa")

        return conexion

    except:
        print("falla en la conexion ")

def mysql_display(conexion):
    cursor = conexion.cursor()
    cursor.execute("Select * from collection;")

    personas = cursor.fetchall()
    for i in personas:
        print(i)

    cursor.close()

def mysql_end_connection(conexion):    
    conexion.close()

def insert_data_mysql_collection(conexion,item,file_url,lista_csv):
                    print("Se van a insertar los datos")
                    # insertar datos en la tabla
                    cursorInsert = conexion.cursor()
                    faceid = item[0]
                    print(faceid)
                    cedula = item[2]
                    print(cedula)
                    url = file_url
                    print(url)
                    for person in lista_csv:
                        if person[0]==cedula:
                            consulta = "INSERT  INTO  collection(faceId, nombre,apellido, bucket) VALUES('{0}', '{1}', '{2}','{3}');".format(faceid,person[1],person[2],url)
                            cursorInsert.execute(consulta)
                            break

                    conexion.commit()
                    cursorInsert.close()

def insert_data_mysql_control(conexion,item,lista_csv):
                    print("Se van a insertar los datos a control")
                    # insertar datos en la tabla
                    cursorInsert = conexion.cursor()
                    cedula = item[2]
                    print(cedula)
                    for person in lista_csv:
                        if person[0]==cedula:
                            consulta = "INSERT  INTO  control(cedula, nombre, apellido, cargo, fecha, hora,estado,similaridad, confianza) VALUES('{0}', '{1}', '{2}','{3}','{4}','{5}','{6}','{7}','{8}');".format(cedula,person[1],person[2],person[3],"0000-00-00","00:00:00",0,0.00,0.00)
                            cursorInsert.execute(consulta)
                            break

                    conexion.commit()
                    cursorInsert.close()

def create_initial_collection_mysql_db(lista,keys,conexion,bucketName,control,lista_csv):

    # la lista creada en la descripcion de las caras en la collection y los paths en la lista keys se recorren
    # y se emparejan los faceId de cada cara con la imagen en el bucket
    for item in lista:
        if item[2] not in control:
            for key in keys:
                #sabemos que en ambas lista coincide el nombre de la carpeta en el bucket con el ExternalImageId de lista
                list = key.split('/')
                if list[0]==item[2]:
                    key_name = key
                    # Get URL of file
                    file_url = "https://s3.amazonaws.com/{}/{}".format(bucketName, key_name)
                    # Mock values for face ID, image ID, and confidence - replace them with actual values from your collection results
                    try:
                        insert_data_mysql_control(conexion,item,lista_csv)
                    except:
                        print("ya esta en control")
                    try:
                        insert_data_mysql_collection(conexion,item,file_url,lista_csv)
                        print("Se agrego exitosamente los datos de la collection a RDS collection table")
                    except:
                        print("El usuario ya se encuentra en la tabla")
def mysql_members(conexion):
    lista =[]
    cursor = conexion.cursor()

    cursor.execute("Select * from control;")

    personas = cursor.fetchall()
    for i in personas:
        lista.append(i[0])
    cursor.close()

    return(lista)

def main():
    #En este caso agregamos las imagenes desde el path del local 
    path =r'C:\Users\user\Desktop\collection'
    path_csv = r'C:\Users\user\Desktop\Despliegue rekognition\personas.xlsx'
    collection_id='collection-rekognition'
    region = "us-east-1"
    bucket = "fotos-collection-rekognition"

    conexion = mysql_start_connection("analitica","analitica123" , 
    "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", "reconocimiento", 3306)

    lista_csv = read_csv(path_csv)

    lista_control = mysql_members(conexion)

    add_faces_to_collection( collection_id, region,path,lista_control)

    lista_collection = list_faces_in_collection(collection_id)

    put_folder_s3(region,path,bucket,lista_control)

    keys = list_Objects_from_Bucket(bucket)

    create_initial_collection_mysql_db(lista_collection,keys,conexion,bucket,lista_control,lista_csv)

    mysql_display(conexion)

    mysql_end_connection(conexion)
    
if __name__ == "__main__":
    main()
