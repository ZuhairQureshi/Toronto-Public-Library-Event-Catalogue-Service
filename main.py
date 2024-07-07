from selenium import webdriver
import pandas as pd
from bs4 import BeautifulSoup
import requests
import time
import datetime
from selenium.webdriver.common.keys import Keys
from fpdf import FPDF
import yagmail
import os 

url = 'https://www.torontopubliclibrary.ca/search.jsp?N=37867+37744+37848&No=10&Ns=p_pub_date_sort&Nso=0'

library_dict = {}

def get_driver():
  options = webdriver.ChromeOptions()
  options.add_argument("disable-infobars")
  options.add_argument("start-maximized")
  options.add_argument("disable-dev-shm-usage")
  options.add_argument("no-sandbox")
  options.add_experimental_option("excludeSwitches", ["enable-automation"])
  options.add_argument("disable-blink-features=AutomationControlled")

  driver = webdriver.Chrome(options=options)
  driver.get(url)
  return driver


def main():
  global url 
  global library_dict
  driver = get_driver()

  page_count = 1
  event_count = 1

  while True:

    html_text = requests.get(url).text.replace("<br>", "")
    soup = BeautifulSoup(html_text, 'html.parser')
  
    catalogue = soup.find_all('div', class_="row collapse")[2::2]
    print(page_count)
    for catalogue_item in catalogue:
      event_name = catalogue_item.find('div', class_='title align-top').a.text

      try:
        location = catalogue_item.find('div', class_="date-location").a.text

      except:
        location = "Online"
        
      descrip = catalogue_item.find('div', class_='description').p.text.strip()

      start_date = catalogue_item.find('span', class_='start-date').text
      start_time = catalogue_item.find('div', class_='start-time') 
      end_time = catalogue_item.find('div', class_='end-time')
      print(start_date)
      if start_date == 'on recurring dates listed below':
        start_date = 'On recurring dates (please view link)'
        
      print(f"Event: {event_name} ({event_count})")
      print(f"Location: {location}")
      print(f"Description: {descrip}")
      
      event_count += 1
      
      sub_url = "https://www.torontopubliclibrary.ca" + catalogue_item.a['href'] + "\n"
      driver.get(sub_url)
      print(driver.current_url)
      print("\n")

      if location not in library_dict:
        library_dict[location] = {
          'Event':[],
          'Description': [],
          'Date': [],
          'Link': []
        }

      library_dict[location]['Event'].append(event_name)
      library_dict[location]['Description'].append(descrip)
      library_dict[location]['Link'].append(driver.current_url)
      library_dict[location]['Date'].append(start_date)

    driver.get(url)
  
    if soup.find('li', class_='pagination-next') is not None:
      route = soup.find('li', class_='pagination-next').a['href']
      url = "https://www.torontopubliclibrary.ca/" + route 
      driver.get(url)
      page_count += 1
  
    else:
      break

  library_dict = dict(sorted(library_dict.items()))

  generate_pdf()


def generate_pdf():
  pdf = FPDF(orientation='P', unit='pt', format='A4')
  pdf.add_page()

  pdf.set_font(family='Times', style='B', size=24)
  pdf.cell(w=0, h=50, txt="Library Programs This Week", align='C', ln=1)
  
  for location in library_dict:
    
    pdf.set_font(family='Times', style='B', size=16)
    pdf.cell(w=0, h=30, txt=location, ln=1)
    
    for i in range(len(library_dict[location]['Event'])):

      event = library_dict[location]['Event'][i]
      descrip = library_dict[location]['Description'][i]
      link = library_dict[location]['Link'][i]
      date = library_dict[location]['Date'][i]
      
      # Event
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Event', ln=1)
      
      pdf.set_font(family='Times', size=12)
      pdf.multi_cell(w=0, h=15, txt=event)

      #Date
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Date', ln=1)

      pdf.set_font(family='Times', size=12)
      pdf.multi_cell(w=0, h=15, txt=date)
      
      # Description
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Description', ln=1)

      pdf.set_font(family='Times', size=12)
      pdf.multi_cell(w=0, h=15, txt=descrip)

      # Link
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Link:', ln=1)

      pdf.set_font(family='Times', size=12)
      pdf.set_text_color(0, 0, 238)
      pdf.cell(w=0, h=15, txt="Click to read more", link=link, ln=1)
      pdf.set_text_color(0, 0, 0)
      
      pdf.cell(w=0, h=20, ln=1)
    
  pdf.output('Upcoming Library Events.pdf')
  send_email()


def send_email():
  sender = 'zqu71658@gmail.com'
  receiver ='selclovelena@gmail.com'
  password = os.getenv('PASSWORD')
  subject = "Toronto Public Libraries' Upcoming Programs"

  contents = ['''This PDF contains the 'Adult' listings for Toronto Public Library programs taking place in the next 7 days.''', 'Upcoming Library Events.pdf']

  yag = yagmail.SMTP(user=sender, password=password)
  yag.send(to=receiver, subject=subject, contents=contents)
  print("Mail sent.")

send_email()
