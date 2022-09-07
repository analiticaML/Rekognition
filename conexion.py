import mysql.connector

try:
    conexion = mysql.connector.connect(user = "analitica", password="analitica123", host = "analitica-ml.cwklrzbxbt5x.us-east-1.rds.amazonaws.com", database = "reconocimiento", port ="3306")
    print("conexion exitosa")
except:
    print("falla en la conexion ")

#Actualizar datos 
cursorUpdate = conexion.cursor()
consultaUpdate = consultaUpdate = "UPDATE control set fecha= '{0}',hora ='{1}',estado='{2}',similaridad='{3}',confianza='{4}' where nombre= '{5}';".format(str("2020-12-05"),str("09:54:12"),1,float(12.323),float(89.2323),"Emanuel")   
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

createRegister(conexion,"Emanuel","2020-08-12","05:23:32")

conexion.close()