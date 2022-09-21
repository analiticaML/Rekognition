import os
import pika
import json

mqHost = "localhost"

def main():

    _, _, files = next(os.walk("C:/Users/user/Documents/prueba"))
    file_count = len(files)

    #Se obtiene la imagen actual en escala de grises
    previousNoItems = file_count


    #Ciclo infinito para la captura de cuadros
    while (True):
        #Nuevo cuadro
        _, _, files = next(os.walk("C:/Users/user/Documents/prueba"))
        file_count = len(files)
        newNoItems = file_count 


        #Se llama a método para detectar movimiento
        if (previousNoItems==newNoItems):
            print("nueva imagen!!")

            frame = files[file_count-1]

            path = "C:/Users/user/Documents/prueba" + "/" + frame 
            data = {}
            data["path"] = path
            
            #Se envía mensaje a la cola del servicio de mensajería
            publish(json.dumps(data), "captured-image-queue", mqHost)
        
            #Se actualiza el cuadro anterior con el cuadro nuevo
            previousNoItems = newNoItems


#método para públicar
def publish(message, queue, mqHost):

    #Se establece conexión con el servidor
    connection = pika.BlockingConnection(pika.ConnectionParameters(mqHost))

    #Se comienza el canal de comunicación
    channel = connection.channel()

    #Se establece la cola
    channel.queue_declare(queue, passive=False, durable=False, exclusive=False, auto_delete=False, arguments=None)

    #Se envía mensaje
    channel.basic_publish("", queue, bytes(message, 'utf-8'), properties=None, mandatory=False)
    print(" [x] Sent %r" % message)

    #Se cierra la conexión
    connection.close()


