import re  # Import the regular expression module
import threading  # Import the threading module for running tasks in the background
import tkinter as tk  # Import the tkinter module for creating GUI applications
from tkinter import ttk  # Import ttk module from tkinter for advanced widgets
from tkinter.scrolledtext import ScrolledText  # Import ScrolledText widget from tkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename  # Import file dialog functions from tkinter
import pymysql  # Import pymysql module for MySQL database interaction
import json  # Import json module for reading and writing JSON files
import os  # Import os module for interacting with the operating system
import creds

# Cache file path
CACHE_FILE = 'word_cache.json'

# Establish a connection to the MySQL database
conn = pymysql.connect(
    host=creds.host,
    user=creds.user,
    password=creds.password,
    database=creds.database,
    charset=creds.charset,
    cursorclass=pymysql.cursors.DictCursor
)

# Set the batch size for loading words from the database
BATCH_SIZE = 5000000

def load_words_from_mysql(progress_var, existing_words):
    # Load words from MySQL database
    words = existing_words

    with conn.cursor() as cursor:
        # Get the total number of rows in the WordList table
        cursor.execute("SELECT COUNT(*) as count FROM WordList WHERE LENGTH(WordText) <= 20")
        total_rows = cursor.fetchone()['count']
        offset = 0

        while offset < total_rows:
            # Load a batch of words from the database
            cursor.execute(
                "SELECT WordText FROM WordList WHERE LENGTH(WordText) <= 20 LIMIT %s OFFSET %s",
                (BATCH_SIZE, offset)
            )
            rows = cursor.fetchall()

            for row in rows:
                words.add(row['WordText'])  # Add each word to the set

            offset += BATCH_SIZE
            progress = (offset / total_rows) * 100  # Progress bar code
            progress_var.set(progress)  # Update the progress bar
            print(f"Loaded {len(rows)} words from MySQL (Batch). Progress: {progress:.2f}%")  # len is used to determine the number of rows fetched from the database.

    print(f"Loaded a total of {len(words)} words from MySQL.")
    save_words_to_cache(words)  # Save the words to the cache file
    return words

def load_words_from_cache():
    # Load words from the cache file if it exists
    if os.path.exists(CACHE_FILE):
        print("Cache file found, loading words from cache...")
        with open(CACHE_FILE, 'r') as file:
            words_list = json.load(file)
            words_set = set(words_list)
            print(f"Loaded {len(words_set)} words from cache.")
            return words_set
    else:
        print("Cache file not found.")
        return set()

def save_words_to_cache(words):
    # Save words to the cache file
    print("Saving words to cache...")
    with open(CACHE_FILE, 'w') as file:
        json.dump(list(words), file)
    print(f"Saved {len(words)} words to cache.")

def load_words(progress_var):
    # Load words from cache and MySQL
    words = load_words_from_cache()  # Load words from cache
    threading.Thread(target=load_words_from_mysql, args=(progress_var, words)).start()  # Load words from MySQL in a separate thread
    return words

# Set of words loaded from cache and MySQL
words = set()
words_loaded_event = threading.Event()  # Event to signal when words are loaded

def open_file(text_edit):
    # Open a file and display its content in the text editor
    filepath = askopenfilename(filetypes=[("All Files", "*.*")])

    if not filepath:
        return

    text_edit.delete(1.0, tk.END)
    with open(filepath, "r") as f:
        content = f.read()
        text_edit.insert(tk.END, content)
    text_edit.master.title(f"Open File: {filepath}")

def save_file(text_edit):
    # Save the content of the text editor to a file
    filepath = asksaveasfilename(filetypes=[("All Files", "*.*")])

    if not filepath:
        return
    
    with open(filepath, "w") as f:
        content = text_edit.get(1.0, tk.END)
        f.write(content)
        text_edit.master.title(f"Save File: {filepath}")

class Illumicheck:
    def __init__(self):
        self.root = tk.Tk()  # Create the main application window
        self.root.title("Illumicheck")  # Set the title of the window
        
        menubar = tk.Menu(self.root)  # Create a menu bar
        self.root.config(menu=menubar)  # Configure the root window to use this menu

        # Create a "File" menu and add "Open" and "Save" commands
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=lambda: open_file(self.text))
        file_menu.add_command(label="Save", command=lambda: save_file(self.text))

        self.root.rowconfigure(0, weight=1)  # Configure row 0 to expand
        self.root.columnconfigure(0, weight=1)  # Configure column 0 to expand
        self.root.columnconfigure(1, weight=0)  # Configure column 1 to not expand

        # Bind keyboard shortcuts for saving and opening files
        self.root.bind("<Control-s>", lambda x: save_file(self.text))
        self.root.bind("<Control-o>", lambda x: open_file(self.text))
        self.root.bind("<Command-s>", lambda x: save_file(self.text))
        self.root.bind("<Command-o>", lambda x: open_file(self.text))

        # Create a ScrolledText widget for text editing
        self.text = ScrolledText(self.root, font=("Helvetica 14"))
        self.text.grid(row=0, column=0, sticky="nsew")

        # Create a progress bar for indicating the loading progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # Bind the key release event to check words as they are typed
        self.text.bind("<KeyRelease>", self.check_word)
        self.old_spaces = 0
        self.incorrect_words = set()

        # Start loading words in a background thread
        threading.Thread(target=self.load_words_in_background).start()
        
        self.root.mainloop()  # Start the Tkinter event loop

    def load_words_in_background(self):
        # Load words in a background thread
        global words
        words = load_words(self.progress_var)  # Load words from cache and start loading MySQL words
        words_loaded_event.set()  # Signal that initial words (from cache) have been loaded

    def check_word(self, event):
        # Check for incorrect words in the text editor
        if not words_loaded_event.is_set():
            return

        word_pattern = re.compile(r'\b\w+\b')  # Regular expression pattern for matching words
        content = self.text.get("1.0", tk.END)  # Get the content of the text editor
        words_in_content = word_pattern.findall(content)  # Find all words in the content
        new_incorrect_words = set()

        for word in words_in_content:
            clean_word = re.sub(r"[^\w]", "", word.lower())  # Clean the word
            if clean_word and clean_word not in words:
                new_incorrect_words.add(clean_word)  # Add incorrect words to the set

        self.incorrect_words = new_incorrect_words
        
        for tag in self.text.tag_names():
            self.text.tag_delete(tag)  # Remove all existing tags

        for word in self.incorrect_words:
            start_idx = content.find(word)
            while start_idx != -1:
                end_idx = start_idx + len(word)
                self.text.tag_add(word, f"1.0+{start_idx}c", f"1.0+{end_idx}c")  # Add a tag for each incorrect word
                self.text.tag_config(word, foreground="red")  # Set the tag color to red
                start_idx = content.find(word, end_idx)

if __name__ == "__main__":
    Illumicheck()  # Start the Illumicheck application
