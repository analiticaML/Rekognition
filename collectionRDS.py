import boto3
from decimal import Decimal
import json
import mysql.connector

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

def create_initial_collection_mysql_db(lista,keys,conexion,bucketName):

    # la lista creada en la descripcion de las caras en la collection y los paths en la lista keys se recorren
    # y se emparejan los faceId de cada cara con la imagen en el bucket
    for item in lista:
        for key in keys:
            #sabemos que en ambas lista coincide el nombre de la carpeta en el bucket con el ExternalImageId de lista
            list = key.split('/')
            if list[0]==item[2]:
        
                key_name = key
                region = "us-east-1"
                # Get URL of file
                file_url = "https://s3.amazonaws.com/{}/{}".format(bucketName, key_name)

                def insert_data_mysql(conexion):
                    print("Se van a insertar los datos")
                    # insertar datos en la tabla
                    cursorInsert = conexion.cursor()
                    faceid = item[0]
                    print(faceid)
                    nombre = item[2]
                    print(nombre)
                    url = file_url
                    print(url)

                    consulta = "INSERT  INTO  collection(faceId, nombre, bucket) VALUES('{0}', '{1}', '{2}');".format(faceid,nombre,url)
                    cursorInsert.execute(consulta)

                    conexion.commit()
                    cursorInsert.close()

                # Mock values for face ID, image ID, and confidence - replace them with actual values from your collection results
                try:
                    insert_data_mysql(conexion)

                    print("Se agrego exitosamente los datos de la collection a RDS collection table")
                except:
                    print("El usuario ya se encuentra en la tabla")
                
    

# la funcion list_faces_in_collection retorna una lista con la información de cada
# cara en la collection
#  
def list_faces_in_collection(collection_id):

    lista=[]
    maxResults=1
    faces_count=0
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

            faces_count+=1
        if 'NextToken' in response:
            nextToken=response['NextToken']

            response=client.list_faces(CollectionId=collection_id,
                                       NextToken=nextToken,MaxResults=maxResults)
        else:
            tokens=False
    return lista, faces_count   

def list_Objects_from_Bucket(bucketName):
    # se invoca el servicio de amazon s3
    client = boto3.client('s3')

    # nombre del bucket
    bucketName = "prueba-bucket-machine"

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


def main():

    #Nombre del bucket donde se encuentran las imagenes
    bucketName = "prueba-bucket-machine"
    collection_id = 'collection-rekognition'


    lista,faces_count = list_faces_in_collection(collection_id)
    print(lista)
    keys = list_Objects_from_Bucket(bucketName)
    print(keys)

    print("faces count: " + str(faces_count))

    conexion = mysql_start_connection("analitica","analitica123" , 
    "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", "reconocimiento", 3306)

    print("Se incia la creación de la base de datos")
    create_initial_collection_mysql_db(lista,keys,conexion,bucketName)

    print("se creó la base de datos")
    mysql_display(conexion)

    mysql_end_connection(conexion)
    

if __name__ == "__main__":
    main()