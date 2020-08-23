from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import time
import re
from collections import Counter


class JobScraper(object):
    path = r"C:\Program Files (x86)\chromedriver_win32\chromedriver.exe"
    def __init__(self):
        self.driver = webdriver.Chrome(executable_path =self.path, chrome_options=self.options)
    def glassdoor(self,job_type, num_jobs=30):
        
        self.driver.get("https://glassdoor.com/Job/index.htm")
        self.driver.implicitly_wait(3)
        
        search = self.driver.find_element_by_id("KeywordSearch")
        location = self.driver.find_element_by_id("LocationSearch")
        button = self.driver.find_element_by_id("HeroSearchButton")
        search.send_keys(job_type)
        button.click()
        job_postings = []
        while len(job_postings) <= num_jobs:
            self.driver.implicitly_wait(5)
            
            jobs = self.driver.find_elements_by_class_name("react-job-listing")
            for job in jobs:
                if len(job_postings) > num_jobs:
                    break
                try:
                    popup = self.driver.find_element_by_class_name("modal_main")
                    if popup:
                        close = popup.find_element_by_class_name("modal_closeIcon")
                        close.click()
                    print("closed")
                except NoSuchElementException or StaleElementReferenceException:
                    pass
                try:
                    link = job.find_element_by_css_selector("div.jobHeader > a").get_attribute('href')
                except NoSuchElementException or StaleElementReferenceException:
                    link =""
                try:
                    rating = job.find_element_by_class_name("compactStars").text
                except NoSuchElementException or StaleElementReferenceException:
                    rating=""
                try:
                    salary = job.find_element_by_class_name("salary").text
                except NoSuchElementException or StaleElementReferenceException:
                    salary=""
                try: 
                    company = job.find_element_by_class_name("jobEmpolyerName").text
                except NoSuchElementException or StaleElementReferenceException:
                    company=""
                ActionChains(self.driver).move_to_element(job).click(job).perform()
                self.driver.implicitly_wait(5)
                
                jobinfo = self.driver.find_element_by_id("JDCol")
                
                try:
                    title = jobinfo.find_element_by_class_name("title").text 
                except NoSuchElementException or StaleElementReferenceException:
                    title=""
                try:
                    description = jobinfo.find_element_by_class_name("jobDescriptionContent").text
                except NoSuchElementException or StaleElementReferenceException:
                    description=""
                
                jobData = {"rating": rating, "title":title, "link": link, "company": company, "salary":salary, "description": description}

                job_postings.append(jobData)

        
        self.driver.quit()
        return job_postings
            
    def indeed(self,job_type, num_jobs=30):
        self.driver.get("https://indeed.com")
        self.driver.implicitly_wait(5)
        search = self.driver.find_element_by_name("q")
        location = self.driver.find_element_by_name("l")
        button = self.driver.find_element_by_class_name("icl-Button")
        search.send_keys(job_type)
        button.click()
        jbpostings = []
        while len(jbpostings) < num_jobs:
    
            self.driver.implicitly_wait(5)
            try:
                popup = self.driver.find_element_by_id("popover-foreground")
                closeBtn = popup.find_element_by_class_name("icl-CloseButton")
                closeBtn.click()
            except NoSuchElementException:
                pass
            jobs = self.driver.find_elements_by_class_name("jobsearch-SerpJobCard")
            for job in jobs:
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
                jbpostings.append(data)
            Nextbtn = self.driver.find_element_by_xpath("//a[@aria-label='Next']")
            Nextbtn.click()
        print("length", len(jbpostings))
        time.sleep(2)
        self.driver.quit()
        return jbpostings

    def analyse_text(self,data):
        words = []
        for job in data:
            res = re.findall(r"\b[a-zA-z/\-+#.]+\b", job["description"].lower())
            words.extend(res)
        counter = Counter(words)
        return counter

    def find_by_languages(self,data, technologies):
        technologies.reverse()
        string = r""
        for word in technologies:
            if "+#".find(word[-1]) == -1:
                string += rf"\b{re.escape(word)}\b|"
            else:
                string += rf"\b{re.escape(word)}|"
        words = []
        for job in data:
            matches = re.findall(string[:len(string)-1], job["description"].lower(), flags=re.IGNORECASE)
            words.extend(matches)
            tech = Counter(matches)
            job["technologies"] = tech
            score = 0
            for k in tech.keys():
                try:
                    score += technologies.index(k) + 1 
                except:
                    pass 
            job["score"] = score
        counter = Counter(words)
        return counter

    def sort_by_tech(self, data):
        return sorted(data, key=lambda x:x["score"], reverse=True)


scraper = JobScraper()
data = scraper.indeed("Software Engineer", 10)
tech = ["python", "javascript", "java","c++", "c#", "react", "angular", "vue", "aws", "sql", "docker", "asp.net"]
print(scraper.find_by_languages(data, tech))
# jobs = sort_by_tech(data)
# for job in jobs:
#     print(job["title"])
#     print(job["score"])
