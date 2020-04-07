from flask import Flask, jsonify, request, send_file
import StringIO

# Include the swift functions
execfile('swift.py')


app = Flask(__name__)

#### Some handlers ########
@app.errorhandler(404)
def not_found(error=None):
    message = {
            'status': 404,
            'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp


#############################
###### ENDPOINTS ############
#############################

# Helper function
@app.route('/api/help', methods = ['GET'])
def help():
    """Print available functions."""
    func_list = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            func_list[rule.rule] = app.view_functions[rule.endpoint].__doc__
    return jsonify(func_list)


@app.route('/api/v1/allvoicemails', methods=['GET'])
def get_allvoicemails():
    """List all available voicemails."""
    voicemails = []
    headers, containers = get_account()
    if headers['x-account-container-count'] > 0:
      for c in containers:
        headers, objects = get_container(c['name'])
        if headers['x-container-object-count'] > 0:
            for obj in objects:
                voicemails.append({'mailbox': c['name'], 'name': obj['name']})

    return jsonify(voicemails)


@app.route('/api/v1/mailboxes', methods=['GET'])
def get_mailboxes():
    """List available mailboxes."""
    mailboxes = []
    headers, containers = get_account()
    if headers['x-account-container-count'] > 0:
      for c in containers:
        mailboxes.append(c['name'])

    return jsonify({"mailboxes": mailboxes})


@app.route('/api/v1/mailboxes/<mailbox>', methods=['GET', 'PUT'])
def parse_mailbox(mailbox):
    """Get information on a specific mailbox or create new."""
    if request.method == 'GET':
        return jsonify(head_container(mailbox))
    elif request.method == 'PUT':
        return jsonify({'status':put_container(mailbox)})
    else:
        # For sanity. Should never arrive here
        return not_found()

@app.route('/api/v1/mailboxes/<mailbox>/voicemails', methods=['GET', 'POST'])
def parse_voicemails(mailbox):
    """GET/POST voicemails for a mailbox."""
    if request.method == 'GET':
        headers, objects = get_container(mailbox)
        voicemails = []
        if headers['x-container-object-count'] > 0:
            for obj in objects:
                voicemails.append(obj['name'])
        return jsonify({'mailbox': mailbox,'voicemails': voicemails})

    elif request.method == 'POST':
        # Read the call data
        calldata = json.loads(request.form['calldata'].strip())
        # Translate call data to object storage metadata
        headers=dict( ('X-Object-Meta-Calldata-%s' % k, calldata[k]) for k in calldata.keys() )
        audio = request.files['file']
        voicemail = 'voicemail-' + calldata['messageid']

        # Ensure the container exists before attempting to put an object in it
        put_container(mailbox)
        etag = put_object(mailbox, voicemail, audio, headers)

        return jsonify({'etag': etag, 'voicemail': voicemail, 'input': calldata})


@app.route('/api/v1/mailboxes/<mailbox>/voicemails/<voicemail>', methods=['GET'])
def get_voicemail(mailbox, voicemail):
    """Get information about a voicemail in a mailbox."""
    return jsonify(head_object(mailbox, voicemail))


@app.route('/api/v1/mailboxes/<mailbox>/voicemails/<voicemail>/audio', methods=['GET'])
def get_audio(mailbox, voicemail):
    """GET audio file from a voicemail."""
    headers, obj = get_object(mailbox, voicemail)
    audio = StringIO.StringIO()
    audio.write(obj)
    audio.seek(0)
    return send_file(audio, mimetype='audio/wave', attachment_filename=voicemail + '.wav')


@app.route('/api/v1/mailboxes/<mailbox>/voicemails/<voicemail>/transcript', methods=['GET', 'POST'])
def parse_transcript(mailbox, voicemail):
    """GET/POST transcript of a voicemail."""
    obj_meta = head_object(mailbox, voicemail)
    if request.method == 'GET':
        if obj_meta.get('x-object-meta-calldata-transcript'):
            transcript = obj_meta.get('x-object-meta-calldata-transcript')
        elif obj_meta.get('x-object-meta-calldata-transcript-1'):
            transcript = ''
            i = 1
            while obj_meta.get('x-object-meta-calldata-transcript-%i' % i):
                transcript += obj_meta.get('x-object-meta-calldata-transcript-%i' % i)
                i += 1
        else:
            return not_found()
        return jsonify({"transcript": transcript})

    elif request.method == 'POST':
        data = request.get_json()
        print data
        text = data['transcript']
        add_object_metadata(mailbox, voicemail, obj_meta, 'calldata-transcript', text)
        return jsonify({"transcript": text})

    else:
        # We should never arrive here, but for the sake of sanity.
        return not_found()

@app.route('/api/v1/mailboxes/<mailbox>/voicemails/<voicemail>/calldata', methods=['GET'])
def get_calldata(mailbox, voicemail):
    """GET all available call data from a voicemail."""
    obj_meta = head_object(mailbox, voicemail)
    meta='x-object-meta-calldata-'
    calldata = {}
    for key in obj_meta:
        if key.startswith(meta):
            calldata[key[len(meta):]] = obj_meta[key]

    return jsonify({"calldata": calldata})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
