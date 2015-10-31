NOTE_HEADLINE = re.compile(
    '^'                    # Starts at the begging of the line
    '(?P<header_start>[=]+)'  # Heading beggining
    '(?P<question>[^=\|\[\{]*)'  # Name of the viewport, all before the | sign
                             # Cannot include '[', '=', '|, and '{'
    '@'                   # Divider @
    '(?P<metadata>[^=@]*?)'       # Filter
    '\s*'                  # Any whitespace
    '(?P<header_end>[=]+)'  # Heading ending
    )

class WikiNote(object):

    def __init__(self, proxy):
        self.fields = dict()
        self.data = dict()
        self.proxy = proxy

    @classmethod
    def from_line(cls, number, proxy):
        """
        This methods detects if a current line is a note-defining headline. If
        positive, it will try to parse the note data out of the block.
        """

        match = re.search(NOTE_HEADLINE, vim.current.buffer[number])

        if not match:
            return None

        self = cls(proxy)

        # If we have a match, determine if it's an existing note
        metadata = match.group('metadata').strip()
        question = match.group('question').strip()

        self.data.update({
            'header_start': match.group('header_start'),
            'header_end': match.group('header_end'),
            'id': metadata,
            'line': number,
        })

        # Parse out the answer
        answerlines = []
        for line in vim.current.buffer[(number+1):]:
            candidate = line.strip()

            # Consider new heading or --- as a end of the answer
            if candidate.startswith('=') or candidate.startswith('---'):
                break
            elif candidate:
                answerlines.append(candidate)

        self.fields.update({
            'Heading': "Added from anki",
            'Front': question,
            'Back': '</br>\n'.join(answerlines),
        })

        return self

    def __repr__(self):
        return repr(self.fields)

    @property
    def created(self):
        return self.data.get('id') is not None

    def save(self):
        if self.data.get('id') is not None:
            return

        obtained_id = self.proxy.add_note('TestDeck', 'Basic', self.fields)

        if obtained_id:
            self.data['id'] = obtained_id
            self.proxy.collection.flush()
            self.proxy.collection.save()
            self.update_in_buffer()

    def update_in_buffer(self):
        """
        Updates the representation of the note in the buffer.
        Note: Currently only affects the header.
        """

        line = ' '.join([
            self.data['header_start'],
            self.fields['Front'],
            '@',
            str(self.data['id']),
            self.data['header_end'],
        ])

        vim.current.buffer[self.data['line']] = line