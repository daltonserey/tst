# coding: utf-8
"""
"""
from __future__ import unicode_literals
from __future__ import print_function

import json
import random
import codecs
import string
import sys

class DataGenerator:
    def __init__(self):
        self.words_used = {}
        self.integers_used = {}

    def integer(self, num, min=-sys.maxint-1, max=sys.maxint):
        if num in self.integers_used:
            return self.integers_used[num]

        integer = random.randint(min, max)
        self.integers_used[num] = integer
        return self.integers_used[num]


    def word(self, num, length=None, min=1, max=15, alphabet=None):
        if num in self.words_used:
            return self.words_used[num]

        if alphabet:
            if alphabet == '[A..Z]':
                symbols = string.ascii_uppercase
            elif alphabet == '[a..z]':
                symbols = string.ascii_lowercase
            elif alphabet == '[0..9]':
                symbols = string.digits
            else:
                symbols = string.letters
        else:
            symbols = string.letters

        # create word
        length = length or random.randint(min, max)
        word = "".join([random.choice(symbols) for i in xrange(length)])
        self.words_used[num] = word
        return self.words_used[num]


    def reset_values(self):
        self.words_used.clear()
        self.integers_used.clear()
