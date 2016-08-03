import re, requests
from urlparse import urlparse
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


CODE_INCLUDE_TAG = re.compile(r'\[!\[[\w ]+\]\(https:\/\/www.mbed.com\/embed\/\?url=[\w?=:/.-]+\)\]\([\w:/.-]+\)')
V2_IMPORT_URL = 'https://developer.mbed.org/compiler/#import:'
V3_IMPORT_URL = 'https://mbed.com/ide/open/?url='


class CodeInclusionPreprocessor(Preprocessor):
    '''
    Build a code block based on a given source file. Also create an import button
    to import the project into one of the mbed IDEs. Import button creates a foundation
    modal which allows user to select IDE.
    '''
    modal_id = 0 # Each modal in the document needs a unique id

    def get_repo_url(self, url, import_path, slice):
        parsed_url = urlparse(url)
        for p in parsed_url.path.split('/')[:slice]:
            if p:
                import_path += '/' + p
        return import_path

    def get_github_repo_url(self, url):
        '''
        Get the url of the git repo on GitHub
        '''
        return self.get_repo_url(url, 'https://github.com', 3)

    def get_mbed_dev_repo_url(self, url):
        '''
        Get the url of the hg repo on the developer site
        '''
        return self.get_repo_url(url, 'https://developer.mbed.org', 5)

    def get_import_url(self, url):
        if 'github.com' in url:
            return self.get_github_repo_url(url)
        elif 'developer.mbed.' in url:
            return self.get_mbed_dev_repo_url(url)

    def get_import_button(self, url):
        '''
        Only create button for classic IDE for now...
        '''
        repo_url = self.get_import_url(url)
        v2_url = V2_IMPORT_URL + repo_url
        return '<a href="%s" style="float:right; color:white;" class="button" target="_blank">Import into mbed IDE</a>' % v2_url

    def get_source_url(self, url):
        parsed_url = urlparse(url)
        if 'github.com' in parsed_url.netloc:
            source_url = 'https://raw.githubusercontent.com/'
            github_user = parsed_url.path.split('/')[1]
            github_repo = parsed_url.path.split('/')[2]
            file_path = ''
            for loc in parsed_url.path.split('/')[4:]:
                file_path += '/' + loc
            return source_url + github_user + '/' + github_repo + file_path
        elif 'developer.mbed' in parsed_url.netloc:
            path = parsed_url.path.split('/')
            path[5] = 'raw-file'
            file_path = ''
            for p in path:
                if p:
                    file_path += '/' + p
            return 'https://developer.mbed.org' + file_path

    def build_code_block(self, lines, url):
        filename = url.split('/')[-1]
        code_header = '<div class="code-header"><a href=%s target="_blank"><i class="fa fa-file-code-o"></i> <b class="filename">%s</b></a>' % (url, filename) + self.get_import_button(url) + '</div>'
        code_string = ''
        for line in lines:
            code_string += line
        code_block = [
            '<div class="code-include-block">',
            code_header,
            '```', code_string, '```',
            '</div>'
        ]
        return code_block

    def run(self, lines):
        new_lines = []
        prev_line = ''
        for line in lines:
            m = CODE_INCLUDE_TAG.match(line)
            if m:
                urls = re.findall(r'\([\w:/.?=-]+\)', m.group())
                source_url = urls[1][1:-1]
                raw_source_url = self.get_source_url(source_url)
                response = requests.get(raw_source_url)
                if response.status_code == requests.codes.ok:
                    code_block = self.build_code_block(response.text.splitlines(True), source_url)
                    if not prev_line: # There is a bug in the way the code block renders if the preceding line is an empty string, so to fix this add a line with a space before the code block...
                        code_block = ['&nbsp;'] + code_block
                    new_lines += code_block
            else:
                new_lines.append(line)
            prev_line = line
        return new_lines


class Inclusion(Extension):
    def extendMarkdown(self, md, md_globals):
        md.preprocessors.add('code_inclusion', CodeInclusionPreprocessor(md), '>normalize_whitespace')


def makeExtension(*args, **kwargs):
    return Inclusion(*args, **kwargs)
