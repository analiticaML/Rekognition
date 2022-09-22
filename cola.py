import os
import time
import pika
import json
import glob

mqHost = "localhost"

def main():

    y, x, files = next(os.walk("/home/analitica2/Documentos/ftp"))
    print(files)
    file_count = len(files)
    print(file_count)
    print(x)
    print(y)

    #Se obtiene la imagen actual en escala de grises
    previousNoItems = file_count


    #Ciclo infinito para la captura de cuadros
    while (True):
        #Nuevo cuadro
        _, _, files = next(os.walk("/home/analitica2/Documentos/ftp"))
        file_count = len(files)
        newNoItems = file_count 


        #Se llama a método para detectar movimiento
        if (previousNoItems!=newNoItems):
            print("nueva imagen!!")
            
            list_of_files = glob.glob("/home/analitica2/Documentos/ftp/*")
            frame = max(list_of_files, key=os.path.getctime)
            print(frame)
            
            data = {}
            data["path"] = frame

            
            time.sleep(0.2)
            #Se envía mensaje a la cola del servicio de mensajería
            publish(json.dumps(data), "captured-image-queue", mqHost)

            print("Se envio imagen")
        
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

if __name__ == "__main__":
    main()



