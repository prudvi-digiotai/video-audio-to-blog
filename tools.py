from langchain.tools import tool
# from crewai_tools import ScrapeWebsiteTool
# from gtts import gTTS
from pydub import AudioSegment
from groq import Groq
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, ImageClip
import requests
import os
import tempfile
import re
import base64
import pypandoc
import cv2
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from pathlib import Path
from openai import OpenAI

# !sudo apt-get install pandoc

####################################################################################################33
from bs4 import BeautifulSoup
from langchain_community.document_loaders import YoutubeLoader

def extract_sections(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    sections = []
    for link in soup.find_all('a', href=True):
        sections.append({
            'text': link.get_text().strip(),
            'url': link['href']
        })
        
    return sections

def filter_relevant_sections(sections, keywords):
    relevant_sections = []
    for section in sections:
        if any(keyword.lower() in section['text'].lower() for keyword in keywords):
            relevant_sections.append(section)
    
    return relevant_sections

def filter_youtube_links(sections, keywords):
    youtube_sections = []
    for section in sections:
        if 'youtube' not in section['url']:
            sections.remove()

def gather_info_from_sections(relevant_sections):
    content = {}
    for section in relevant_sections:
        try:
            response = requests.get(section['url'])
            soup = BeautifulSoup(response.content, 'html.parser')
            clean_text = clean_scraped_text(soup.get_text())
            content[section['url']] = clean_text
        except Exception as e:
            print(e)
    
    return content

def clean_scraped_text(text):
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s+', ' ', text)

    patterns = [
        r'Home\s+About Us.*?\s+Contact Us',
        r'This website uses cookies.*?Privacy & Cookies Policy',  
        r'Copyright.*?Powered by.*',  
    ]

    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

    text = re.sub(r'\|.*?\|', '', text)  
    text = text.strip()  

    return text

def youtube_transcript_loader(url):
    try:
        loader = YoutubeLoader.from_youtube_url(
            url, add_video_info=False
        )
        transcript = loader.load()[0]
        print(len(transcript.page_content.split(" ")))
        return transcript.page_content
    except Exception as e:
        print(e)
    
def gather_youtube_data(sections, keywords):
    youtube_sections = []
    for i, section in enumerate(sections):
        if 'youtube' in section['url']:
            youtube_sections.append(section)

    content = {}
    for section in youtube_sections:
        text = youtube_transcript_loader(section['url'])
        if text is not None:
            content[section['url']] = text

    relevant_content = {}
    for k, v in content.items():
        if any(keyword.lower() in v.lower() for keyword in keywords):
            relevant_content[k] = v

    return relevant_content

def extract_relevant_sections_from_website(website_url, keywords):
    sections = extract_sections(website_url)
    filtered_sections = filter_relevant_sections(sections, keywords)
    gathered_info = gather_info_from_sections(filtered_sections)
    youtube_info = gather_youtube_data(sections, keywords)
    total_info = gathered_info | youtube_info
    refined_info = {url: text for url, text in total_info.items() if len(text) > 200}  # Example threshold for content length

    return refined_info

# context = extract_relevant_sections_from_website(website_url = "https://www.digiotai.com/", keywords =  ["Future of AI", "AI", "artificial intelligence", "AI technology", "generative AI"])



##########################################################################################################333#


def convert_md_to_docx(md_file_path, docx_file_path):
    output = pypandoc.convert_file(md_file_path, 'docx', outputfile=docx_file_path)
    assert output == "", "Conversion failed"
    print(f"Converted {md_file_path} to {docx_file_path}")

def generate_image_openai(text, num):

    temp_output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    output_image = temp_output_file.name

    client = OpenAI()

    try:
        response = client.images.generate(
            model="dall-e-2",
            prompt=text,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = response.data[0].url

        print(f'image {num} generated')

        image_response = requests.get(image_url)
        # print('response')
        if image_response.status_code == 200:
            with open(output_image, 'wb') as file:
                file.write(image_response.content)
                # print('write')
        else:
            raise Exception(f"Failed to download image with status code {image_response.status_code} and message: {image_response.text}")

    except Exception as e:
        raise Exception(f"Image generation failed: {e}")

    return output_image

def generate_images_and_add_to_blog(blog_content):
    """This tool is used to generate images and add them to blog
    Args:
    blog_content: A complete blog with prompts enclosed in <image> prompt </image> tag.
    Returns:
    A complete blog"""
            
    print(blog_content)
    # print('*****************************************************')
    # print(type(blog_content))

    blog_content = str(blog_content)
    
    image_descriptions = re.findall(r'<image>(.*?)</image>', blog_content)
    
    temp_folder = tempfile.gettempdir()
    md_file_path = os.path.join(temp_folder, 'blog_post.md')
    docx_file_path = os.path.join(temp_folder, 'blog_post.docx')
    
    if os.path.exists(md_file_path):
        os.remove(md_file_path)
    if os.path.exists(docx_file_path):
        os.remove(docx_file_path)
    
    images = []
    for i, text in enumerate(image_descriptions):
        try:
            img_path = generate_image_openai(text, i)
            images.append(img_path)
            blog_content = blog_content.replace(f'<image>{text}</image>', f'![]({img_path})')
        except Exception as e:
            print(e)
            raise Exception(f"Image generation failed: {e}")

    try:
        with open(md_file_path, 'w') as f:
            f.write(blog_content)
        
        convert_md_to_docx(md_file_path, docx_file_path)
        print(f"Markdown file saved at: {md_file_path}")
        print(f"Document file saved at: {docx_file_path}")
    except Exception as error:
        print(error)
        
    return md_file_path, docx_file_path, images

def process_script(script):
    """Used to process the script into dictionary format"""
    dict = {}
    text_for_image_generation = re.findall(r'<image>(.*?)</?image>', script, re.DOTALL)
    text_for_speech_generation = re.findall(r'<narration>(.*?)</?narration>', script, re.DOTALL)
    dict['text_for_image_generation'] = text_for_image_generation
    dict['text_for_speech_generation'] = text_for_speech_generation
    return dict