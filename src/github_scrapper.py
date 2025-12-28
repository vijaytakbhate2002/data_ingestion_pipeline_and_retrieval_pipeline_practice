import requests
import json
import certifi
import os
from xhtml2pdf import pisa
import markdown
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN_GITHUB = os.getenv('TOKEN_GITHUB')
if not TOKEN_GITHUB:
    raise RuntimeError("GITHUB token not found in environment!")


class GithubScrapper:

    HEADERS = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "readme-pdf-generator",
        "Authorization": f"Bearer {TOKEN_GITHUB}"
        }

    def __init__(self, username:str, save_folder:str) -> None:
        self.username = username
        self.github_restapi = f"https://api.github.com/users/{username}/repos?per_page=100"
        self.save_folder = save_folder



    def getProfileInfo(self) -> list:
        """
        This function will return all the repositories metadata in dictionary format
        Reutrn:     
            list
        """
        url = f"https://api.github.com/users/{self.username}/repos?per_page=100"
        response = requests.get(url, headers=self.HEADERS, verify=certifi.where())
        response.raise_for_status()
        return response.json()

    

    def getRepoInfo(self, profile_metadata:list) -> list:
        """
        This functin will iterate through every readme file meatadata and return list of required metadata of respective repositories
        Return: 
            list
        """

        readme_contents = []

        for repo_info in profile_metadata:

            repo_name = repo_info["name"]
            repo_api = f"https://api.github.com/repos/{self.username}/{repo_name}/readme"

            response = requests.get(repo_api, headers=self.HEADERS)

            if response.status_code != 200:
                print(response.status_code)
                print(f"❌ Failed to fetch REPO METADATA for {repo_name}")
                continue

            print(f" Successfully fetched REPO METADATA for {repo_name}")

            data = response.json()  
            data['owner'] = self.username
            data['repo_name'] = repo_name

            readme_contents.append(data)
        return readme_contents
    

    
    def saveAsPDF(self, repo_info:dict) -> None:
        """
        Args: 
            repo_info: this is a dictionary with metadata of single readme file, including url and name
        Hit's readme api, convert the markdown content into pdf format and it will save it

        Return:
            None
        """
        print("ENtered into save pdf...")
        try:
            markdown_content = requests.get(repo_info['download_url']).content
            markdown_content = markdown_content.decode('utf-8')
            repo_name = repo_info['repo_name']
            repo_name = repo_name + ".pdf"
        except Exception as e:
            return print(e)

        print(f" ............................... {repo_name} ..............................................................")

        html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])

        styled_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Helvetica, sans-serif; font-size: 12px; line-height: 1.5; color: #333; }}
                h1, h2, h3 {{ color: #24292e; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
                h1 {{ font-size: 2em; }}
                h2 {{ font-size: 1.5em; }}
                code {{ background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; }}
                pre {{ background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 6px; }}
                blockquote {{ border-left: 4px solid #dfe2e5; color: #6a737d; padding: 0 1em; }}
                img {{ max-width: 100%; }}
                a {{ color: #0366d6; text-decoration: none; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        output_path = os.path.join(self.save_folder, repo_name)

        try:
            print(f"Converting to PDF: {output_path}...")
            with open(output_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(styled_html, dest=pdf_file)
            
            if pisa_status.err:
                print(f"Error generating PDF for {output_path}")
                return False
            
            print(f"Successfully saved PDF to {output_path}")
            return True
        except Exception as e:
            print(f"Exception converting to PDF: {e}")
            return False
        

    def scrap(self) -> None:
        """
        This is pipeline function which combines all the required processes to scrap read files from github and save these into 
        pdf format
        """

        profile_meatadata = self.getProfileInfo()
        repos_meatadata = self.getRepoInfo(profile_metadata=profile_meatadata)

        # print("......................................Done with repo info fetching ...............................")
        # print(json.dumps(repos_meatadata[2]))
        # print("......................................Done with repo info fetching ...............................")

        for repo_info in repos_meatadata:
            self.saveAsPDF(repo_info=repo_info)

        

if __name__ == "__main__":
    import config
    github_scrapper = GithubScrapper(username=config.GITHUB_USERNAME, save_folder=config.GITHUB_PDF_FOLDER)
    github_scrapper.scrap()

