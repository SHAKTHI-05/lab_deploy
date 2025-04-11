from flask import Blueprint, render_template, request, redirect, session, url_for, flash, Response
from .auth import login_user
from .config import get_user_config, set_user_config

import face_recognition
import cv2
import numpy as np
import time
import pytz
from datetime import datetime
from collections import defaultdict
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import pyttsx3
import threading
load_dotenv()

main = Blueprint('main', __name__)

# Supabase init
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# TTS
engine = pyttsx3.init()
engine.setProperty('rate', 135)

server_started = False  # Global flag to detect first request after app starts

@main.before_app_request
def reset_session_on_restart():
    global server_started
    if not server_started:
        print("[before_app_request] First request after server start — clearing session")
        session.clear()
        session['script_running'] = False
        session['show_video'] = False
        session.modified = True
        server_started = True

# Camera class
class Camera:
    _instance = None
    _cap = None
    _running = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Camera, cls).__new__(cls)
            cls._instance._init_camera()
        else:
        # Reinitialize camera if it was released
            if cls._instance._cap is None or not cls._instance._cap.isOpened():
                cls._instance._init_camera()
        return cls._instance

    def _init_camera(self):
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._running = True

    def get_frame(self):
        if self._cap is None or not self._cap.isOpened():
            print("[Camera] Reinitializing camera...")
            self._init_camera()
        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret:
                return frame
        return None

    def release(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap = None
        self._running = False

# Common helpers
def load_face_encodings():
    response = supabase.table('stud_details').select('*').execute()
    encodings, rollnos, details = [], [], {}
    for row in response.data:
        rollno = row['roll_no']
        encoding = np.array(row['embedding'], dtype=np.float64)
        encodings.append(encoding)
        rollnos.append(rollno)
        details[rollno] = {
            'Name': row['name'],
            'Department': row['department'],
            'YearOfStudy': row['year_grad'],
            'Programme': row['programme']
        }
    return encodings, rollnos, details

   
def log_entry(rollno, details, lab_id):
    def task():
        ist = pytz.timezone('Asia/Kolkata')
        entry_time = datetime.now(ist).isoformat()
        supabase.table('stud_log').insert({
            'roll_no': rollno,
            'name': details['Name'],
            'programme': details['Programme'],
            'department': details['Department'],
            'year_grad': details['YearOfStudy'],
            'entry_time': entry_time,
            'occupancy': 1,
            'lab_id': lab_id
        }).execute()
        engine.say(details['Name'] + ' has entered')
        engine.runAndWait()
    threading.Thread(target=task).start()
def log_exit(rollno, lab_id):
    def task():
        ist = pytz.timezone('Asia/Kolkata')
        exit_time = datetime.now(ist).isoformat()
        response = supabase.table('stud_log') \
            .select('*') \
            .eq('roll_no', rollno) \
            .is_('exit_time', 'null') \
            .eq('lab_id', lab_id) \
            .order('entry_time', desc=True) \
            .limit(1) \
            .execute()
        if response.data:
            log_id = response.data[0]['id']
            supabase.table('stud_log') \
                .update({'exit_time': exit_time, 'occupancy': 0}) \
                .eq('id', log_id) \
                .execute()
            engine.say(response.data[0]['name'] + ' has exited')
            engine.runAndWait()
    threading.Thread(target=task).start()
# Config 1
def generate_frames_config1(user_id):
    encodings, rollnos, details = load_face_encodings()
    consecutive_count = defaultdict(int)
    camera = Camera()

    try:
        while True:
            if not camera._running:
                time.sleep(0.1)
                continue

            frame = camera.get_frame()
            if frame is None:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)
            faces = face_recognition.face_encodings(rgb, locations)

            recognized = set()

            for (top, right, bottom, left), face in zip(locations, faces):
                matches = face_recognition.compare_faces(encodings, face)
                distances = face_recognition.face_distance(encodings, face)
                best_index = np.argmin(distances)

                if matches[best_index] and distances[best_index] < 0.6:
                    rollno = rollnos[best_index]
                    name = details[rollno]['Name']
                    recognized.add(rollno)

                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, f"{name} ({rollno})", (left, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

                    now = datetime.now()
                    response = supabase.table('stud_log').select('*').eq('roll_no', rollno).order('entry_time', desc=True).limit(1).execute()
                    if response.data:
                        latest = response.data[0]
                        entry = datetime.fromisoformat(latest['entry_time'])
                        exit = datetime.fromisoformat(latest['exit_time']) if latest['exit_time'] else None
                        occupancy = latest['occupancy']

                        if occupancy == 0 and (not exit or (now - exit).total_seconds() > 120):
                            consecutive_count[rollno] += 1
                            if consecutive_count[rollno] > 3:
                                log_entry(rollno, details[rollno],user_id)
                                consecutive_count[rollno] = 0
                        elif occupancy == 1 and (now - entry).total_seconds() > 30:
                            consecutive_count[rollno] += 1
                            if consecutive_count[rollno] > 3:
                                log_exit(rollno, user_id)
                                consecutive_count[rollno] = 0
                    else:
                        consecutive_count[rollno] += 1
                        if consecutive_count[rollno] > 3:
                            log_entry(rollno, details[rollno],user_id)
                            consecutive_count[rollno] = 0
                else:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown", (left, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            for rollno in list(consecutive_count):
                if rollno not in recognized:
                    consecutive_count[rollno] = max(0, consecutive_count[rollno] - 1)

            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    except Exception as e:
        print(f"[ERROR] Video feed crashed: {e}")
        camera.release()
        time.sleep(0.5)


# Routes
@main.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        [user, access_token, refresh_token] = login_user(request.form['email'], request.form['password'])
        if user:
            session['user_id'] = user.id
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            session['just_logged_in'] = True  
            return redirect(url_for('main.config'))
        else:
            flash('Invalid login')
    return render_template('login.html')

@main.route('/config', methods=['GET', 'POST'])
def config():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('main.login'))

    user_config = get_user_config()

    if request.method == 'POST':
        new_config = request.form['config']
        set_user_config(new_config)
        return redirect(url_for('main.dashboard'))
    
    if session.pop('just_logged_in', False) and user_config:
        return redirect(url_for('main.dashboard'))

    return render_template('config.html', config=user_config['config_name'] if user_config else None)

@main.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    global script_running

    if not session.get('user_id'):
        return redirect(url_for('main.login'))
    
    if request.method == 'GET':
        if 'script_running' not in session:
            session['script_running'] = False
        if 'show_video' not in session:
            session['show_video'] = False
        session.modified = True

    if request.method == 'POST':
        action = request.form['action']
        config = get_user_config()['config_name']
        if action == 'start':
            Camera()
            session['script_running'] = True
            session['show_video'] = False
            session.modified = True

        elif action == 'stop':
            Camera().release()
            session['script_running'] = False
            session['show_video'] = False
            session.modified = True
            
        elif action == 'show':
            session['show_video'] = True
            session.modified = True
            
        elif action == 'hide':
            session['show_video'] = False
            session.modified = True
            print("[INFO] Camera stopped")
            return redirect(url_for('main.dashboard'))
        
        elif action == 'logout':
            session.clear()
            return redirect(url_for('main.login'))
        elif action == 'change':
            return redirect(url_for('main.config'))
        session.modified = True

    return render_template('dashboard.html')

@main.route('/video_feed')
def video_feed():
    user_id = session.get('user_id')
    show_video = session.get('show_video', False)
    script_running = session.get('script_running', False)
    print(f"[video_feed] show_video={show_video}, script_running={script_running}")

    if not (session.get('show_video') and session.get('script_running')):
        return Response("Stream not available", status=204)

    config = get_user_config()['config_name']
    if config == 'single_cam_mode':
        return Response(generate_frames_config1(user_id), mimetype='multipart/x-mixed-replace; boundary=frame')
    # elif config == 'config2':
    #     return Response(generate_frames_config2(), mimetype='multipart/x-mixed-replace; boundary=frame')
    # elif config == 'config3':
    #     return Response(generate_frames_config3(), mimetype='multipart/x-mixed-replace; boundary=frame')

    return Response("Invalid config", status=400)
