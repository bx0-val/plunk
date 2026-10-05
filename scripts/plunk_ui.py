"""Small, dependency-free terminal presentation shared by every Plunk command."""
import os
import shutil
import sys
import textwrap

COLORS = {'orange': '38;5;208', 'mint': '38;5;114', 'muted': '38;5;245', 'red': '38;5;203', 'bold': '1', 'cream': '38;5;230'}

class Terminal:
    def __init__(self, mode='auto', stream=None):
        self.stream = stream or sys.stdout
        self.width = max(28, shutil.get_terminal_size((80, 24)).columns)
        self.interactive = self.stream.isatty()
        self.color = mode == 'always' or (mode == 'auto' and 'NO_COLOR' not in os.environ and os.environ.get('TERM') != 'dumb' and (self.interactive or os.environ.get('FORCE_COLOR', '0') not in ('', '0')))

    def paint(self, style, text):
        # Destinations can contain arbitrary filenames; never execute their terminal controls.
        text = ''.join(c if c >= ' ' and c != '\x7f' else ' ' for c in str(text))
        return f'\033[{COLORS.get(style, style)}m{text}\033[0m' if self.color else text

    def line(self, text=''):
        print(text, file=self.stream)

    def title(self, title, subtitle=None):
        self.line()
        self.line('  ' + self.paint('bold', 'plunk') + self.paint('orange', '.') + '  ' + self.paint('muted', '/') + '  ' + self.paint('bold', title))
        if subtitle:
            self.note(subtitle)
        self.line('  ' + self.paint('muted', '─' * min(self.width - 4, 60)))

    def note(self, text):
        for line in textwrap.wrap(str(text), width=self.width - 4, break_long_words=True) or ['']:
            self.line('  ' + self.paint('muted', line))

    def success(self, text):
        self.line('  ' + self.paint('mint', '✓') + ' ' + self.paint('cream', text))

    def field(self, label, value, style='cream'):
        self.line('  ' + self.paint('muted', label.upper()))
        # A terminal may visually wrap a URL, but injected newlines break copying it.
        lines = [str(value)] if str(value).startswith(('https://', 'http://')) else textwrap.wrap(str(value), width=self.width - 6, break_long_words=True) or ['']
        for line in lines:
            self.line('    ' + self.paint(style, line))

    def step(self, number, text):
        self.line('  ' + self.paint('orange', f'{number:02}') + '  ' + self.paint('bold', text))

    def pairing(self, name, base, code, minutes, qr_matrix=None):
        self.title('Pair your phone', 'One small connection. A lot less sending things to yourself.')
        self.field('Server', name)
        self.line()
        if qr_matrix and self.interactive and len(qr_matrix[0]) + 4 <= self.width:
            # A fixed black-on-white half-block QR is scannable in light AND dark terminals.
            matrix = [*qr_matrix, [False] * len(qr_matrix[0])]
            for index in range(0, len(qr_matrix), 2):
                line = ''.join('█' if a and b else '▀' if a else '▄' if b else ' ' for a, b in zip(matrix[index], matrix[index + 1]))
                self.line('  ' + (f'\033[30;107m{line}\033[0m' if self.color else line))
            self.line()
        self.line('  ' + self.paint('orange', '●') + '  ' + self.paint('bold', f'{code[:3]}  {code[3:]}'))
        self.note(f'One use · expires in {minutes} minutes · a new code replaces this one')
        self.line()
        self.step(1, 'Scan with your iPhone camera. Keep Tailscale connected.')
        self.step(2, 'In Safari: Share → Add to Home Screen.')
        self.step(3, 'Open the Plunk icon → Connect a server → enter the code.')
        self.line()
        self.field('Open on your phone', f'{base}/app#pair={code}', 'orange')
        self.note('Already installed? Open Plunk and enter this code in Server settings.')
        self.line()

    def help(self):
        self.title('Your camera. Your folders.', 'Pic → Name → Location')
        for label, commands in [
            ('GET CONNECTED', [('install', 'Set up this Linux server'), ('pair', 'Connect a phone with a one-time code')]),
            ('MAKE IT PART OF YOUR WORK', [('here', 'Offer the current folder to your phone'), ('add PATH', 'Offer another folder'), ('ls', 'See destinations and their IDs'), ('rm ID', 'Remove a destination; keep its files')]),
            ('CHECK IN', [('status', 'See service health and your app address'), ('url', 'Print just the app URL, ready to pipe'), ('logs', 'Read recent service logs')]),
        ]:
            self.line()
            self.note(label)
            for command, description in commands:
                self.line('  ' + self.paint('orange', f'plunk {command}'))
                self.note('  ' + description)
        self.line()
        self.note('plunk <command> --help  ·  --color auto|always|never  ·  respects NO_COLOR')
        self.line()
