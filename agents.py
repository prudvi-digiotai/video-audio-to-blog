from utils import upload_file, PARENT_FOLDER_ID, send_email, post_image_and_text
from tools import generate_image_openai, generate_images_and_add_to_blog
import nltk
import re

class BlogAgent():
    def __init__(self, llm, topic, summarized_content) -> None:
        self.llm = llm
        self.topic = topic
        self.summarized_content = summarized_content

    def generate_text(self):

        prompt_yt = (
            f"Write an engaging blog post based on the following details:\n\n"
            f"**Topic:** {self.topic}\n"
            f"**Context:** {self.summarized_content}\n\n"
            f"Start with a captivating introduction, followed by well-organized body sections with clear headings. Use insights from the video transcript to enrich each section. "
            f"Include '<-IMAGE->' placeholders after the introduction and at a relevant point in the body. Conclude with a summary of key points and a call-to-action."
            f"Output the blog in markdown format with a title, introduction, body sections, and conclusion. Write in a conversational style to engage readers."
        )

        blog_content = self.llm.invoke(prompt_yt).content.strip()
        return blog_content

    def save_blog(self, blog_content, filename="blog.md"):
        with open(filename, "w") as file:
            file.write(blog_content)
        print(f"Blog saved to {filename}")

    def add_image_prompts(self, blog_content):
        prompt = (
            "Please replace all instances of '<-IMAGE->' with specific image prompts. "
            "Each image prompt should be enclosed within '<image>' and '</image>' tags. "
            "Ensure that the image prompts avoid including any text, names of individuals, company names, logos, or other identifiable information. "
            "Think of the image prompt as 'what you want to see in the final image.' "
            "Provide a descriptive prompt that clearly defines the elements, colors, and subjects. "
            "For instance: 'The sky was a crisp (blue:0.3) and (green:0.8)' indicates a sky that is predominantly green with a hint of blue. "
            "The weights (e.g., 0.3 and 0.8) apply to all words in the prompt, guiding the emphasis of the colors and elements. "
            "While you may reduce the number of images, ensure that no two image prompts are identical."
            f"context:\n{blog_content}"
            "Expected Output: A complete blog with image prompts enclosed in <image> tags."
        )

        blog_content = self.llm.invoke(prompt).content.strip()

        return blog_content

    def add_images(self, blog_content):
        md_file, docx_file, imgs_path = generate_images_and_add_to_blog(blog_content)
        return md_file, docx_file, imgs_path
    
    def upload_to_drive(self, docx_file_path):
        blog_id = upload_file(docx_file_path, 'blog post', PARENT_FOLDER_ID)
        blog_link = f"https://drive.google.com/file/d/{blog_id}/view?usp=sharing"
        blog_status = f'Blog generated, link to blog: {blog_link}'
        return blog_status

    def generate_blog(self):
        blog_content = self.generate_text()
        self.save_blog(blog_content)
        blog_with_prompts = self.add_image_prompts(blog_content)
        blog_md, blog_doc, imgs_path = self.add_images(blog_with_prompts)
        akg = self.upload_to_drive(blog_doc)
        return blog_content, blog_md, imgs_path, akg
    
class LinkedinAgent:
    def __init__(self, llm, topic, url, blog) -> None:
        self.llm = llm
        self.topic = topic
        self.blog = blog
        self.url = url

    def generate_text(self):
        prompt = (
            "Create a LinkedIn post based on the following topic and blog. The post should be professional, engaging, and suitable for a LinkedIn audience. "
            "It should introduce the topic, provide a brief summary, and include a call-to-action if relevant. The text should be concise yet informative."
            f"Topic: {self.topic}\n"
            f"Company's website: {self.url}\n"
            f"Blog content:\n{self.blog}\n\n"
            "Expected Output: A well-structured LinkedIn post(around 250 words)."
        )
        
        post_text = self.llm.invoke(prompt).content.strip()
        return post_text
    
    def generate_image(self, post_content):
        prompt = (
            "Generate concise image prompt for the below LinkedIn Post. "
            "Think of the image prompt as 'what you want to see in the final image.' "
            "Provide a descriptive prompt that clearly defines the elements, colors, and subjects. "
            "For instance: 'The sky was a crisp (blue:0.3) and (green:0.8)' indicates a sky that is predominantly green with a hint of blue. "
            "The weights (e.g., 0.3 and 0.8) apply to all words in the prompt, guiding the emphasis of the colors and elements. "
            f"Title: {self.topic}\n"
            f"LinkedIn Post: {post_content}\n"
            "Expected Output: A concise prompt used to generate image in <image></image> tag."
        )
        response = self.llm.invoke(prompt).content.strip()
        img_prompt = re.findall(r'<image>(.*?)</?image>', response, re.DOTALL)[0]
        img_path = generate_image_openai(img_prompt, 0)
        return img_path
    
    def post_on_linkedin(self, token, post_content, image_path):
        ack = post_image_and_text(token, self.topic, post_content, image_path)
        return ack

class TwitterAgent:
    def __init__(self, llm, topic, url, blog) -> None:
        self.llm = llm
        self.topic = topic
        self.blog = blog
        self.url = url

    def generate_tweet(self):
        prompt = (
            "Create a short tweet of 230 characters based on the following topic and blog. The tweet should be concise, engaging, and suitable for a Twitter audience. "
            "It should introduce the topic, provide a brief summary, and include a call-to-action if relevant. "
            "Do not include company website url in the tweet. "
            f"Topic: {self.topic}\n"
            f"Company's website: {self.url}\n"
            f"Blog content:\n{self.blog}\n\n"
            "Expected Output: A well-crafted tweet. "
        )

        tweet_text = self.llm.invoke(prompt).content.strip()
        return tweet_text
    
    def twitter_tweet(self, tweet, consumer_key, consumer_secret, access_token, access_token_secret):

        try:
            import tweepy
            print(tweet, consumer_key, consumer_secret, access_token, access_token_secret)
            client = tweepy.Client(consumer_key=consumer_key, consumer_secret=consumer_secret, 
                            access_token=access_token, access_token_secret=access_token_secret)
        
            tweet = tweet.strip('"')
            res = client.create_tweet(text=tweet)
            print(res)
            return 'Twitter tweet generated and posted to user twitter account successfully'
        except Exception as e:
            return Exception(f"Failed to tweet: {e}")

    def post_on_twitter(self, consumer_key, consumer_secret, access_token, access_token_secret):
        tweet = self.generate_tweet()
        print(len(tweet))
        akg = self.twitter_tweet(tweet, consumer_key, consumer_secret, access_token, access_token_secret)
        return akg


class EmailAgent:
    def __init__(self, llm, to_mail):
        self.llm = llm
        self.to_mail = to_mail

    def write_email(self, name, blog_status=None):
        email_body_template = (
            f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; margin: 0; padding: 20px;">
                    <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                        <div style="text-align: center; padding-bottom: 20px; border-bottom: 1px solid #eeeeee;">
                            <h1 style="color: #333333; margin: 0;">Social Media Manager</h1>
                        </div>
                        <div style="padding: 20px;">
                            <p style="font-size: 16px; color: #333333;">Hello {name},</p>
                            <p style="font-size: 16px; color: #555555;">We’re excited to share your latest updates with you. Here’s a summary of what we’ve prepared:</p>

                            <div style="margin-top: 20px;">
                                <h3 style="color: #007BFF; font-size: 18px;">Blog Update</h3>
                                <p style="font-size: 16px; color: #555555;">{blog_status or 'No blog content available.'}</p>
                            </div>

                        </div>
                        <div style="padding-top: 20px; border-top: 1px solid #eeeeee; text-align: center;">
                            <p style="font-size: 16px; color: #555555; margin: 0;">Thank you for using our service!</p>
                            <p style="font-size: 16px; color: #555555; margin: 0;">Best regards,<br>Your Content Team</p>
                        </div>
                    </div>
                </body>
            </html>
            """
        )
        return email_body_template

    def send_email(self, name, blog_status=None):
        name = name.split('@')[0]
        email_body = self.write_email(name, blog_status)
        subject = "Your Generated Content Update"
        send_email(self.to_mail, subject, email_body)
        return f"Email sent to {self.to_mail}!"
