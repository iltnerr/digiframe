import tkinter as tk
from PIL import Image, ImageTk, ImageFilter, ImageChops
import os
import random
import datetime
import subprocess
import time

DELAY_CYCLE_SECONDS = 2 if os.name == "nt" else 5*60
CHANGE_PLAYLIST_SECONDS = 10 if os.name == "nt" else 24*60*60
PLAYLISTS_DIR = 'playlists/'
PORTRAIT_MODE = True

class HiddenRoot(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.wm_geometry("0x0+0+0")
        self.window = MySlideShow(self)
        self.window.startCycle()


class MySlideShow(tk.Toplevel):
    def __init__(self, *args, **kwargs):
        tk.Toplevel.__init__(self, *args, **kwargs)
        self.persistent_image = None
        
        # remove window decorations
        self.overrideredirect(True)

        # initialize random playlist
        self.playlists = os.listdir(PLAYLISTS_DIR)
        self.curr_playlist = "stable_diffusion"
        self.curr_playlist_last_update = datetime.datetime.now()
        self.playlist_changed = False

        self.imageList = os.listdir(os.path.join(PLAYLISTS_DIR, self.curr_playlist))
        random.shuffle(self.imageList)
        self.curr_image_id = 0

        # used to display as background image
        self.label = tk.Label(self)
        self.label.pack(side="top", fill="both", expand=True)   

        # hdmi on/off schedule
        self.hdmi_switch = True 
        self.is_default_hdmi_schedule = True  
        self.default_hdmi_schedule = {
                                0: (18,21), # Mon
                                1: (18,21), # Tue
                                2: (18,21), # Wed
                                3: (18,21), # Thu
                                4: (17,22), # Fri
                                5: (10,22), # Sat
                                6: (10,21), # Sun
                                }   
        
        # set window size to fit screen
        self.scr_w, self.scr_h = self.winfo_screenwidth(), self.winfo_screenheight()        
        self.wm_geometry("{}x{}+{}+{}".format(self.scr_w, self.scr_h, 0, 0))                       
        
    def print_settings(self):
        print(f"\n\n\nCycle Length: {DELAY_CYCLE_SECONDS/60} minutes")
        print(f"Default Schedule: {self.is_default_hdmi_schedule}")
        print(f"Portrait Mode: {PORTRAIT_MODE}")
        print(f"\nKeybinds:\nF1 - Change Playlist\nF2 - Switch Schedule")
        print("\n---------------------------\n")
    
    def next_playlist(self):
        sample = random.choice(self.playlists)
        
        while sample == self.curr_playlist: #avoid repetitions
            sample = random.choice(self.playlists)
        self.curr_playlist = sample
        
        self.curr_playlist_last_update = datetime.datetime.now()
        self.curr_image_id = 0
        self.playlist_changed = True
        print(f"{datetime.datetime.now()}: Switched Playlist to {self.curr_playlist}.")
        
    def switch_schedule(self):
        self.is_default_hdmi_schedule = not self.is_default_hdmi_schedule
        print(f"{datetime.datetime.now()}: Changed Schedule: self.is_default_hdmi_schedule = {self.is_default_hdmi_schedule}")
        
    def show_new_playlist(self):
        self.next_playlist()
        self.check_imageList()
        image_path = os.path.join(PLAYLISTS_DIR, self.curr_playlist, self.imageList[self.curr_image_id])
        self.showImage(image_path)

    def showImage(self, filename):
        image = Image.open(filename)
        if PORTRAIT_MODE:
            image = image.rotate(-90, expand=True)

        img_w, img_h = image.size
        
        # rescale image to fit screen size
        if PORTRAIT_MODE:
            ratio = self.scr_h / img_h
            image = image.resize((int(ratio*img_w), self.scr_h))
            img_w, img_h = image.size # get new image size after resizing
        else:
            image.thumbnail((self.scr_w, self.scr_h), Image.Resampling.LANCZOS) # TODO: this can only downscale
            
        # create blurry background and center it
        ratio = self.scr_w / img_w
        hsize = int((float(img_h) * float(ratio)))
        bg = image.resize((self.scr_w, hsize), Image.Resampling.LANCZOS)        
        bg = bg.filter(ImageFilter.GaussianBlur(40))
        bg_w, bg_h = bg.size
        
        # center Background
        bg_hoffset = (bg_h - self.scr_h) // 2
        bg = ImageChops.offset(bg, 0, -bg_hoffset)
        
        # paste image to center of screen ------ should be a one liner?
        if os.name == "nt": # nt=windows
            offset = ((bg_w - img_w) // 2, (bg_h - img_h) // 2)
        else:
            offset = ((self.scr_w - img_w) // 2, (self.scr_h - img_h) // 2)
            
        bg.paste(image, offset)
        
        # tk image 
        self.persistent_image = ImageTk.PhotoImage(bg)
        self.label.configure(image=self.persistent_image)

    def check_playlist(self):
        t_elapsed = (datetime.datetime.now() - self.curr_playlist_last_update).total_seconds()
        if t_elapsed > CHANGE_PLAYLIST_SECONDS:
            self.next_playlist()

    def check_imageList(self):
        playlist_path = os.path.join(PLAYLISTS_DIR, self.curr_playlist)
        images = [file for file in os.listdir(playlist_path) if os.path.isfile(os.path.join(playlist_path, file))]

        if set(images) != set(self.imageList): 
            if not self.playlist_changed:
                
                if len(set(images)) > len(set(self.imageList)):
                    # images were added
                    print(f"{datetime.datetime.now()}: New images detected. Inserting them into the playlist to display them immediately.")
                    diff = set(images) - set(self.imageList)
                    self.imageList = self.imageList[:self.curr_image_id+1] + list(diff) + self.imageList[self.curr_image_id+1:]
                    print(f"DIFF = {list(diff)}")
                    print(f"self.imageList = {self.imageList}")
                else:
                    # images were removed
                    print(f"{datetime.datetime.now()}: Images were removed. Updating playlist.")
                    self.imageList = images
                    self.curr_image_id = 0
                    print(f"self.imageList = {self.imageList}")

        if self.playlist_changed:
            self.imageList = os.listdir(os.path.join(PLAYLISTS_DIR, self.curr_playlist))
            random.shuffle(self.imageList)
            self.playlist_changed = False

        if self.imageList[self.curr_image_id] == self.imageList[-1]:
            print(f"{datetime.datetime.now()}: End of playlist reached. Shuffle and repeat.")
            random.shuffle(self.imageList)
            self.curr_image_id = 0
        else:
            self.curr_image_id += 1

    def check_hdmi_schedule(self):
        t_now = datetime.datetime.now()
        day = datetime.datetime.today().weekday() # 0=Monday, 6=Sunday
        on, off = self.default_hdmi_schedule[day] if self.is_default_hdmi_schedule else (12, 22)

        if on <= t_now.hour < off:
            if not self.hdmi_switch:
                returncode = subprocess.run(["xrandr", "--output", "HDMI-1", "--auto"], capture_output=True) 
                print(f"Subprocess Return Code:\nstdout={returncode.stdout}\nstderr={returncode.stderr}")
                self.hdmi_switch = True
                print(f"{t_now}: HDMI turned on.")
        else:
            # turn hdmi off and repeatedly check when it should be turned on again 
            if self.hdmi_switch:
                returncode = subprocess.run(["xrandr", "--output", "HDMI-1", "--off"], capture_output=True)
                print(f"Subprocess Return Code:\nstdout={returncode.stdout}\nstderr={returncode.stderr}")
                self.hdmi_switch = False
                print(f"{t_now}: HDMI turned off.")
            
            t_sleep = 15*60 
            print(f"{t_now}: HDMI is off. Sleeping for {t_sleep/60} minutes.")
            time.sleep(t_sleep)
            self.check_hdmi_schedule()

    def startCycle(self):
        if not os.name == "nt":
            self.check_hdmi_schedule()
        self.check_playlist()
        self.check_imageList()

        image_path = os.path.join(PLAYLISTS_DIR, self.curr_playlist, self.imageList[self.curr_image_id])
        self.showImage(image_path)
        
        # Callback after x ms (cycle through pics)
        self.after(DELAY_CYCLE_SECONDS*1000, self.startCycle)


if not os.name == "nt":
    subprocess.run(["xrandr", "--output", "HDMI-1", "--auto"]) # make sure hdmi is turned on when initializing!
    
slideShow = HiddenRoot()
slideShow.bind("<Escape>", lambda e: slideShow.destroy())
slideShow.bind("<F1>", lambda e: slideShow.window.show_new_playlist())
slideShow.bind("<F2>", lambda e: slideShow.window.switch_schedule())

slideShow.window.print_settings()
slideShow.mainloop()
