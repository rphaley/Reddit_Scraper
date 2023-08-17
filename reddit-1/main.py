#Troubleshooting
debug = 1

#TODO
#Import modules
import configparser, datetime, importlib, json, logging, openai, os, queue, random, re, requests, sys, threading, time, traceback
#Import custom modules
from sendEmail import sendEmail
from processDB import cleanJSON, readJSON, writeJSON
from response import generateResponse
#Import Google Cloud modules
try:
    if os.environ["GCP_Hosted"]:
        
        if debug == 1: print(f'[+] GCP found, installing dependencies')
        import google.cloud.logging
        from google.cloud import storage

        #Setup logging
        client = google.cloud.logging.Client()
        client.get_default_handler()
        client.setup_logging()
except Exception as e:
    print(f'[-] Error importing GCP modules in main.py: {e}')


#if debug == 1: print(f'[+] ENV Vars: {os.environ}')

def check(site, config, data, db_queue, debug):
    #Get setting from config file
    blstFlair = [item.strip() for item in config.get('settings', 'FlairExclusions').split(',')]
    blstTitle = [item.strip() for item in config.get('settings', 'TitleExclusions').split(',')]
    blstPost = [item.strip() for item in config.get('settings', 'PostExclusions').split(',')]
    blstInclusions = [item.strip() for item in config.get('settings', 'Inclusions').split(',')]
    blstFeatInclusions = [item.strip() for item in config.get('settings', 'FeatureInclusions').split(',')]
    blstLocInclusions = [item.strip() for item in config.get('settings', 'LocationInclusions').split(',')]
    winVer = [item.strip() for item in config.get('settings', 'winVer').split(',')]


    CN = re.findall('r\/\w{2}',site)
    CN = CN[0][2:]
    subredditName = re.findall('https\:\/\/www\.reddit\.com\/r\/(\w+)\/.*', site)

    #GET JSON FROM SUBREDDIT
    try:
        response = requests.get(site, verify=True, timeout=5,headers = {f'User-agent': 'Mozilla/5.0 (Windows NT {random.choice(winVer)}; Win64; x64;)'})
    except Exception as e:
        print(f"[-] Client Error retrieving web data from {subredditName} Reason:{e}")
        logging.warning(f"[-] HTTP Client Error retrieving web data from {subredditName} Reason:{e}")
    
    #Check for HTTP Errors
    try:
        parsed_json = json.loads(response.content)
        if response.status_code != 200:
            if debug == 1: print(f"[-] Server Error retrieving web data from {subredditName}")
            if b'error' in parsed_json:
                print(f"[-] Reddit error: Reason: '{parsed_json['reason']}' Message: '{parsed_json['message']}' from {subredditName}")
                return
            
    except Exception as e:
        print(f"[-] Error retrieving web data from {subredditName} Reason:{e}")
        logging.warning(f"[-] Error retrieving web data from {subredditName} Reason:{e}")
        return
    
    #Iterate through posts
    for post in range(0,50):
        #Check for stickied threads
        bad = 0
        #Check is thread is stickied, ignore
        if parsed_json['data']['children'][post]['data']['stickied'] == True:
            if debug == 1: print(f'Stickied Thread in {subredditName}, ignoring')
            continue
        try:
            #Parse specific output
            flair = parsed_json['data']['children'][post]['data']['link_flair_text']
            title = parsed_json['data']['children'][post]['data']['title']
            postBody = parsed_json['data']['children'][post]['data']['selftext']
            author = parsed_json['data']['children'][post]['data']['author']
            id = parsed_json['data']['children'][post]['data']['id']
            createdTime = parsed_json['data']['children'][post]['data']['created_utc']
            url = parsed_json['data']['children'][post]['data']['url']
            if debug == 1: print(f'Flair:{flair}, Title:{title}, URL:{url}') 
        except Exception as e:
            # Get the current exception information
            exc_type, exc_obj, tb = sys.exc_info()
            # Get the line number where the exception occurred
            line_number = traceback.extract_tb(tb)[-1][1]
            # Get the full traceback as a string
            traceback_str = traceback.format_exc()
            # Raise a new exception with the original exception message and line number
            print(f'[-] Error parsing JSON: Error:{e}, Line:{line_number}, Traceback:{traceback_str}')
            continue

        #Check id against database
        if id in data:
            if debug == 1: print(f'[BAD][{subredditName[0]}] ID:{id} already in database')
            bad = 1
            continue

        postBad = 0
        #Check exclusion in post body
        if postBody:
            postBody_tmp = postBody.upper()
            for j in blstPost:
                j = j.upper()
                if debug == 1: print(f'[PostEx Check][{subredditName[0]}] CurrentCheck:{j}, Post:{postBody_tmp}')
                if j in postBody_tmp:
                    if debug == 1: print(f'[BAD][{subredditName[0]}] Body keyword exclusion "{j}" on:{postBody_tmp}')
                    postBad = postBad + 1
                    continue
            if postBad > 1: continue

        #Check exclusion in title
        if title:
            title = title.upper()
            age = title[0:2]
            #cast age to int
            try:
                age = int(age)
                if int(age) < 25 or int(age) > 40:
                    if debug == 1: print(f'[BAD][{subredditName[0]}] Incorrect age:{age} on:{title}')
                    bad = 1
                    continue
            except ValueError:
                continue

            for j in blstTitle:
                j = j.upper()
                if debug == 1: print(f'[TitleEx Check][{subredditName[0]}] CurrentCheck:{j}, Title:{title}')
                if j in title:
                    if debug == 1: print(f'[BAD][{subredditName[0]}] Title keyword exclusion "{j}" on:{title}')
                    bad = 1
                    continue
            if bad == 1: continue

        #Check exclusion in flair
        if flair:
            flair = flair.upper()
            for k in blstFlair:
                k = k.upper()
                if debug == 1: print(f'[FlairEx Check][{subredditName[0]}] CurrentCheck:{k}, Title:{flair}')
                if k in flair:
                    if debug == 1: print(f'[BAD][{subredditName[0]}] Flair keyword exclusion "{k}" on:{flair}')
                    bad = 1
                    continue
            if bad == 1: continue

        #Check inclusion in post body or title
        if postBody and title:
            postBody_tmp = postBody.upper()
            title = title.upper()
            #Create list of keywords found for quality check
            keywork_match_lst = []

            #set default good value to false
            locGood = 0
            for loc in blstLocInclusions:
                loc = loc.upper()
                if debug == 1: print(f'[LocationInclusionCheck][{subredditName[0]}] CurrentCheck:{loc}, Post:{postBody_tmp} Title:{title}')
                if loc in postBody_tmp or loc in title:
                    if debug == 1: print(f'[LocationInclusionCheck][GOOD][{subredditName[0]}] keyword "{loc}" found on:{postBody_tmp.rstrip()} or {title}')
                    if loc in postBody_tmp:
                        keywork_match_lst.append(loc)
                        if debug == 1: print(f'[LocationInclusionCheck][GOOD][{subredditName[0]}] Post keyword "{loc}" found on:{postBody_tmp}')
                        locGood = locGood + 1
                    elif loc in title:
                        keywork_match_lst.append(loc)
                        if debug == 1: print(f'[LocationInclusionCheck][GOOD][{subredditName[0]}] Title keyword "{loc}" found on:{title}')
                        locGood = locGood + 1
            if locGood == 0: continue


            #set default good value to false
            featGood = 0
            for feat in blstFeatInclusions:
                feat = feat.upper()
                if debug == 1: print(f'[FeatureInclusionCheck][{subredditName[0]}] CurrentCheck:{feat}, Post:{postBody_tmp} Title:{title}')
                if feat in postBody_tmp or feat in title:
                    if debug == 1: print(f'[FeatureInclusionCheck][GOOD][{subredditName[0]}] keyword "{feat}" found on:{postBody_tmp.rstrip()} or {title}')
                    if feat in postBody_tmp:
                        keywork_match_lst.append(feat)
                        if debug == 1: print(f'[FeatureInclusionCheck][GOOD][{subredditName[0]}] Post keyword "{feat}" found on:{postBody_tmp}')
                        featGood = featGood + 1
                    elif feat in title:
                        keywork_match_lst.append(feat)
                        if debug == 1: print(f'[FeatureInclusionCheck][GOOD][{subredditName[0]}] Title keyword "{feat}" found on:{title}')
                        featGood = featGood + 1
            if featGood == 0: continue


            for j in blstInclusions:
                j = j.upper()
                if debug == 1: print(f'[InclusionCheck][{subredditName[0]}] CurrentCheck:{j}, Post:{postBody_tmp} Title:{title}')
                if j in postBody_tmp or j in title:
                    if debug == 1: print(f'[InclusionCheck][GOOD][{subredditName[0]}] keyword "{j}" found on:{postBody_tmp.rstrip()} or {title}')
                    if j in postBody_tmp:
                        keywork_match_lst.append(j)
                        if debug == 1: print(f'[InclusionCheck][GOOD][{subredditName[0]}] Post keyword "{j}" found on:{postBody_tmp}')
                    elif j in title:
                        keywork_match_lst.append(j)
                        if debug == 1: print(f'[InclusionCheck][GOOD][{subredditName[0]}] Title keyword "{j}" found on:{title}')



        #We got to the end, process post
        try:
            #Generate Response
            postResponse = generateResponse(config, author, postBody, debug)
        except Exception as e:
            print(f'[-] Error generating response from OpenAI API: {e}')
            continue
        try:
            #Send email
            print('='*50 + 'EMAIL' + '='*50)
            sendEmail(config, debug, f'{title}',url,subredditName[0], postBody, author, postResponse, keywork_match_lst)
        except Exception as e:
            print(f'[-] Error sending email: {e}')
            continue

        #update database with new post id and created time and keyword match
        data[id] = {"createdTime":createdTime,"keywordMatch":keywork_match_lst}
        db_queue.put(data)


    print('='*50 + f'CHECK {post} COMPLETE ON {subredditName[0]}' + '='*50)


        


def Hosts(config, debug):
    threads = []
    #Read JSON database from GCP bucket
    try:
        if debug == 1: print(f'Reading database from GCP bucket')
        data = readJSON(config, debug)
    except Exception as e:
        print(f'[-] Error checking {id} against database: {e}')
        return

    #Get list of uris from config file
    sites = [item.strip() for item in config.get('settings', 'sites').split(',')]
    db_queue = queue.Queue()
    for uri in sites:
        if debug == 1: print("Trying {}...".format(uri))
        t = threading.Thread(target=check, args=(uri, config, data, db_queue, debug,)) #Create thread for each host
        #kill process if main thread ends
        t.daemon = True            
        # Start the thread, which will execute the 'check' function in parallel with the main thread
        t.start()
        # Add the thread to the 'threads' list so we can keep track of it
        threads.append(t)
    # After creating all threads, wait for each thread to complete before proceeding
    for t in threads:
        t.join()
    
    db_writer(db_queue, config)


def db_writer(db_queue, config):
    while not db_queue.empty():
        try:
            if debug == 1: print(f'Starting db_writer function')
            item = db_queue.get()
            if debug == 1: print(f'Got item from queue')
            if item is None:  # Sentinel value to stop the thread
                break
            
            writeJSON(config, item, debug)
            if debug == 1: print(f'Wrote item to json bucket')
            db_queue.task_done()
        except queue.Empty:
            # Handle an empty queue exception
            if debug == 1: print(f'Empty queue')
            return
        except Exception as e:
            print(f'[-] Error writing to json bucket: Error:{e}')
            return 'Something went wrong', 500

#if __name__ == "__main__":
def main(request):
    
    # Create the parser object
    config = configparser.ConfigParser()
    config.read('config.ini')

    cleanJSON(config, debug)

    Hosts(config, debug)
    return "Run Successfully"


#For local host testing
main('test')