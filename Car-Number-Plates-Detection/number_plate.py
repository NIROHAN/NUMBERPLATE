import cv2
import pytesseract
import pyodbc
import os

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# MS SQL Database connection setup (Windows Authentication)
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

# Create plates directory if it doesn't exist
if not os.path.exists("plates"):
    os.makedirs("plates")

# Load Haar Cascade for plate detection
harcascade = "model/haarcascade_russian_plate_number.xml"

cap = cv2.VideoCapture(0)
cap.set(3, 640)  # Width
cap.set(4, 480)  # Height

min_area = 500
count = 0

while True:
    success, img = cap.read()
    plate_cascade = cv2.CascadeClassifier(harcascade)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect license plates
    plates = plate_cascade.detectMultiScale(img_gray, 1.1, 4)

    for (x, y, w, h) in plates:
        area = w * h
        if area > min_area:
            # Draw rectangle around the plate
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(img, "Number Plate", (x, y - 5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 255), 2)

            img_roi = img[y:y + h, x:x + w]
            cv2.imshow("ROI", img_roi)

            # Perform OCR on the detected plate
            plate_text = pytesseract.image_to_string(img_roi, config='--psm 8')  # Use psm 8 for single-word detection
            plate_text = plate_text.strip()

            if plate_text:
                # Check if the plate is already in the database
                cursor.execute("SELECT Name, Age FROM PlateData WHERE PlateText = ?", (plate_text,))
                record = cursor.fetchone()

                if record:
                    name, age = record
                    cv2.putText(img, f"Name: {name}", (x, y + h + 20), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 255), 2)
                    cv2.putText(img, f"Age: {age}", (x, y + h + 40), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 255), 2)

    cv2.imshow("Result", img)

    # Save plate data when 's' is pressed
    if cv2.waitKey(1) & 0xFF == ord('s'):
        plate_filename = f"plates/scanned_img_{count}.jpg"
        cv2.imwrite(plate_filename, img_roi)

        # Input additional details
        name = input(f"Enter name for plate {plate_text}: ")
        age = int(input(f"Enter age for plate {plate_text}: "))

        # Save to the database
        cursor.execute("INSERT INTO PlateData (PlateImagePath, PlateText, Name, Age) VALUES (?, ?, ?, ?)",
                       (plate_filename, plate_text, name, age))
        conn.commit()

        cv2.rectangle(img, (0, 200), (640, 300), (0, 255, 0), cv2.FILLED)
        cv2.putText(img, "Plate Saved", (150, 265), cv2.FONT_HERSHEY_COMPLEX_SMALL, 2, (0, 0, 255), 2)
        cv2.imshow("Results", img)
        cv2.waitKey(500)
        count += 1

    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
conn.close()
