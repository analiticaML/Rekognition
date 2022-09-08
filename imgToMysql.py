import mysql.connector
import base64
import matplotlib.pyplot as plt

def convertToBinaryData(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        im_b64 = file.read()
        # plt.imshow(im_b64)
        # plt.show()
        
    return im_b64


def insertBLOB( name,fecha, hora, estado, similaridad,confianza, photo):
    print("Inserting BLOB into python_employee table")
    try:
        empPicture = convertToBinaryData(photo)
        connection = mysql.connector.connect(host='analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com',
                                             database='reconocimiento',
                                             user='analitica',
                                             password='analitica123',
                                             port ="3306")
        print("conexion exitosa")

        cursor = connection.cursor()
        sql_insert_blob_query = "INSERT INTO control(nombre, fecha, hora,estado, similaridad, confianza, imagen) VALUES('{0}', '{1}', '{2}','{3}', '{4}', '{5}','{6}');".format(name,
                     fecha, hora, estado, similaridad, confianza, base64.b64encode(empPicture))


        # Convert data into tuple format
        result = cursor.execute(sql_insert_blob_query)
        connection.commit()
        print("Image and file inserted successfully as a BLOB into python_employee table", result)

    except mysql.connector.Error as error:
        print("Failed inserting BLOB data into MySQL table {}".format(error))

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

insertBLOB("Selene","2022-12-34","09:13:13",1,98.12, 99.10,r"C:\Users\user\Desktop\collection\Emanuel\Emanuel.png")
