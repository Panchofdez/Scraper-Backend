from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import time
import re
import os
from collections import Counter

PRODUCTION = True


class JobScraper(object):
    chrome_options = Options()

    def __init__(self):
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--window-size=1920x1080")
        if PRODUCTION:
            self.chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
            self.chrome_options.add_argument("--disable-dev-shm-usage")
            self.chrome_options.add_argument("--no-sandbox")
            path = os.environ.get("CHROMEDRIVER_PATH")
        else:
            path = r"C:\Program Files (x86)\chromedriver_win32\chromedriver.exe"
        self.driver = webdriver.Chrome(executable_path =path, chrome_options=self.chrome_options)

    def glassdoor(self,job_type, num_jobs=30):
        
        self.driver.get("https://glassdoor.com/Job/index.htm")
        self.driver.implicitly_wait(3)
        
        search = self.driver.find_element_by_id("KeywordSearch")
        location = self.driver.find_element_by_id("LocationSearch")
        button = self.driver.find_element_by_id("HeroSearchButton")
        search.send_keys(job_type)
        button.click()
        job_postings = []
        break_early = False
        start = time.perf_counter()
        while len(job_postings) <= num_jobs:
            
            jobs = self.driver.find_elements_by_class_name("react-job-listing")
            print(len(jobs))

            if len(jobs) == 0:
                return job_postings

            for job in jobs:
                if len(job_postings) >= num_jobs:
                    break_early = True
                    break
                jobData = {"rating":"", "company": "", "salary":"", "title":"", "link":"", "description":""}
                try:
                    popup = self.driver.find_element_by_class_name("modal_main")
                    if popup:
                        close = popup.find_element_by_class_name("modal_closeIcon")
                        close.click()
                except NoSuchElementException or StaleElementReferenceException as err:
                   pass

                try:
                    #get the description, if unable to retrieve description just skip the job posting 
                    ActionChains(self.driver).move_to_element(job).click(job).perform()
                    self.driver.implicitly_wait(1)
                    jobinfo = self.driver.find_element_by_id("JDCol")
                    more_button = jobinfo.find_element_by_class_name("css-t3xrds")
                    ActionChains(self.driver).move_to_element(more_button).click(more_button).perform()
                    self.driver.implicitly_wait(4)
                    jobData["description"]= jobinfo.find_element_by_class_name("jobDescriptionContent").text
                    
                except NoSuchElementException as err:
                    print("No such element error in retrieving description\n", err)
                    continue
                
                except StaleElementReferenceException as err:
                   print("Stale element error in retrieving description\n", err)
                   continue

                try:
                    elements = job.find_elements(By.TAG_NAME, "span")
                    for idx, e in enumerate(elements):
                        item = e.text
                        if item.strip() != "":
                            if idx == 1:
                                jobData["rating"] = item
                            elif idx == 2:
                                jobData["company"] = item
                            elif idx == 5:
                                jobData["title"] = item
                            elif idx == 7:
                                jobData["salary"] = item
               
                except NoSuchElementException as err:
                    print("No such element error in retrieving span elements\n", err)
                
                except StaleElementReferenceException as err:
                   print("Stale element error in retrieving span elements\n", err)

                try:
                    jobData["link"] = job.find_element_by_class_name("jobLink").get_attribute("href")
                except NoSuchElementException as err:
                    print("No such element error in retrieving link\n", err)
                
                except StaleElementReferenceException as err:
                   print("Stale element error in retrieving link\n", err)
                


                print(jobData)
                job_postings.append(jobData)

                #if it takes too long then just end the loop
                end = time.perf_counter()
                if end -start > 360:
                    print("TOOK TOO LONG")
                    break_early = True
                    break
            
            if break_early:
                break
            
            #if its ok then just load the next page.
            next_btn = self.driver.find_element_by_class_name('css-1yshuyv')
            try:
              
                ActionChains(self.driver).move_to_element(next_btn).click(next_btn).perform()
                self.driver.implicitly_wait(4)
                print("Button Clicked")
            except NoSuchElementException as err:
                print("No such element error in retrieving next button\n", err)
                break
                
            except StaleElementReferenceException as err:
                print("Stale element error in retrieving next button\n", err)
                break
            
        self.driver.quit()
        return job_postings
            
    def indeed(self,job_type, num_jobs=30):
        #CURRENTLY DOES NOT WORK AS INDEED IS BLOCKING 
        self.driver.get("https://ca.indeed.com")
        self.driver.implicitly_wait(3)
        search = self.driver.find_element_by_name("q")
        location = self.driver.find_element_by_name("l")
        button = self.driver.find_element_by_class_name("icl-WhatWhere-buttonWrapper")
        search.send_keys(job_type)
        self.driver.implicitly_wait(1)
        print("BUTTON", button)
        try:
            ActionChains(self.driver).move_to_element(button).click(button).perform()
            print("clicked")
            self.driver.implicitly_wait(3)
        except Exception as err:
            print(err)

        jbpostings = []
        while len(jbpostings) < num_jobs:
            
            self.driver.implicitly_wait(1)
            try:
                popup = self.driver.find_element_by_id("popover-foreground")
                closeBtn = popup.find_element_by_class_name("icl-CloseButton")
                closeBtn.click()
            except NoSuchElementException:
                pass
            jobs = self.driver.find_elements_by_class_name("jobsearch-SerpJobCard")
            if len(jobs) <= 0:
                return
            for job in jobs:

                if len(jbpostings) >= num_jobs:
                    break

                try:
                    title = job.find_element_by_class_name("jobtitle").text
                    link = job.find_element_by_link_text(title).get_attribute('href')
                    job.click()
                except NoSuchElementException:
                    title=""
                    link=""
                try:
                    description = self.driver.find_element_by_id("vjs-desc").text
                except NoSuchElementException:
                    description=""
                company = job.find_element_by_class_name("company").text
                location = job.find_element_by_class_name("location").text
                try:
                    salary = job.find_element_by_class_name("salarySnippet").text
                except NoSuchElementException:
                    salary=""
                

                data={"title":title, "company": company, "salary":salary,"location":location, "description": description, "link":link}
                print("DATA", data)
                jbpostings.append(data)
            Nextbtn = self.driver.find_element_by_xpath("//a[@aria-label='Next']")
            ActionChains(self.driver).click(Nextbtn).perform()
        print("length", len(jbpostings))

        self.driver.quit()
        return jbpostings

    # def analyse_text(self,data):
    #     words = []
    #     for job in data:
    #         res = re.findall(r"\b[a-zA-z/\-+#.]+\b", job["description"].lower())
    #         words.extend(res)
    #     counter = Counter(words)
    #     return counter

    # def find_by_languages(self,data, technologies):
    #     technologies.reverse()
    #     string = r""
    #     for word in technologies:
    #         if "+#".find(word[-1]) == -1:
    #             string += rf"\b{re.escape(word)}\b|"
    #         else:
    #             string += rf"\b{re.escape(word)}|"
    #     words = []
    #     for job in data:
    #         matches = re.findall(string[:len(string)-1], job["description"].lower(), flags=re.IGNORECASE)
    #         words.extend(matches)
    #         tech = Counter(matches)
    #         job["technologies"] = tech
    #         score = 0
    #         for k in tech.keys():
    #             try:
    #                 score += technologies.index(k) + 1 
    #             except:
    #                 pass 
    #         job["score"] = score
    #     counter = Counter(words)
    #     return counter

    # def sort_by_tech(self, data):
    #     return sorted(data, key=lambda x:x["score"], reverse=True)


# scraper = JobScraper()
# data = scraper.indeed("Software Engineer", 10)
# data = scraper.glassdoor("Software Engineer", 20)
# tech = ["python", "javascript", "java","c++", "c#", "react", "angular", "vue", "aws", "sql", "docker", "asp.net", "postgresql"]
# print("NUM JOBS", len(data))
# print(scraper.find_by_languages(data, tech))
# jobs = scraper.sort_by_tech(data)
# for job in jobs:
#     print(job["title"])
#     print(job["score"])
