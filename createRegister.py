#Función para insertar item a la tabla de registros
def createRegister(conexion,imgsid,date,time):

                    cursorInsert = conexion.cursor()

                    nombre = imgsid #nombre de la persona (External Image Id)
                    fecha = date #Fecha
                    hora = time #Hora

                    #query para insertar en tabla
                    consulta = "INSERT  INTO  registro(nombre, fecha, hora) VALUES('{0}', '{1}', '{2}');".format(nombre,
                     fecha, hora)
                 
                    cursorInsert.execute(consulta)

                    conexion.commit()
                    cursorInsert.close()

#Se llama la función createRegister
#createRegister(imgsid[0],date,time)