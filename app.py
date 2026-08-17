import os
import json
import uuid
import requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

app = Flask(__name__)

if not os.path.exists('static'):
    os.makedirs('static')

def process_ai_video(topic, api_key, voice, ratio, file_format):
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
        image_clip = ImageClip(img_file).set_duration(audio_clip.duration)
        video_clip = image_clip.set_audio(audio_clip)
        
        clips.append(video_clip)
        
    ext = ".mp4" if file_format == "mp4" else ".webm"
    output_filename = f"video_{uuid.uuid4().hex[:8]}{ext}"
    output_path = os.path.join("static", output_filename)
    
    final_video = concatenate_videoclips(clips, method="compose")
    
    if file_format == "mp4":
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    else:
        final_video.write_videofile(output_path, fps=24, codec="libvpx", audio_codec="libvorbis")
        
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)
            
    return output_filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    topic = data.get('topic')
    api_key = data.get('api_key')
    voice = data.get('voice', 'onyx')
    ratio = data.get('ratio', '16:9')
    file_format = data.get('format', 'mp4')
    
    if not topic or not api_key:
        return jsonify({"error": "Mavzu va API kalitni kiriting!"}), 400
        
    try:
        video_file = process_ai_video(topic, api_key, voice, ratio, file_format)
        return jsonify({"video_url": f"/static/{video_file}", "filename": video_file})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
