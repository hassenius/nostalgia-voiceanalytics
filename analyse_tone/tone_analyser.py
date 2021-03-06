#!/usr/bin/env python
# Standard modules
import sys, os, json
import logging
# special modules requiring installation
import pika
import requests
from requests.auth import HTTPBasicAuth


# Load the common swift library
execfile('swift.py')

# MQ Details
EXCHANGE = 'audio_demo'
QUEUE = 'transcripts'
WORKER_NAME='tone_analyser.py'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

LOGGER.info('Starting application')

if os.environ.get('VCAP_SERVICES'):
   vcap_services = os.environ.get('VCAP_SERVICES')
   
   # Tone Analyzer Credentials
   decoded = json.loads(vcap_services)['tone_analyzer'][0]
   ta_url = str(decoded['credentials']['url'])
   ta_username = str(decoded['credentials']['username'])
   ta_password = str(decoded['credentials']['password'])
   
    # MQ Credentials
   decoded = json.loads(vcap_services)['cloudamqp'][0]
   mq_url = str(decoded['credentials']['uri'])
   
else:
  exit("No credentials")

def do_analyse(text, return_raw = False):
  response = requests.post(url=ta_url + '/v1/tone', auth=HTTPBasicAuth(ta_username, ta_password), data=json.dumps({"scorecard":"email","text":text}), headers={"content-type": "application/json"})
  if return_raw:
    return response.json()
  else:
    answer = {}
    for tone in response.json()['children']:
      for spec in tone['children']:
        answer['calldata-tone-%s' % spec['name']] = str(int(float(spec['normalized_score']) * 100))
        
  return answer
  
def callback(ch, method, properties, body):
  LOGGER.info('Received message: %s' % body)
  
  # Received a new message, where the body is a json string with container and filename
  file_details = json.loads(body)
  container = file_details['container']
  obj = file_details['object']
  transcript = file_details['call_data']['transcript']
  # Get tone analysis details for the trascribed text
  tone_analysis_dict = do_analyse(transcript)
  # Add the tone analysis to object metadata
  add_dict_to_object_metadata(container, obj, tone_analysis_dict)
  LOGGER.debug('Finished')

## Create a connection to Message Queue
for i in range(0,100):
    try:
      connection = pika.BlockingConnection(pika.URLParameters(mq_url))
    except pika.exceptions.ConnectionClosed:
      print "Attempt %i failedConnection closed, trying again" % i
      continue
    break
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE)
channel.queue_declare(QUEUE)

#result = channel.queue_declare(QUEUE)
#queue_name = result.method.queue
channel.queue_bind(exchange=EXCHANGE,queue=QUEUE)

print 'Waiting for messages. To exit press CTRL+C'

  
channel.basic_consume(callback,
                      queue=QUEUE,
                      no_ack=True,
                      consumer_tag=WORKER_NAME)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
    
connection.close()
