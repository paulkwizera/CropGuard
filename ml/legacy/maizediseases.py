from ultralytics import YOLO
import cv2
import os
from db.db import check_credentials, check_existance

#Login / Register
print("========== CropGuard - Maize Disease Detector ==========")
print("Please login or register to continue.")

logged_in = False
while not logged_in:
    print("\n1. Login")
    print("2. Register")
    option = input("Choose an option (1 or 2): ").strip()

    if option == "1":
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        logged_in = check_credentials(username, password)

    elif option == "2":
        username = input("Choose a username: ").strip()
        password = input("Choose a password: ").strip()
        logged_in = check_existance(username, password)

    else:
        print("Invalid option. Enter 1 or 2.")

# Detection 
print("\n---maize diseases detector---")
print("how would you like to provide the input")
print("1. livecam")
print("2. image from gallery")

# load our model
model = YOLO('best.pt')

choice = int(input("choose between one and two ").strip())

# run detection using cam
if choice == 1:
    source_path = '0'
    print("Opening webcam..... Press 'q' on the image window to quit")

# run detection from gallery
elif choice == 2:
    path = input("enter the files full path from file explorer: ").strip()
    if os.path.exists(path):
        source_path = path
    else:
        print(f"Error: Could not find the image from this path {path}")
        exit()

else:
    print("INVALID CHOICE")
    exit()

# execution stage
results = model.predict(source=source_path, show=True, conf=0.8, imgsz=320)

# to quit
print("Detection finished. Press any key on the image window to close")
cv2.waitKey(0)
cv2.destroyAllWindows()
