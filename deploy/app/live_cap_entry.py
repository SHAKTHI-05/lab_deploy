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
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Function to load face encodings from Supabase
def load_face_encodings_from_supabase():
    response = supabase.table('stud_details').select('*').execute()
    known_face_encodings = []
    known_face_rollnos = []
    known_face_details = {}

    for row in response.data:
        rollno = row['roll_no']
        encoding = np.array(row['embedding'], dtype=np.float64)  # Assuming embeddings is stored as JSON array
        known_face_encodings.append(encoding)
        known_face_rollnos.append(rollno)
        known_face_details[rollno] = {
            'Name': row['name'],
            'Department': row['department'],
            'YearOfStudy': row['year_grad'],
            'Programme': row['programme']
        }
    return known_face_encodings, known_face_rollnos, known_face_details

def log_student_entry(rollno, details):
    ist = pytz.timezone('Asia/Kolkata')
    entry_time = datetime.now(ist).isoformat()
    
    supabase.table('stud_log').insert({
        'roll_no': rollno,
        'name': details['Name'],
        'programme': details['Programme'],
        'department': details['Department'],
        'year_grad': details['YearOfStudy'],
        'entry_time': entry_time,
        'occupancy': 1
    }).execute()

# Load stored encodings from Supabase
known_face_encodings, known_face_rollnos, known_face_details = load_face_encodings_from_supabase()

# Video capture setup remains the same
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Initialize tracking variables
consecutive_count = defaultdict(int)

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    # Convert to RGB (for face_recognition)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detect all faces in the frame
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    # Reset recognition flags for this frame
    recognized_this_frame = set()
    
    # Process each face found in the frame
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        rollno = "Unknown"
        
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        
        if matches[best_match_index] and face_distances[best_match_index] < 0.5:
            rollno = known_face_rollnos[best_match_index]
            name = known_face_details[rollno]['Name']
            recognized_this_frame.add(rollno)
            
            # Draw bounding box and label
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, f"{name} ({rollno})", (left + 6, bottom - 6), font, 0.5, (0, 0, 0), 1)
            
            # Handle attendance logging
            current_time = datetime.now()
            
            # Check existing logs in Supabase
            response = supabase.table('stud_log') \
                .select('*') \
                .eq('roll_no', rollno) \
                .order('entry_time', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data:
                latest_log = response.data[0]
                entry_time = datetime.fromisoformat(latest_log['entry_time'])
                exit_time = datetime.fromisoformat(latest_log['exit_time']) if latest_log['exit_time'] else None
                occupancy = latest_log['occupancy']
                
                if (occupancy == 0 and (current_time - exit_time).total_seconds() >= 120) or not response.data:
                    consecutive_count[rollno] += 1
                    if consecutive_count[rollno] > 5:
                        '''# Check and delete lab request if exists
                        req_response = supabase.table('lab_req') \
                            .select('*') \
                            .eq('roll_no', rollno) \
                            .execute()
                        if req_response.data:
                            supabase.table('lab_req') \
                                .delete() \
                                .eq('roll_no', rollno) \
                                .execute()
                        '''
                        log_student_entry(rollno, known_face_details[rollno])
                        consecutive_count[rollno] = 0
                
            else:
                consecutive_count[rollno] += 1
                if consecutive_count[rollno] > 5:
                    log_student_entry(rollno, known_face_details[rollno])
                    consecutive_count[rollno] = 0
        
        else:
            # Draw bounding box for unknown faces
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, "Unknown", (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
    
    # Reset counts for faces not detected in this frame
    for rollno in list(consecutive_count.keys()):
        if rollno not in recognized_this_frame:
            consecutive_count[rollno] = max(0, consecutive_count[rollno] - 1)
    
    # Display the resulting image
    cv2.imshow('Video', frame)
    
    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
cap.release()
cv2.destroyAllWindows()