import os
import csv
from collections import deque


class Tja:
    def __init__(self, path, encoding="utf-8"):
        if isTja(path):
            self.path = path
            self.header = {}
            self.course = []
            with open(path, "r", encoding=encoding) as f:
                for line in f:
                    # REMOVE BOM AND LININGS
                    line = (
                        line.replace(chr(0xFEFF), "")
                        .replace("\r", "")
                        .replace("\n", "")
                    )
                    # REMOVE COMMENTS
                    if "//" in line:
                        line = line[: line.index("//")]
                    if len(line) == 0:
                        continue
                    if isHeader(line):
                        if getHeaderName(line) == "COURSE":
                            self.course.append(Course(getHeaderValue(line)))
                        else:
                            # COURSE HEADERS
                            if len(self.course) > 0:
                                if len(self.course[-1].measures[-1]) > 0:
                                    if self.course[-1].measures[-1][0] == "#END":
                                        # FOR DOUBLE CHARTS
                                        if isCommand(line):
                                            if getCommandName(line) == "START":
                                                # W/OUT ANY HEADERS
                                                self.course.append(
                                                    Course(
                                                        self.course[-1].header["COURSE"]
                                                    )
                                                )
                                                self.course[-1].header[
                                                    "LEVEL"
                                                ] = self.course[-2].header["LEVEL"]
                                        elif isHeader(line):
                                            self.course.append(
                                                Course(self.course[-1].header["COURSE"])
                                            )
                                            self.course[-1].header[
                                                "LEVEL"
                                            ] = self.course[-2].header["LEVEL"]
                                self.course[-1].addHeader(
                                    getHeaderName(line), getHeaderValue(line)
                                )
                            else:
                                if isCommand(line):
                                    # START W/OUT COURSE HEADER
                                    if getCommandName(line) == "START":
                                        self.course.append(Course())
                                else:
                                    # COMMON HEADERS
                                    self.header[getHeaderName(line)] = getHeaderValue(
                                        line
                                    )  # .replace(',', '$')
                    elif len(self.course) > 0:
                        self.course[-1].appendNotes(line)

    def isAudioExist(self):
        files = listFiles(getAddr(self.path))
        return (getAddr(self.path) + "\\" + self.header["WAVE"]) in files
    
    def withLyricsCommand(self):
        course = self.course[0]
        for measure in course.measures:
            for line in measure:
                if isCommand(line):
                    if getCommandName(line) == "LYRIC" and len(getCommandParameters(line)) > 0:
                        return True
        return False

    def lyricsToVtt(self):
        time = -float(self.header["OFFSET"])
        bpm = float(self.header["BPM"])
        measureRatio = 1.0
        vttText = "WEBVTT"
        course = self.course[0]
        lastLyricTime = 0.0
        lastLyricText = ""
        for measure in course.measures:
            measureNotes = getMeasureNotesCount(measure)
            for line in measure:
                if isNotes(line):
                    if measureNotes != 0:
                        time += (
                            240
                            * measureRatio
                            * getNotesCount(line)
                            / bpm
                            / measureNotes
                        )
                    else:
                        time += 240 * measureRatio / bpm
                elif isCommand(line):
                    if getCommandName(line) == "MEASURE":
                        value = getCommandParameters(line)
                        measureRatio = int(value[: value.index("/")]) / int(
                            value[value.index("/") + 1 :]
                        )
                    if getCommandName(line) == "BPMCHANGE":
                        bpm = float(getCommandParameters(line))
                    if getCommandName(line) == "LYRIC":
                        if len(lastLyricText) != 0:
                            vttText = (
                                vttText
                                + "\n\n"
                                + toTime(lastLyricTime)
                                + " --> "
                                + toTime(time)
                                + "\n"
                                + lastLyricText
                            )
                        lastLyricTime = time
                        lastLyricText = getCommandParameters(line)
                    if getCommandName(line) == "END":
                        if len(lastLyricText) != 0:
                            vttText = (
                                vttText
                                + "\n\n"
                                + toTime(lastLyricTime)
                                + " --> "
                                + toTime(time)
                                + "\n"
                                + lastLyricText
                            )

        return vttText


class Course:
    def __init__(self, course="Oni"):
        self.header = {"COURSE": course}
        self.measures = [[]]

    def addHeader(self, name, value):
        self.header[name] = value

    def appendNotes(self, notes):
        self.measures[-1].append(notes)
        if "," in notes:
            if not isCommand(notes):
                self.measures.append([])

    def printMeasures(self):
        measureNo = 0
        for measure in self.measures:
            measureNo += 1
            print(str(measureNo) + "\t" + str(measure))


def toTime(f):
    f += 0.0005
    min = int(100 + f // 60)
    sec = int(100 + f % 60 // 1)
    milliSec = int(1000 + f % 1 // 0.001)
    return (
        str(min)[1:] + ":" + str(sec)[1:] + "." + str(milliSec)[1:]
    )


def getAddr(path):
    return os.path.dirname(path)


def getFName(path):
    return os.path.splitext(os.path.basename(path))[0]


def getFExt(path):
    return os.path.splitext(os.path.basename(path))[1][1:]


def isTja(path):
    return getFExt(path) == "tja"


def isHeader(line):
    return ":" in line


def getHeaderName(line):
    return line[: line.index(":")]


def getHeaderValue(line):
    return line[line.index(":") + 1 :]


def isCommand(line):
    return line[0] == "#"


def getCommandName(line):
    if " " in line:
        return line[1 : line.index(" ")]
    else:
        return line[1:]


def getCommandParameters(line):
    if " " in line:
        return line[line.index(" ") + 1 :]
    else:
        return ""


def isNotes(line):
    for ch in line:
        if ch not in " 0123456789ABCFG,":
            return False
    return True


def getNotesCount(line):
    count = 0
    for ch in line:
        if ch in "0123456789ABCFG":
            count += 1
    return count


def getMeasureNotesCount(measure):
    count = 0
    for line in measure:
        if isNotes(line):
            count += getNotesCount(line)
    return count


def listFiles(path):
    fs = []
    for entry in os.scandir(path):
        if entry.is_dir():
            folders = deque([str(entry.path)])
            while len(folders) != 0:
                for entry2 in os.scandir(folders.popleft()):
                    if entry2.is_dir():
                        folders.append(entry2.path)
                    elif entry2.is_file():
                        fs.append(entry2.path)
        elif entry.is_file():
            fs.append(entry.path)
    return fs


for f in listFiles("."):
    if isTja(f):
        tja = Tja(f)
        print("Analyzing " + getFName(f) + "...", end = "\r")
        if tja.withLyricsCommand():
            print("Writing " + getFName(f) + "...")
            vtt = open(f[:-3] + "vtt", "w")
            vtt.write(tja.lyricsToVtt())
            vtt.close()