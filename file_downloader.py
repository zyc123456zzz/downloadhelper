import subprocess
import sys
import argparse
import time
from tqdm import tqdm
import requests
import threading
import os
from queue import Queue
import signal
from threading import Thread
import decoder
import ftplib
import struct
import shutil
import zipfile
import py7zr
import rarfile

MAX_THREAD = 10  # 最大线程数
TAG = "****RESUME FROM HERE****"
TAG = TAG.encode()
input_stream=[] # format : ***(url) ***(out_path) ***(concurrency)
threadLock = threading.Lock()
file_lock = threading.Lock()

'''
互斥线程为：更改数据列表的8个子线程，访问数据列表的主线程。都需要加锁
多建一个子线程，来完成监视总体的工作
'''

# a function to add url and makes them a queue.
# all urls comes from our inputs -- using add_download() function.
# for every url download task, we need to use the previous download method to make it.

class DownloadManager(threading.Thread):
    def __init__(self, thread_name):
        super(DownloadManager, self).__init__(name=thread_name)
        self.url_queue = Queue()    # urls_queue where we can put and get info from
        self.__flag = threading.Event()
        self.__flag.set()   # means __flag is true  flag--pause
        self.__running = threading.Event()
        self.__running.set()    # running -- cancel

    # how this thread runs by cpu ----consumer
    def run(self):
        print("Start downloading...")
        while self.__running.isSet():
            self.__flag.wait()  # if true then run the process, else just wait until __flag turns true.
            ### run program
            while not self.url_queue.empty():
                url, save_path, con, max_speed = self.url_queue.get()
                # print(1)
                downloader=single_downloader(url,save_path,con,max_speed)
                downloader.setDaemon(True)
                downloader.start()
                downloader.join()
                self.url_queue.task_done()


            # let the process end when it doesn't work
            time.sleep(5)   # in case the process bar subprocess haven't finished
            os.kill(os.getpid(), signal.SIGTERM)

    # add file download tasks  ----producer
    def add_download(self, url, save_path,con_number,max_speed):
        self.url_queue.put((url, save_path, con_number,max_speed))

    def pause(self):
        self.__flag.clear()

    def resume(self):
        self.__flag.set()

    def cancel(self):
        self.__flag.set()
        self.__running.clear()
        os.kill(os.getpid(), signal.SIGTERM)


# single file downloader module
class single_downloader(threading.Thread):
    def __init__(self,url, filename, con, max_speed):
        threading.Thread.__init__(self)
        self.thread_data=[0]*con
        self.url = url
        self.filename = filename
        self.con = con
        self.resume = False
        self.max_speed=max_speed


    def run(self):
        # need to get a key then run the sub-process
        threadLock.acquire()
        # download a part of this file, so... we need to know which part to download.
        self.download_file(self.url, self.filename,self.max_speed, self.con)
        threadLock.release()

    # used to assign jobs to different threads ---- downloader top layer
    def download_file(self, url, filename, max_speed, concurrency=8):
        # 粗粒度断点重传 如果从当前chunk断掉则连同当前块一起重传
        response = requests.head(url)
        file_size = int(response.headers.get('Content-Length', 0))
        chunk_size = file_size // concurrency
        if os.path.exists(filename):
            self.resume=True
            first_byte=os.path.getsize(filename)
            first_byte=first_byte//chunk_size   # the chunk needed to be retransmitted
        else:
            first_byte=0

        first_byte=first_byte*chunk_size    # the exact position we need to start downloading
        # download the rest of this file
        chunk_size = (file_size - first_byte) // concurrency

        # 通过访问列表来更改已经下载的数据并且来显示总体的进度
        def data_detector():
            print("WHOLE PROCESS BAR IS WORKING NOW!\n")
            last = 0
            with tqdm(total=file_size, unit='B', unit_scale=True, desc='Total Process: ') as process_bar:
                for i in range(file_size):
                    threadLock.acquire()
                    total = sum(self.thread_data)
                    threadLock.release()
                    delta = total - last
                    last = total
                    process_bar.update(delta)

        # used for downloading a part of a file
        def download_chunk(url, start, end, filename, number,max_speed):
            print(f'\nStart download thread-{number}')
            headers = {'Range': f'bytes={start}-{end}'}

            batch_size = 1024  # 每次下载的大小
            content_size = end - start

            response = requests.get(url, headers=headers, stream=True)
            if response.status_code != 206:
                print("NOT SUPPORTED!")
                print("The HTTP status_code is: " + str(response.status_code))
                sys.exit(1)

            with open(filename, 'ab+') as file:
                file.seek(start)
                # tagged resume process
                if self.resume:
                    file.write(TAG)
                    self.resume=False

                with tqdm(total=content_size, unit='B', desc=f'thread-{number}: ', unit_scale=True,
                          unit_divisor=1024) as proocess_bar:
                    for data in response.iter_content(chunk_size=batch_size):
                        file.write(data)
                        self.thread_data[number] += len(data)
                        # 更新线程执行进度
                        proocess_bar.update(len(data))

                        # speed limitation
                        if max_speed > 0:
                            t = len(data) / max_speed
                            time.sleep(t)
        # all_process bar
        thread_detector = Thread(target=data_detector)
        thread_detector.setDaemon(True)
        thread_detector.start()

        # sub_process bar
        for i in range(concurrency):
            start = first_byte + i * chunk_size
            end = start + chunk_size - 1 if i < concurrency - 1 else file_size - 1
            thread = Thread(target=download_chunk, args=(url, start, end, filename, i, max_speed, ))
            thread.setDaemon(True)
            thread.start()
            thread.join()  # join() is set

        # when we download all parts of the file, we need to unzip it and classify it
        print("Classifier working!")
        worker = classifier()
        file_type = worker.get_filetype(self.filename)
        print("The file_type is: " + file_type + "\n")
        print(filename + "下载完成！\n")


class ftp_downloader:
    def __init__(self, url):
        self.ftp=ftplib.FTP(url)
    def cwd(self,dir):
        self.ftp.cwd(dir)

    def Login(self, user='', passwd=''):
        self.ftp.login(user, passwd)
        # print(self.ftp.welcome)

    def DownLoadFile(self, LocalFile, RemoteFile):  # 下载单个文件
        file_handler = open(LocalFile, 'wb+')
        bufsize=1024
        # self.ftp.retrbinary("RETR %s" % (RemoteFile), file_handler.write)#接收服务器上文件并写入本地文件
        self.ftp.retrbinary('RETR ' + RemoteFile, file_handler.write,bufsize)
        file_handler.close()
        print("Ftp Download Successfully!")
        return True

    def close(self):
        self.ftp.quit()


# classify the downloaded file according to the postfix
class classifier():
    type_dict = {
        'FFD8FF': 'jpg', '89504E47': 'png', '47494638': 'gif', '49492A00': 'tif',
        '424D': 'bmp', '38425053': 'psd', '7B5C727466': 'rtf', '3C3F786D6C': 'xml',
        '68746D6C3E': 'html', '44656C69766572792D646174653A': 'eml', 'CFAD12FEC5FD746F': 'dbx', '2142444E': 'pst',
        'D0CF11E0': 'doc/xls', '5374616E64617264204A': 'mdb', 'FF575043': 'wpd', '252150532D41646F6265': 'ps/eps',
        '255044462D312E': 'pdf', 'AC9EBD8F': 'qdf', 'E3828596': 'pwl', '504B0304': 'zip',
        '52617221': 'rar', '57415645': 'wav', '41564920': 'avi', '2E7261FD': 'ram',
        '2E524D46': 'rm', '000001BA': 'mpg', '000001B3': 'mpg', '6D6F6F76': 'mov', '3026B2758E66CF11': 'asf',
        '4D546864': 'mid', '377ABCAF271C':'7z', '4D5A':'exe',
    }

    # 转成16进制字符串
    def bytes2hex(self,bytes):
        num = len(bytes)
        hexstr = u""
        for i in range(num):
            t = u"%x" % bytes[i]
            if len(t) % 2:
                hexstr += u"0"
            hexstr += t
        return hexstr.upper()

    # 获得类型
    def get_filetype(self,filename):
        file = open(filename, 'rb')
        ftype = 'unknown'

        for k, v in self.type_dict.items():
            num_bytes = int(len(k) / 2)
            file.seek(0)
            hbytes = struct.unpack('B' * num_bytes, file.read(num_bytes))
            code = self.bytes2hex(hbytes)
            if code == k:
                ftype = v
                break

        # print(ftype + "\n")
        file.close()

        if (ftype == 'jpg') or (ftype == 'png') or (ftype == 'gif') or (ftype == 'tif') or (ftype == 'bmp'):
            output_path = './image/' + filename
        elif (ftype == 'mov') or (ftype == 'avi') or (ftype == 'rm') or (ftype == 'mpg') or (ftype == 'asf'):
            output_path = './video/' + filename
        elif (ftype == 'zip') or (ftype == 'rar') or (ftype == '7z'):
            output_path = './compressed/' + filename
        elif (ftype == 'mid') or (ftype == 'wav'):
            output_path = './music/' + filename
        elif (ftype == 'pdf') or (ftype == 'doc') or (ftype == 'xsl') or (ftype == 'rtf') or (ftype == 'xsl'):
            output_path = './file/' + filename
        elif ftype == 'exe':
            output_path = './apps/' + filename
        else:
            output_path = './others/' + filename

        # file move
        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))
        shutil.move(filename,output_path)

        # unzip the file
        if ftype == 'zip' :
            with zipfile.ZipFile(output_path,'r') as __:
                if not os.path.exists('./unzipped/'):
                    os.makedirs('./unzipped/')
                __.extractall('./unzipped/')
        elif ftype == '7z':
            with py7zr.SevenZipFile(output_path,mode='r') as __:
                if not os.path.exists('./unzipped/'):
                    os.makedirs('./unzipped/')
                __.extractall('./unzipped/')
        elif ftype == 'rar':
            with rarfile.RarFile(output_path) as __:
                if not os.path.exists('./unzipped/'):
                    os.makedirs('./unzipped/')
                __.extractall('./unzipped/')


        # auto install
        # use subprocess to finish this job
        if ftype == 'exe':
            subprocess.Popen(output_path)

        return ftype

# everything needs to be done here


def main():
    # 输入模块
    parser = argparse.ArgumentParser(description='单个文件下载程序')
    parser.add_argument('--url', '-u', required=True, help='要下载的文件地址')
    parser.add_argument('--output', '-o', required=True, help='输出的文件名')
    parser.add_argument('--concurrency', '-n', type=int, default=8, help='并发线程数，默认为8')
    parser.add_argument('--speed', '-s', type=int, default=1000, help='下载速度限制，默认为1000B/s')

    args = parser.parse_args()
    url = args.url
    output = args.output
    concurrency = args.concurrency
    speed = args.speed

    input_stream.append((url, output, concurrency, speed))

    # thread data means the download process of all file information
    # decoder function was put in main_page
    # use the specific class to download all files

    download_manager = DownloadManager('ALL_TASKS_GOING_NOW')
    for item in input_stream:
        download_manager.add_download(item[0], item[1], item[2], item[3])

    download_manager.start()


'''    # test ftp downloader
    ftp=ftp_downloader('ftp.us.debian.org')
    ftp.Login()
    ftp.cwd('debian')
    ftp.DownLoadFile('README','README')
    ftp.close()'''

if __name__ == '__main__':
    main()

