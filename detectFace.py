from distutils.command.clean import clean
import json
import os
import logging
import boto3
import urllib
import io
from PIL import Image, ImageDraw, ExifTags, ImageColor



def lambda_handler(event, context):
    # TODO implement

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    dictionary, num = detect_faces(bucket,key)

    print('\n Resultado final: \n')
    print(dictionary)
    print('número de personas: ' + '{0:.0f}'.format(num) + '\n')

   

def detect_faces(bucket,key):

    client=boto3.client('rekognition', 'us-east-1')

    threshold = 80
    maxFaces = 1


    print(bucket)
    print(key)
    
    response = client.detect_faces(Image={'S3Object': {'Bucket': bucket, 'Name': key}},
        Attributes=['ALL'])

    print('Detected faces for ' + key)   

    for faceDetail in response['FaceDetails']:
        print('The detected face is between ' + str(faceDetail['AgeRange']['Low']) 
            + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')

        # print('Here are the other attributes:')
        # print(json.dumps(faceDetail, indent=4, sort_keys=True))

        # Access predictions for individual face details and print them
        print("Gender: " + str(faceDetail['Gender']))
        # print("Smile: " + str(faceDetail['Smile']))
        # print("Eyeglasses: " + str(faceDetail['Eyeglasses']))
        # print("Emotions: " + str(faceDetail['Emotions'][0]))


    # Load image from S3 bucket
    s3_connection = boto3.resource('s3')
    s3_object = s3_connection.Object(bucket,key)
    s3_response = s3_object.get()

    

    stream = io.BytesIO(s3_response['Body'].read())

    print('Hasta aquí se ejecura sin PIL')
    image=Image.open(stream)

    imgWidth, imgHeight = image.size  

    print('Se va a imprimir imagen')

    # draw = ImageDraw.Draw(image)  
                
    dict={}


    count=1

    # calculate and display bounding boxes for each detected face       
    # print('Bounding boxes for ' + key)    
    for faceDetail in response['FaceDetails']:
    

        
        box = faceDetail['BoundingBox']
        left = imgWidth * box['Left']
        top = imgHeight * box['Top']
        width = imgWidth * box['Width']
        height = imgHeight * box['Height']

        dict['cara'+'{0:.0f}'.format(count)]=[left,top,left+width,top-height]
                
        count=count+1


        print('Left: ' + '{0:.0f}'.format(left))
        print('Top: ' + '{0:.0f}'.format(top))
        print('Face Width: ' + "{0:.0f}".format(width))
        print('Face Height: ' + "{0:.0f}".format(height))

        points = (
            (left,top),
            (left + width, top),
            (left + width, top + height),
            (left , top + height),
            (left, top)

        )
        # draw.line(points, fill='#00d400', width=2)

    print('número de caras')
    numCaras=len(response['FaceDetails'])


    # image.show()

    return dict, numCaras


def cropFace(image,dict,numCaras,key):

    client=boto3.client('s3')

    for i in range(1,numCaras+1):
        key=key[0:len(key)-4]
        nombre=key+i

        dimensiones=dict['cara'+i]

        imagecrop=image.crop(dimensiones[0],dimensiones[1],dimensiones[2],dimensiones[3])

        client.upload_fileobj(imagecrop, 'prueba-rekognition-analitica', nombre+'.jpg')



