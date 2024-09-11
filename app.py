import json
import os
from pprint import pprint

private_key_id = os.getenv('private_key_id')
private_key = os.getenv('private_key')
client_email = os.getenv('client_email')
client_id = os.getenv('client_id')
auth_uri = os.getenv('auth_uri')
token_uri = os.getenv('token_uri')
auth_provider_x509_cert_url = os.getenv('auth_provider_x509_cert_url')
client_x509_cert_url = os.getenv('client_x509_cert_url')
universe_domain =  os.getenv("universe_domain")

service_account_info = {
    "type": "service_account",
    "project_id": os.getenv('project_id'),
    "private_key_id": private_key_id,
    "private_key": private_key,
    "client_email": client_email,
    "client_id": client_id,
    "auth_uri": auth_uri,
    "token_uri": token_uri,
    "auth_provider_x509_cert_url": auth_provider_x509_cert_url,
    "client_x509_cert_url": client_x509_cert_url,
    "universe_domain": universe_domain
}
pprint(service_account_info)

with open('service_account.json', 'w') as f:
    json.dump(service_account_info, f, indent=2)

token = os.getenv('token')
refresh_token = os.getenv('refresh_token')
token_uri = os.getenv('token_uri')
client_id_mail = os.getenv('client_id_mail')
client_secret = os.getenv('client_secret')
scopes = os.getenv('scopes')
universe_domain = os.getenv('universe_domain')
account = os.getenv('account')
expiry = os.getenv('expiry')

token_info = {
    "token": token,
    "refresh_token": refresh_token,
    "token_uri": token_uri,
    "client_id": client_id_mail,
    "client_secret": client_secret,
    "scopes": ["https://www.googleapis.com/auth/gmail.send"],
    "universe_domain": universe_domain,
    "account": account,
    "expiry": expiry
}
pprint(token_info)

with open('token.json', 'w') as f:
    json.dump(token_info, f)






import streamlit as st
from moviepy.editor import VideoFileClip
from openai import OpenAI
import tempfile
import os
from langchain_openai import ChatOpenAI
from agents import BlogAgent, EmailAgent, LinkedinAgent, TwitterAgent
from utils import twitter_tweet
# from dotenv import load_dotenv
# load_dotenv()

client = OpenAI()

def extract_audio_from_video(video_path):
    with VideoFileClip(video_path) as video:
        audio = video.audio
        temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio.write_audiofile(temp_audio_file.name)
    return temp_audio_file.name

def transcribe_audio(audio_file_path):
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcription.text

def main():
    st.title("Video/Audio to Blog")

    topic = st.text_input('Enter the topic')
    uploaded_file = st.file_uploader("Upload Video or Audio", type=["mp4", "mp3", "wav", "m4a"])
    to_mail = st.text_input('Enter your email')
    url = None

    options = st.multiselect("Select what to generate", ["LinkedIn Post", "Twitter Tweet"])



    if st.button('submit'):
        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
                temp_file.write(uploaded_file.read())
                temp_file_path = temp_file.name

            if temp_file_path.endswith(".mp4"):
                st.write("Extracting audio from video...")
                audio_path = extract_audio_from_video(temp_file_path)
            else:
                audio_path = temp_file_path

            st.write("Transcribing audio...")
            transcription = transcribe_audio(audio_path)
            # st.text_area("Transcription", transcription, height=100)

            # make blog
            llm = ChatOpenAI(model='gpt-4o-mini')

            with st.spinner("Creating Blog..."):
                with st.expander("Blog"):
                    blog_agent = BlogAgent(llm, topic, transcription)
                    blog_content, blog_md, imgs, blog_status = blog_agent.generate_blog()
                    with open(blog_md, 'r) as f:
                        blog_markdown = f.read()
                    st.markdown(blog_markdown)
                    st.image(imgs, ['image 1', 'image 2'], width=320)
                    

            if "LinkedIn Post" in options:
                with st.spinner("Creating LinkedIn Post..."):
                    with st.expander("LinkedIn Post"):
                        linkedin_agent = LinkedinAgent(llm, topic, url, blog_content)
                        post_content = linkedin_agent.generate_text()
                        st.write(post_content)
                        st.image(imgs, ['image 1', 'image 2'], width=320)
                        token = st.text_input("LinkedIn Access Token", type="password")
                        if st.button('Post with image 1'):
                            if token:
                                linkedin_agent.post_on_linkedin(token, post_content, imgs[0])
                                st.success('posted')
                            else:
                                st.warning("Please enter a LinkedIn access token.")
                        if st.button('Post with image 2'):
                            if token:
                                linkedin_agent.post_on_linkedin(token, post_content, imgs[0])
                                st.success('posted')
                            else:
                                st.warning("Please enter a LinkedIn access token.")


            if "Twitter Tweet" in options:
                with st.spinner("Creating Twitter Tweet..."):
                    with st.expander("Twitter Tweet"):
                        twitter_agent = TwitterAgent(llm, topic, url, blog_content)
                        twitter_content = twitter_agent.generate_tweet()
                        st.write(len(twitter_content))
                        st.write(twitter_content)
                        consumer_key        = st.text_input(label='', placeholder='consumer key')
                        consumer_secret     = st.text_input(label='', placeholder='consumer secret')
                        access_token        = st.text_input(label='', placeholder='access token')
                        access_token_secret = st.text_input(label='', placeholder='access token secret')
                        if st.button('Tweet'):
                            twitter_status = twitter_tweet(twitter_content, consumer_key, consumer_secret, access_token, access_token_secret)
                            st.success(twitter_status)


            email_agent = EmailAgent(llm, to_mail)
            mail = email_agent.send_email(to_mail, blog_status)

            # Cleanup temporary files
            try:
                os.remove(temp_file_path)
                if temp_file_path.endswith(".mp4"):
                    os.remove(audio_path)
            except PermissionError:
                st.error("Failed to remove temporary files due to a permission error. Please try closing any applications that might be using the files and try again.")

if __name__ == "__main__":
    main()
