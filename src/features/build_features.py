
# imports
import re
import os
import pickle
import pandas as pd
import numpy as np
from functools import reduce

# Remove rookies from stats
def remove_rookies(stats, rookies):
    
    COLS = ['Player','Year']

    no_rookies = stats.merge(rookies, indicator=True, how='outer')
    no_rookies = no_rookies[no_rookies['_merge'] == 'left_only']
    del no_rookies['_merge']
    
    save_dataset(no_rookies,"../data/interim/norookiestats.pickle")
    
    return no_rookies

# Merge stats with salaries
def salary_merge(salaries, no_rookies):
    
    salaries['Player'] = salaries['Player'].map(lambda x: x.replace(' Jr.',""))
    no_rookies['Player'] = no_rookies['Player'].map(lambda x: x.replace('.',""))
    data_all = pd.merge(salaries,no_rookies, on=['Player','Year'], how='left')
    
    # Remove unnecessary columns that happened on merge conflict
#     data_all.rename(columns={'Tm_x': 'Tm','Pos_x':'Pos','MP_x':'MP'}, inplace=True)
    
    # Drop players that have too many missing stat information
    playerinfo =['Player','Tm','Salary','Year','Pos']
    rest = data_all.columns.difference(playerinfo)
    played = data_all.dropna(thresh=20)
    
    return played

# Merge the FA list into the stats list
def FA_merge(played, freeagents):
    
    FA_check = played.merge(freeagents, indicator=True, how='left')
    played["FA"] = FA_check["_merge"]
    played["FA"] = played["FA"].str.replace("left_only",'No').replace("both","Yes")
    played = played[~played['FA'].isnull()]
    
    # I chose to fill Null values with 0
    played = played.fillna(0)
    
    return played

# Accumulate stats of 3 past seasons and update the list with it
def accumulate_stats(played,stats):
    
    totallist=['MP', 'FG', 'FGA','3P', '3PA',  '2P', 
           '2PA', 'FT', 'FTA', 'ORB', 'DRB', 
           'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']
    
    for i in range(played.shape[0]):
        curr = played.iloc[i].Player
        curryear = played.iloc[i].Year
        years  = [curryear, curryear-1, curryear-2]
        threeyrs = stats[(stats.Player == curr) & (stats.Year.isin(years))]
        if threeyrs.shape[0] > 1:
            print("Update row "+str(i))
            for stat in totallist:
                played.iloc[i, played.columns.get_loc(stat)] = (reduce((lambda x, y: x + y), 
                                  [k*v for k,v in zip(threeyrs[stat],threeyrs.G)])) #/ threeyrs.G.sum()
            played.iloc[i, played.columns.get_loc('G')] = threeyrs.G.sum()#/len(threeyrs)
            played.iloc[i, played.columns.get_loc('GS')] = threeyrs.GS.sum()#/len(threeyrs)
    
    return played

# Clean salaries data
def clean_salaries_dataset(path, filename):
    money = pickle.load(open(path+"/"+filename, "rb"))
    combined={}
    
    for k,v in money.items():
        calendar = str(k)+"/"+str(k-1999).zfill(2)
        print(calendar)
        temp = v[['Player',calendar]]
        temp["Year"] = k
        temp = temp.rename(columns={calendar:"Salary"})
        combined[k]=temp
    
    salaries = reduce(lambda x,y:pd.concat([x,y]),[v for k,v in combined.items()])
    salaries["Salary"] = salaries["Salary"].str.replace('$','').str.replace(',','')
    salaries.Salary = salaries.Salary.astype(int)
    
    return salaries
    
# Clean stats (regular and advanced) data   
def clean_stats_dataset(path, filename1, filename2):
    stats = pickle.load(open(path+"/"+filename2, "rb"))
    advs = pickle.load(open(path+"/"+filename1, "rb"))
    
    for i,j in stats.items():
        temp = j 
        temp['total'] = (temp['Tm'] == 'TOT')
        temp = temp.sort_values('total', ascending=False).drop_duplicates(['Player','Age']).drop('total', 1)
        stats[i]=temp
        
    for i,j in advs.items():
        temp = j 
        temp['total'] = (temp['Tm'] == 'TOT')
        temp = temp.sort_values('total', ascending=False).drop_duplicates(['Player','Age']).drop('total', 1)
        advs[i]=temp
        
    combined={}
    for (a1,b1),(a2,b2) in zip(stats.items(),advs.items()):
        df = b1.merge(b2, how="inner",on=["Player","Age","Pos","Tm","G"])#,"MP"])
        combined[a1]=df.sort_values("Player")
        print("Stats Row for "+str(a1)+": "+str(b1.shape[0])
              +", Adv Row for "+str(a2)+": "+str(b2.shape[0])+", After combined: "+str(df.shape[0]))
    
    for k,v in combined.items():
        v=v.drop(['Rk_x','Unnamed: 19','Unnamed: 24', 'Rk_y','MP_y'], axis=1)
        v['Year'] = k
        combined[k]=v
    
    combined_stats = reduce(lambda x,y:pd.concat([x,y]),[v for k,v in combined.items() if k != 2019 or k != 2008])
    combined_stats = combined_stats.reset_index(drop=True);
    
    unchanged = ['Player','Pos','Tm','Year']
    intlist = ['Age','G','GS']
    floatlist= combined_stats.columns.difference(unchanged+intlist)
    
    combined_stats[intlist] = combined_stats[intlist].astype(int)
    combined_stats[floatlist] = combined_stats[floatlist].astype(float)
    combined_stats.rename(columns={'MP_x':'MP'}, inplace=True)
    
    return combined_stats

# Clean rookies data
def clean_rookies_dataset(path, filename):
    rookies = pickle.load(open(path+"/"+filename, "rb"))
    
    combined_rookies = pd.DataFrame()
    for v,k in rookies.items():
        temp = rookies[v][rookies[v].Player != 'Player']
        temp = temp[~(temp.Player.isnull())]
        temp['Year']=v
        combined_rookies = pd.concat([combined_rookies,temp])
    
    return combined_rookies

# Clean FA data
def clean_fa_dataset(path, filename):
    freeagents = pickle.load(open(path+"/"+filename, "rb"))
    FAS={}
    for k,v in freeagents.items():
        v.columns=[re.sub(r"Player.+","Player",col) for col in v.columns]
        v.columns=[re.sub(r"\d+ Cap Hit","Cap Hit",col) for col in v.columns]
        v["Year"] = k
        FAS[k]=v
    
    freeagents = reduce(lambda x,y:pd.concat([x,y]),[v for k,v in FAS.items() if k != 2019])
    freeagents = freeagents[['Player','Year']]
    
    return freeagents

# Build overall dataset
def build_dataset(salaries, stats, rookies, freeagents):
    
    no_rookies = remove_rookies(stats, rookies)
    
    played = salary_merge(salaries, no_rookies)
    
    players = FA_merge(played, freeagents)
    
    return accumulate_stats(players,stats)

# dump file to pickle
def save_features(data,filename):
    with open(filename,"wb") as writer:
        pickle.dump(data,writer)

def run():
    """
    Executes a set of helper functions that read files from data/raw, cleans them,
    and converts the data into a design matrix that is ready for modeling.
    """
    salaries = clean_salaries_dataset('data/raw', "salaries2.pickle")
    stats = clean_stats_dataset('data/raw', "advstats2.pickle", "regstats2.pickle")
    rookies = clean_rookies_dataset('data/raw','rookies2.pickle')
    freeagents = clean_fa_dataset('data/raw','freeagents2.pickle')
    
    save_dataset(salaries, "data/interim/salaries2.pickle")
    save_dataset(stats, "data/interim/stats2.pickle")
    save_dataset(rookies, "data/interim/rookies2.pickle")
    save_dataset(freeagents, "data/interim/fa2.pickle")
    
    full_data = build_dataset(salaries, stats, rookies, freeagents)
    
    save_features(full_data,'data/processed/data2.pickle')
    
    
