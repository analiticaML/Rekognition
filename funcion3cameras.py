#Se importan librerías
from email.mime import image
from typing_extensions import Self
from faceDetector import FaceDetector
from imageService import ImageService
from cameraService import CameraService
from personDetector import PersonDetector
from rabbitmqService import RabbitmqService
import json
import cv2
import datetime

#Clase donde se desarrolla el proceso de streaming, guardado de captura y notificación
# a servidor de mensajería 
class Recorder:

    #Cosntructor
    def __init__(self,path, mqHost, movementSensibility, millisecondsBetweenCaptures):
        self.path = path
        self.mqHost = mqHost
        self.movementSensibility =  movementSensibility
        self.millisecondsBetweenCaptures = millisecondsBetweenCaptures

    def checkDetection(self,cameraservice, previousGrayFrame, sensibility, newFrame,
    imageservice, persondetector,facedetector, rabbitmqservice, indicador):

        newFrameGrayScale = cameraservice.getGrayScaleFrame(newFrame)
        #Se llama a método para detectar movimiento
        if (cameraservice.detectMovement(previousGrayFrame, newFrameGrayScale, sensibility)):
            print("Motion detected!!!")

            #Se guarda la fecha de hoy y se convierte a string 
            now = datetime.datetime.now()
            date=str(now.year)+str(now.month)+str(now.day)+str(now.hour)+str(now.minute)+str(now.second)+str(now.microsecond)
            #Se gurda la imagen el directorio local con nombre de la imagen como la fecha y hora de la captura
            path = self.path + "/" + date + indicador + ".jpg"
            data = {}
            data["path"] = path
            print("Data: " + str(data["path"]))
            imageservice.saveImage(newFrame, path)




            objetos= persondetector.detectObjects(path)
            caras = facedetector.facedetector(path)

            if 0 in objetos:
                print("Se detectó a una persona")                         
                    
                if caras.size != 0:
                    print("Se detectó una cara")

                    imageservice.saveImage(newFrame, "/home/analitica2/Documentos/RecuadrosPersonas"+ "/" + date + ".jpg")
                    #Se envía mensaje a la cola del servicio de mensajería
                    rabbitmqservice.publish(json.dumps(data), "captured-image-queue", self.mqHost)


    #Método para comenzar el streaming
    def start(self):

        #Se crea objeto tipo ImageService
        imageservice=ImageService()
        #Método para verificar existencia del directorio donde se guardan las capturas
        imageservice.setFolder(self.path)

        #Se crea objeto tipo CameraService
        cameraservice=CameraService()
        cameraservice2 = CameraService()
        cameraservice3 = CameraService()
        #Se establece conexión del streaming
        cameraservice.openCamera(800, 1080, "rtsp://192.168.1.16:554/live1s1.sdp")
        cameraservice2.openCamera(640, 480, "rtsp://admin:admin@192.168.1.101:1935")
        cameraservice3.openCamera(640, 480, "rtsp://admin:admin@192.168.1.8:1935")

        #Se obtiene la imagen actual en escala de grises
        previousGrayFrame = cameraservice.getGrayScaleFrame(cameraservice.getFrame())
        previousGrayFrame2 = cameraservice2.getGrayScaleFrame(cameraservice2.getFrame())
        previousGrayFrame3 = cameraservice3.getGrayScaleFrame(cameraservice3.getFrame())

        #Se esteblece un contador para disminuir el número de imágenes a las cuales
        #se les hace el análisis. 
        cuenta=0

        facedetector = FaceDetector()
        persondetector = PersonDetector()
        #Se crea objeto tipo Rabbitmq
        rabbitmqservice=RabbitmqService()

        #Ciclo infinito para la captura de cuadros
        while (True):
            #Nuevo cuadro
            newFrame = cameraservice.getFrame()
            newFrame2 = cameraservice2.getFrame()
            newFrame3 = cameraservice3.getFrame()
            cuenta = cuenta + 1
            #Se salta el análisis de 5 imágenes
            if (cuenta > 30):
            #try:
                self.checkDetection(cameraservice, previousGrayFrame, 50000, newFrame,
                        imageservice, persondetector,facedetector, rabbitmqservice, "cam1")
                #Cambia  a escala de grises el nuevo cuadro
                newFrameGrayScale = cameraservice.getGrayScaleFrame(newFrame)
            #except:
                #cameraservice.openCamera(800, 1080, "rtsp://192.168.1.16:554/live1s1.sdp")
            
            #try:
                self.checkDetection(cameraservice2, previousGrayFrame2, 50000, newFrame2,
                        imageservice, persondetector,facedetector, rabbitmqservice, "cam2")
                #Cambia  a escala de grises el nuevo cuadro
                newFrameGrayScale2 = cameraservice2.getGrayScaleFrame(newFrame2)
            #except:
                #cameraservice.openCamera(640, 480, "rtsp://admin:admin@192.168.1.101:1935")
            
            #try:
                self.checkDetection(cameraservice3, previousGrayFrame3, 50000, newFrame3,
                        imageservice, persondetector,facedetector, rabbitmqservice, "cam3")
                #Cambia  a escala de grises el nuevo cuadro
                newFrameGrayScale3 = cameraservice3.getGrayScaleFrame(newFrame3)
            #except:
                #cameraservice.openCamera(640, 480, "rtsp://admin:admin@192.168.1.8:1935")

                    
                #Se actualiza el cuadro anterior con el cuadro nuevo
                previousGrayFrame = newFrameGrayScale
                previousGrayFrame2 = newFrameGrayScale2
                previousGrayFrame3 = newFrameGrayScale3

                #Se reinicia contador
                cuenta=0
           