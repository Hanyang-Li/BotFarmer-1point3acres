import re
import json
import datetime
import boto3

def lambda_handler(event, context):
    RE_LOGS = r'log\/(\d{14}).json'
    RE_USER = r'\/user.json'
    TIME_FORMAT = '%Y%m%d%H%M%S'
    with open('config.json', 'r') as file:
        settings = json.load(file)
    BUCKET = settings['Bucket']
    SQS_URL = settings['SQS URL']
    PRESERVE = settings['Preserve Days']
    s3 = boto3.resource('s3')
    sqs = boto3.client('sqs')

    # Get all the items in S3 bucket
    contents = boto3.client('s3').list_objects(Bucket=BUCKET)['Contents']
    
    # Get all the logs in S3 bucket and delete the expired logs
    now_time = datetime.datetime.utcnow()
    delta_time = datetime.timedelta(days=int(PRESERVE))
    expire_time = (now_time - delta_time).strftime(TIME_FORMAT)
    for log in [c['Key'] for c in contents if re.search(RE_LOGS, c['Key'])]:
        if re.search(RE_LOGS, log).group(1) < expire_time:
            obj = s3.Object(BUCKET, log)
            obj.delete()
    
    # Get all the user and make requests for them
    for user in [c['Key'] for c in contents if re.search(RE_USER, c['Key'])]:
        config = json.loads(s3.Object(BUCKET, user).get()['Body'].read().decode('utf-8'))
        methods = []
        if config['check in']:
            methods.append('check_in')
        if config['take quiz']:
            methods.append('take_quiz')
        body = {'uid': config['uid'], 'methods': methods}
        response = sqs.send_message(
            QueueUrl=SQS_URL,
            DelaySeconds=0,
            MessageAttributes={},
            MessageBody=(json.dumps(body, ensure_ascii=False))
        )
    return {
        'statusCode': 200
    }
