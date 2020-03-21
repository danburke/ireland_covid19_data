#%%

from bs4 import BeautifulSoup, SoupStrainer
import requests
import pandas as pd
import re
import numpy as np

##%%

# define some helper functions

def get_press_release_links(
        base_url: str = 'https://www.gov.ie',
        page_url: str = '/en/news/7e0924-latest-updates-on-covid-19-coronavirus/') -> list:
    url = f'{base_url}{page_url}'
    page = requests.get(url)
    data = page.text
    soup = BeautifulSoup(data)

    links = []
    for link in soup.find_all('a'):
        link_href = link.get('href')
        if link_href:
            if '/en/press-release/' in link_href:
                if link_href[0:4] == '/en/':
                    links.append(f"{base_url}{link_href}")
                else:
                    links.append(link_href)
    return links

##%%

# get all press releases
press_release_links = get_press_release_links()
print(press_release_links)

##%%

# create some empty dataframes to collect data into
df_hospital_statistics = pd.DataFrame()
df_gender = pd.DataFrame()
df_age = pd.DataFrame()
df_spread = pd.DataFrame()
df_healthcare_workers = pd.DataFrame()
df_county = pd.DataFrame()

# loop over each press release, pull out tables and wrangle accordingly
for press_release_link in press_release_links:

    print(f"... getting tables from {press_release_link} ...")
    page = requests.get(press_release_link)
    data = page.text
    soup = BeautifulSoup(data)
    num_tables = len(soup.find_all('table'))

    # get published date from the press release
    published_search = re.search('Published:(.*)2020', data, re.IGNORECASE)
    if published_search:
        published_date = published_search.group(1).strip()
    else:
        published_date = ''
    date_cleaner = [
        ('March', '03'),
        ('April', '04'),
        ('May', '05'),
    ]
    for month_string, month_num in date_cleaner:
        if month_string in published_date:
            published_date = published_date.replace(month_string, '').strip()
            published_date = published_date.strip().zfill(2)
            published_date = f'2020-{month_num}-{published_date}'

    # if tables found then try process them
    if num_tables > 0:

        print(f"... {num_tables} tables found ...")

        # read all tables into a list of data frames
        df_list = pd.read_html(press_release_link)

        # now process each data frame
        for df in df_list:

            # add a tag to each df relating to what table it is from
            df_list_tagged = []

            for df in df_list:

                raw_data = '|'.join([str(x).lower() for x in df.values.tolist()])

                if 'total number of cases' in raw_data:
                    tag = 'hospital_statistics'
                    df = df.rename({0: 'measure', 1: 'number', 2: 'pct'}, axis='columns')
                elif 'male' in raw_data:
                    tag = 'gender'
                    df = df.rename({0: 'gender', 1: 'number', 2: 'pct'}, axis='columns')
                elif 'community transmission' in raw_data:
                    tag = 'spread'
                    df = df.rename({0: 'measure', 1: 'number', 2: 'pct'}, axis='columns')
                    df['pct'] = np.where(df['number'].astype(str).str.contains('%'), df['number'], df['pct'])
                elif 'travel related' in raw_data:
                    tag = 'healthcare_workers'
                    df = df.rename({0: 'measure', 1: 'number', 2: 'pct'}, axis='columns')
                elif 'dublin' in raw_data:
                    tag = 'county'
                    df = df.rename({0: 'county', 1: 'metric', 2: 'pct'}, axis='columns')
                elif ('age group' in raw_data) & ('<1' in raw_data):
                    tag = 'age'
                    df = df.rename({0: 'age', 1: 'number', 2: 'pct'}, axis='columns')
                elif ('<5' in raw_data) & ('65+' in raw_data):
                    tag = 'age_hospital'
                else:
                    tag = 'UNKNOWN'

                # clean up data a bit
                if 'number' in df.columns:
                    df = df[df['number'] != 'Number of people']
                    df = df[df['number'] != 'Number']
                    df = df[df['number'] != '% known']
                    df['number'] = np.where(df['number'].astype(str).str.contains('%'), np.nan, df['number'])
                    df['number'] = df['number'].astype(float)
                if 'pct' in df.columns:
                    df = df[df['pct'] != '% of total']
                    df['pct'] = df['pct'].astype(str).str.replace('%', '').astype(float) / 100
                if 'metric' in df.columns:
                    df = df[df['metric'] != 'Number of cases']

                # add some metadata
                df['tag'] = tag
                df['published_date'] = published_date
                df['source'] = press_release_link
                df_list_tagged.append(df)
                #print(df_list_tagged)

        # break out df's and append to df specific for each table in the html
        for df in df_list_tagged:
            tag = df['tag'].unique()[0]
            if tag == 'hospital_statistics':
                df_hospital_statistics = df_hospital_statistics.append(df)
                df_hospital_statistics = df_hospital_statistics.dropna(how='all', axis=1)
            elif tag == 'gender':
                df_gender = df_gender.append(df)
                df_gender = df_gender.dropna(how='all', axis=1)
            elif tag == 'age':
                df_age = df_age.append(df)
                df_age = df_age.dropna(how='all', axis=1)
            elif tag == 'spread':
                df_spread = df_spread.append(df)
                df_spread = df_spread.dropna(how='all', axis=1)
            elif tag == 'healthcare_workers':
                df_healthcare_workers = df_healthcare_workers.append(df)
                df_healthcare_workers = df_healthcare_workers.dropna(how='all', axis=1)
            elif tag == 'county':
                df_county = df_county.append(df)
                df_county = df_county.dropna(how='all', axis=1)

    else:

        print("... no tables found ...")

##%%

# save as csv to data folder
df_hospital_statistics.to_csv('data/hospital_statistics.csv', index=False)
df_gender.to_csv('data/gender.csv', index=False)
df_age.to_csv('data/age.csv', index=False)
df_spread.to_csv('data/spread.csv', index=False)
df_healthcare_workers.to_csv('data/healthcare_workers.csv', index=False)
df_county.to_csv('data/county.csv', index=False)
