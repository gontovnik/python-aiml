'''
This class implements the AIML pattern-matching algorithm described
by Dr. Richard Wallace at the following site:
http://www.alicebot.org/documentation/matching.html
'''

from __future__ import print_function

from collections import namedtuple

import marshal
import pprint
import re
import string
import sys

from .constants import *

MatchResult = namedtuple('MatchResult', 'pattern template')

class PatternMgr:
    # special dictionary keys
    _UNDERSCORE = '0'
    _STAR       = '1'
    _TEMPLATE   = '2'
    _THAT       = '3'
    _TOPIC      = '4'
    _BOT_NAME   = '5'
    _CARET      = '6'
    
    def __init__(self):
        self._root = {}
        self._templateCount = 0
        self._botName = u"Nameless"
        punctuation = r"""`~!@#$%^&*()-_=+[{]}\|;:'",<.>/?"""
        self._puncStripRE = re.compile("[" + re.escape(punctuation) + "]")
        self._whitespaceRE = re.compile(r"\s+", re.UNICODE)

    def numTemplates(self):
        """Return the number of templates currently stored."""
        return self._templateCount

    def setBotName(self, name):
        """Set the name of the bot, used to match <bot name="name"> tags in
        patterns.  The name must be a single word!
        """
        # Collapse a multi-word name into a single word
        self._botName = unicode( ' '.join(name.split()) )

    def dump(self):
        """Print all learned patterns, for debugging purposes."""
        pprint.pprint(self._root)

    def save(self, filename):
        """Dump the current patterns to the file specified by filename.  To
        restore later, use restore().
        """
        try:
            outFile = open(filename, "wb")
            marshal.dump(self._templateCount, outFile)
            marshal.dump(self._botName, outFile)
            marshal.dump(self._root, outFile)
            outFile.close()
        except Exception as e:
            print( "Error saving PatternMgr to file %s:" % filename )
            raise

    def restore(self, filename):
        """Restore a previously save()d collection of patterns."""
        try:
            inFile = open(filename, "rb")
            self._templateCount = marshal.load(inFile)
            self._botName = marshal.load(inFile)
            self._root = marshal.load(inFile)
            inFile.close()
        except Exception as e:
            print( "Error restoring PatternMgr from file %s:" % filename )
            raise

    def add(self, data, template):
        """Add a [pattern/that/topic] tuple and its corresponding template
        to the node tree.
        """
        pattern,that,topic = data
        # TODO: make sure words contains only legal characters
        # (alphanumerics,*,_)

        # Navigate through the node tree to the template's location, adding
        # nodes if necessary.
        node = self._root
        for word in pattern.split():
            key = word
            if key == u"_":
                key = self._UNDERSCORE
            elif key == u"*":
                key = self._STAR
            elif key == u"^":
                key = self._CARET
            elif key == u"BOT_NAME":
                key = self._BOT_NAME
            if key not in node:
                node[key] = {}
            node = node[key]

        # navigate further down, if a non-empty "that" pattern was included
        if len(that) > 0:
            if self._THAT not in node:
                node[self._THAT] = {}
            node = node[self._THAT]
            for word in that.split():
                key = word
                if key == u"_":
                    key = self._UNDERSCORE
                elif key == u"*":
                    key = self._STAR
                if key not in node:
                    node[key] = {}
                node = node[key]

        # navigate yet further down, if a non-empty "topic" string was included
        if len(topic) > 0:
            if self._TOPIC not in node:
                node[self._TOPIC] = {}
            node = node[self._TOPIC]
            for word in topic.split():
                key = word
                if key == u"_":
                    key = self._UNDERSCORE
                elif key == u"*":
                    key = self._STAR
                if key not in node:
                    node[key] = {}
                node = node[key]


        # add the template.
        if self._TEMPLATE not in node:
            self._templateCount += 1    
        node[self._TEMPLATE] = template

    def match(self, pattern, that, topic):
        """Return the template which is the closest match to pattern. The
        'that' parameter contains the bot's previous response. The 'topic'
        parameter contains the current topic of conversation.

        Returns None if no template is found.
        """
        if len(pattern) == 0:
            return None
        # Mutilate the input.  Remove all punctuation and convert the
        # text to all caps.
        input_ = pattern.upper()
        input_ = re.sub(self._puncStripRE, " ", input_)
        if that.strip() == u"": that = u"ULTRABOGUSDUMMYTHAT" # 'that' must never be empty
        thatInput = that.upper()
        thatInput = re.sub(self._puncStripRE, " ", thatInput)
        thatInput = re.sub(self._whitespaceRE, " ", thatInput)
        if topic.strip() == u"": topic = u"ULTRABOGUSDUMMYTOPIC" # 'topic' must never be empty
        topicInput = topic.upper()
        topicInput = re.sub(self._puncStripRE, " ", topicInput)
        
        # Pass the input off to the recursive call
        patMatch, template = self._match(input_.split(), thatInput.split(), topicInput.split(), self._root)
        if template is None or patMatch is None:
            return None
        return MatchResult(patMatch, template)

    def wildcard(self, wildcardType, pattern, that, topic, index):
        """Returns a string, the portion of pattern that was matched by a *.

        The 'wildcardType' parameter specifies which type of wildcard to find.
        Legal values are:
         - 'caret': matches a caret in the main pattern.
         - 'star': matches a star in the main pattern.
         - 'thatstar': matches a star in the that pattern.
         - 'topicstar': matches a star in the topic pattern.
        """
        # Mutilate the input.  Remove all punctuation and convert the
        # text to all caps.
        input_ = pattern.upper()
        input_ = re.sub(self._puncStripRE, " ", input_)
        input_ = re.sub(self._whitespaceRE, " ", input_)
        if that.strip() == u"": that = u"ULTRABOGUSDUMMYTHAT" # 'that' must never be empty
        thatInput = that.upper()
        thatInput = re.sub(self._puncStripRE, " ", thatInput)
        thatInput = re.sub(self._whitespaceRE, " ", thatInput)
        if topic.strip() == u"": topic = u"ULTRABOGUSDUMMYTOPIC" # 'topic' must never be empty
        topicInput = topic.upper()
        topicInput = re.sub(self._puncStripRE, " ", topicInput)
        topicInput = re.sub(self._whitespaceRE, " ", topicInput)

        # Pass the input off to the recursive pattern-matcher
        patMatch, template = self._match(input_.split(), thatInput.split(), topicInput.split(), self._root)
        if template == None:
            return ""

        # Extract the appropriate portion of the pattern, based on the
        # wildcardType argument.
        words = None
        if wildcardType == 'caret':
            patMatch = patMatch[:patMatch.index(self._THAT)]
            words = input_.split()
        elif wildcardType == 'star':
            patMatch = patMatch[:patMatch.index(self._THAT)]
            words = input_.split()
        elif wildcardType == 'thatstar':
            patMatch = patMatch[patMatch.index(self._THAT)+1 : patMatch.index(self._TOPIC)]
            words = thatInput.split()
        elif wildcardType == 'topicstar':
            patMatch = patMatch[patMatch.index(self._TOPIC)+1 :]
            words = topicInput.split()
        else:
            # unknown value
            raise ValueError( "wildcardType must be in ['caret', 'star', 'thatstar', 'topicstar']" )
        
        # compare the input string to the matched pattern, word by word.
        # At the end of this loop, if foundTheRightWildcard is true, start and
        # end will contain the start and end indices (in "words") of
        # the substring that the desired wildcard matched.
        foundTheRightWildcard = False
        start = end = j = numStars = numCarets = k = 0
        for i in range(len(words)):
            # This condition is true after processing a wildcard
            # that ISN'T the one we're looking for.
            if i < k:
                continue
            # If we're reached the end of the pattern, we're done.
            if j == len(patMatch):
                break
            if not foundTheRightWildcard:
                if patMatch[j] in [self._STAR, self._UNDERSCORE]: #we got a star
                    numStars += 1
                    if numStars == index:
                        # This is the star we care about.
                        foundTheRightWildcard = 'star' in wildcardType
                    start = i
                    # Iterate through the rest of the string.
                    for k in range (i, len(words)):
                        # If the star is at the end of the pattern,
                        # we know exactly where it ends.
                        if j+1  == len (patMatch):
                            end = len (words)
                            break
                        # If the words have started matching the
                        # pattern again, the star has ended.
                        if patMatch[j+1] == words[k]:
                            end = k - 1
                            i = k
                            break
                elif patMatch[j] in [self._CARET]: #we got a caret
                    numCarets += 1
                    if numCarets == index:
                        # This is the caret we care about.
                        foundTheRightWildcard = 'caret' in wildcardType
                    start = i
                    # Iterate through the rest of the string.
                    for k in range (i, len(words)):
                        # If the caret is at the end of the pattern,
                        # we know exactly where it ends.
                        if j+1  == len (patMatch):
                            end = len (words)
                            break
                        # If the words have started matching the
                        # pattern again, the caret has ended.
                        if patMatch[j+1] == words[k]:
                            _i = i
                            end = k - 1
                            i = k
                            if _i == i:
                                j += 1
                            break
                # If we just finished processing the wildcard we cared
                # about, we exit the loop early.
                if foundTheRightWildcard:
                    break
            # Move to the next element of the pattern.
            j += 1
            
        # extract the wildcard words from the original, unmutilated input.
        if foundTheRightWildcard:
            #print( ' '.join(pattern.split()[start:end+1]) )
            if wildcardType == 'caret': return ' '.join(pattern.split()[start:end+1])
            elif wildcardType == 'star': return ' '.join(pattern.split()[start:end+1])
            elif wildcardType == 'thatstar': return ' '.join(that.split()[start:end+1])
            elif wildcardType == 'topicstar': return ' '.join(topic.split()[start:end+1])
        else: return u""

    def caret(self, caretType, pattern, that, topic, index):
        """Returns a string, the portion of pattern that was matched by a ^.

        The 'caretType' parameter specifies which type of caret to find.
        Legal values are:
         - 'caret': matches a caret in the main pattern.
        """
        # Mutilate the input.  Remove all punctuation and convert the
        # text to all caps.
        input_ = pattern.upper()
        input_ = re.sub(self._puncStripRE, " ", input_)
        input_ = re.sub(self._whitespaceRE, " ", input_)
        if that.strip() == u"": that = u"ULTRABOGUSDUMMYTHAT" # 'that' must never be empty
        thatInput = that.upper()
        thatInput = re.sub(self._puncStripRE, " ", thatInput)
        thatInput = re.sub(self._whitespaceRE, " ", thatInput)
        if topic.strip() == u"": topic = u"ULTRABOGUSDUMMYTOPIC" # 'topic' must never be empty
        topicInput = topic.upper()
        topicInput = re.sub(self._puncStripRE, " ", topicInput)
        topicInput = re.sub(self._whitespaceRE, " ", topicInput)

        # Pass the input off to the recursive pattern-matcher
        patMatch, template = self._match(input_.split(), thatInput.split(), topicInput.split(), self._root)
        if template == None:
            return ""

        # Extract the appropriate portion of the pattern, based on the
        # caretType argument.
        words = None
        if caretType == 'caret':
            patMatch = patMatch[:patMatch.index(self._THAT)]
            words = input_.split()
        else:
            # unknown value
            raise ValueError( "caretType must be in ['caret']" )

        # compare the input string to the matched pattern, word by word.
        # At the end of this loop, if foundTheRightCaret is true, start and
        # end will contain the start and end indices (in "words") of
        # the substring that the desired caret matched.
        foundTheRightCaret = False
        start = end = j = numCarets = k = 0
        for i in range(len(words)):
            # This condition is true after processing a caret
            # that ISN'T the one we're looking for.
            if i < k:
                continue
            # If we're reached the end of the pattern, we're done.
            if j == len(patMatch):
                break
            if not foundTheRightCaret:
                if patMatch[j] in [self._CARET]: #we got a caret
                    numCarets += 1
                    if numCarets == index:
                        # This is the caret we care about.
                        foundTheRightCaret = True
                    start = i
                    # Iterate through the rest of the string.
                    for k in range (i, len(words)):
                        # If the caret is at the end of the pattern,
                        # we know exactly where it ends.
                        if j+1  == len (patMatch):
                            end = len (words)
                            break
                        # If the words have started matching the
                        # pattern again, the caret has ended.
                        if patMatch[j+1] == words[k]:
                            _i = i
                            end = k - 1
                            i = k
                            if _i == i:
                                j += 1
                            break
                # If we just finished processing the caret we cared
                # about, we exit the loop early.
                if foundTheRightCaret:
                    break
            # Move to the next element of the pattern.
            j += 1
            
        # extract the caret words from the original, unmutilated input.
        if foundTheRightCaret:
            #print( ' '.join(pattern.split()[start:end+1]) )
            if caretType == 'caret': return ' '.join(pattern.split()[start:end+1])
        else: return u""

    def _match(self, words, thatWords, topicWords, root):
        """Return a tuple (pat, tem) where pat is a list of nodes, starting
        at the root and leading to the matching pattern, and tem is the
        matched template.

        """ 
        # base-case: if the word list is empty, return the current node's
        # template.
        if len(words) == 0:
            # we're out of words.
            pattern = []
            template = None

            # Required to make cases when caret is at the end WORK
            if self._CARET in root:
                pattern, template = self._match(words, thatWords, topicWords, root[self._CARET])
                if template is not None:
                    newPattern = [self._CARET] + pattern
                    return (newPattern, template)
            elif len(thatWords) > 0:
                # If thatWords isn't empty, recursively
                # pattern-match on the _THAT node with thatWords as words.
                try:
                    pattern, template = self._match(thatWords, [], topicWords, root[self._THAT])
                    if pattern != None:
                        pattern = [self._THAT] + pattern
                except KeyError:
                    pattern = []
                    template = None
            elif len(topicWords) > 0:
                # If thatWords is empty and topicWords isn't, recursively pattern
                # on the _TOPIC node with topicWords as words.
                try:
                    pattern, template = self._match(topicWords, [], [], root[self._TOPIC])
                    if pattern != None:
                        pattern = [self._TOPIC] + pattern
                except KeyError:
                    pattern = []
                    template = None
            if template == None:
                # we're totally out of input.  Grab the template at this node.
                pattern = []
                try: template = root[self._TEMPLATE]
                except KeyError: template = None
            return (pattern, template)

        first = words[0]
        suffix = words[1:]
        
        # Check underscore.
        # Note: this is causing problems in the standard AIML set, and is
        # currently disabled.
        if self._UNDERSCORE in root:
            # Must include the case where suf is [] in order to handle the case
            # where a * or _ is at the end of the pattern.
            for j in range(len(suffix)+1):
                suf = suffix[j:]
                pattern, template = self._match(suf, thatWords, topicWords, root[self._UNDERSCORE])
                if template is not None:
                    newPattern = [self._UNDERSCORE] + pattern
                    return (newPattern, template)

        # Check first
        if first in root:
            pattern, template = self._match(suffix, thatWords, topicWords, root[first])
            if template is not None:
                newPattern = [first] + pattern
                return (newPattern, template)

        # check bot name
        if self._BOT_NAME in root and first == self._botName:
            pattern, template = self._match(suffix, thatWords, topicWords, root[self._BOT_NAME])
            if template is not None:
                newPattern = [first] + pattern
                return (newPattern, template)
        
        # check caret
        if self._CARET in root:
            # Must include the case where suf is [] in order to handle the case
            # where a ^ is at the end of the pattern.
            _suffix = words
            for j in range(len(_suffix)+1):
                suf = _suffix[j:]
                pattern, template = self._match(suf, thatWords, topicWords, root[self._CARET])
                if template is not None:
                    newPattern = [self._CARET] + pattern
                    return (newPattern, template)
        
        # check star
        if self._STAR in root:
            # Must include the case where suf is [] in order to handle the case
            # where a * or _ is at the end of the pattern.
            for j in range(len(suffix)+1):
                suf = suffix[j:]
                pattern, template = self._match(suf, thatWords, topicWords, root[self._STAR])
                if template is not None:
                    newPattern = [self._STAR] + pattern
                    return (newPattern, template)

        # No matches were found.
        return (None, None)         
