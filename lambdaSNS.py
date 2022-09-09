'''
Función para enviar SNS por correo cuando se actualiza un item de una tabla de DynamoDB
'''

#Se importan librerías
import json
import boto3

def lambda_handler(event, context):

   #Se toma el primary key del item que se actualizó
    Id = event['Records'][0]['dynamodb']['Keys']['FaceID']['S']
   #Se toma el valor de la columna status del item que se actualizó
    status=event['Records'][0]['dynamodb']['NewImage']['Status']['S']

    print('identificación')
    print(Id)
    print('actualización status')
    print(status)

   #Si el estatus es 'NO' se envía mensaje de "persona desconocida" a correo preestablecido 
    if status == 'NO':

      client = boto3.client('sns')

      snsArn = 'arn:aws:sns:us-east-1:533886999211:FaceSNS'
      message = "Persona desconocida."

      response = client.publish(
         TopicArn = snsArn,
         Message = message ,
         Subject='Seguridad Telemetrik'
      )

      return {
         'statusCode': 200,
         'body': json.dumps(response)
      }