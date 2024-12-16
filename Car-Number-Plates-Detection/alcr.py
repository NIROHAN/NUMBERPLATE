import easyocr

# Initialize EasyOCR reader for multiple languages
reader = easyocr.Reader(['en'])  # Add more languages as needed

while True:
    success, img = cap.read()

    # Detect license plates
    results = reader.readtext(img)

    for result in results:
        plate_text = result[1]
        if plate_text:
            # Check if the plate is already in the database
            cursor.execute("SELECT Name, Age FROM PlateData WHERE PlateText = ?", (plate_text,))
            record = cursor.fetchone()

            if record:
                name, age = record
                # Draw the detected plate
                x, y, w, h = result[0]
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(img, "Number Plate", (x, y - 5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 0, 255), 2)
                cv2.putText(img, f"Name: {name}", (x, y + h + 20), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 255), 2)
                cv2.putText(img, f"Age: {age}", (x, y + h + 40), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 255), 2)

    cv2.imshow("Result", img)
