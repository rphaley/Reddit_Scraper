import json, os, time
try:
    if os.environ["GCP_Hosted"]:
        print(f'[+] GCP found, installing dependencies')
        from google.cloud import storage
except Exception as e:
    print(f'[-] Error importing GCP modules in processDB.py: {e}')



def readJSON(config, debug):
    try:
        # # Authenticate using the service account key
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get('DBSettings', 'credFile')
        bucket_name = config.get('DBSettings', 'BucketName')
        json_file_name = config.get('DBSettings', 'DatabaseName')

        # Read the JSON file from Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if debug == 1: print(f'[+] Successfully connected to bucket')
        blob = bucket.blob(json_file_name)

        json_data = blob.download_as_text()
        if debug == 1: print(f'[+] Successfully read database')
        data = json.loads(json_data)

        return data

    except Exception as e:
        print(f'[-] Error reading from json bucket: {e}')
        return 'Something went wrong', 500
    

def writeJSON(config, data, debug):
    try:
        # # Authenticate using the service account key
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get('DBSettings', 'credFile')
        bucket_name = config.get('DBSettings', 'BucketName')
        json_file_name = config.get('DBSettings', 'DatabaseName')

        # Read the JSON file from Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if debug == 1: print(f'[+] Successfully connected to bucket')
        blob = bucket.blob(json_file_name)

        # Write the modified data back to the JSON file
        json_data_modified = json.dumps(data)
        blob.upload_from_string(json_data_modified)
        if debug == 1: print(f'[+] Updated database uploaded to GCP bucket.')
        return 'JSON file read, modified, and written successfully!', 200

    except Exception as e:
        print(f'[-] Error writing to json bucket: {e}')
        return 'Something went wrong', 500

def cleanJSON(config, debug):
    try:
        # # Authenticate using the service account key
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.get('DBSettings', 'credFile')
        bucket_name = config.get('DBSettings', 'BucketName')
        json_file_name = config.get('DBSettings', 'DatabaseName')

        # Read the JSON file from Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if debug == 1: print(f'[+] Successfully connected to bucket')
        blob = bucket.blob(json_file_name)
        
        if not blob.exists():
            if debug == 1: print(f'[] No database found.  Creating one...')
            # Create an empty JSON file
            empty_data = {}
            empty_json_data = json.dumps(empty_data)
            blob.upload_from_string(empty_json_data, content_type='application/json')
            if debug == 1: print(f'[+] New database uploaded to GCP bucket.')
            return
        json_data = blob.download_as_text()
        data = json.loads(json_data)
        if debug == 1: print(f'[+] Successfully read database')

        #Get current epoch time
        current_utc_time = int(time.time())
        #Clean up the data
        for i in list(data):
            #Get the epoch time of the post
            post_time = data[i]
            #Get the difference between the post time and current time
            time_diff = current_utc_time - post_time
            #If the difference is greater than 24 hours, remove the post
            if time_diff > 86400:
                data.pop(i)

    except Exception as e:
        print(f'[-] Error cleaning json bucket: {e}')
        return 'Something went wrong', 500