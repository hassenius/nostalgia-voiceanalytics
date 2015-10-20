#!/usr/bin/env python
import sys, uuid, os
import requests, json
import mimetypes
import rabbitpy
from requests.auth import HTTPBasicAuth
import swiftclient.client as swift_client

# MQ Topic to publish to
#PUBLISH_TOPIC = 'mqlight/audiodemo/audiofiles'
EXCHANGE = 'audio_demo'
QUEUE = 'audiofiles'
ROUTING_KEY = 'audiofiles'

# Setup input
audiofile = str(sys.argv[1])
d = str(sys.argv[2])
call_data = json.loads(json.loads(d))
recepient = call_data['mailbox']
filename = 'voicemail-' + call_data['messageid']
mail_to = str(sys.argv[3])



# Setup Swift Client
try:
    import swiftclient.client as swift_client
except ImportError:
    import swift.common.client as swift_client

if os.environ.get('VCAP_SERVICES'):
   vcap_services = os.environ.get('VCAP_SERVICES')
   decoded = json.loads(vcap_services)['Object Storage'][0]
   vcap_username = str(decoded['credentials']['username'])
   vcap_password = str(decoded['credentials']['password'])
   vcap_auth_url = str(decoded['credentials']['auth_url'])

else:
  exit("No object storage credentials")


# Get real Object Storage credentials
credentials = requests.get(url=vcap_auth_url, auth=HTTPBasicAuth(vcap_username, vcap_password))

auth_url = credentials.json()['CloudIntegration']['auth_url']
username = credentials.json()['CloudIntegration']['credentials']['userid']
password = credentials.json()['CloudIntegration']['credentials']['password']
swift_url = credentials.json()['CloudIntegration']['swift_url']
tenant_name = credentials.json()['CloudIntegration']['project']

# Create a new object storage client
client = swift_client.Connection(auth_url + '/v2.0', username, password, tenant_name=tenant_name, auth_version="2.0")

# Make sure container exists for recepient
client.put_container(recepient)


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
