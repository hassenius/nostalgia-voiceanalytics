#!/usr/bin/env python
# Standard modules
import os, json
# Special modules requiring installation
#import bottle
from requests.auth import HTTPBasicAuth
import requests
from flask import Flask
from flask import request, send_from_directory, redirect

execfile('swift.py')

port = int(os.getenv('VCAP_APP_PORT', 8080))

DEBUG_MODE=True

if os.environ.get('VCAP_SERVICES'):
   if DEBUG_MODE:
     print 'Loading credentials from VCAP_SERVICES'
   vcap_services = os.environ.get('VCAP_SERVICES')

   # Tone Analyzer Credentials
   decoded = json.loads(vcap_services)['tone_analyzer'][0]
   st_url = str(decoded['credentials']['url'])
   st_username = str(decoded['credentials']['username'])
   st_password = str(decoded['credentials']['password'])
   
else:
  exit("VCAP_SERVICES")


def get_mailboxes():
  mailboxes = []
  headers, containers = get_account()
  for container in containers:
    if head_container(container['name'])['x-container-object-count'] > 0:
      mailbox={}
      mailbox['name'] = container['name']
      mailbox['voicemails'] = []
      
      headers, objects = get_container(container['name'])
      for obj in objects:
        vm_entry = {}
        vm_entry['filename'] = obj['name']
        vm_entry['owner'] = container['name']
        
        #print 'retrieving %s from %s' % (obj['name'], container['name'])
        obj_meta = head_object(container['name'], obj['name'])
        vm_entry['from'] = obj_meta.get('x-object-meta-calldata-cidnum', 'Unknown')
        vm_entry['duration'] = obj_meta.get('x-object-meta-calldata-duration', 'Unknown')
        vm_entry['messageid'] = obj_meta.get('x-object-meta-calldata-messageid', 'Unknown')
        vm_entry['time'] = obj_meta.get('x-object-meta-calldata-date', 'Unknown')
        
        if obj_meta.get('x-object-meta-calldata-transcript'):
          vm_entry['transcript'] = obj_meta.get('x-object-meta-calldata-transcript')  
        elif obj_meta.get('x-object-meta-calldata-transcript-1'):
          vm_entry['transcript'] = ''
          i = 1
          while obj_meta.get('x-object-meta-calldata-transcript-%i' % i):
            vm_entry['transcript'] += obj_meta.get('x-object-meta-calldata-transcript-%i' % i)
            i += 1
        else:
          vm_entry['transcript'] = 'Waiting for transcript - Refresh page to see updates...'
        
        mailbox['voicemails'].append(vm_entry)
        
      mailboxes.append(mailbox)
  
  return mailboxes


def do_analyse(text):
  response = requests.post(url=st_url + '/v1/tone', auth=HTTPBasicAuth(st_username, st_password), data=json.dumps({"scorecard":"email","text":text}), headers={"content-type": "application/json"})
  #response = requests.get(url=st_url + '/v1/tone?scorecard=email&text=justtesting', auth=HTTPBasicAuth(st_username, st_password))
  #return response.json())
  answer = {}
  for tone in response.json()['children']:
    for spec in tone['children']:
      answer[spec['id']] = {}
      answer[spec['id']]['name'] = spec['name']
      answer[spec['id']]['score'] = spec['normalized_score']
      
  return answer
  
def print_mailboxestable():
  mailboxes = get_mailboxes()
  text = '<html><link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">' 
  text += '<h1>MailBoxes</h1>'
  text += '<p><table class="table table-striped" padding="5">'
  text += '<thead><tr><th>ID</th><th>From</th><th>Delete</th><th>Transcript</th><th>Tone Analysis</th></tr></thead>'
  text += '<tbody>'
  for mailbox in mailboxes:
    text += '<tr><td colspan="5"><h3><br /><br />Entries for mailbox ' + mailbox['name'] + '</h3></td></tr>'
    for message in mailbox['voicemails']:
      tone_analyse = do_analyse(message['transcript'])
      text += '<tr><th scope="row">%(messageid)s</th> \
        <td>%(from)s</td> \
        <td><form action="/modify" method="post"><input type="hidden" name="owner" value="%(owner)s" /><input type="hidden" name="filename" value="%(filename)s" /> <input type="image" src="/static/trash-300px.png" alt="Submit" width="30" height="30"></form></td> \
        <td>%(transcript)s</td>' % message
      text += '<td>'
      for key, emotion in tone_analyse.iteritems():
        text += emotion['name'] + ': ' + str(int(float(emotion['score']) * 100)) + '% <br />'
      text += '</td></tr>'

      # print '%s: %i <br />' % (emotion['name'], float(emotion['score']) * 100)
      
  text += '</tbody></table></p></html>'
  
  return text


app = Flask(__name__, static_url_path="/static")

@app.route("/")
def print_mailboxes():
  return print_mailboxestable()
  
  
@app.route("/hello")
def print_hello():
  return get_mailboxes()
  
@app.route("/modify", methods=['POST'])
def modify():
  if request.method == "POST":
    obj = request.form['filename']
    container = request.form['owner']
    print "wanted to delete %s from %s" % (obj, container)
    delete_object(container, obj)
  return redirect('/')

app.run(host='0.0.0.0', port=port)

## Desired end result:
#Mailboxes:

#Mailbox - Username
#from  -  transcription
