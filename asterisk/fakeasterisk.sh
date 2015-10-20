#!/bin/bash

json_data=$(sed -n 's/data=//p' stream.part2 | python -c 'import json,sys; print json.dumps(sys.stdin.read())' )
#json_data='{"callerid":"+35318562445","duration":"0:10","messageid":"19","name":"IBM Test","mailbox":"101","cidnum":"+35318562445","cidname":"","date":"Monday, October 12, 2015 at 10:56:52 AM"}'
audiofile='./stream.part3.wav'


to_field=$(sed -n 's/To: //p' stream.part)
source /home/ibmcloud/backup/vcap_variables.sh

python shipaudio.py ${audiofile} "${json_data}" "${to_field}"

#python shipaudio.py ${audiofile} "${json_data}"
