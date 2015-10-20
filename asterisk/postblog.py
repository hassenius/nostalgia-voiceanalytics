#!/usr/bin/env python
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import posts, media
from wordpress_xmlrpc.compat import xmlrpc_client
import sys, argparse, os, mimetypes

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--subject', action='store', dest='subject', metavar='SUBJECT', help='Subject of post')
parser.add_argument('-c', '--content', action='store', dest='content', metavar='CONTENT', help='Content of post')
parser.add_argument('-f', '--file', action='store', dest='attachment', metavar='FILE', help='File to attach to post')
args = parser.parse_args()

## Complain if we don't have post information
if args.subject == None or args.content == None:
  parser.print_help()
  print "\nMissing Post information!"
  exit()


#contentfile = str(sys.argv[1])

#message = open(contentfile, 'rb').read()

message = args.content

client = Client('http://129.41.157.126/wordpress/xmlrpc.php', 'transcriber', 'SomethingSecret')
# posts = client.call(posts.GetPosts())

from wordpress_xmlrpc import WordPressPost


if args.attachment is not None:
  data = {
    'name': os.path.basename(args.attachment),
    #'type': mimetypes.read_mime_types(args.attachment) or mimetypes.guess_type(args.attachment)[0]
    'type': 'audio/x-wave'
  }
  
  with open(args.attachment, 'rb') as filename:
    data['bits'] = xmlrpc_client.Binary(filename.read())

  response = client.call(media.UploadFile(data))

  message += '<br>Audio file available here: ' + response['url']
  message += ' [audio wav="' + response['url'] + '"][/audio]'



post = WordPressPost()
post.title = args.subject
post.content = message
post.id = client.call(posts.NewPost(post))

post.post_status = 'publish'
client.call(posts.EditPost(post.id, post))
