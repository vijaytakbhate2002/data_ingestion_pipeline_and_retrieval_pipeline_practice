import requests
import json
import certifi
import os
from xhtml2pdf import pisa
import markdown
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

log_file = os.path.join(os.getcwd(), "logs.log")

if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_file
           for h in logger.handlers):
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        handler.setLevel(logging.DEBUG)

        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.debug("Logging initialized to %s", log_file)
    except Exception:
        pass


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
    

    def __init__(self, username:str, save_folder:str, metadata_save_folder:str) -> None:
        self.username = username
        self.github_restapi = f"https://api.github.com/users/{username}/repos?per_page=100"
        self.save_folder = save_folder
        self.metadata_save_folder = metadata_save_folder



    def getProfileInfo(self) -> list:
        """
        This function will return all the repositories metadata in dictionary format
        Reutrn:     
            list
        """
        url = f"https://api.github.com/users/{self.username}/repos?per_page=100"
        logger.info("Fetching profile info for user %s from %s", self.username, url)
        response = requests.get(url, headers=self.HEADERS, verify=certifi.where())
        response.raise_for_status()
        logger.debug("Profile info fetched: status=%s", response.status_code)
        return response.json()

    

    def getRepoInfo(self, profile_metadata:list) -> list:
        """
        This functin will iterate through every readme file meatadata and return list of required metadata of respective repositories
        Return: 
            list
        """

        readme_contents = []

        for repo_info in profile_metadata:

            usable_data = {}

            repo_name = repo_info["name"]
            created_at = repo_info['created_at']
            updated_at = repo_info['updated_at']
            pushed_at = repo_info['pushed_at']
            language = repo_info['language']
            full_name = repo_info['full_name']
            private = repo_info['private']
            description = repo_info['description']
            repo_url = repo_info['html_url']

            repo_api = f"https://api.github.com/repos/{self.username}/{repo_name}/readme"

            logger.debug("Requesting README for repo: %s url=%s", repo_name, repo_api)
            response = requests.get(repo_api, headers=self.HEADERS)

            if response.status_code != 200:
                logger.warning("Failed to fetch REPO METADATA for %s, status=%s", repo_name, response.status_code)
                print(response.status_code)
                print(f"❌ Failed to fetch REPO METADATA for {repo_name}")
                continue

            logger.info("Successfully fetched REPO METADATA for %s", repo_name)
            print(f" Successfully fetched REPO METADATA for {repo_name}")

            data = response.json()  

            usable_data['download_url'] = data.get('download_url')
            usable_data['repository_url'] = repo_url
            usable_data['repo_name'] = repo_name
            usable_data['created_at'] = created_at
            usable_data['updated_at'] = updated_at
            usable_data['pushed_at'] = pushed_at
            usable_data['language'] = language
            usable_data['full_name'] = full_name
            usable_data['private'] = private
            usable_data['description'] = description
            usable_data['size'] = data.get('size')

            readme_contents.append(usable_data)
        
        with open(self.metadata_save_folder, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        metadata['github'] = readme_contents
        logger.info("Writing metadata to %s (%d repos)", self.metadata_save_folder, len(readme_contents))

        with open(self.metadata_save_folder, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        logger.debug("Wrote metadata to %s", self.metadata_save_folder)
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
        logger.info("saveAsPDF started for repo: %s", repo_info.get('repo_name', '<unknown>'))
        try:
            markdown_content = requests.get(repo_info['download_url']).content
            markdown_content = markdown_content.decode('utf-8')
            repo_name = repo_info['repo_name']
            repo_name = repo_name + ".pdf"
        except Exception as e:
            logger.exception("Failed to fetch or decode markdown for repo: %s", repo_info.get('repo_name'))
            return print(e)

        print(f" ............................... {repo_name} ..............................................................")
        logger.debug("Preparing HTML content for %s", repo_name)

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
            logger.info("Converting to PDF: %s", output_path)
            with open(output_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(styled_html, dest=pdf_file)
            
            if pisa_status.err:
                logger.error("Error generating PDF for %s", output_path)
                print(f"Error generating PDF for {output_path}")
                return False
            
            logger.info("Successfully saved PDF to %s", output_path)
            print(f"Successfully saved PDF to {output_path}")
            return True
        except Exception as e:
            logger.exception("Exception converting HTML to PDF for %s", output_path)
            print(f"Exception converting to PDF: {e}")
            return False
        

    def scrap(self) -> None:
        """
        This is pipeline function which combines all the required processes to scrap read files from github and save these into 
        pdf format
        """

        logger.info("Starting scrap pipeline for user %s", self.username)
        profile_meatadata = self.getProfileInfo()
        logger.debug("Fetched %d repositories from profile", len(profile_meatadata))

        logger.info("scrap() exiting early (original behavior preserved)")
        # return 
        
        repos_meatadata = self.getRepoInfo(profile_metadata=profile_meatadata)

        for repo_info in repos_meatadata:
            self.saveAsPDF(repo_info=repo_info)

        

if __name__ == "__main__":
    import config
    github_scrapper = GithubScrapper(username=config.GITHUB_USERNAME, 
                                     save_folder=config.GITHUB_PDF_FOLDER,
                                     metadata_save_folder=config.METADATA_JSON_PATH)
    github_scrapper.scrap()

