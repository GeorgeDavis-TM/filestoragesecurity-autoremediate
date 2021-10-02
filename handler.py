import os
import json
import boto3
import time
from datetime import datetime, timedelta
from urllib.parse import unquote

f = open("config.json", "r")
configDict = json.loads(f.read())
f.close()

def getFssScanErrorObjectInventoryList(logsClient, scannerLambdaLogGroupNamesList, logGroupInsightQuery, timeDeltaInLogQuery):

    scannerStatusMessageList = []
    for configItem in configDict["scanner"]["error-status"]:
        if configDict["scanner"]["error-status"][configItem]:            
            scannerStatusMessageList.append(configItem)

    logGroupInsightQuery += " | filter scanner_status_message in " + str(scannerStatusMessageList)

    start_query_response = logsClient.start_query(
        logGroupNames=scannerLambdaLogGroupNamesList,
        startTime=int((datetime.today() - timedelta(hours=int(timeDeltaInLogQuery))).timestamp()),
        endTime=int(datetime.now().timestamp()),
        queryString=logGroupInsightQuery
    )

    query_id = start_query_response['queryId']

    response = None

    while response == None or response['status'] == 'Running':
        print('Waiting for query to complete ...')
        time.sleep(3)
        response = logsClient.get_query_results(
            queryId=query_id
        )

    resultList = []

    for result in response["results"]:

        tempDict = {}

        for i in range(0, len(result)):
            
            tempDict.update({result[i]["field"]: result[i]["value"]})

        resultList.append(tempDict)    

    return resultList

def s3CopyObject(s3Client, srcBucket, destBucket, key):

    copySourceDict = {'Bucket': srcBucket, 'Key': key}

    s3CopyObjectResponse = s3Client.copy_object(
        CopySource=copySourceDict,
        Bucket=destBucket,    
        Key=key,
        MetadataDirective='REPLACE'
    )

    return s3CopyObjectResponse

def main(event, context):

    scannerLambdaLogGroupNamesList = os.environ.get("scannerLambdaLogGroupNames").split(",")
    logGroupInsightQuery = str(os.environ.get("logGroupInsightQuery"))
    timeDeltaInLogQuery=os.environ.get("timeDeltaInLogQuery")

    logsClient = boto3.client('logs')

    scanErrObjInventoryList = getFssScanErrorObjectInventoryList(logsClient, scannerLambdaLogGroupNamesList, logGroupInsightQuery, timeDeltaInLogQuery)

    s3Client = boto3.client('s3')

    for object in scanErrObjInventoryList:

        print(str(s3CopyObject(s3Client, object["srcBucket"], object["srcBucket"], unquote(object["key"]))))