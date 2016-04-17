from __future__ import print_function
import operator
import os
import re
import sys
import vim

# Insert the knowledge on the python path
BASE_DIR = vim.eval("s:plugin_path")
sys.path.insert(0, os.path.join(BASE_DIR, 'knowledge'))

import error
# Handle error without traceback, if they're KnowledgeException
def output_exception(original_hook, exception_type, value, tb):
    if exception_type is error.KnowledgeException:
        print(unicode(value), file=sys.stderr)
    else:
        original_hook(exception_type, value, tb)

# Wrap the original except hook
sys.excepthook = lambda a,b,c: output_exception(sys.excepthook, a, b, c)

from proxy import AnkiProxy, MnemosyneProxy
from wikinote import WikiNote, Header

SRS_PROVIDER = vim.vars.get('knowledge_srs_provider')
DATA_DIR = vim.vars.get('knowledge_data_dir')
proxy = None

if SRS_PROVIDER == 'Anki':
    proxy = AnkiProxy(DATA_DIR)
elif SRS_PROVIDER == 'Mnemosyne':
    proxy = MnemosyneProxy(DATA_DIR)
elif SRS_PROVIDER is None:
    raise error.KnowledgeException(
        "Variable knowledge_srs_provider has to have "
        "one of the following values: Anki, Mnemosyne"
    )
else:
    raise error.KnowledgeException(
        "SRS provider '{0}' is not supported."
        .format(SRS_PROVIDER)
    )


class HeaderStack(object):
    """
    A stack that keeps track of the metadata defined by the header
    hierarchy.
    """

    def __init__(self):
        self.headers = dict()

    def push(self, header):
        pushed_level = len(header.data['header_start'])

        # Pop any headers on the lower levels
        kept_levels = {
            key: self.headers[key]
            for key in self.headers.keys()
            if key < pushed_level
        }
        self.headers = kept_levels

        # Set the currently pushed level
        self.headers[pushed_level] = header

    @property
    def tags(self):
        tag_sets = [
            set(header.data.get('tags', []))
            for header in self.headers.values()
        ]

        return reduce(operator.or_, tag_sets, set())

    @property
    def deck(self):
        keys = sorted(self.headers.keys(), reverse=True)
        for key in keys:
            deck = self.headers[key].data.get('deck')
            if deck is not None:
                return deck

    @property
    def model(self):
        keys = sorted(self.headers.keys(), reverse=True)
        for key in keys:
            model = self.headers[key].data.get('model')
            if model is not None:
                return model


def create_notes(update=False):
    """
    Loops over current buffer and adds any new notes to Anki.
    """

    stack = HeaderStack()

    for line_number in range(len(vim.current.buffer)):
        note = WikiNote.from_line(
            line_number,
            proxy,
            tags=stack.tags,
            deck=stack.deck,
            model=stack.model,
        )

        if note is None:
            header = Header.from_line(line_number)
            if header is not None:
                stack.push(header)

        elif not note.created or update:
            note.save()
