import json
import boto3

# se debe agregar la siguien politica en el rol de la funcion que es invocada se especifica el arn
# de la funcion que invoca
'''
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:InvokeAsync"
            ],
            "Resource": "arn:aws:lambda:us-east-1:853702706419:function:Function-lambda-Rekognition"
        }
    ]
}
'''

lambda_client = boto3.client('lambda')
lambda_payload = {"name":"Emanuel","age":"22"}
lambda_payload = json.dumps(lambda_payload)
lambda_client.invoke(FunctionName='ParentFunction', 
                InvocationType='Event',
                Payload=lambda_payload)

