from flask import Flask, render_template, request, Response, redirect, url_for
import cv2
import pytesseract
import pyodbc
import os
import subprocess

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Flask setup
app = Flask(__name__)
UPLOAD_FOLDER = 'plates'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create plates directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Database connection setup
server = 'NIROHAN'  # Replace with your server name
database = 'LicensePlateDB'  # Replace with your database name
connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"

try:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")
    exit()

# Haar Cascade for plate detection
harcascade = "model/haarcascade_russian_plate_number.xml"


def preprocess_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply GaussianBlur to reduce noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Use adaptive thresholding for better contrast
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    return thresh

# Helper function: Detect and recognize license plates
def process_plate_image(image_path=None, image=None):
    if image_path:
        image = cv2.imread(image_path)
    if image is None:
        return None, None, "Error: Unable to process image."
    
    # Preprocess the image
    processed_image = preprocess_image(image)
    
    # Load the plate cascade
    plate_cascade = cv2.CascadeClassifier(harcascade)

    # Detect plates
    plates = plate_cascade.detectMultiScale(processed_image, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

    plate_text = None

    for (x, y, w, h) in plates:
        img_roi = image[y:y + h, x:x + w]

        # Use Tesseract to extract text
        plate_text = pytesseract.image_to_string(img_roi, config='--psm 6').strip()
        if plate_text:  # Break on first valid detection
            return plate_text, img_roi, None
        
        if plate_text:
            plate_filename = f"plates/scanned_img_{count}.jpg"
            cv2.imwrite(plate_filename, img_roi)


    return None, None, "No plates detected."


    


# Route to serve the scan page where the live feed will be displayed
@app.route('/scan_page')
def scan_page():
    return render_template('scan_page.html')

min_area = 5000  # Adjust this threshold based on your requirements

# Global variable to track the plate for which you want to add details
current_plate_text = None
current_plate_image = None
count = 0  # Counter for image file naming

def generate_frames():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # 0 is the default camera
    cap.set(3, 640)  # Set width
    cap.set(4, 480)  # Set height

    while True:
        success, frame = cap.read()
        
        if not success:
            break
        

        # plates = plate_cascade.detectMultiScale(img_gray, 1.1, 4)
        # Process frame for plate detection
        plate_text, img_roi, error = process_plate_image(image=frame)
        if plate_text:
            # Overlay plate information on the frame
            img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            plate_cascade = cv2.CascadeClassifier(harcascade)
            plates = plate_cascade.detectMultiScale(img_gray, 1.1, 4)
            cv2.putText(frame, f"Plate: {plate_text}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
        if cv2.waitKey(1) & 0xFF == ord('s'):
            plate_filename = f"plates/scanned_img_{count}.jpg"
            cv2.imwrite(plate_filename, img_roi)


        # Encode the frame to JPEG and yield it
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

    
@app.route('/add_plate_details')
def add_plate_details():
    return render_template('Scan_page.html', plate_text=current_plate_text, image_path=current_plate_image,image =cv2.imwrite(plate_filename, img_roi))

# Homepage
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file or file.filename == '':
        return render_template('error.html', message="No file selected")

    # Save the uploaded file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # Process the uploaded image
    plate_text, img_roi, error = process_plate_image(image_path=filepath)
    if error:
        return render_template('result.html', message=error)

    # Save the detected plate image
    plate_filename = os.path.join(app.config['UPLOAD_FOLDER'], f"processed_{file.filename}")
    if img_roi is not None:
        cv2.imwrite(plate_filename, img_roi)

    # Database lookup
    cursor.execute("SELECT Name, Age FROM PlateData WHERE PlateText = ?", (plate_text,))
    record = cursor.fetchone()

    if record:
        name, age = record
        return render_template('result.html', plate=plate_text, name=name, age=age, message="Plate found in the database")
    else:
        return render_template('add_details.html', plate=plate_text, image_path=plate_filename, message="Plate not found in database. Please provide details.")

# Live camera scanning route
@app.route('/scan')
def scan_plate():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')




# Save details route
@app.route('/save_details', methods=['POST'])
def save_details():
    plate_text = request.form['plate']
    name = request.form['name']
    age = request.form['age']
    image_path = request.form.get('image_path', 'default_path')  # Replace 'default_path' with a placeholder


    try:
        cursor.execute(
            "INSERT INTO PlateData (PlateImagePath, PlateText, Name, Age) VALUES (?, ?, ?, ?)",
            (image_path, plate_text, name, age)
        )
        conn.commit()
        return render_template('success.html', message="Details saved successfully!")
    except Exception as e:
        return render_template('error.html', message=f"Failed to save details: {e}")

@app.route('/scan_number_plate')
def scan_number_plate():
    subprocess.run(['python', 'number_plate.py'])  # Running the Python script
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
