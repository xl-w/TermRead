#!/usr/bin/env python3
import re, os, tty, sys, termios, json, math

# ANSI escape codes.
HIDE = '\x1b[?25l'
SHOW = '\x1b[?25h'
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
        'q': 'Quit',
        'M': 'Mark',
        'I': 'Image'
        }

# Print with proper formatting.
def format_print(text, length=16, separator='\t\t'):
    ls = text.split(separator)
    template = '{:<%s}      ' % str(length) * len(ls)
    print(template.format(*ls))

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
    book = {'pages': [], 'images': [], 'subsections': []}
    raw = epub.read_epub(ebook)
    for item in raw.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = bs4.BeautifulSoup(item.get_content(), 'lxml')
        # Chapter title.
        title = ''
        headers = soup.find_all(re.compile('h\d+'))
        if headers != []:
            title = headers[0].text
            # Handle <br/>.
            for br in soup.select('br'):
                br.replace_with('\n')
            # Colorized chapter text. 
            content = soup.text.replace(title, MAGENTA+title+ENDC+GREEN, 1)
            book['pages'].append({re.sub('\s+', '\t\t', title): content+ENDC})
            if len(headers) > 1:
                for idx in range(1, len(headers)):
                    # A list of subsection titles.
                    book['subsections'].append(headers[idx].text)
        if soup.img:
            ls = soup.find_all('img')
            for image in ls:
                name = ''
                # Images in HTML.
                if image.findNextSibling():
                    sibling = image.findNextSibling()
                    if sibling.name == 'p' and sibling.parent == image.parent:
                        name = sibling.text
                href = image['src'].replace('../', '')
                # Images in ebook.
                img = raw.get_item_with_href(href)
                content = img.content
                if name == '':
                    if title == '':
                        name = img.get_name().replace('images/', '')
                    else:
                        name = img.get_name().replace('images/', title.replace('\n', ' ')+'-')
                else:
                    name = re.sub('.+\.', name+'.', img.get_name())
            book['images'].append({name: content.decode('latin1')})
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
        if os.path.exists(Reader.home+'/.TermRead/'+self.title+'/info.json'):
            with open(Reader.home+'/.TermRead/'+self.title+'/info.json') as f:
                info = json.load(f)
                self.pages = info['pages']
                self.markList = info['markList']
                self.currentPage = info['currentPage']
        else:
            pageText = ''
            pageLines = 0
            pages = {'Chapters': [], 'Pages': []}
            # Divide chapters into pages.
            book = parse(ebook)
            for chapter in book['pages']:
                chapterTitle = list(chapter.keys())[0]
                pages['Chapters'].append({'Title': chapterTitle, 'Page': str(len(pages['Pages']))})
                # Divide the main body into lines.
                lines = chapter[chapterTitle].split('\n')
                for item in lines:
                    if re.match('\[\d+\]$', item):
                        idx = lines.index(item)
                        lines[idx-1] += item + lines[idx+1]
                        lines[idx+1] = ''
                        lines[idx] = ''
                for line in lines:
                    # Empty string.
                    if not line:
                        continue
                    for subsection in book['subsections']:
                        if subsection == line:
                            pages['Chapters'].append({'Title': '\u21B3\t\t'+re.sub('\s+', '\t\t', subsection), 'Page': str(len(pages['Pages']))})
                            book['subsections'].remove(subsection)
                            break
                    length = math.ceil(textlen(line)/Reader.columns)
                    if pageLines + length > Reader.rows - 4:
                        pages['Pages'].append(pageText)
                        pageText = ''
                        pageLines = 0
                    pageText += line + '\n'
                    pageLines += length
            self.pages = pages
            # Initial settings for marks and the current page number.
            self.markList = []
            self.currentPage = 0
            # Create the folder.
            if not os.path.exists(Reader.home+'/.TermRead/'+self.title):
                os.mkdir(Reader.home+'/.TermRead/'+self.title)
            # Save the json file of images for the first time.
            with open(Reader.home+'/.TermRead/'+self.title + '/img.json', 'w') as f:
                json.dump({'images': book['images']}, f, indent=4, ensure_ascii=False)

    # Display the current page.
    def page(self):
        if 0 <= self.currentPage < len(self.pages['Pages']):
            content = self.pages['Pages'][self.currentPage]
            print(GREEN+content+ENDC)
        else:
            print(RED+'The page number is out of range.'+ENDC)

    # Save the reading progress as a json file.
    def save(self):
        info = {'pages': self.pages, 'markList': self.markList,  'currentPage': self.currentPage} 
        folder = Reader.home + '/.TermRead/' + self.title
        with open(folder + '/info.json', 'w') as f:
            json.dump(info, f, indent=4, ensure_ascii=False)
        os.system('clear')
        print(RED+'\nSaved!'+ENDC)

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
        appendText = RED+'Page range: '+ENDC+'\t\t'+CYAN+'0-'+str(len(self.pages['Pages'])-1)+ENDC
        appendText += RED+'\nCurrent page: '+ENDC+'\t\t'+CYAN+str(self.currentPage)+ENDC
        os.system('clear')
        for idx in range(min(Reader.rows-4,len(catalog))):
            format_print(catalog[idx])
        print(appendText)
        # Starting page number.
        start = 0
        tty.setcbreak(sys.stdin)
        while True:
            keypress = sys.stdin.read(1)[0]
            if keypress == 'q':
                break
            elif keypress in ['j', 'k']:
                if keypress == 'j':
                    if start < math.ceil(len(catalog)/(Reader.rows-4)) - 1:
                        start += 1
                else: 
                    if start > 0:
                        start -= 1
                os.system('clear')
                for idx in range(start*(Reader.rows-4), min((start+1)*(Reader.rows-4),len(catalog))):
                    format_print(catalog[idx])
                print(appendText)
            else:
                print(RED+'Press q to quit. Press j to move page down and k to move page up.'+ENDC)

    # Display the usage message.
    def help(self):
        os.system('clear')
        print(RED+'If you want to reparse the ebook, delete that folder under ~/.TermRead. \nShortcut keys:'+ENDC)
        for key in shortcuts.keys():
            print(RED+key+ENDC+'\t\t'+CYAN+shortcuts[key]+ENDC)
        tty.setcbreak(sys.stdin)
        while True:
            keypress = sys.stdin.read(1)[0]
            if keypress == 'q':
                break
            print(RED+'Press q to quit.'+ENDC)

    # Navigate between pages.
    def goto(self):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, Reader.originalSettings)
        while True:
            inp = input(RED+'Page number, or enter q to quit: '+ENDC)
            if inp == 'q':
                tty.setcbreak(sys.stdin)
                break
            elif inp == '0' or re.match('[1-9][0-9]*$', inp):
                num = eval(re.findall('\d+', inp)[0])
                if 0 <= num < len(self.pages['Pages']):
                    self.currentPage = num
                    tty.setcbreak(sys.stdin)
                    break

    # Download images from the ebook.
    def images(self):
        os.system('clear')
        if os.path.exists('img'):
            if os.path.exists('img/'+self.title):
                print(RED+'Already exists! \nPlease check ./img/'+self.title+'. \nRedirect in 4s.'+ENDC)
                os.system('sleep 3')
                return
        else:
            os.mkdir('img')
        with open(Reader.home+'/.TermRead/'+self.title + '/img.json', 'r') as f:
            img = json.load(f)
        os.mkdir('img/'+self.title)
        print(RED+'Start downloading images from the book.'+ENDC)
        for image in img['images']:
            name = list(image.keys())[0]
            content = image[name].encode('latin1')
            with open('img/'+self.title+'/'+name, 'wb') as f:
                f.write(content)
        if img['images'] == []:
            print(RED+'Finished! \nNo image found.'+ENDC)
        else:
            print(RED+'Finished! \nPlease check ./img/'+self.title+'. \nRedirect in 3s.'+ENDC)
        os.system('sleep 3')

    # Set a mark.
    def marks(self):
        tty.setcbreak(sys.stdin)
        while True:
            os.system('clear')
            print(RED+'Press q to quit, press 0 - 9 to navigate. \nPress a to add a mark at the current page. \nPress d to delete, D to delete all. \nYou can add up 10 marks. \nIndex\t\tPage\t\tText'+ENDC)
            for mark in self.markList:
                print(RED+str(self.markList.index(mark))+'\t\t'+str(mark['Page'])+'\t\t'+mark['Text']+ENDC)
            keypress = sys.stdin.read(1)[0]
            if keypress == 'q':
                break
            elif keypress in ['a', 'd', 'D']:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, Reader.originalSettings)
                if keypress == 'a':
                    if len(self.markList) >= 10:
                        self.markList.pop(0)
                    inp = input(RED+'Add some text here: '+ENDC)
                    self.markList.append({'Page': self.currentPage, 'Text': inp})
                elif keypress == 'd':
                    inp = input(RED+'Delete: '+ENDC)
                    if inp.isdigit():
                        if eval(inp) in range(len(self.markList)):
                            self.markList.pop(eval(inp))
                else:
                    inp = input(RED+'Delete all? Enter y to confirm: '+ENDC)
                    if inp == 'y':
                        self.markList = []
                tty.setcbreak(sys.stdin)
            elif keypress.isdigit():
                if eval(keypress) in range(len(self.markList)):
                    self.currentPage = self.markList[eval(keypress)]['Page']
                    break

    def read(self):
        print(CYAN+'Welcome to TermRead! \nPress any key to continue except shortcut keys: '+ENDC)
        for key in shortcuts.keys():
            print(RED+key+ENDC+'\t\t'+CYAN+shortcuts[key]+ENDC)
        tty.setcbreak(sys.stdin)
        # Hide cursor.
        print(HIDE)
        # Keypress 'q' to quit.
        while self.keypress != chr(113):
            self.keypress = sys.stdin.read(1)[0]
            if self.keypress == 'j':
                self.pagedown()
            elif self.keypress == 'k':
                self.pageup()
            elif self.keypress == 'c':
                self.chapters()
            elif self.keypress == 'h':
                self.help()
            elif self.keypress == 'g':
                self.goto()
            elif self.keypress == 'M':
                self.marks()
            elif self.keypress == 'I':
                self.images()
            os.system('clear')
            self.page()
        self.save()
        # Show cursor.
        print(SHOW)
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
