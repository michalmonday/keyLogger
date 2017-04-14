# keyLogger

The working mechanism utilises FTP server as a intermediate between the victim and the attacker. The cool thing about FTP server is that it can be created for free within 5 minutes, all you need is an email, no personal data. The idea to use FTP as a medium has been taken by me from "★Cam★" user's [release](https://hackforums.net/showthread.php?tid=5558161). This project relies on his release too but it was little bit "wooden", this code/project doesn't resemble it anymore so I share it as mine.

The keys.py is the file which does all the work, logging the keystrokes, collecting some system information, making screenshots and sending all of these encrypted to the FTP server as files.

The keys_retriever.py is used to connect to the FTP server, collect the information, automatically decrypt it and present to the user. It also has a function to upload a file to the FTP server which will be automatically downloaded by the keys.py with an option to execute it or add to system startup. There's also a special handling for "nirsoft" executables.

Example of an output:
![](http://i.imgur.com/b4viSNF.png)
