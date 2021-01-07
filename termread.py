#!/usr/bin/env python3
import re, os, tty, sys, termios, json, math 

# ANSI escape codes.
ENDC = '\033[0m'
RED = '\033[1;31m'
CYAN = '\033[1;36m'
GREEN = '\033[1;32m'
MAGENTA = '\033[1;35m'

# Supported keyboard shortcuts.
shortcuts = {
        'j': 'Pagedown',
        'k': 'Pageup',
        'c': 'Cagalog',
        'g': 'Goto',
        'h': 'Help',
        'q': 'Quit'
        }

# Detect the length of the given text.
def textlen(text):
    length = 0
    for character in text:
        # Detect Japanese and Chinese characters.
        if u'\u0800' <= character <= u'\u9fa5':
            length += 2
        else:
            length += 1
    return length

# Parse ebooks. 
def parse(ebook):
    book = []
    raw = epub.read_epub(ebook)
    for item in raw.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = bs4.BeautifulSoup(item.get_content(), 'lxml')
            if soup.find('h2'):
                # Chapter title.
                title = soup.h2.text
                # Colorized chapter text. 
                content = soup.text.replace(title, MAGENTA+title+ENDC+GREEN)
                book.append({title: content+ENDC})
    return book

class Reader():
    home = os.path.expanduser('~')
    originalSettings = termios.tcgetattr(sys.stdin)
    rows, columns = [eval(item) for item in os.popen('stty size', 'r').read().split()]
    if not os.path.exists(home+'/.TermRead'):
        os.mkdir(home+'/.TermRead')

    def __init__(self, ebook):
        # Null character.
        self.keypress = 0 
        self.title = re.findall('(.+)\.(?:epub)', ebook)[0]
        if os.path.exists(Reader.home+'/.TermRead/'+self.title):
            with open(Reader.home+'/.TermRead/'+self.title+'/info.json') as f:
                info = json.load(f)
                self.pages = info['pages']
                self.currentPage = info['currentPage']
        else:
            pageText = ''
            pageLines = 0
            pages = {'Chapters':[], 'Pages':[]}
            # Divide chapters into pages.
            book = parse(ebook)
            for chapter in book:
                chapterTitle = list(chapter.keys())[0]
                pages['Chapters'].append({'Title': chapterTitle, 'Page': str(len(pages['Pages']))})
                lines = [item for item in chapter[chapterTitle].split('\n') if item != '']
                for line in lines:
                    length = math.ceil(textlen(line)/Reader.columns)
                    if pageLines + length > Reader.rows - 4:
                        pages['Pages'].append(pageText)
                        pageText = ''
                        pageLines = 0
                    pageText += line + '\n'
                    pageLines += length
            self.pages = pages
            self.currentPage = 0

    # Display the current page.
    def page(self):
        if 0 <= self.currentPage < len(self.pages['Pages']):
            content = self.pages['Pages'][self.currentPage]
            print(GREEN+content+ENDC)
        else:
            print(RED+'The page number is out of range.'+ENDC)

    # Save the reading progress as a json file.
    def save(self):
        info = {'pages': self.pages, 'currentPage': self.currentPage} 
        folder = Reader.home + '/.TermRead/' + self.title
        if not os.path.exists(folder):
            os.mkdir(folder)
        with open(folder + '/info.json', 'w') as f:
            json.dump(info, f, indent=4, ensure_ascii=False)
        os.system('clear')
        print(RED+'Saved!'+ENDC)

    def pagedown(self):
        if self.currentPage < len(self.pages['Pages']) - 1:
            self.currentPage += 1

    def pageup(self):
        if self.currentPage > 0:
            self.currentPage -= 1

    # Display the catalog.
    def chapters(self):
        catalog =  [RED+'Page'+ENDC+'\t\t'+CYAN+'Title'+ENDC]
        for chapter in self.pages['Chapters']:
            # Page number.
            page = chapter['Page']
            # Chapter title.
            title = chapter['Title']
            catalog.append(RED+page+ENDC+'\t\t'+CYAN+title+ENDC)
        catalog.append(RED+'Page range: '+ENDC+'\t'+CYAN+'0-'+str(len(self.pages['Pages'])-1)+ENDC)
        catalog.append(RED+'Current page: '+ENDC+'\t'+CYAN+str(self.currentPage)+ENDC)
        os.system('clear')
        for idx in range(Reader.rows-4):
            print(catalog[idx])
        # Starting page number.
        start = 0
        while True:
            inp = input(RED+'Enter q to quit, n and p stand for the next and previous page respectively: '+ENDC)
            if inp == 'q':
                break
            elif inp in ['n', 'p']:
                if inp == 'n':
                    if start < math.ceil(len(catalog)/(Reader.rows-4)) - 1:
                        start += 1
                else: 
                    if start > 0:
                        start -= 1
                os.system('clear')
                for idx in range(start*(Reader.rows-4), min((start+1)*(Reader.rows-4),len(catalog))):
                    print(catalog[idx])

    # Display the usage message.
    def help(self):
        os.system('clear')
        print(RED+'If you want to reparse the ebook, delete that folder under ~/.TermRead. \nShortcut keys:'+ENDC)
        for key in shortcuts.keys():
            print(RED+key+ENDC+'\t\t'+CYAN+shortcuts[key]+ENDC)
        while True:
            inp = input(RED+'Enter q to quit: '+ENDC)
            if inp == 'q':
                break

    # Navigate between pages.
    def goto(self):
        while True:
            inp = input(RED+'Page number: '+ENDC)
            if re.match('[1-9][0-9]*$', inp):
                num = eval(re.findall('\d+', inp)[0])
                if 0 <= num < len(self.pages['Pages']):
                    self.currentPage = num
                    break

    def read(self):
        print(CYAN+'Welcome to TermRead! \nPress any key to continue except shortcut keys: '+ENDC)
        for key in shortcuts.keys():
            print(RED+key+ENDC+'\t\t'+CYAN+shortcuts[key]+ENDC)
        tty.setcbreak(sys.stdin)
        # Keypress 'q' to quit.
        while self.keypress != chr(113):
            self.keypress = sys.stdin.read(1)[0]
            if self.keypress == 'j':
                self.pagedown()
            elif self.keypress == 'k':
                self.pageup()
            elif self.keypress in ['h', 'g', 'c']:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, Reader.originalSettings)
                if self.keypress == 'h':
                    self.help()
                elif self.keypress == 'g':
                    self.goto()
                else:
                    self.chapters()
                tty.setcbreak(sys.stdin)
            os.system('clear')
            self.page()
        self.save()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, Reader.originalSettings)

def main():
    try:
        global bs4, ebooklib, epub
        import bs4, ebooklib
        from ebooklib import epub
        if len(sys.argv) > 1:
            if os.path.exists(sys.argv[1]):
                Reader(sys.argv[1]).read()
            else:
                print('Check your file path again!')
        else:
            print('An ebook is needed!')
    except ImportError:
        print('Please install bs4 and ebooklib first!')

if __name__ == '__main__':
    main()
