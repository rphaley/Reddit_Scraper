#TODO

import requests, json, time, random
from sendEmail import sendEmail

#Phrases to Exclude from Titles
blst =['M4','4F','T','META','[M']
OLDResponse = ''

while True:
    response = requests.get('https://www.reddit.com/r/r4r.json', verify=False, timeout=5,headers = {'User-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:57.0)'})
    #Check for Errors
    if response.content == b'{"message": "Too Many Requests", "error": 429}':
        print("Reddit error requests")
    elif response.status_code != 200:
        print("Error retrieving web data")
        time.sleep(random.randint(30,250))
        continue
    #Parse output
    parsed_json = json.loads(response.content)

    
    #Check if data changed since last visit
    h = 0
    while True:
        print(h)
        bad = 0
        #Check is thread is stickied, ignore
        if parsed_json['data']['children'][h]['data']['stickied'] == True:
            print('Stickied Thread, ignoring')
            h += 1
            continue
        #Ignore thread change
        elif parsed_json['data']['children'][h]['data']['title'] == OLDResponse:
            print('Thread has not changed, ignore')
            print('same')
            bad = 1
            h += 1
            break
        #Thread has changed, update
        else:
            print('Thread has changed, updating')
            i = h
            OLDResponse = parsed_json['data']['children'][h]['data']['title']
            break
    if bad == 1:
        time.sleep(random.randint(30,250))
        continue

    #Parse specific output
    flair = parsed_json['data']['children'][i]['data']['link_flair_text']
    title = parsed_json['data']['children'][i]['data']['title']
    url = parsed_json['data']['children'][i]['data']['url']
    title = title.upper()

    
    #Check for empty string
    if not flair:
        for j in blst:
            if j in title:
                bad = 1
                break
        if bad == 0:
            sendEmail('{}\n'.format(title),url)
            print('[REDDIT]{}\n{}\n'.format(title,url))
        continue
    #Check if flair is found
    flair = flair.upper()
    for k in blst:
        if k in flair:
            bad = 1
            break  
    if bad == 0 and flair[0]!='M':
        sendEmail('[{}] {}'.format(flair,title),url)
        print('[REDDIT][{}] {}\n{}\n'.format(flair,title,url))
        continue
    print("Check Complete")
    time.sleep(random.randint(30,250))

