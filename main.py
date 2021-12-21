import re
import os
import codecs
import tkinter as tk
from tkinter import filedialog, messagebox

def setModifier(type, line, classname):
    defaultType = str()
    if type == "struct":
        defaultType = '+'
    else:
        defaultType = '-'

    RE = r'(private protected|protected internal|public|private|protected|internal)'
    match = re.findall(RE, line)
    if len(match) == 0:
        if(isConstructor(line,classname)):
            line = '+ ' + line
        else:
            line = defaultType + ' ' + line
    else:
        newModifier = str()
        if(match[0] == 'public'):
            newModifier = '+'
        else:
            newModifier = '-'
        line = line.replace(match[0], newModifier,1)
    return line

def removeAttributes(text):
    attributeRE = r'^(?<!\S)\[.*\](?!\S)'
    founds = re.findall(attributeRE, text, re.MULTILINE)
    for found in founds:
        text = text.replace(found,'',1)
    return text

def removeComments(text):
    oneLineCommentRE = r'//+.*'
    multilineComment = r'/\*.*?\*/'
    macro = r'#.*'

    text = re.sub(oneLineCommentRE, '', text)
    text = re.sub(macro, '', text)
    founds = re.findall(multilineComment, text, re.DOTALL)
    for found in founds:
        text = text.replace(found, '', 1)
    return text


def removeEqual(line):
    lineIter = 0
    isBrace = False
    for sym in line:
        if sym == '(':
            isBrace = True
        elif sym == ')':
            isBrace = False

        if not isBrace and sym == '=':
            line =  line[0:lineIter]
            break
        lineIter += 1
    return line.strip()

def isTheNestedType(line):
    if len(re.findall(r'((?<!\S)(class|struct|enum|interface)(?!\S))',line)) == 0:
        return False
    return True

def isConstructor(line, classname):
    start = r'(?<!\S)'
    end = r'(?!\S)'
    RE = r'{}{}{}'.format(start,classname,end)
    line = line.split('(')[0].strip()
    founds = re.findall(RE,line, re.MULTILINE)
    if len(founds) == 0:
        return False
    return True

def isOperatorOverloading(line):
    RE = r'(?<!\S)operator(?!\S)'
    if len(re.findall(RE, line, re.MULTILINE)) == 0:
        return False
    return True

def getClassName(name):
    return name.split('<')[0].split(':')[0].strip()

def removeParametersNamesProcedure(line):
    word = '('
    parameters = line[1:len(line) - 1].split(',')
    for parIndex, parameter in enumerate(parameters):
        if parameter:
            parameters[parIndex] = parameter.strip()
            parts = parameters[parIndex].split()
            withAdditionalWord = len(re.findall(r'((?<!\S)(ref|in|out)(?!\S))', parts[0])) != 0

            if (parIndex != 0):
                word += ', '

            if (withAdditionalWord):
                word += parts[0] + ' ' + parts[1]
            else:
                word += parts[0]

    word += ')'
    return word

def removeParametersNames(words):
    for index,word in enumerate(words):
        words[index] = word.strip()
        if words[index][0] == '(' and words[index][len(words[index])-1] == ')':
            words[index] = removeParametersNamesProcedure(words[index])
            break
    return words

def removeConstructorParametersNames(constructor):
    firstBracketIndex = constructor.find('(')
    parametersPart = constructor[firstBracketIndex:constructor.find(')')]
    constructor = constructor[:firstBracketIndex].rstrip()
    constructor += ' ' + removeParametersNamesProcedure(parametersPart)
    return constructor

def organize(classname,text,type):

    lines = text.split('\n')

    nestedTypes = str()

    methods = str()
    fields = str()


    if type != 'enum':
        for line in lines:

            if line == '':
                continue

            if isOperatorOverloading(line):
                continue

            line = setModifier(type, line, classname)

            if isTheNestedType(line):
                nestedTypes += line.strip() + '\n'
                continue
            if isConstructor(line, classname):
                line = removeConstructorParametersNames(line)
                methods = line.strip() + '\n' + methods
                continue

            line = removeEqual(line)

            if line[len(line)-1] == ')':
                index = line.find('(')
                if (index != -1 and line[index-1]!=' '):
                    line = line[:index] + ' ' + line[index:]

            words = []

            bi = 0
            ei = 0
            isBrace = False
            isAngleBrackets = False
            line.strip()

            for sym in line:
                if sym.isspace() and not isAngleBrackets and not isBrace:
                    words.append(line[bi:ei])
                    bi = ei
                else:
                    if sym == '<':
                        isAngleBrackets = True
                    elif sym == '>':
                        isAngleBrackets = False
                    else:
                        if not isAngleBrackets:
                            if sym == '(':
                                isBrace = True
                            elif sym == ')':
                                isBrace = False


                ei+=1
            words.append(line[bi:ei])
            words = removeParametersNames(words)

            # ///////////////////////////////////
            isMethod = True

            if words[len(words) - 1].find('(') == -1:
                isMethod = False

            words.append(':')
            wordsCount = len(words)

            if isMethod:
                words[wordsCount - 1], words[wordsCount - 2] = words[wordsCount - 2], words[wordsCount - 1]
                words[wordsCount - 1], words[wordsCount - 4] = words[wordsCount - 4], words[wordsCount - 1]
                words[wordsCount - 3], words[wordsCount - 4] = words[wordsCount - 4], words[wordsCount - 3]

            else:
                words[wordsCount - 1], words[wordsCount - 2] = words[wordsCount - 2], words[wordsCount - 1]
                words[wordsCount - 1], words[wordsCount - 3] = words[wordsCount - 3], words[wordsCount - 1]

            # /////////////////////////////////////////////////////

            line = str()
            for word in words:
                if word != 'static':
                    line += word + ' '
            if isMethod:
                methods += line.strip() + '\n'
            else:
                fields += line.strip() + '\n'
    else:
        lines = text.split(',')
        for line in lines:
            line = removeEqual(line)
            fields += line.strip() + '\n'

    return fields.strip(), methods.strip(), nestedTypes.strip()

def getNested(text, type, name):
    className = getClassName(name)
    insideText = getInside(text, type, name)
    return organize(className, insideText, type)

def deleteBlocks(text):

    ob = 0
    cb = 0
    text_iter = -1
    start_pos = -1

    replaces = []

    for symbol in text:
        if symbol == '{':
            if start_pos == -1:
                start_pos = text_iter
            ob+=1
        elif symbol == '}':
            cb+=1

        if ob != 0 and cb != 0 and ob == cb:
            replace = text[start_pos+1:text_iter+1]
            replaces.append(replace)
            ob = 0
            cb = 0
            start_pos = -1
        text_iter+=1
    for replace in replaces:
        text = text.replace(replace, '' ,1)
    pattern = r'\s*(\}|;)\s*'
    text = re.sub(pattern, '\n', text).strip()
    text = removeAttributes(text)
    return text

def getBlock(text):
    ob = 0
    cb = 0
    text_iter = 0
    start_pos = -1
    for symbol in text:
        if symbol == '{':
            if start_pos == -1:
                start_pos = text_iter
            ob+=1
        elif symbol == '}':
            cb+=1

        if ob != 0 and cb != 0 and ob == cb:
            return text[start_pos + 1:text_iter]
        text_iter+=1

def getInside (text, type, name):
    text = text.replace("\n", " ")
    signature =  f"{type} {name}"
    braces = r'\s*\{.*\}'
    RE = r'{}{}'.format(signature,braces)
    return deleteBlocks(getBlock(re.findall(RE, text)[0]))

def getValidText(text):

    text = removeComments(text)
    text = text.replace("\n", " ")
    text = ' '.join(text.split())

    return text


def getStruct(text):
    fileText = str()
    text = getValidText(text)
    mainRE = r'((class|struct|enum|interface)\s(\w[^{]*)\{)'

    ces = re.findall(mainRE, text, re.DOTALL)
    cesAndBlock = [] #ces - classes, enums, structs

    for value in ces:
        type = value[1]
        fullname = value[2]
        fields, methods, nestedTypes = getNested(text, type, fullname)
        cesAndBlock.append((type,fullname, fields, methods, nestedTypes))

    for value in cesAndBlock:

        if value[2] or value[3]:
            fileText += f"____________________________________________________________" \
                        f"\n\n{value[0]} {value[1]}"
            if value[2]:
                if value[0] == 'enum':
                    fileText += f'\n\n# Values: \n{value[2]}'
                else:
                    fileText += f'\n\n# Fields: \n{value[2]}'
            if value[0] != 'enum' and value[3]:
                fileText += f'\n\n# Methods: \n{value[3]}'

            if value[0] != 'enum' and value[4]:
                fileText += f'\n\n# Nested types: \n{value[4]}\n'
            fileText += '\n'

    return fileText


def getFileText(filePath):
    with codecs.open(filePath, 'r', "utf_8_sig") as file:
        return file.read()

def goToFolder(folderPath):
    fileText = str()
    for root, dirs, files in os.walk(folderPath):
        for file in files:
            filePath = os.path.join(root, file)
            filename, file_extension = os.path.splitext(filePath)
            fileNameParts = filename.split('\\')
            name = fileNameParts[len(fileNameParts) - 1] + file_extension
            if file_extension == '.cs' \
                    and not ("g.i.cs" in name) \
                    and not ("g.cs" in name) \
                    and not (".Designer.cs" in name):
                text = getStruct(getFileText(filePath))
                if text != '':
                    fileText += "\t\t\tFILE " +  name + '\n'
                    fileText += text
                    fileText += "____________________________________________________________\n\n"

    with open(folderPath + '/classDiagram.txt','w') as file:
        file.write(fileText)
        return file.name



def main():
    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory()

    if folder != '':
        filePath = goToFolder(folder)
        messagebox.showinfo("File saved", "Class diagram was saved " + filePath)

    # path = "C:\\Users\\userZ\\Desktop\\New.cs"
    # # folder = "C:\\ProgrammingLearning\\GVSS\\gvss_project"
    # print(getStruct(getFileText(path)))

    #!НЕ УБИРАЕТ СТАТИЧЕСКИЙ КОНСТРУКТОР (НАЗВАНИЕ)


if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
