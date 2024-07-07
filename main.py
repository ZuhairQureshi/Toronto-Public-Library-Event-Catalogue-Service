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


url = 'https://www.torontopubliclibrary.ca/search.jsp?N=37867+37744+37848&No=10&Ns=p_pub_date_sort&Nso=0'  # TPL 'Adult' Programs starting page
library_dict = {}

def get_driver():
  ''' This function configures webdriver settings '''
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

  # Counter variables (for output tracing - to ensure all listings are accounted for)
  page_count = 1
  event_count = 1

  # Main scraping loop
  while True:

    # Get HTML and create Soup object
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'html.parser')

    catalogue = soup.find_all('div', class_="row collapse")[2::2]  # get the element encapsulating all program listings

    # Loop through all program listings on the page one-by-one
    for catalogue_item in catalogue:

      event_name = catalogue_item.find('div', class_='title align-top').a.text  # extract the title of the event

      # Extract the library branch, either embedded within the link, or 'Online' otherwise
      try:
        location = catalogue_item.find('div', class_="date-location").a.text   

      except:
        location = "Online"

      descrip = catalogue_item.find('div', class_='description').p.text.strip()  # get the truncated description

      
      start_date = catalogue_item.find('span', class_='start-date').text   # get the date 

       # Advise user to check website if the date is non-specific
      if start_date == 'on recurring dates listed below': 
        start_date = 'On recurring dates (please view link)'

      # Output tracing to ensure scraping matches webdriver activity
      print(start_date)
      print(f"Event: {event_name} ({event_count})")
      print(f"Location: {location}")
      print(f"Description: {descrip}")
      
      event_count += 1

      # Redirect the webdriver to the next program listing and trace url
      sub_url = "https://www.torontopubliclibrary.ca" + catalogue_item.a['href'] + "\n"
      driver.get(sub_url)
      print(driver.current_url)
      print("\n")

      # Order listings by library location
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

    # Return to listings page, so that 'Next' button can be located
    driver.get(url)

    # Check for the existence of the 'Next' button (i.e. if there is another page)
    if soup.find('li', class_='pagination-next') is not None:
      route = soup.find('li', class_='pagination-next').a['href']
      url = "https://www.torontopubliclibrary.ca/" + route 
      driver.get(url)
      page_count += 1
  
    else:
      break  # no 'Next' page indicates the final page has been scraped, so break the main loop

  library_dict = dict(sorted(library_dict.items()))  # alphabetically arrange the dictionary by location branch

  generate_pdf()  # when the main loop, begin preparing the PDF 


def generate_pdf():
  '''This function creates the PDF using webscraped library program data according to branch location'''
  pdf = FPDF(orientation='P', unit='pt', format='A4')
  pdf.add_page()

  # Create title of PDF and center it 
  pdf.set_font(family='Times', style='B', size=24)
  pdf.cell(w=0, h=50, txt="Library Programs This Week", align='C', ln=1)

  # Go through each listing by branch 
  for location in library_dict:

    # Display the location name 
    pdf.set_font(family='Times', style='B', size=16)
    pdf.cell(w=0, h=30, txt=location, ln=1)

    # Loop through every single listing associated with the library branch
    for i in range(len(library_dict[location]['Event'])):

      # Extract all listing information 
      event = library_dict[location]['Event'][i]
      descrip = library_dict[location]['Description'][i]
      link = library_dict[location]['Link'][i]
      date = library_dict[location]['Date'][i]
      
      # Display event information
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Event', ln=1)
      
      pdf.set_font(family='Times', size=12)
      pdf.multi_cell(w=0, h=15, txt=event)

      # Display date information
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Date', ln=1)

      pdf.set_font(family='Times', size=12)
      pdf.multi_cell(w=0, h=15, txt=date)
      
      # Display description
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Description', ln=1)

      pdf.set_font(family='Times', size=12)
      pdf.multi_cell(w=0, h=15, txt=descrip)

      # Display link, prompt viewer to click
      pdf.set_font(family='Times', style='B', size=14)
      pdf.cell(w=0, h=30, txt='Link:', ln=1)

      pdf.set_font(family='Times', size=12)
      pdf.set_text_color(0, 0, 238)
      pdf.cell(w=0, h=15, txt="Click to read more", link=link, ln=1)
      pdf.set_text_color(0, 0, 0)
      
      pdf.cell(w=0, h=20, ln=1)

  pdf.output('Upcoming Library Events.pdf')  # output the PDF File
  
  send_email()  # prepare the email


def send_email():
  '''This function emails the end-user with the condensed PDF catalogue'''

  # Create credentials
  sender = 'SENDEREMAIL@gmail.com'
  receiver ='RECEIVEREMAIL@gmail.com'
  password = os.getenv('PASSWORD')
  subject = "Toronto Public Libraries' Upcoming Programs"

  # Put brief explainer, attach PDF, and email
  contents = ['''This PDF contains the 'Adult' listings for Toronto Public Library programs taking place in the next 7 days.''', 'Upcoming Library Events.pdf']

  yag = yagmail.SMTP(user=sender, password=password)
  yag.send(to=receiver, subject=subject, contents=contents)
  print("Mail sent.")


main()
