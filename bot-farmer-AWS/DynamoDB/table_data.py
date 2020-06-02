import os
import sys
import time
import json
import platform
import boto3

# Windows cmd needs colorama to run ANSI format code
if 'windows' in platform.system().lower():
    import colorama
    colorama.init()

# Initialize AWS environment variables
with open('aws-profile.json', 'r', encoding='utf-8') as file:
    profile = json.load(file)
os.environ.setdefault("AWS_ACCESS_KEY_ID", profile['IAM access key'])
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", profile['IAM secret key'])
os.environ.setdefault("AWS_DEFAULT_REGION", profile['region'])

# Initialize global variables
dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource('dynamodb')
cheat_sheet = None
table = None


def load_tables(func):
    """
    A decorator which runs before all the other operations, to make sure file and table exist
    """
    def wrapper(*args, **kwargs):
        """
        Load the file and table, if one does not exist, create one
        """
        # Check whether the global variables are defined
        global cheat_sheet, table
        if cheat_sheet is None or table is None:

            # Check local table (json file)
            try: 
                with open('cheat_sheet.json', 'r', encoding='utf-8') as file:
                    cheat_sheet = json.load(file)
            except (FileNotFoundError, json.decoder.JSONDecodeError) as error:
                # Case that file does not exist or it is empty even without '{}'
                print("Create cheat_sheet JSON file ", end='')
                cheat_sheet = dict()
                with open('cheat_sheet.json', 'w', encoding='utf-8') as file:
                    json.dump(cheat_sheet, file, ensure_ascii=False)
                print("\033[1;32m[Done]\033[0m")
            
            # Check cloud table (DynamoDB)
            table_name = profile['table']
            existing_tables = dynamodb_client.list_tables()['TableNames']
            create_new = False
            if table_name not in existing_tables:
                print("Create DynamoDB table {} ".format(table_name), end='', flush=True)
                create_new = True
                response = dynamodb_client.create_table(
                    KeySchema=[
                        {
                            'AttributeName': 'Question',
                            'KeyType': 'HASH',
                        },
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'Question',
                            'AttributeType': 'S',
                        },
                    ],
                    ProvisionedThroughput={
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5,
                    },
                    TableName=table_name,
                )
            # Get Table object but not check whether the resourse is valid
            table = dynamodb.Table(table_name)
            if create_new:
                # It takes time for DynamoDB to create table, wait util it is valid
                table.wait_until_exists()
                print("\033[1;32m[Done]\033[0m")

        # Run the following function
        return func(*args, **kwargs)
    
    return wrapper


@load_tables
def upload():
    """
    Totally replace the table on cloud with cheat_sheet
    """
    # Clear the table on cloud
    scan = table.scan()
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(Key={'Question': each['Question']})
    # Upload cheat_sheet to table on cloud
    with table.batch_writer() as batch:
        for question, answers in cheat_sheet.items():
            item = {'Question': question, 'Answers':answers}
            batch.put_item(item)
    print("\r\033[KUpload \033[1;32m[Done]\033[0m: cheat_sheet --> DynamoDB table")


@load_tables
def download():
    """
    Totally replace cheat_sheet file with table on cloud
    """
    # Clear cheat_sheet dictionary
    cheat_sheet = dict()
    # Get all the items from table on cloud
    items = table.scan()['Items']
    for item in items:
        cheat_sheet[item['Question']] = item['Answers']
    # Over write cheat_sheet.json file
    with open('cheat_sheet.json', 'w', encoding='utf-8') as file:
        json.dump(cheat_sheet, file, ensure_ascii=False, indent=2)
    print("\r\033[KDownload \033[1;32m[Done]\033[0m: cheat_sheet <-- DynamoDB table")


@load_tables
def merge():
    """
    Merge the information of cheat_sheet and table, update both of them
    """
    # Merge table into cheat_sheet dictionary
    items = table.scan()['Items']
    for item in items:
        question = item['Question']
        answers = item['Answers']
        cheat_sheet.setdefault(question, []).extend([a for a in answers if a not in cheat_sheet[question]])
    # Over write cheat_sheet.json file
    with open('cheat_sheet.json', 'w', encoding='utf-8') as file:
        json.dump(cheat_sheet, file, ensure_ascii=False, indent=2)
    # Upload cheat_sheet to table on cloud
    upload()
    print("\033[A\033[KDownload \033[1;32m[Done]\033[0m: cheat_sheet <-> DynamoDB table")


@load_tables
def _get_method_from_args():
    """
    Check argument validation, and return the method name.
    The validation rules are:
      - Once run this script, user must input and only input 1 arg from [upload / download/ merge]
      - User can merge sheet and table directly
      - User can upload sheet to empty table or download table to empty sheet directly
      - User will be rejected to upload / download sheet and table which both have contents, add '-f' arg to force operation
      - User will be rejected while doing other operation
    """
    # Initialize constants and variables
    VALID_ARGS = ['upload', 'download', 'merge', '-f']
    METHODS = [arg for arg in VALID_ARGS if arg[0] != '-']
    arguments = sys.argv
    # Check validation
    hasInvalidArg = len([a for a in arguments[1:] if a not in VALID_ARGS]) > 0
    hasOneMethod = len([a for a in arguments if a in METHODS]) == 1
    isEmptySheet = len(cheat_sheet) == 0
    isEmptyTable = len(table.scan()['Items']) == 0
    isForced = '-f' in arguments
    method = [a for a in arguments if a in METHODS][0] if hasOneMethod else None
    if hasInvalidArg or (not hasOneMethod):
        print("\033[1;31m[Error]\033[0m Please input 1 and only 1 method from [upload / download/ merge]!")
        sys.exit(1)
    elif method == 'merge':
        print("{} \033[1;34m[Pending]\033[0m".format(method.title()), end='', flush=True)
        return method
    elif not isEmptySheet and not isEmptyTable and not isForced:
        print("\033[1;31m[Error]\033[0m Both table and sheet are not empty, please add '-f' arg to force {}!".format(method))
        sys.exit(1)
    elif (isEmptySheet and method == 'download') or (isEmptyTable and method == 'upload') or isForced:
        print("{} \033[1;34m[Pending]\033[0m".format(method.title()), end='', flush=True)
        return method
    else:
        print("\033[1;31m[Error]\033[0m Cannot over write sheet or table without data!")
        sys.exit(1)


if __name__ == "__main__":
    method = _get_method_from_args()
    exec(method + '()')
