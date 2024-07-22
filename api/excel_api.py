import asyncio
from office365.graph_client import GraphClient
import pandas as pd
from io import BytesIO
from config import CONFIG

class ExcelAPI:
    def __init__(self):
        self.client_id = CONFIG.AZURE_CLIENT_ID
        self.client_secret = CONFIG.AZURE_CLIENT_SECRET
        self.tenant_id = CONFIG.AZURE_TENANT_ID
        self.site_url = CONFIG.SHAREPOINT_SITE_URL
        self.file_path = CONFIG.EXCEL_FILE_URL

    async def get_excel_data(self):
        if not await self.test_graph_access():
            raise Exception("Failed to access Microsoft Graph. Please check your credentials and permissions.")

        try:
            print(f"Client ID: {self.client_id}")
            print(f"Tenant ID: {self.tenant_id}")
            print(f"Site URL: {self.site_url}")
            print(f"File Path: {self.file_path}")

            client = GraphClient.with_client_secret(self.tenant_id, self.client_id, self.client_secret)
            
            # Get the site
            site = client.sites.get_by_url(self.site_url).get().execute_query()
            
            # Get all drives
            drives = site.drives.get().execute_query()
            print(f"Found {len(drives)} drives:")
            for drive in drives:
                print(f"Drive name: {drive.name}, ID: {drive.id}")

            if not drives:
                raise Exception("No drives found in the site")

            # Use the first drive (usually the default document library)
            drive = drives[0]
            
            # List items in the root of the drive
            items = drive.root.children.get().execute_query()
            print(f"Items in root of drive {drive.name}:")
            for item in items:
                print(f"  - {item.name} ({'Folder' if item.folder else 'File'})")

            # Try to find the file
            try:
                file = drive.root.get_by_path(self.file_path).get().execute_query()
                print(f"File found: {file.name}")
                
                content = file.get_content().execute_query()
                if isinstance(content, bytes):
                    print(f"File content downloaded. Size: {len(content)} bytes")
                else:
                    print(f"File content downloaded. Type: {type(content)}")

                # If content is not bytes, try to get the value
                if not isinstance(content, bytes):
                    if hasattr(content, 'value'):
                        content = content.value

                df = pd.read_excel(BytesIO(content))
                print(f"Excel file parsed successfully. Shape: {df.shape}")

                return df
            except Exception as e:
                print(f"Error accessing file: {str(e)}")
                raise Exception(f"Could not access file '{self.file_path}': {str(e)}")

        except Exception as e:
            print(f"Unexpected error in get_excel_data: {str(e)}")
            raise

    async def test_graph_access(self):
        try:
            print(f"Testing Graph API access with Client ID: {self.client_id}")
            print(f"Tenant ID: {self.tenant_id}")
            print(f"Site URL: {self.site_url}")
            
            client = GraphClient.with_client_secret(self.tenant_id, self.client_id, self.client_secret)
            site = client.sites.get_by_url(self.site_url).get().execute_query()
            print(f"Successfully accessed Graph API. Site properties: {site.properties}")
            return True
        except Exception as e:
            print(f"Error accessing Graph API: {str(e)}")
            return False

    def search_products(self, df, keywords):
        keywords_set = set(keywords.lower().split())
        
        def match_keywords(row):
            text = (str(row['Description']).lower() +
                    str(row['Category']).lower() +
                    str(row['Sub Category']).lower())
            return all(keyword in text for keyword in keywords_set)
        
        results = df[df.apply(match_keywords, axis=1)]
        return results

    def format_results(self, results):
        formatted_results = []
        for _, row in results.iterrows():
            formatted_result = ""
            for column, value in row.items():
                formatted_result += f"{column}: {value}\n"
            formatted_results.append(formatted_result)
        return "\n\n".join(formatted_results)