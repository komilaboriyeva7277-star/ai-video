import os
import json
import uuid
import requests
import streamlit as st
from openai import OpenAI
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

st.set_page_config(page_title="AI Video Studio Pro", page_icon="🎬", layout="centered")

st.title("🎬 AI Video Studio Pro")
st.write("OpenAI API orqali avtomatik video va audio yaratish tizimi")

api_key = st.text_input("OpenAI API Kalitini kiriting:", type="password", placeholder="sk-proj-...")
topic = st.text_input("Video Mavzusi:", placeholder="Masalan: Samarqand tarixi va obidalari")

col1, col2 = st.columns(2)
with col1:
    voice = st.selectbox("Ovoz turi (TTS):", ["onyx", "echo", "nova", "shimmer"])
with col2:
    ratio = st.selectbox("Kadr Nisbati:", ["16:9", "9:16", "1:1"])

if st.button("🚀 Video Yaratish", use_container_width=True):
    if not api_key or not topic:
        st.error("Iltimos, API kalit va mavzuni kiriting!")
    else:
        try:
            with st.spinner("Ssenariy va media ishlanmoqda... (1-2 daqiqa kuting)"):
                client = OpenAI(api_key=api_key)
                
                size = "1024x1024"
                if ratio == "16:9":
                    size = "1792x1024"
                elif ratio == "9:16":
                    size = "1024x1792"
                    
                prompt = f"""
                Mavzu: '{topic}'
                Ushbu mavzu bo'yicha 2 ta kadrdan iborat qisqa video uchun ssenariy tuzing.
                - 'narrative' maydonidagi matn O'ZBEK TILIDA bo'lsin.
                - 'image_prompt' DALL-E 3 uchun INGLIZ TILIDA bo'lsin.
                
                JSON formatda qaytaring:
                {{
                    "scenes": [
                        {{"narrative": "O'zbekcha matn", "image_prompt": "English prompt"}}
                    ]
                }}
                """
                
                gpt_res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                scenes = json.loads(gpt_res.choices[0].message.content)["scenes"]
                
                clips = []
                temp_files = []
                
                for idx, scene in enumerate(scenes):
                    img_file = f"temp_img_{idx}_{uuid.uuid4().hex[:6]}.png"
                    audio_file = f"temp_audio_{idx}_{uuid.uuid4().hex[:6]}.mp3"
                    temp_files.extend([img_file, audio_file])
                    
                    img_res = client.images.generate(
                        model="dall-e-3",
                        prompt=scene["image_prompt"],
                        n=1,
                        size=size
                    )
                    img_data = requests.get(img_res.data[0].url).content
                    with open(img_file, "wb") as f:
                        f.write(img_data)
                        
                    tts_res = client.audio.speech.create(
                        model="tts-1",
                        voice=voice,
                        input=scene["narrative"]
                    )
                    tts_res.stream_to_file(audio_file)
                    
                    audio_clip = AudioFileClip(audio_file)
                    image_clip = ImageClip(img_file).with_duration(audio_clip.duration)
                    video_clip = image_clip.with_audio(audio_clip)
                    
                    clips.append(video_clip)
                    
                output_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
                final_video = concatenate_videoclips(clips, method="compose")
                final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac")
                
                for f in temp_files:
                    if os.path.exists(f):
                        os.remove(f)
                        
                st.success("Video muvaffaqiyatli tayyorlandi!")
                st.video(output_filename)
                
                with open(output_filename, "rb") as file:
                    st.download_button(
                        label="📥 Videoni Yuklab Olish",
                        data=file,
                        file_name=output_filename,
                        mime="video/mp4"
                    )
        except Exception as e:
            st.error(f"Xatolik yuz berdi: {str(e)}")
