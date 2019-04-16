from bs4 import BeautifulSoup as bsoup
from urllib import request
import dateutil.parser as dateparse
import re
from functools import reduce
import pandas as pd
import argparse
import os

argp = argparse.ArgumentParser()
argp.add_argument('-u', '--url', help='main glassdoor url', type=str, default='https://www.glassdoor.ca')
argp.add_argument('-f','--first-page', help='first landing page for company e.g. "/Reviews/<>.htm"', type=str)
argp.add_argument('-o','--output-file', help='output csv file path', type=str, default='result.csv')
args = argp.parse_args()

user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
headers={'User-Agent':user_agent}
parent_url = args.url + '{}'

get_url = parent_url.format(args.first_page)
req = request.Request(get_url, None, headers)
gd_resp = request.urlopen(req)
content = bsoup(gd_resp.read(), 'html.parser')
gd_resp.close()
expired = False

result_df = None

while not expired:
    reviews = content.find_all('div',{'class':'hreview'})

    datetimes = [x.find('time', {'class':'date subtle small'}) for x in reviews]
    datetimes = [dateparse.parse(x.attrs['datetime']) if x is not None else None for x in datetimes]
    
    helpful_count = [x.find('span', {'class':'helpfulCount subtle'}) for x in reviews]
    helpful_count = [re.search(r' *helpful *\((?P<count>\d+)\)',x.text,re.IGNORECASE).group('count') if x is not None else None for x in helpful_count]
    
    headlines = list(map(lambda x: x.find('span', {'class':'summary'}).contents[0].replace('"',''), reviews))

    stars = list(map(lambda x: x.find('span', {'class':'value-title'}).attrs['title'], reviews))

    subratings = [x.find('div', {'class':'subRatings module stars__StarsStyles__subRatings'}) for x in reviews]
    
    subratings_title = [x.find_all('span',{'class':'gdBars gdRatings med'}) if x is not None else None for x in subratings]
    subratings_title = [[y.attrs['title'] for y in x] if x is not None else None for x in subratings_title]
    
    subratings_name = [x.find_all('div',{'class':'minor'}) if x is not None else None for x in subratings]
    subratings_name = [[y.text for y in x] if x is not None else None for x in subratings_name]
    
    subratings_keys = reduce(lambda x,y: x.union(y),map(lambda x: set(x) if x is not None else set(), subratings_name))
    subratings =  {x: [] for x in subratings_keys}
    for x,y in zip(subratings_name,subratings_title):
        if x is not None:
            for k,v in zip(x,y):
                subratings[k].append(v)
            for missing in subratings_keys.difference(x):
                subratings[missing].append(None)
        else:
            for k in subratings_keys:
                subratings[k].append(None)
            
    if 'Comp & Benefits' in subratings:
        subratings['comp_rating'] = subratings.pop('Comp & Benefits')
    if 'Work/Life Balance' in subratings:
        subratings['work_life_rating'] = subratings.pop('Work/Life Balance')
    if 'Career Opportunities' in subratings:
        subratings['career_rating'] = subratings.pop('Career Opportunities')
    if 'Culture & Values' in subratings:
        subratings['culture_rating'] = subratings.pop('Culture & Values')
    if 'Senior Management' in subratings:
        subratings['management_rating'] = subratings.pop('Senior Management')
                   
    author = list(map(lambda x: re.findall(r'^(.+?) \- (.+)$',x.find('span',{'class':'authorJobTitle middle reviewer'}).contents[0])[0], reviews))
    author_status = list(map(lambda x: x[0], author))
    author_role = list(map(lambda x: x[1], author))

    recommend = [x.find('div',{'class':'row reviewBodyCell recommends'}) for x in reviews]
    
    outlook_positive = [x.find('span',string='Positive Outlook') if x is not None else None for x in recommend]
    outlook_neutral = [x.find('span',string='Neutral Outlook') if x is not None else None for x in recommend]
    outlook_negative = [x.find('span',string='Negative Outlook') if x is not None else None for x in recommend]
    
    outlook_positive = [x.text if x is not None else '' for x in outlook_positive]
    outlook_neutral = [x.text if x is not None else '' for x in outlook_neutral]
    outlook_negative = [x.text if x is not None else '' for x in outlook_negative]
    outlook = [(x + y + z).replace(' Outlook','') for x,y,z in zip(outlook_positive, outlook_neutral, outlook_negative)]
    
    recommends_positive = [x.find('span',string='Recommends') if x is not None else None for x in recommend]
    recommends_negative = [x.find('span',string='Doesn\'t Recommend') if x is not None else None for x in recommend]
    
    recommends_positive = [x.text if x is not None else '' for x in recommends_positive]
    recommends_negative = [x.text if x is not None else '' for x in recommends_negative]
    recommended = [x + y for x,y in zip(recommends_positive, recommends_negative)]
    
    ceo_approve = [x.find('span', string='Approves of CEO') if x is not None else None for x in recommend]
    ceo_neutral = [x.find('span', string='No opinion of CEO') if x is not None else None for x in recommend]
    ceo_disapprove = [x.find('span', string='Disapproves of CEO') if x is not None else None for x in recommend]
    
    ceo_approve = [x.text if x is not None else '' for x in ceo_approve]
    ceo_neutral = [x.text if x is not None else '' for x in ceo_neutral]
    ceo_disapprove = [x.text if x is not None else '' for x in ceo_disapprove]
    approve_ceo = [(x + y + z).replace(' of','') for x,y,z in zip(ceo_approve, ceo_neutral, ceo_disapprove)]

    longevity = list(map(lambda x: x.find('p',{'class':'mainText mb-0'}), reviews))
    longevity = [re.findall(r'at [\w\d]+ (.+)',x.text.replace('\xa0',u' '), re.IGNORECASE+re.DOTALL)[0] if x is not None else '' for x in longevity]

    text_main = list(map(lambda x: x.find('div', {'class':'description'}).find_all('div',{'class':'mt-md'}), reviews))
        
    text_pros = map(lambda x: [y.find('p',{'class':'strong'},string='Pros') for y in x], text_main)
    text_pros = map(lambda x: [y.next_sibling.text if y is not None else '' for y in x], text_pros)
    text_pros = list(map(lambda x: reduce(lambda a,b: a+b,x), text_pros))
    
    text_cons = map(lambda x: [y.find('p',{'class':'strong'},string='Cons') for y in x], text_main)
    text_cons = map(lambda x: [y.next_sibling.text if y is not None else '' for y in x], text_cons)
    text_cons = list(map(lambda x: reduce(lambda a,b: a+b,x), text_cons))
    
    text_advice = map(lambda x: [y.find('p',{'class':'strong'},string='Advice to Management') for y in x], text_main)
    text_advice = map(lambda x: [y.next_sibling.text if y is not None else '' for y in x], text_advice)
    text_advice = list(map(lambda x: reduce(lambda a,b: a+b,x), text_advice))
    
    result = pd.DataFrame({'date':datetimes, 'helpful':helpful_count, 'headline':headlines, 'overall_rating':stars, **subratings,
          'author_status':author_status, 'author_role':author_role,
          'recommend':recommended, 'outlook':outlook, 'approve_ceo':approve_ceo,
          'longevity':longevity, 'pros':text_pros, 'cons':text_cons, 'advice':text_advice})
    if result_df is None:
        result_df = result.copy()
    else:
        result_df = pd.concat([result_df,result])

    next_page = content.find('link', {'rel':'next'})
    if next_page is not None:
        get_url = next_page.attrs['href']
        req = request.Request(get_url, None, headers)
        gd_resp = request.urlopen(req)
        content = bsoup(gd_resp.read(), 'html.parser')
        gd_resp.close()
    else:
        expired = True
    
    result_df[['pros','cons','advice']] = reduce(lambda x,y: pd.concat([x,y],axis=1), map(lambda x: result_df[x].apply(lambda y: str(y)), ['pros','cons','advice']))
    
if not os.path.exists(os.path.dirname(os.path.abspath(args.output_file))):
    os.makedirs(os.dirname(args.output_file))
result_df.to_csv(args.output_file,index=False)