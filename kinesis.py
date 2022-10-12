import boto3
import numpy as np
import cv2

kinesis_client = boto3.client('kinesisvideo',
   region_name = "us-east-1"
)

response = kinesis_client.get_data_endpoint(
   StreamARN = 'ARN',
   APIName = 'GET_MEDIA'
)
video_client = boto3.client('kinesis-video-media',
   endpoint_url = response['DataEndpoint']
)
stream = video_client.get_media(
   StreamARN = 'ARN',
   StartSelector = {
      'StartSelectorType': 'NOW'
   }
)
# print(stream)

datafeed = stream['Payload'].read()
fourcc = cv2.VideoWriter_fourcc( * 'XVID')
out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))

while (True):
    ret, frame = stream['Payload'].read()

    out.write(frame)

    cv2.imshow('frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    else :
        break
    
out.release()
cv2.destroyAllWindows()