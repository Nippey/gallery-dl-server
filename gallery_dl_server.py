# /Library/Frameworks/Python.framework/Versions/3.7/bin/python3

import argparse
import os
import gallery_dl

from bottle import route, run, Bottle, request, static_file, template
from queue import Queue
from threading import Thread, Lock
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import datetime
import time
import os
import traceback

parser = argparse.ArgumentParser()
parser.add_argument("--zip_downloads", 
                    nargs='?',
                    const=1,
                    default='True',
                    choices=['False', 'True'], 
                    help="Zip files into CBZ after download")
args = parser.parse_args()

class GalleryDb():
    def __init__(self, dbname="gallery-dl.db"):
        self.con = sqlite3.connect(dbname, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.queue_lock = Lock()
        
        cur = self.con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS downloads(id INTEGER, url TEXT NOT NULL, status TEXT NOT NULL, enqueued INTEGER, started INTEGER DEFAULT 0, finished INTEGER DEFAULT 0, path TEXT DEFAULT '', size INTEGER DEFAULT 0, PRIMARY KEY('id'))")
        self.con.commit()

    def get_queue(self):
        cur = self.con.cursor()
        res = cur.execute("SELECT * FROM downloads")
        return res.fetchall()
        
    def add_urls(self, urls):
        try:
            self.queue_lock.acquire()
            data = [(url, "enqueued", datetime.datetime.now()) for url in urls]
            cur = self.con.cursor()
            cur.executemany("INSERT INTO downloads('url', 'status', 'enqueued') VALUES(?, ?, ?)", data)
            self.con.commit()
        finally:
            self.queue_lock.release()
    
    def dl_started(self, id):
        try:
            self.queue_lock.acquire()
            cur = self.con.cursor()
            cur.execute(f"UPDATE downloads SET status = 'started', started = '{datetime.datetime.now()}' WHERE id == {id} LIMIT 1;")
            self.con.commit()
        finally:
            self.queue_lock.release()
            
    def dl_finished(self, id, fpath, fsize):
        try:
            self.queue_lock.acquire()
            cur = self.con.cursor()
            cur.execute(f"UPDATE downloads SET status = 'finished', finished = '{datetime.datetime.now()}', path = '{fpath}', size = '{fsize}' WHERE id == {id} LIMIT 1;")
            self.con.commit()
        finally:
            self.queue_lock.release()

    def dl_error(self, id):
        try:
            self.queue_lock.acquire()
            cur = self.con.cursor()
            cur.execute(f"UPDATE downloads SET status = 'error' WHERE id == {id} LIMIT 1;")
            self.con.commit()
        finally:
            self.queue_lock.release()

    def get_next_row(self):
        try:
            self.queue_lock.acquire()
            cur = self.con.cursor()
            res = cur.execute("SELECT id, url FROM downloads WHERE status = 'enqueued' ORDER BY id LIMIT 1;")
            row = res.fetchone()
        finally:
            self.queue_lock.release()
            
        return row

    def dl_delete(self, id):
        try:
            self.queue_lock.acquire()
            cur = self.con.cursor()
            cur.execute(f"DELETE FROM downloads WHERE id = {id} LIMIT 1;")
            self.con.commit()
        finally:
            self.queue_lock.release()

    def dl_restart(self, id):
        try:
            self.queue_lock.acquire()
            cur = self.con.cursor()
            cur.execute(f"UPDATE downloads SET status = 'enqueued' WHERE id == {id} LIMIT 1;")
            self.con.commit()
        finally:
            self.queue_lock.release()


galleryDb = GalleryDb()

queue_changed = Queue()


app = Bottle()
MAX_WORKERS = 2
DL_THREAD = ThreadPoolExecutor(max_workers=MAX_WORKERS)
IN_FLIGHT = {}
EXIT = False
RETRIES = 2

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8080

GALLERY_PATH = './gallery-dl/'
ZIP_SUFFIX = 'cbz'

class NoPathExists(Exception):
    pass

def sizeof_fmt(num, suffix="B"):
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def report_finished(id, error, fpath, fname):
    queue_changed.put((id, error, fpath, fname))
    pass

def report_new():
    queue_changed.put((-1, ))
    pass

def queue_handler():
    report_new()

    print(f'[  ] Queue Handler started!')
    while not EXIT:
        queue_elm = queue_changed.get()
        id = queue_elm[0]
        
        #Something finished
        if isinstance(id, int) and id > 0:
            thread_data = IN_FLIGHT.pop(id, None)
            
            error = queue_elm[1]
            fpath = queue_elm[2]
            fname = queue_elm[3]
            
            if error == 1: #"Hard-Error", stop
                galleryDb.dl_error(id)
                print(f'[{id}] Thread failed!')
            elif error == 2 and thread_data["retry"] > 0: #"Soft-Error", try again
                galleryDb.dl_error(id)
                IN_FLIGHT[row["id"]] = {
                    "thread": DL_THREAD.submit(call_gallery_dl, row["url"], row["id"]), 
                    "retry":  thread_data["retry"]-1
                }
                print(f'[{id}] Thread restarted (Retry {RETRIES-(thread_data["retry"]-1)})!')
            else:
                fsize = sizeof_fmt(os.path.getsize(os.path.join(fpath,fname)))
                galleryDb.dl_finished(id, fpath, fsize)
                print(f'[{id}] Thread finished!')

        #Add next job(s)
        while len(IN_FLIGHT) < MAX_WORKERS:
            row = galleryDb.get_next_row()
            
            if row == None:
                break
            
            print(f'[{row["id"]}] Thread started!')
            IN_FLIGHT[row["id"]] = {
                "thread": DL_THREAD.submit(call_gallery_dl, row["url"], row["id"]), 
                "retry": RETRIES
            }
            
            galleryDb.dl_started(row["id"])
            
            time.sleep(1)
            
def call_gallery_dl(url, id):
    error = 1
    fpath = None
    fname = None
    
    try:
        print(f'[{id}] Start downloading!')
        gallery_dl.config.load()
        download_job = gallery_dl.job.DownloadJob
        downloader = download_job(url)
        downloader.run()
        
        fpath = downloader.pathfmt.directory
        fname = downloader.pathfmt.filename
        if fpath and fname:
            error = 0
        
        #import pdb;pdb.set_trace()
        
        if args.zip_downloads == 'True':
            download_path = downloader.pathfmt.directory
            zip_directories(download_path)
            
        print(f'[{id}] Finished downloading!')

    except gallery_dl.exception.NoExtractorError as gd:
        print(gd)
    except ValueError as ve:
        #Try to catch "generator already executing"
        #This will happen if called multiple times shortly after each other
        print(ve)
        error = 2 #"Soft-Error"
    except Exception as e:
        print(e)
        print(traceback.format_exc())
    finally:
        report_finished(id, error, fpath, fname)
        print(f'[{id}] Thread exit!')
  


@app.route('/', method=['POST','GET'])
def gallery_main():
    flashclass = ""
    flash = ""

    if request.method == 'POST':
        urls = request.forms.get('url')
        urls = urls.splitlines()
        no_urls = len(urls)

        if not urls:
            return {'Missing URL'}
        
        #Get some metadata:
        #job = gallery_dl.job.DownloadJob(url)
        #extractor = job.extractor.__module__
        
        galleryDb.add_urls(urls)
        
        report_new()
        
        flashclass = "flash-green"
        flash = f"{no_urls} URL(s) successfully added to queue"
        
        print(flash)
        
    #return static_file('index.html', root='./')
    return template('index', root='./', queue_length = DL_THREAD._work_queue.qsize(), flashclass = flashclass, flash = flash, queue = galleryDb.get_queue())

@app.route('/delete/<id>', method='GET')
def delete_entry(id):
    flashclass = ""
    flash = ""

    #TODO: Check if "in flight" or exists at all
    galleryDb.dl_delete(id)
    flashclass = "flash-green"
    flash = f"Deleted entry with id {id}"

    return template('index', root='./', queue_length = DL_THREAD._work_queue.qsize(), flashclass = flashclass, flash = flash, queue = galleryDb.get_queue())

@app.route('/restart/<id>', method='GET')
def restart_entry(id):
    flashclass = ""
    flash = ""

    #TODO: Check if exists
    galleryDb.dl_restart(id)
    flashclass = "flash-green"
    flash = f"Restarted entry with id {id}"
    
    report_new()
    
    return template('index', root='./', queue_length = DL_THREAD._work_queue.qsize(), flashclass = flashclass, flash = flash, queue = galleryDb.get_queue())

@app.route('/debug')
def debug():
    import pdb
    import sys
    import traceback
    import threading
    for th in threading.enumerate(): 
        print(th)
        traceback.print_stack(sys._current_frames()[th.ident])
        print()
    pdb.set_trace()  

@app.route('/gallery-dl/create_zip', method='GET')
def find_directories_and_zip():
    if not os.path.exists(GALLERY_PATH):
        raise NoPathExists("GALLERY PATH does not exist; Download something and try again")

    top_dir = os.listdir(GALLERY_PATH)
    for each_dir in top_dir:
        each_dir_path = os.path.join(GALLERY_PATH, each_dir)
        zip_directories(each_dir_path)

    return {'successful_created_zips': True}


def zip_directories(path_to_zip):
    for root_path, dirct, files in os.walk(path_to_zip):

        # Check if there are photos in the files, if not skip directory
        photos_in_directory = [x for x in files if x.rsplit('.', 1)[1] in ('jpg', 'png')]
        if not photos_in_directory:
            print('No photos in directory: ' + root_path)
            continue

        # Remove trailing / if it exists
        zip_path, zip_file = root_path.rstrip('/').rsplit('/', 1)
        zip_file_name = zip_file + '.' + ZIP_SUFFIX
        zip_file_path = os.path.join(zip_path, zip_file_name)

        # Check if zip file has already been created and skip if already created
        # TODO: Allow ability to ignore check and re-zip folders.
        if os.path.exists(zip_file_path):
            existing_zip = ZipFile(zip_file_path)
            items_in_zip = existing_zip.namelist()

            # If the photos in the directory is less than or equal to items in zip; skip
            if len(photos_in_directory) <= len(items_in_zip):
                print('Files have already been zipped.')
                print('Skipping')
                continue

        print('Creating file: ' + zip_file_path)
        with ZipFile(zip_file_path, 'w') as myzip:
            for each_photo in photos_in_directory:
                each_photo_path = os.path.join(root_path, each_photo)
                myzip.write(each_photo_path)
        print('Finished creating zip for: ' + root_path)


if __name__ == '__main__':
    Thread(target=queue_handler).start() #threading.Thread(target=run, kwargs=dict(host='localhost', port=8080)).start()
    app.run(host=DEFAULT_HOST, port=DEFAULT_PORT, debug=True, reloader=True)
