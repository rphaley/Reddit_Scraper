#Troubleshooting
debug = 0

#TODO
#Import modules
import configparser, datetime, importlib, json, logging, openai, os, praw, queue, random, re, requests, sys, threading, time, traceback
from datetime import datetime
#Import custom modules
from sendEmail import sendEmail
from processDB import cleanJSON, readJSON, writeJSON
from response import generateResponse
#Import Google Cloud modules
# try:
#     if os.environ["GCP_Hosted"]:
        
#         if debug == 1: print(f'[+] GCP found, installing dependencies')
#         import google.cloud.logging
#         from google.cloud import storage

#         #Setup logging
#         client = google.cloud.logging.Client()
#         client.get_default_handler()
#         client.setup_logging()
# except Exception as e:
#     print(f'[-] Error importing GCP modules in main.py: {e}')


#Print environment variables
#if debug == 1: print(f'[+] ENV Vars: {os.environ}')




def check(site, config, data, db_queue, debug):
    #Get setting from config file
    blstFlair = [item.lstrip() for item in config.get('settings', 'FlairExclusions').split(',')]
    blstTitle = [item.lstrip() for item in config.get('settings', 'TitleExclusions').split(',')]
    blstPost = [item.lstrip() for item in config.get('settings', 'PostExclusions').split(',')]
    blstInclusions = [item.lstrip() for item in config.get('settings', 'Inclusions').split(',')]
    blstFeatInclusions = [item.lstrip() for item in config.get('settings', 'FeatureInclusions').split(',')]
    blstLocInclusions = [item.lstrip() for item in config.get('settings', 'LocationInclusions').split(',')]
    blstTime = config.getint('settings', 'ScanTimeframe') * 3600
    app_id = config.get('REDDITSettings', 'app_id')
    secret = config.get('REDDITSettings', 'secret')


    subredditName = site

    # Get calling IP address
    if debug == 1: 
        try:
            r = requests.get('http://ipinfo.io/ip')
            print(r.text)
        except Exception as e:
            print(f'[-] Error getting public IP: {e}')

    # Authenticate with Reddit
    reddit = praw.Reddit(
        client_id=app_id,
        client_secret=secret,
        user_agent="script:v1.0.0",
    )

    #GET JSON FROM SUBREDDIT
    try:
        #response = requests.get(site, verify=True, timeout=5,headers = {f'User-agent': random.choice(user_agents)})
        posts = reddit.subreddit(site).new(limit=75)
    except Exception as e:
        print(f"[-] Client Error retrieving web data from {subredditName} Reason:{e}")
        logging.warning(f"[-] HTTP Client Error retrieving web data from {subredditName} Reason:{e}")
    
    # #Check for HTTP Errors
    # try:
    #     if debug == 1: print(f'[+] Response status code: {response.status_code}')
    #     if debug == 1: print(f'[+] Response content: {response.content[:500]}')
    #     try:
    #         parsed_json = json.loads(response.content)
    #     except ValueError as e:
    #         print(f'[-] Error parsing JSON: {e}')
    #         return

    #     if response.status_code != 200:
    #         if debug == 1: print(f"[-] Server Error retrieving web data from {subredditName}")
    #         if b'error' in parsed_json:
    #             print(f"[-] Reddit error: Reason: '{parsed_json['reason']}' Message: '{parsed_json['message']}' from {subredditName}")
    #             return
            
            
    # except Exception as e:
    #     print(f"[-] Error retrieving web data from {subredditName} Reason:{e}")
    #     logging.warning(f"[-] Error retrieving web data from {subredditName} Reason:{e}")
    #     return
    
    #Iterate through posts
    for post in posts:
        #post = vars(post)
        #Check for stickied threads
        bad = 0
        #Check is thread is stickied, ignore
        if post.stickied == True:
            if debug == 1: print(f'Stickied Thread in {subredditName}, ignoring')
            continue
        try:
            #Parse specific output
            flair = post.link_flair_text
            title = post.title
            postBody = post.selftext
            author = post.author.name if post.author else '[deleted]'
            id = post.id
            createdTime = post.created_utc
            url = post.url
            if debug == 1: print(f'Flair:{flair}, Title:{title}, URL:{url}') 
        except Exception as e:
            print(vars(post))
            # Get the current exception information
            exc_type, exc_obj, tb = sys.exc_info()
            # Get the line number where the exception occurred
            line_number = traceback.extract_tb(tb)[-1][1]
            # Get the full traceback as a string
            traceback_str = traceback.format_exc()
            # Raise a new exception with the original exception message and line number
            print(f'[-] Error parsing JSON: Error:{e}, Line:{line_number}, Traceback:{traceback_str}')
            continue

        #Throw away posts with no body
        if postBody == '': continue

        #Check if post is within timeframe
        if int(time.time()) - createdTime > blstTime:
            if debug == 1: print(f'[BAD][{subredditName}][{id}] Post is too old.  Ignoring.')
            continue

        #Check id against database
        if id in data:
            if debug == 1: print(f'[BAD][{subredditName}][{id}] ID:{id} already in database {data}.')
            continue
        else:
            if debug == 1: print(f'[GOOD][{subredditName}][{id}] ID:{id} not in database {data}. Continuing...')

        postBad = 0
        #Check exclusion in post body
        if postBody:
            postBody_tmp = postBody.upper()
            for j in blstPost:
                j = j.upper()
                if debug == 1: print(f'[PostEx Check][{subredditName}][{id}] CurrentCheck:{j}, Post:{postBody_tmp}')
                if j in postBody_tmp:
                    if debug == 1: print(f'[BAD][{subredditName}][{id}] Body keyword exclusion "{j}" on:{postBody_tmp}')
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
                    if debug == 1: print(f'[BAD][{subredditName}][{id}] Incorrect age:{age} on:{title}')
                    bad = 1
                    continue
            except ValueError:
                continue

            for j in blstTitle:
                j = j.upper()
                if debug == 1: print(f'[TitleEx Check][{subredditName}][{id}] CurrentCheck:{j}, Title:{title}')
                if j in title:
                    if debug == 1: print(f'[BAD][{subredditName}][{id}] Title keyword exclusion "{j}" on:{title}')
                    bad = 1
                    continue
            if bad == 1: continue

        #Check exclusion in flair
        if flair:
            flair = flair.upper()
            for k in blstFlair:
                k = k.upper()
                if debug == 1: print(f'[FlairEx Check][{subredditName}][{id}] CurrentCheck:{k}, Title:{flair}')
                if k in flair:
                    if debug == 1: print(f'[BAD][{subredditName}][{id}] Flair keyword exclusion "{k}" on:{flair}')
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
                if debug == 1: print(f'[LocationInclusionCheck][{subredditName}][{id}] CurrentCheck:{loc}, Post:{postBody_tmp} Title:{title}')
                if loc in postBody_tmp or loc in title:
                    if debug == 1: print(f'[LocationInclusionCheck][GOOD][{subredditName}][{id}] keyword "{loc}" found on:{postBody_tmp.rstrip()} or {title}')
                    if loc in postBody_tmp:
                        #keywork_match_lst.append(''.join(c for c in loc if c.isalnum()))
                        keywork_match_lst.append(loc)
                        if debug == 1: print(f'[LocationInclusionCheck][GOOD][{subredditName}][{id}] Post keyword "{loc}" found on:{postBody_tmp}')
                        locGood = locGood + 1
                    elif loc in title:
                        #keywork_match_lst.append(''.join(c for c in loc if c.isalnum()))
                        keywork_match_lst.append(loc)
                        if debug == 1: print(f'[LocationInclusionCheck][GOOD][{subredditName}][{id}] Title keyword "{loc}" found on:{title}')
                        locGood = locGood + 1
            if locGood == 0: continue


            #set default good value to false
            good = 0
            for feat in blstFeatInclusions:
                feat = feat.upper()
                if debug == 1: print(f'[FeatureInclusionCheck][{subredditName}][{id}] CurrentCheck:{feat}, Post:{postBody_tmp} Title:{title}')
                if feat in postBody_tmp or feat in title:
                    if debug == 1: print(f'[FeatureInclusionCheck][GOOD][{subredditName}][{id}] keyword "{feat}" found on:{postBody_tmp.rstrip()} or {title}')
                    if feat in postBody_tmp:
                        #keywork_match_lst.append(''.join(c for c in feat if c.isalnum()))
                        keywork_match_lst.append(feat)
                        if debug == 1: print(f'[FeatureInclusionCheck][GOOD][{subredditName}][{id}] Post keyword "{feat}" found on:{postBody_tmp}')
                        good = good + 1
                    elif feat in title:
                        #keywork_match_lst.append(''.join(c for c in feat if c.isalnum()))
                        keywork_match_lst.append(feat)
                        if debug == 1: print(f'[FeatureInclusionCheck][GOOD][{subredditName}][{id}] Title keyword "{feat}" found on:{title}')
                        good = good + 1


            for j in blstInclusions:
                j = j.upper()
                if debug == 1: print(f'[InclusionCheck][{subredditName}][{id}] CurrentCheck:{j}, Post:{postBody_tmp} Title:{title}')
                if j in postBody_tmp or j in title:
                    if debug == 1: print(f'[InclusionCheck][GOOD][{subredditName}][{id}] keyword "{j}" found on:{postBody_tmp.rstrip()} or {title}')
                    if j in postBody_tmp:
                        #keywork_match_lst.append(''.join(c for c in j if c.isalnum()))
                        keywork_match_lst.append(j)
                        if debug == 1: print(f'[InclusionCheck][GOOD][{subredditName}][{id}] Post keyword "{j}" found on:{postBody_tmp}')
                        good = good + 1
                    elif j in title:
                        #keywork_match_lst.append(''.join(c for c in j if c.isalnum()))
                        keywork_match_lst.append(j)
                        if debug == 1: print(f'[InclusionCheck][GOOD][{subredditName}][{id}] Title keyword "{j}" found on:{title}')
                        good = good + 1
            if good < 2: continue
            if len(keywork_match_lst) < 2: continue


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
            sendEmail(config, debug, f'{title}',url,subredditName, postBody, author, postResponse, keywork_match_lst)
        except Exception as e:
            print(f'[-] Error sending email: {e}')
            continue

        #update database with new post id and created time and keyword match
        # data[id] = {"createdTime":createdTime,"keywordMatch":keywork_match_lst}
        # db_queue.put(data)
        human_time = str(datetime.fromtimestamp(createdTime).strftime('%Y-%m-%d_%H:%M:%S'))
        db_queue.put({id:{"author":author,"createdTime":createdTime,"humanTime":human_time,"keywordMatch":keywork_match_lst,"subreddit":subredditName,"title":title,"url":url}})


    print('='*50 + f'CHECK {post} COMPLETE ON {subredditName}' + '='*50)


        


def Hosts(config, debug):
    threads = []
    #Read JSON database from GCP bucket
    try:
        if debug == 1: print(f'[Hosts] Reading database from GCP bucket')
        data = readJSON(config, debug)
        if debug == 1: print(f'[+][Hosts] Database read successfully: {data}')
    except Exception as e:
        print(f'[-][Hosts] Error checking {id} against database: {e}')
        return

    #Get list of uris from config file
    subreddits = [item.strip() for item in config.get('settings', 'subreddits').split(',')]

    db_queue = queue.Queue()
    for uri in subreddits:
        if debug == 1: print(f'Trying "{uri}"')
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
    
    db_writer(db_queue, config, data)


def db_writer(db_queue, config, data):
    tmp_json = data
    while not db_queue.empty():
        try:
            if debug == 1: print(f'[db_writer] Starting db_writer function')
            item = db_queue.get()
            if debug == 1: print(f'[db_writer] Got item from queue {item}.')
            if item is None:  # Sentinel value to stop the thread
                break
            combined_dict = tmp_json.copy()
            for key, value in item.items():
                if key in combined_dict:
                    combined_dict[key].update(value)
                else:
                    combined_dict[key] = value
            tmp_json = combined_dict
            if debug == 1: print(f'[db_writer] Added item {item} to process list.')
            db_queue.task_done()
        except queue.Empty:
            # Handle an empty queue exception
            if debug == 1: print(f'[db_writer] Empty queue')
            return
        except Exception as e:
            print(f'[-][db_writer] Error writing to json bucket: Error:{e}')
            return 'Something went wrong', 500
    writeJSON(config, tmp_json, debug)
    if debug == 1: print(f'[db_writer] Wrote new items to json bucket {tmp_json}')

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