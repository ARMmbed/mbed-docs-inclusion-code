import re, requests
from urlparse import urlparse
from markdown import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


CODE_INCLUDE_TAG = re.compile(r'\[!\[[\w ]+\]\(https:\/\/www.mbed.com\/embed\/\?url=[\w?=:/.-]+\)\]\([\w:/.-]+\)')
COMPILER_URL = 'https://developer.mbed.org/compiler/#import:'

class CodeInclusionPreprocessor(Preprocessor):
    '''
    Build a code block based on a given source file. Uses the mbed-import-button javascript project
    to render the actual button.
    '''
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
        clone_url = self.get_import_url(url)
        compiler_url = COMPILER_URL + clone_url
        return \
"""
<div class="import-button-holder"><div id="import-button" class="import-button"></div></div>
<script type="text/javascript">
  new ImportButton($("#import-button"), {
    last_used_workspace: {
      type: "compiler"
    },
    compiler_import_url: %r,
    clone_url: %r,
    is_library: false,
    c9_enabled: false,
    cli_enabled: true,
    userinfo_api: '/api-proxy/v3/userinfo/'
  });
</script>
""" % (str(compiler_url), str(clone_url))

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
        code_header = \
"""
<div class="code-header">
    <a href=%r target="_blank">
        <i class="fa fa-file-code-o"></i>
        <b class="filename">%s</b>
    </a>
    %s
</div>
""" % (str(url), filename, self.get_import_button(url))

        code_string = "".join(lines)
        return [
            '<div class="code-include-block">',
            code_header,
            '```', code_string, '```',
            '</div>'
        ]

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
                    code_block = self.build_code_block(response.text.strip().splitlines(True), source_url)
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

if __name__ == "__main__":
    # If someone decides to run this file as an executable, let's just
    # output something matching the regex.
    md = Markdown(extensions=['extra', 'code_inclusion'])
    print md.convert("[![View code](https://www.mbed.com/embed/?url=https://developer.mbed.org/teams/mbed-os-examples/code/mbed-os-example-blinky/)](https://developer.mbed.org/teams/mbed-os-examples/code/mbed-os-example-blinky/file/tip/main.cpp)")
