import json
import boto3

def lambda_handler(event, context):

    Id = event['Records'][0]['dynamodb']['Keys']['FaceID']['S']

    status=event['Records'][0]['dynamodb']['NewImage']['Status']['S']

    print('identificación')
    print(Id)
    print('actualización status')
    print(status)

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