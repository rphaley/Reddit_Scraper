import json, os, sys, time, traceback
try:
    if os.environ["GCP_Hosted"]:
        print(f'[+] GCP found, installing dependencies')
        from google.cloud import storage
except Exception as e:
    print(f'[-] Error importing GCP modules in processDB.py: {e}')



def readJSON(config, debug):
    try:
        # # Authenticate using the service account key
        # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get('DBSettings', 'credFile')
        bucket_name = config.get('DBSettings', 'BucketName')
        json_file_name = config.get('DBSettings', 'DatabaseName')

        # Read the JSON file from Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if debug == 1: print(f'[+][readJSON] Successfully connected to bucket {bucket_name}')
        blob = bucket.blob(json_file_name)

        json_data = blob.download_as_text()
        if debug == 1: print(f'[+][readJSON] Successfully read database {json_data}.')
        data = json.loads(json_data)
        if debug == 1: print(f'[+][readJSON] Successfully parsed database {data}.')

        return data

    except Exception as e:
        # Get the current exception information
        exc_type, exc_obj, tb = sys.exc_info()
        # Get the line number where the exception occurred
        line_number = traceback.extract_tb(tb)[-1][1]
        # Get the full traceback as a string
        traceback_str = traceback.format_exc()
        # Raise a new exception with the original exception message and line number
        print(f'[-][readJSON] Error reading from json bucket: Error:{e}, Line:{line_number}, Traceback:{traceback_str}')
        return 'Something went wrong', 500
    

def writeJSON(config, data, debug):
    try:
        # # Authenticate using the service account key
       # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get('DBSettings', 'credFile')
        bucket_name = config.get('DBSettings', 'BucketName')
        json_file_name = config.get('DBSettings', 'DatabaseName')

        # Read the JSON file from Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if debug == 1: print(f'[+][writeJSON] Successfully connected to bucket')
        blob = bucket.blob(json_file_name)

        # Write the modified data back to the JSON file
        json_data_modified = json.dumps(data)
        blob.upload_from_string(json_data_modified)
        if debug == 1: print(f'[+][writeJSON] Updated database uploaded to GCP bucket.')
        return 'JSON file read, modified, and written successfully!', 200

    except Exception as e:
        # Get the current exception information
        exc_type, exc_obj, tb = sys.exc_info()
        # Get the line number where the exception occurred
        line_number = traceback.extract_tb(tb)[-1][1]
        # Get the full traceback as a string
        traceback_str = traceback.format_exc()
        # Raise a new exception with the original exception message and line number
        print(f'[-][writeJSON] Error writing to json bucket: Error:{e}, Line:{line_number}, Traceback:{traceback_str}')
        return 'Something went wrong', 500

def cleanJSON(config, debug):
    try:
        # # Authenticate using the service account key
        #os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get('DBSettings', 'credFile')
        bucket_name = config.get('DBSettings', 'BucketName')
        json_file_name = config.get('DBSettings', 'DatabaseName')
        scan_time_frame = config.getint('settings', 'ScanTimeframe') * 3600

        # Read the JSON file from Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if debug == 1: print(f'[+][cleanJSON] Successfully connected to bucket')
        blob = bucket.blob(json_file_name)
        
        if not blob.exists():
            if debug == 1: print(f'[][cleanJSON] No database found.  Creating one...')
            # Create an empty JSON file
            empty_data = {}
            empty_json_data = json.dumps(empty_data)
            blob.upload_from_string(empty_json_data, content_type='application/json')
            if debug == 1: print(f'[+][cleanJSON] New database uploaded to GCP bucket.')
            return
        json_data = blob.download_as_text()
        data = json.loads(json_data)
        if debug == 1: print(f'[+][cleanJSON] Successfully read database')

        #Get current epoch time
        current_utc_time = int(time.time())
        #Clean up the data
        change = 0
        for i in list(data):
            #Get the epoch time of the post
            post_time = data[i]['createdTime']
            #Get the difference between the post time and current time
            time_diff = current_utc_time - post_time
            #If the difference is greater than scan time frame setting, remove the post
            if time_diff > scan_time_frame:
                if debug == 1: print(f'[+][cleanJSON] Old post id {data[i]} found, removing.')
                data.pop(i)
                change = 1

        if change:
            # Write the modified data back to the JSON file
            json_data_modified = json.dumps(data)
            blob.upload_from_string(json_data_modified)
            if debug == 1: print(f'[+][cleanJSON] Updated database uploaded to GCP bucket {data}.')
            return 'JSON file read, modified, and written successfully!', 200

    except Exception as e:
        # Get the current exception information
        exc_type, exc_obj, tb = sys.exc_info()
        # Get the line number where the exception occurred
        line_number = traceback.extract_tb(tb)[-1][1]
        # Get the full traceback as a string
        traceback_str = traceback.format_exc()
        # Raise a new exception with the original exception message and line number
        print(f'[-][cleanJSON] Error cleaning json bucket: Error:{e}, Line:{line_number}, Traceback:{traceback_str}')
        return 'Something went wrong', 500
