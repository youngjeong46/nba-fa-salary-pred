
# imports
import pandas as pd
import time
from datetime import datetime
import os
import pickle

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException       
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

def check_exists(driver,classname):
    try:
        driver.find_element_by_class_name(classname)
    except NoSuchElementException:
        return False
    return True

def initialize_selenium(URL):
    # initialize selenium
    chromedriver = "/Applications/chromedriver" 
    os.environ["webdriver.chrome.driver"] = chromedriver
    driver = webdriver.Chrome(chromedriver)
    driver.get(URL)
    
    return driver  

# Generate dictionary to store our data per year
def data_to_dict(years):
    """
    Generate Dictionary that will store our data per year in this format:
    
    Key (Year): Value (Data)
    
    years: int indicating how many years of data will be stored
    """
    data = {}
    CURRENT_YEAR = int(datetime.now().year)
    years_label = range(CURRENT_YEAR-1,CURRENT_YEAR-years,-1)
    
    return years_label, data
    
def download_salary_data(URL,years):
    
    years_label, data = data_to_dict(years)
    driver = initialize_selenium(URL)

    for i in in years_label:
        time.sleep(2)
        df = pd.read_html(driver.current_url)[0] 
        while check_exists(driver,'jcarousel-next-disabled') == False:
            next = driver.find_element_by_class_name('jcarousel-next')
            next.click()
            time.sleep(5)
            temp = pd.read_html(driver.current_url)[0]
            df = df.append(temp,ignore_index=True)
        years = Select(driver.find_element_by_class_name('tablesm'))
        years.select_by_visible_text(str(i-1)+"-"+str(i))
        data[i]=df
    
    driver.quit()
    
    return data

def download_rookie_data(URL, years):
    
    years_label, data = data_to_dict(years)
    driver = initialize_selenium(URL)
    wait = WebDriverWait(driver, 10)
    
    for i in years_label:
        df = pd.read_html(driver.current_url)[0]
        df.columns=df.columns.droplevel()
        df = df[['Player']]
        data[i]=df
        prev_year = driver.find_element_by_css_selector("a.button2.prev")
        prev_year.click()
        time.sleep(10)
    
    driver.quit()
    
    return data
    
    
def download_player_data(URL, years, type_data):
    
    years_label, data = data_to_dict(years)
    driver = initialize_selenium(URL)
    wait = WebDriverWait(driver, 10)
    
    # get to the current season stats, this may have changed
    tab = driver.find_elements_by_id("header_leagues")
    hover = ActionChains(driver).move_to_element(tab[0])
    hover.perform()
    wait.until(EC.visibility_of_element_located((By.LINK_TEXT, type_data))).click()
    
    for i in years_label:
        df = pd.read_html(driver.current_url)[0]
        df = df[df.Rk != 'Rk']
        data[i]=df
        prev_year = driver.find_element_by_css_selector("a.button2.prev")
        prev_year.click()
        time.sleep(10)
    
    driver.quit()
    
    return data

def download_fa_data(URL):
    years_label, data = data_to_dict(years)
    driver = initialize_selenium(URL)

    for i in range(2018,2010,-1):
        years = Select(driver.find_element_by_name('year'))
        years.select_by_visible_text(str(i))
        submit = driver.find_element_by_class_name('go')
        submit.click()
        time.sleep(10)
        df = pd.read_html(driver.current_url)[0]
        data[i]=df
        
    return data

def save_dataset(data,filename):
    with open(filename, 'wb') as w:
        pickle.dump(data,w)
        
def run():
    """
    Executes a set of helper functions that download data from one or more sources
    and saves those datasets to the data/raw directory.
    """
    data_fa = download_fa_data("https://www.spotrac.com/nba/free-agents/")
    data_reg = download_player_data("https://www.basketball-reference.com", 12, "Per G")
    data_adv = download_player_data("https://www.basketball-reference.com", 12, "Advanced")
    data_salary = download_salary_data("http://www.espn.com/nba/salaries/_/year/2019", 12)
    data_rookie = download_rookie_data("https://www.basketball-reference.com/leagues/NBA_2018_rookies.html", 12)
    save_dataset(data_fa, "data/raw/datafa.pickle")
    save_dataset(data_reg, "data/raw/regstats.pickle")
    save_dataset(data_adv, "data/raw/advstats.pickle")
    save_dataset(data_salary, "data/raw/salaries.pickle")
    save_dataset(data_rookie, "data/raw/rookies.pickle")
