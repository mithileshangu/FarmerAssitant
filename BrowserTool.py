import os
import re
import base64
import platform
import asyncio
import json
from pathlib import Path
from typing import Optional
from phi.tools import Toolkit
from phi.utils.log import logger
from playwright.async_api import async_playwright
from groq import Groq
import time

class BrowserAgent(Toolkit):
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_browser: bool = True,
        username: str = "your_username",
        password: str = "your_password"
    ):
        super().__init__(name="browser_agent")
        self.api_key = api_key or os.environ.get('GROQ_API_KEY')
        self.username = username
        self.password = password
        if not self.api_key:
            raise ValueError("API key must be provided or set as GROQ_API_KEY environment variable")
        
        mark_page = Path(__file__).resolve().parent / "mark_page.js"
        with open(mark_page, encoding="utf-8") as f:
            self.MARK_PAGE_SCRIPT = f.read()
        
        self.PROMPT = """Imagine you are a robot browsing the web, just like humans. Now you need to complete a task. In each iteration,
        you will receive an Observation that includes a screenshot of a webpage and some texts. 
        Carefully analyze the bounding box information and the web page contents to identify the Numerical Label corresponding 
        to the Web Element that requires interaction, then follow
        You must try to ignore popups and try to stay signed out of google initially unless the user asks you to login
        the guidelines and choose one of the following actions:

        1. Click a Web Element.
        2. Delete existing content in a textbox and then type content.
        3. Scroll up or down.
        4. Wait 
        5. Go back
        7. Return to google to start over.
        8. Respond with the final answer
        9. Log in to a website.
        10. Scrape the current page.

        Correspondingly, Action should STRICTLY follow the format:

        - Click [Numerical_Label] 
        - Type [Numerical_Label]; [Content] 
        - Scroll [Numerical_Label or WINDOW]; [up or down] 
        - Wait 
        - GoBack
        - ANSWER; [content]
        - Login; [Username]; [Password]
        - SCRAPE

        Key Guidelines You MUST follow:

        * Action guidelines *
        1) Execute only one action per iteration.
        2) Always click close on the popups.
        3) When clicking or typing, ensure to select the correct bounding box.
        4) Numeric labels lie in the top-left corner of their corresponding bounding boxes and are colored the same.
        5) If the desired target is to do something like taking a action, you need to answer with ANSWER; FINISHED. For exmaple if i ask to write something or play a video

        * Web Browsing Guidelines *
        1) Don't interact with useless web elements like Login, Sign-in, donation that appear in Webpages
        2) Select strategically to minimize time wasted.

        * Scraping Guideline *
        1) Use the SCRAPE command when you believe the current page contains valuable information that should be saved for later analysis.

        Your reply should strictly follow the format:

        Thought: {{Your brief thoughts (briefly summarize the info that will help ANSWER)}}
        Action: {{One Action format you choose}}
        Then the User will provide:
        Observation: {{A labeled bounding boxes and contents given by User}}"""

        if use_browser:
            self.register(self.browse)

    def browse(self, query: str) -> str:
        """Use this function to browse the web and find information.

        :param query: The query to search for on the web.
        :return: The result of the web search or an error message.
        """
        try:
            return asyncio.get_event_loop().run_until_complete(self._browse(query))
        except Exception as e:
            logger.error(f"Error in browse: {e}")
            return f"error: {e}"
    
    async def is_login_page(self, page):
        selectors = [
            'input[type="password"]',
            'form[action="login"]',
            'form[action="signin"]',
            'button:has-text("Log in")',
            'button:has-text("Sign in")'
        ]
        for selector in selectors:
            if await page.query_selector(selector):
                return True
        return False
    
    async def login(self, page, username, password):
        try:
            await page.wait_for_selector('input[type="text"], input[type="email"]', timeout=5000)
            username = username or os.getenv("BROWSER_USERNAME")
            password = password or os.getenv("BROWSER_PASSWORD")
            if not username or not password:
                logger.warning("Browser credentials are not configured.")
                return False

            await page.type('input[type="text"], input[type="email"]', username)
            await page.keyboard.press('Tab')
            await asyncio.sleep(0.5)
            await page.type('input[type="password"]', password)
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('networkidle')

            current_url = page.url.lower()
            page_title = await page.title()
            return "home" in current_url
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    async def _browse(self, query: str) -> str:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto('https://www.google.com')
            # await page.goto('https://forms.office.com/Pages/ResponsePage.aspx?id=SCk8t0tCm0CGtiJQQjuHDYU_jEwxW-ZBikaTerm3-jhUMzBQN1BEWUkwRllYME5CMEpTR05NREdMVi4u')
            result = await self.get_information(query, page)
            await browser.close()
            return result
    
    async def scrape_financial_data(self, page):
        try:
            # Look for elements containing financial data
            content = await page.content()
            
            # Use regular expressions or CSS selectors to find relevant data (e.g., gross sales and gross profit)
            sales_data = re.findall(r'(?i)Gross Sales:?\s*\$?\d[\d,]*\.?\d*', content)
            profit_data = re.findall(r'(?i)Gross Profit:?\s*\$?\d[\d,]*\.?\d*', content)
            discount_data = re.findall(r'(?i)Discount:?\s*\$?\d[\d,]*\.?\d*', content)
            
            financial_data = {
                "gross_sales": sales_data,
                "gross_profit": profit_data,
                "discounts": discount_data
            }
            
            # Save the scraped data to a JSON file
            with open('financial_data.json', 'w') as f:
                json.dump(financial_data, f, indent=4)
            
            logger.info("Financial data scraped and saved successfully.")
            return "SCRAPE"
        except Exception as e:
            logger.error(f"Error during data scraping: {e}")
            return "NO"

    async def get_information(self, query, page):
        login_attempt_count = 0
        while True:
            try:
                obj = await self.mark_page(page)
            except:
                await asyncio.sleep(5)
                continue

            obj = self.format_descriptions(obj)
            text = await page.inner_text('body')
            is_login_page = await self.is_login_page(page)

            if is_login_page and login_attempt_count < 5:
                new_query = self.PROMPT + "\n Valid Bounding boxes: " + obj['bbox_descriptions'] + '\nQuestion: This appears to be a login page. Please use the Login command with appropriate credentials.'
            else:
                new_query = self.PROMPT + "\n Valid Bounding boxes: " + obj['bbox_descriptions'] + '\nQuestion:' + query

            resp = self.llama3_agent(new_query)
            parsed_commands = self.parse_commands(resp)

            for command in parsed_commands:
                if isinstance(command, dict):
                    command_type = list(command.keys())[0]
                    if command_type == 'Login':
                        username, password = command['Login']
                        success = await self.login(page, username, password)
                        login_attempt_count += 1
                        if not success:
                            logger.warning("Login attempt failed")
                        else:
                            login_attempt_count = 0
                    elif command_type == 'Type':
                        location, content = command['Type']
                        await self.type_text(page, location, content, obj)
                    elif command_type == 'Click':
                        location = command['Click'][0]
                        await self.click(page, obj, query, location)
                    elif command_type == 'Scroll':
                        await self.scroll(page, obj, command['Scroll'])
                elif command == 'Wait':
                    await asyncio.sleep(5)
                elif command == 'GoBack':
                    await page.go_back()
                elif command == 'Google':
                    await page.goto('https://www.google.com')
                elif command == 'ANSWER':
                    return command['ANSWER'][0]
                elif command == 'FINISHED':
                    break
                elif command == 'SCRAPE':
                    return await self.scrape_page(page)

            await asyncio.sleep(2)
        return "No answer found or task completed."

    async def scrape_page(self, page):
        try:
            # Get the complete HTML of the current page
            html_content = await page.content()
            
            # Generate a unique filename based on the current timestamp
            timestamp = int(time.time())
            filename = f"scraped_page_{timestamp}.html"
            
            # Save the HTML content to a file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Page scraped successfully. Saved as {filename}")
            return f"SCRAPED; Page content saved to {filename}"
        except Exception as e:
            logger.error(f"Error during page scraping: {e}")
            return f"SCRAPE_ERROR; {str(e)}"

    async def mark_page(self, page):
        await page.evaluate(self.MARK_PAGE_SCRIPT)
        for _ in range(10):
            try:
                bboxes = await page.evaluate("markPage()")
                break
            except:
                await asyncio.sleep(3)
        screenshot = await page.screenshot(path='annotated_screenshot_with_numbers.png')
        await page.evaluate("unmarkPage()")
        return {
            "img": base64.b64encode(screenshot).decode(),
            "bboxes": bboxes,
        }

    @staticmethod
    def format_descriptions(state):
        labels = []
        for i, bbox in enumerate(state["bboxes"]):
            text = bbox.get("ariaLabel") or ""
            if not text.strip():
                text = bbox["text"]
            el_type = bbox.get("type")
            labels.append(f'{i} (<{el_type}/>): "{text}"')
        bbox_descriptions = "\nValid Bounding Boxes:\n" + "\n".join(labels)
        return {**state, "bbox_descriptions": bbox_descriptions}

    async def click(self, page, state, query, location):
        bbox_id = int(location)
        try:
            bbox = state["bboxes"][bbox_id]
        except IndexError:
            return f"Error: no bbox for : {bbox_id}"
        x, y = bbox["x"], bbox["y"]
        return await page.mouse.click(x, y)

    async def type_text(self, page, location, text_content, state):
        bbox_id = int(location)
        bbox = state["bboxes"][bbox_id]
        x, y = bbox["x"], bbox["y"]
        await page.mouse.click(x, y)
        select_all = "Meta+A" if platform.system() == "Darwin" else "Control+A"
        await page.keyboard.press(select_all)
        await page.keyboard.press("Backspace")
        await page.keyboard.type(text_content)
        return await page.keyboard.press("Enter")

    async def scroll(self, page, state, scroll_args):
        if scroll_args is None or len(scroll_args) != 2:
            return "Failed to scroll due to incorrect arguments."

        target, direction = scroll_args
        scroll_amount = 500 if target.upper() == "WINDOW" else 200
        scroll_direction = -scroll_amount if direction.lower() == "up" else scroll_amount

        if target.upper() == "WINDOW":
            await page.evaluate(f"window.scrollBy(0, {scroll_direction})")
        else:
            target_id = int(target)
            bbox = state["bboxes"][target_id]
            x, y = bbox["x"], bbox["y"]
            await page.mouse.move(x, y)
            await page.mouse.wheel(0, scroll_direction)

        return f"Scrolled {direction} in {'window' if target.upper() == 'WINDOW' else 'element'}"

    def llama3_agent(self, q):
        client = Groq(api_key=self.api_key)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": q}],
            model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        )
        return chat_completion.choices[0].message.content

    @staticmethod
    def parse_commands(text):
        command_patterns = {
            'Click': r'Click \[?(\d+)\]?',
            'Type': r'Type \[?(\d+)\]?; (.*)',
            'Scroll': r'Scroll \[?(\d+|WINDOW)\]?; \[?(up|down)\]?',
            'Scroll1': r'Scroll \[?(up|down)\]?; \[?(\d+|WINDOW)\]?',
            'Wait': r'Wait',
            'GoBack': r'GoBack',
            'Bing': r'Bing',
            'Google': r'Google',
            'ANSWER': r'ANSWER; (.*)',
            'FINISHED': r'FINISHED',
            'Login': r'Login; (.*); (.*)',
            'SCRAPE': r'SCRAPE'
        }
        
        parsed_commands = []
        
        for command, pattern in command_patterns.items():
            for match in re.finditer(pattern, text):
                if command in ['Click', 'Type', 'Scroll', 'Scroll1', 'ANSWER','Login']:
                    if command == 'Scroll1':
                        command = 'Scroll'
                        parsed_commands.append({command: match.groups()[::-1]})
                    else:
                        parsed_commands.append({command: match.groups()})
                else:
                    parsed_commands.append(command)
        
        return parsed_commands