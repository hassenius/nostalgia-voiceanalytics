#!/usr/bin/env python
import sys, uuid, os
import requests, json
import mimetypes
import rabbitpy
from requests.auth import HTTPBasicAuth
import swiftclient.client as swift_client

# Make sure debug is set
if not 'DEBUG_MODE' in globals():
  DEBUG_MODE=False

# MQ Topic to publish to
#PUBLISH_TOPIC = 'mqlight/audiodemo/audiofiles'
EXCHANGE = 'audio_demo'
QUEUE = 'audiofiles'
ROUTING_KEY = 'audiofiles'

# Setup Swift Client
try:
    import swiftclient.client as swift_client
except ImportError:
    import swift.common.client as swift_client

if os.environ.get('VCAP_SERVICES'):
  if DEBUG_MODE:
    print 'Getting Object Storage Credentials'
  vcap_services = os.environ.get('VCAP_SERVICES')
  decoded = json.loads(vcap_services)['Object-Storage'][0]
  userid = str(decoded['credentials']['userId'])
  password = str(decoded['credentials']['password'])
  auth_url = str(decoded['credentials']['auth_url'])
  project_id = str(decoded['credentials']['projectId'])
  region = str(decoded['credentials']['region'])

else:
  exit("No object storage credentials")
if DEBUG_MODE:
  print '...finished'
  

def get_token_and_endpoint(authurl, projectid, userid, password, region, endpoint_type='publicURL'):
  data={"auth": {"tenantId": projectid, "passwordCredentials": {"userId":  userid, "password": password} } }
  r = requests.post(authurl + '/v2.0/tokens', data=json.dumps(data), headers={"Content-Type": "application/json"})
  if r.status_code != 200:
    print 'Something went wrong while getting token'
    print 'Status code: %s and status text: " %s "'  % (r.status_code, r.text)
  
  token = r.json()['access']['token']['id']
  for service in r.json()['access']['serviceCatalog']:
    if service['type'] == 'object-store':
      for endpoint in service['endpoints']:
        if endpoint['region'] == region:
          os_endpoint = endpoint[endpoint_type]
    
  return (token, os_endpoint)

token, endpoint = get_token_and_endpoint(auth_url, project_id, userid, password, region)

# Create a global object storage client
client = swift_client.Connection(preauthurl=endpoint, preauthtoken=token)

# Setup input
audiofile = str(sys.argv[1])
d = str(sys.argv[2])
call_data = json.loads(json.loads(d))
recepient = call_data['mailbox']
filename = 'voicemail-' + call_data['messageid']
mail_to = str(sys.argv[3])



# Upload Voicemail to voicemail users container
with open(audiofile, 'rb') as file:
    file_data = file.read()

# Available data: # {u'name': u'IBM Test', u'callerid': u'+35318562445', u'cidname': u'', u'mailbox': u'101', u'date': u'Monday, October 12, 2015 at 10:56:52 AM', u'cidnum': u'+35318562445', u'messageid': u'20', u'duration': u'0:10'}
headers=dict( ('X-Object-Meta-Calldata-%s' % k, call_data[k]) for k in call_data.keys() )
etag = client.put_object(recepient, filename, file_data, headers=headers)

# Build the message body
payload = {
  'container': recepient,
  'object': filename,
  'etag': etag,
  'mail_to': mail_to,
  'call_data': call_data}


# Post the message
with rabbitpy.Connection('amqp://eovnztng:bPbtTaxd8KvFI5JQVzf8Jc6wtbe662FS@white-swan.rmq.cloudamqp.com/eovnztng') as conn:
    with conn.channel() as channel:

        # Create the exchange
        exchange = rabbitpy.Exchange(channel, EXCHANGE)
        exchange.declare()

        # Create the queue
        queue = rabbitpy.Queue(channel, QUEUE)
        queue.declare()

        # Bind the queue
        queue.bind(exchange, ROUTING_KEY)

        # Create and start the transaction
        tx = rabbitpy.Tx(channel)
        tx.select()

        # Create the message
        message = rabbitpy.Message(channel,
                                  json.dumps(payload),
                                   {'content_type': 'text/plain',
                                    'message_type': 'audio file uploaded'})

        # Publish the message
        message.publish(exchange, ROUTING_KEY)

        # Commit the message
        tx.commit()
