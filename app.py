'''
MIT License

Copyright (c) 2019 Arshdeep Bahga and Vijay Madisetti

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Modified by Yannick Fumukani
'''

#!flask/bin/python
from aifc import Error
from flask import Flask, jsonify, abort, request, make_response, session, url_for, current_app 
from flask_session import Session
from flask import render_template, redirect
import os
import time
import datetime
import exifread
import json
import boto3

import mysql.connector

# from flask import current_app, flash, jsonify, make_response, redirect, request, url_for

app = Flask(__name__, static_url_path="")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

 # Set a secret key for sessions


# App related
APP_PORT = 5000

# Upload constant info
# UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'media')
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'media')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
BASE_URL = f"http://localhost:{APP_PORT}/media/"

# Access code console
AWS_ACCESS_KEY = "AKIAUQ3KAUNZQJT5JXMJEDDDD"
AWS_SECRET_KEY = "GWRWg/BUnYOKVmYF9W+dOmddZ4JbDqBomuDPL3kAddddd"
REGION = "us-east-1"

# Bucket info
BUCKET_NAME = "photo-bucket-yf"

# Azrael2023
# Database info
DB_HOSTNAME = "db-final.c9lg85cqwybk.us-east-1.rds.amazonaws.com"
DB_USERNAME = 'admin'
DB_PASSWORD = 'Azrael2023'
DB_NAME = 'gallery'
DB_PORT = 3306


# helper functions

def getExifData(path_name):
    f = open(path_name, 'rb')
    tags = exifread.process_file(f)
    ExifData = {}
    for tag in tags.keys():
        if tag not in ('JPEGThumbnail', 'TIFFThumbnail',
                       'Filename', 'EXIF MakerNote'):
            key = "%s" % (tag)
            val = "%s" % (tags[tag])
            ExifData[key] = val
    return ExifData


# Photo file upload to s3 Bucket

def s3uploading(filename, filenameWithPath):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY,
                      aws_secret_access_key=AWS_SECRET_KEY)

    bucket = BUCKET_NAME
    path_filename = "photos/" + filename
    print(path_filename)

    try:
        s3.upload_file(filenameWithPath, bucket, path_filename)
        s3.put_object_acl(ACL='public-read', Bucket=bucket, Key=path_filename)
    except Error as e:
        print("The file upload failed")

    return "https://"+BUCKET_NAME +\
        ".s3.amazonaws.com/" + path_filename
        

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Check if the username and password are correct
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'password':
            session['username'] = username
            return redirect("/")
        else:
            return render_template('login.html', error='Invalid username or password')
    else:
        return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    # Remove the username from the session
    session['username'] = None
    return redirect(url_for('login'))


# check if the extension is an image
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/', methods=['GET', 'POST'])
def index():

    if not session.get('username') :
        return redirect(url_for('login'))
         
    conn = mysql.connector.connect(host=DB_HOSTNAME, user=DB_USERNAME, password=DB_PASSWORD, database=DB_NAME)    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos")
    results = cursor.fetchall()

    items = []
    for item in results:
        photo = {}
        photo['PhotoID'] = item[0]
        photo['CreationTime'] = item[1]
        photo['Title'] = item[2]
        photo['Description'] = item[3]
        photo['Tags'] = item[4]
        photo['URL'] = item[5]
        items.append(photo)
    conn.close()

    print (items)
    return render_template('index.html', photos=items)
    # return render_template('index.html', photos=items)
    


# TODO implementing ...
@app.route('/add', methods=['GET', 'POST'])
def add_photo():
    
    if not session.get('username') :
        return redirect(url_for('login'))
   
    if request.method == 'POST':    
        uploadedFileURL=''
        file = request.files['imagefile']
        title = request.form['title']
        tags = request.form['tags']
        description = request.form['description']
        
        print (title,tags,description)
        if file and allowed_file(file.filename):
            filename = file.filename
            filenameWithPath = os.path.join(UPLOAD_FOLDER, filename)
            print (filenameWithPath)
            file.save(filenameWithPath)            
            uploadedFileURL = s3uploading(filename, filenameWithPath);
            ExifData=getExifData(filenameWithPath)
            print (ExifData)
            ts=time.time()
            timestamp = datetime.datetime.\
                        fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = mysql.connector.connect(host=DB_HOSTNAME, user=DB_USERNAME, password=DB_PASSWORD, database=DB_NAME)    
            cursor = conn.cursor()

            statement = "INSERT INTO photos (CreationTime, Title, Description, Tags, URL, EXIF) VALUES (" +\
                        "'"+str(timestamp)+"', '" +\
                        title+"', '" +\
                        description+"', '" +\
                        tags+"', '" +\
                        uploadedFileURL+"', '" +\
                        json.dumps(ExifData)+"');"

            cursor.execute(statement)
            conn.commit()
            cursor.close()
            
            # delete the file locally after being uploaded to the server
            os.unlink(filenameWithPath)
            
        return redirect('/')
        # return make_responsse(jsonify({"message" : "Image added successfully"}), 200)

    else:
        #return make_responsse(jsonify({"message" : "No available route", "severity": "danger"}), 401)
        return render_template('form.html')


# * Completed
@app.route('/<int:photoID>', methods=['GET'])
def view_photo(photoID):
    
    if not session.get('username') :
        return redirect(url_for('login'))
        
    conn = mysql.connector.connect(host=DB_HOSTNAME, user=DB_USERNAME, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor()
   # cursor.execute("SELECT * FROM photos")
    cursor.execute("SELECT * FROM photos WHERE PhotoID="+str(photoID)+"")

    results = cursor.fetchall()

    items = []
    
    for item in results:
        photo = {}
        photo['PhotoID'] = item[0]
        photo['CreationTime'] = item[1]
        photo['Title'] = item[2]
        photo['Description'] = item[3]
        photo['Tags'] = item[4]
        photo['URL'] = item[5]
        # photo['ExifData'] = json.loads(item[6])
        photo['ExifData'] = json.loads(item[6])
        items.append(photo)
    cursor.close()
    
    tags=items[0]['Tags'].split(',')
    exifdata=items[0]['ExifData']
    
    return render_template('photodetail.html', photo=items[0], 
                            tags=tags, exifdata=exifdata)

    # return make_response(jsonify({'data': items}), 200)

# * Searching photo
@app.route('/search/', methods=['GET'])
def search_page():
    
    if not session.get('username') :
        return redirect(url_for('login'))
        
    query = request.args.get('query', None)
    
    conn = mysql.connector.connect(host=DB_HOSTNAME, user=DB_USERNAME, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos \
                    WHERE Title LIKE '%"+query + "%' \
                    UNION SELECT * FROM \
                    photos WHERE \
                    Description LIKE '%"+query + "%' UNION \
                    SELECT * FROM photos \
                    WHERE Tags LIKE '%"+query+"%' ;")

    results = cursor.fetchall()

    items = []
    for item in results:
        photo = {}
        photo['PhotoID'] = item[0]
        photo['CreationTime'] = item[1]
        photo['Title'] = item[2]
        photo['Description'] = item[3]
        photo['Tags'] = item[4]
        photo['URL'] = item[5]
        photo['ExifData'] = item[6]
        items.append(photo)
        
    cursor.close()
    
    print (items)
    return render_template('search.html', photos=items, 
                            searchquery=query)
    # return make_response({'data': item}, 200)


if __name__ == '__main__':
    app.secret_key = 'cdffeeqsweeff566y6777'
    app.run(debug=True, host="0.0.0.0", port=APP_PORT)
