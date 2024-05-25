# Version 0.0.1
import re
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter.filedialog import askopenfilename, asksaveasfilename
import pymysql

# Connect to MySQL database using PyMySQL
conn = pymysql.connect(host='localhost', user='root', password='***', database='spellchecker', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

def load_words_from_mysql():
    turkish_words = set()
    with conn.cursor() as cursor:
        cursor.execute("SELECT turkishwords FROM TDK")
        for row in cursor.fetchall():
            turkish_words.add(row['turkishwords'])
    return turkish_words

# Load Turkish words from the MySQL database
turkish_words = load_words_from_mysql()

def open_file(text_edit):
    filepath = askopenfilename(filetypes=[("All Files", "*.*",)])

    if not filepath:
        return

    text_edit.delete(1.0, tk.END)
    with open(filepath, "r") as f:
        content = f.read()
        text_edit.insert(tk.END, content)
    text_edit.master.title(f"Open File:{filepath}")

def save_file(text_edit):
    filepath = asksaveasfilename(filetypes=[("All Files", "*.*",)])

    if not filepath:
        return
    
    with open(filepath, "w") as f:
        content = text_edit.get(1.0, tk.END)
        f.write(content)
        text_edit.master.title(f"Save File:{filepath}")

class Illumicheck:
    def __init__(self):
        self.root = tk.Tk() 
        self.root.title("Illumicheck")
        
        # Create a menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Create a File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=lambda: open_file(self.text))
        file_menu.add_command(label="Save", command=lambda: save_file(self.text))

        # Configure row and column weights
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)  # Keep the frame fixed width

        self.root.bind("<Control-s>", lambda x: save_file(self.text))
        self.root.bind("<Control-o>", lambda x: open_file(self.text))
        self.root.bind("<Command-s>", lambda x: save_file(self.text))
        self.root.bind("<Command-o>", lambda x: open_file(self.text))

        self.text = ScrolledText(self.root, font=("Helvetica 14"))
        self.text.grid(row=0, column=0, sticky="nsew")  # Make the text widget sticky in all directions

        self.text.bind("<KeyRelease>", self.check)
        self.old_spaces = 0
        
        self.root.mainloop() 

    def check(self, event):
        content = self.text.get("1.0", tk.END)  # 1.0 is the first character, 1.1 is the second character, 1.2 is the third character etc.  # tk.END this gives the full content of the text box
        space_count = content.count(" ") # Count the white spaces

        if space_count != self.old_spaces: # If space count is not the same, != as self.old_spaces
            self.old_spaces = space_count

            for tag in self.text.tag_names():
                self.text.tag_delete(tag)
            
            for word in content.split(" "):
                if re.sub(r"[^\w]", "", word.lower()) not in turkish_words:
                    position = content.find(word)
                    self.text.tag_add(word, f"1.{position}", f"1.{position + len(word)}")
                    self.text.tag_config(word, foreground="red")

Illumicheck()
