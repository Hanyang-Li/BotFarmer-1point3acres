import json
import boto3
import automatic

def lambda_handler(event, context):
    # Initialize S3 bucket
    with open('config.json', 'r') as f:
        config = json.load(f)
    S3_USERS_BUCKET = config['S3_USERS_BUCKET']
    s3 = boto3.resource('s3')

    # Get message from AWS SQS
    msg = json.loads(event['Records'][0]['body'])

    # Initialize automatic module
    obj = s3.Object(S3_USERS_BUCKET, 'users/{}/user.json'.format(msg['uid']))
    passwd = json.loads(obj.get()['Body'].read().decode('utf-8'))['passwd']
    log = automatic.set_user_info(msg['uid'], passwd, msg.setdefault('log', None))
    
    # Run specific method in automatic
    for method in msg['methods']:
        if method == 'check_in':
            log = automatic.check_in()
        elif method == 'take_quiz':
            log = automatic.take_quiz(msg.setdefault('answer', None))
    
    # Write the log to S3 bucket
    obj = s3.Object(S3_USERS_BUCKET, 'users/{}/log/{}.json'.format(log['uid'], log['num']))
    obj.put(Body=json.dumps(log, ensure_ascii=False, indent=2))

    print(log)

    # Close session in this lambda function and clear log
    # To not affect this function to process another message from SQS
    automatic.close_lambda()

    return {
        'statusCode': 200,
        'body': log
    }
