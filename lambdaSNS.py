'''
Función para enviar SNS por correo cuando se actualiza un item de una tabla de DynamoDB
'''

#Se importan librerías
import json
import boto3
import io

def lambda_handler(event, context):

   client = boto3.client('sns')

   snsArn = 'arn:aws:sns:us-east-1:533886999211:FaceSNS'
   message = "Persona desconocida. \n http://localhost:3000/d/a2DTA1G4z/control?orgId=1&refresh=10s&from=1663229818365&to=1663251418365&viewPanel=12"

   response = client.publish(
      TopicArn = snsArn,
      Message = message ,
      Subject='Seguridad Telemetrik',
   )

   return {
      'statusCode': 200,
      'body': json.dumps(response)
   }