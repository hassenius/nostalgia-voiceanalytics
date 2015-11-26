#!/usr/bin/env python
# Standard modules
import os, json
import logging
from timeit import default_timer as timer
# Special modules requiring installation
#import bottle
from requests.auth import HTTPBasicAuth
import requests
from flask import Flask
from flask import request, send_from_directory, redirect, Response

execfile('swift.py')

port = int(os.getenv('VCAP_APP_PORT', 8080))

DEBUG_MODE=True

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

LOGGER.info('Starting application')

if os.environ.get('VCAP_SERVICES'):
   if DEBUG_MODE:
     print 'Loading credentials from VCAP_SERVICES'
   vcap_services = os.environ.get('VCAP_SERVICES')
   
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
        
        obj_meta = head_object(container['name'], obj['name'])
        
        # Get Call details
        vm_entry['from'] = obj_meta.get('x-object-meta-calldata-cidnum', 'Unknown')
        vm_entry['duration'] = obj_meta.get('x-object-meta-calldata-duration', 'Unknown')
        vm_entry['messageid'] = obj_meta.get('x-object-meta-calldata-messageid', 'Unknown')
        vm_entry['time'] = obj_meta.get('x-object-meta-calldata-date', 'Unknown')
        
        # Get message transcript
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
        
        # Get Tone Analysis
        tones = ['cheerfulness', 'negative', 'anger', 'analytical', 'confident', 'tentative', 'openness', 'agreeableness', 'conscientiousness']
        for tone in tones:
          if obj_meta.get('x-object-meta-calldata-calldata-tone-%s' % tone):
          #if obj_meta.get('x-object-meta-%s' % tone):
            vm_entry[tone] = obj_meta.get('x-object-meta-calldata-tone-%s' % tone)
            #vm_entry[tone] = obj_meta.get('x-object-meta-%s' % tone)
          else:
            vm_entry[tone] = 'Waiting for Watson analysis'
        
        mailbox['voicemails'].append(vm_entry)
        
      mailboxes.append(mailbox)
  
  return mailboxes



def print_mailboxestable():
  start = timer()
  LOGGER.debug('Creating mailbox table')
  tones = {'emotion': ['anger', 'cheerfulness', 'negative'], 'social': ['openness', 'agreeableness', 'conscientiousness'], 'writing': ['analytical', 'confident', 'tentative']}
  #tones = ['cheerfulness', 'negative', 'anger', 'analytical', 'confident', 'tentative', 'openness', 'agreeableness', 'conscientiousness']
  
  mailboxes = get_mailboxes()
  text = '<html><link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">' 
  text += '<h1>MailBoxes</h1><br />'
  for mailbox in mailboxes:
    text += '<p><h3>Entries for mailbox ' + mailbox['name'] + '</h3></p>'
    text += '<p><table class="table table-striped" padding="5">'
    text += '<thead><tr><th>ID</th><th>From</th><th>Time</th><th>Duration</th><th>Actions</th><th>Transcript</th></tr></thead>'
    text += '<tbody>'
    for message in mailbox['voicemails']:
      text += '<tr><th scope="row">%(messageid)s</th> \
        <td>%(from)s</td> \
        <td>%(time)s</td> \
        <td>%(duration)s</td>\
        <td> \
          <form action="/modify" method="post"><input type="hidden" name="owner" value="%(owner)s" /><input type="hidden" name="filename" value="%(filename)s" /> <input type="image" src="/static/trash-300px.png" alt="Submit" width="30" height="30"></form> \
          <audio id="player-%(filename)s" preload="none"> <source src="/audio/%(owner)s/%(filename)s" type="audio/wav" preload="none"> </audio> \
          <input type="image" src="/static/Play-Icon-300px.png" onclick="document.getElementById(\'player-%(filename)s\').play()" alt="Play" width="30" height="30"> \
          <input type="image" src="/static/pause-300px.png" onclick="document.getElementById(\'player-%(filename)s\').pause()" alt="Pause" width="30" height="30"> \
        </td> \
        <td><table width="100%%"><tr><td colspan="3">%(transcript)s</td></tr><tr><td colspan="3"><hr /></td></tr>' % message
#        
#        ' % message 
#      text += '
      # This is table in row
      #for tone in tone_analyse['children']:
      for key in tones:
        text += '<tr>'
        for tone in tones[key]:
          #text += '<tr><th scope="row">%s</th><' % tone['name']
          text += '<td>%s: %s%%</td>' % (tone.capitalize(), message[tone])
        text += '</tr>'
      # This ends table in row
      text += '</table>'
      text += '</td></tr>'

      # print '%s: %i <br />' % (emotion['name'], float(emotion['score']) * 100)
      
  text += '</tbody></table></p></html>'
  end = timer()
  LOGGER.debug('Completed in %.2f seconds' % (end - start) )
  
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
    LOGGER.info('Request to delete object %s in container %s' % (obj, container) )
    delete_object(container, obj)
  return redirect('/')

@app.route("/audio/<owner>/<filename>")
def play_audio(owner, filename):
  headers, audio = get_object(owner, filename)
  return Response(audio, mimetype='audio/wav')

app.run(host='0.0.0.0', port=port)  
## Desired end result:
#Mailboxes:

#Mailbox - Username
#from  -  transcription
