import re
import pathlib
from string import Formatter
import os
from datetime import datetime

COMMENT_OPEN = '<!--'
COMMENT_CLOSE = '-->'
SHARD_OPEN = '<shard '
SHARD_CLOSE = '</shard>'

class Shard:
    def __init__(self, name: str, content: str, origin: str = None) -> None:
        self.name = name
        self.content = content
        self.origin = origin

    def render(self, **variables) -> str:
        """ Renders the shard with the given variables """
        return self.content.format(**variables)
    
    def get_variables(self):
        """ Returns a list of all variables used in the shard """
        return list(set(v[1] for v in Formatter().parse(self.content) if v[1] is not None))
    
    def __str__(self):
        return f"{self.name} ({', '.join(self.get_variables())}) -> {self.origin}"
    
class ShardUse:
    def __init__(self, shard: Shard, use: str, variables: dict, origin: str = None):
        self.shard = shard
        self.use = use
        self.variables = variables
        self.origin = origin

    def render(self) -> str:
        """ Renders the shard in the use context """
        return self.shard.render(**self.variables)
    
    def apply(self, template: str) -> str:
        """ Replaces the shard use with the rendered shard in the template"""
        return template.replace(self.use, self.render())
    
def get_file_modification_datetime(filepath: str) -> datetime:
    """ Returns the datetime of the last modification of the file at filepath """
    return datetime.fromtimestamp(os.path.getmtime(filepath))

def extract_attributes(tag: str) -> dict:
    """ Extracts attributes from html tags like <tag att1="value1" att2="value2" ...> """
    return {attr: value for attr, value in re.findall(r'(\w+)\s*=\s*"([^"]*)"', tag)}

def remove_comments(s: str, start: int = 0) -> str:
    """ Removes comments like <!-- ... --> from html source """
    comments = []
    valid = True
    while valid:
        first_open = s.find(COMMENT_OPEN, start)
        first_close = s.find(COMMENT_CLOSE, first_open)
        if first_open < 0 or first_close < 0:
            valid = False
        else:
            comments.append(s[first_open: first_close + len(COMMENT_CLOSE)])
            start = first_close + len(COMMENT_CLOSE)
    for comment in comments:
        s = s.replace(comment, '')
    return s

def get_shard_from_string(s: str, origin: str = None) -> Shard:
    """ Reads one shard from given string s and returns a Shard object """
    start = s.find(SHARD_OPEN) + len(SHARD_OPEN)
    end = s.find('>', start)
    attributes = extract_attributes(s[start: end])
    content = s[end + 1: s.find(SHARD_CLOSE)].strip()
    return Shard(attributes['name'], content, origin)

def get_shards_from_string(s: str, start: int = 0, origin: str = None) -> list[Shard]:
    """ Reads all shards from the given string s and return a list of Shard objects """
    str_shards = []

    # Shard extraction
    valid = True
    while valid:
        first_open = s.find(SHARD_OPEN, start)
        first_close = s.find(SHARD_CLOSE, first_open)
        if first_open < 0 or first_close < 0:
            valid = False
        else:
            str_shards.append(s[first_open: first_close + len(SHARD_CLOSE)])
            start = first_close + len(SHARD_CLOSE)

    # Shard processing
    return [get_shard_from_string(str_shard, origin) for str_shard in str_shards]

def find_corresponding_close(s: str, strs_open: list, str_close: str, start: int = 0) -> int:
    level = 1
    while level > 0:
        positions = [pos for pos in [s.find(str_open, start) for str_open in strs_open] if pos >= 0]
        if len(positions) > 0:
            first_open = min(positions)
        else:
            first_open = -1
        first_close = s.find(str_close, start)

        # Close does not exist
        if first_close < 0:
            return -1
        
        # Open is first
        elif first_open < first_close and first_open >= start:
            level += 1
            start = first_open + 1

        # Close is first
        else:
            level -= 1
            start = first_close + 1
    return first_close

def find_shard_in_template(template: str, shard: Shard, start: int = 0, origin: str = None) -> tuple[Shard, int]:
    """ Finds the first use of a shard in a template string """
    shard_open_with_variables = f'<{shard.name} '
    shard_open_without_variables = f'<{shard.name}>'
    
    # Get correct start tag
    first_open_with_variables = template.find(shard_open_with_variables, start)
    first_open_without_variables = template.find(shard_open_without_variables, start)
    if first_open_with_variables < 0 and first_open_without_variables < 0:
        first_open = -1
    elif first_open_with_variables >= 0 and (first_open_with_variables < first_open_without_variables or first_open_without_variables < 0):
        first_open = first_open_with_variables
        shard_open = shard_open_with_variables
        has_variables = True
    else:
        first_open = first_open_without_variables
        shard_open = shard_open_without_variables
        has_variables = False

    # Get close tag
    if first_open < 0: 
        first_close = -1
    else:
        shard_close = f'</{shard.name}>'
        first_close = find_corresponding_close(template, [shard_open_with_variables, shard_open_without_variables], shard_close, first_open + len(shard_open))

    # No or incorrect shard
    if first_open < 0 or first_close < 0 or first_open > first_close:
        return None, -1

    # Shard found
    else:
        # Get variables
        if has_variables:
            variables_start = first_open + len(shard_open)
            variables_end = template.find('>', variables_start)
            variables = extract_attributes(template[variables_start: variables_end])
            variables['content'] = template[variables_end + 1: first_close]
        else:
            variables = {'content': template[first_open + len(shard_open): first_close]}

        # Return use
        shard_end = first_close + len(shard_close)
        return ShardUse(shard, template[first_open: shard_end], variables, origin), shard_end

def render_template(template: str, shards: list[Shard], origin: str = None) -> str:
    """ Renders a template string with the given shards """
    for shard in shards:
        start = 0
        while start >= 0:
            use, start = find_shard_in_template(template, shard, start, origin)
            if use:
                template = use.apply(template)
    return template



class ShardRenderer:
    def __init__(self, shard_directory: str = 'templates/shards', shard_template_directory: str = 'templates/templates', flask_template_directory: str = 'templates/rendered') -> None:

        # Store directories
        self.shard_directory = shard_directory
        self.shard_template_directory = shard_template_directory
        self.flask_template_directory = flask_template_directory

        # Load shards
        self.shards = []
        self.reload_shards()

    def reload_shards(self):
        """ Reloads shards of all .html files from shard directory """
        self.shards.clear()
        for filepath in pathlib.Path(self.shard_directory).glob('*.html'):
            with open(filepath, 'r') as file:
                self.shards.extend(get_shards_from_string(file.read(), origin=filepath.parts[-1]))

    def render_template_file(self, filename: str):
        """ Renders a template file with the current shards """

        # Read shard template
        with open(os.path.join(self.shard_template_directory, filename), 'r') as file:
            shard_template = file.read()

        # Render
        flask_template = render_template(shard_template, self.shards, filename)

        # Save as flask template
        with open(os.path.join(self.flask_template_directory, filename), 'w') as file:
            file.write(flask_template)

    def update(self):
        """ Renders all outdated templates """
        for shard_template_filepath in pathlib.Path(self.shard_template_directory).glob('*.html'):
            filename = shard_template_filepath.parts[-1]
            flask_template_filepath = os.path.join(self.flask_template_directory, filename)
            if not os.path.exists(flask_template_filepath) or get_file_modification_datetime(shard_template_filepath) > get_file_modification_datetime(flask_template_filepath):
                print(f'Render {filename}')
                self.render_template_file(filename)
        print('Templates updated')

if __name__ == '__main__':
    renderer = ShardRenderer()
    renderer.update()