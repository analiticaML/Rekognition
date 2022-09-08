from inspect import formatargspec
import mysql.connector
import base64
from PIL import Image
import io


img = Image.open(r'C:\Users\user\Desktop\collection\Emanuel\Emanuel.jpg')
img = img.tobytes()

# img_bytes = io.BytesIO()
# img.save(img_bytes, format='JPEG')
# # img_bytes=img_bytes.getvalue()
# # print(img_bytes)

try:
    conexion = mysql.connector.connect(user = "analitica", password="analitica123", host = "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", database = "reconocimiento", port ="3306")
    print("conexion exitosa")
except:
    print("falla en la conexion ")

#Actualizar datos 
cursorUpdate = conexion.cursor()
consultaUpdate = consultaUpdate = "UPDATE control set imagen= '{0}' where nombre= '{1}';".format(img,"Emanuel")   
cursorUpdate.execute(consultaUpdate)
conexion.commit()
cursorUpdate.close()

print("--------------------------------------------------------------------------")

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


conexion.close()