#Troubleshooting
debug = 0

#TODO
#Import modules
import configparser, datetime, importlib, json, logging, openai, os, random, re, requests, threading, time
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

def check(site, config, debug):
    #Get setting from config file
    blstFlair = [item.strip() for item in config.get('settings', 'FlairExclusions').split(',')]
    blstTitle = [item.strip() for item in config.get('settings', 'TitleExclusions').split(',')]
    blstPost = [item.strip() for item in config.get('settings', 'PostExclusions').split(',')]
    blstInclusions = [item.strip() for item in config.get('settings', 'Inclusions').split(',')]
    winVer = [item.strip() for item in config.get('settings', 'winVer').split(',')]


    CN = re.findall('r\/\w{2}',site)
    CN = CN[0][2:]
    subredditName = re.findall('https\:\/\/www\.reddit\.com\/r\/(\w+)\/.*', site)

    #GET JSON FROM SUBREDDIT
    try:
        response = requests.get(site, verify=True, timeout=5,headers = {'User-agent': 'Mozilla/5.0 (Windows NT {}; Win64; x64;)'.format(random.choice(winVer))})
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
    for post in range(0,15):
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
            print(f'[-] Error parsing JSON: {e}')
            continue

        #Check exclusion in post body
        if postBody:
            postBody_tmp = postBody.upper()
            for j in blstPost:
                j = j.upper()
                if debug == 1: print(f'[PostEx Check][{subredditName[0]}] CurrentCheck:{j}, Post:{postBody_tmp}')
                if j in postBody_tmp:
                    if debug == 1: print(f'[BAD][{subredditName[0]}] Body keyword exclusion "{j}" on:{postBody_tmp}')
                    bad = 1
                    continue
            if bad == 1: continue

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
            good = 0
            for j in blstInclusions:
                j = j.upper()
                if debug == 1: print(f'[PostIn and TitleIn Check][{subredditName[0]}] CurrentCheck:{j}, Post:{postBody_tmp} Title:{title}')
                if j in postBody_tmp or j in title:
                    if debug == 1: print(f'[GOOD][{subredditName[0]}] keyword "{j}" found on:{postBody_tmp} or {title}')
                    good = 1
                    continue
            if good == 0: continue


        #Check id against database
        try:
            if debug == 1: print(f'[{subredditName[0]}] Checking {id} against database')
            data = readJSON(config, debug)
        except Exception as e:
            print(f'[-] Error checking {id} against database: {e}')

        if id in data:
            if debug == 1: print(f'[BAD][{subredditName[0]}] ID:{id} already in database')
            bad = 1
            continue
        else:
            try:
                #Generate Response
                postResponse = generateResponse(config, author, postBody, debug)
            except Exception as e:
                print(f'[-] Error generating response from OpenAI API: {e}')
                continue
            try:
                #Send email
                print('='*50 + 'EMAIL' + '='*50)
                sendEmail(config, debug, f'{title}',url,subredditName[0], postBody, author, postResponse)
            except Exception as e:
                print(f'[-] Error sending email: {e}')
                continue

            #append id and createdTime as a key:value pair
            data[id] = createdTime
            writeJSON(config, data, debug)


    print('='*50 + f'CHECK {post} COMPLETE ON {subredditName[0]}' + '='*50)


        


def Hosts(config, debug):
    threads = []
    #Get list of uris from config file
    sites = [item.strip() for item in config.get('settings', 'sites').split(',')]
    for uri in sites:
        if debug == 1: print("Trying {}...".format(uri))
        t = threading.Thread(target=check, args=(uri, config, debug,)) #Create thread for each host
        t.daemon = True             #kill process if main thread ends
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

#if __name__ == "__main__":
def main(request):
    
    # Create the parser object
    config = configparser.ConfigParser()
    config.read('config.ini')

    cleanJSON(config, debug)

    Hosts(config, debug)
    return "Run Successfully"


#For local host testing
#main('test')