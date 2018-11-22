from collections import defaultdict
import os
import shelve
from subprocess import run
import sys

DEFAULT_META = {
    'refs': {},
    'commits': {},
}

def line_dict():
    return defaultdict(set)

def build_entry(data, sha, path):
    with open(path) as f:
        line_contents = map(str.rstrip, f.readlines())

    path_data = data.get(path, defaultdict(line_dict))

    for line_no, line_content in enumerate(line_contents, 1):
        path_data[line_no][line_content].add(sha)

    data[path] = path_data

def scan(data, sha):
    dir_iterators = [os.scandir('discord')]
    while dir_iterators:
        dir_iterator = dir_iterators.pop()
        for entry in dir_iterator:
            if entry.is_dir():
                dir_iterators.append(os.scandir(entry.path))
            elif entry.is_file() and entry.name.endswith('.py'):
                build_entry(data, sha, entry.path)
        dir_iterator.close()

def merge(stored, data):
    print('Storing data')
    for path, lines in data.items():
        print(path)
        for line_no, line_contents in lines.items():
            key = f'{path}:{line_no}'
            stored_data = defaultdict(set, stored.get(key, {}))
            for line_content, shas in line_contents.items():
                stored_data[line_content] |= shas

            stored[key] = dict(stored_data)

def filter_body(lines):
    if lines and lines[0] == "    \n":
        del lines[0]

    if not lines:
        return ""

    return "\n".join([l[4:-1] for l in lines])

def get_meta(sha):
    with os.popen(f'git log --no-walk --format=raw {sha.hex()}') as pipe:
        lines = pipe.readlines()

    pos = 0
    commit_meta = {'parents': set()}
    while pos < len(lines):
        line = lines[pos][:-1] # filter out the newline character
        if line:
            name, content = line.split(' ', 1)
            if name == 'commit':
                assert bytes.fromhex(content) == sha
            elif name == 'author':
                author, timestamp, timezone = content.rsplit(' ', 2)
                commit_meta['author'] = author
                commit_meta['author-time'] = int(timestamp)
            elif name == 'committer':
                committer, timestamp, timezone = content.rsplit(' ', 2)
                commit_meta['committer'] = committer
                commit_meta['committer-time'] = int(timestamp)
            elif name == 'parent':
                commit_meta['parents'].add(bytes.fromhex(content))
            elif name == 'tree':
                pass # ignore
            elif name == 'gpgsig':
                # Signature is indented one space; skip it
                while pos + 1 < len(lines) and lines[pos+1][0] == ' ':
                    pos += 1
            else:
                print(f"unhandled field {name}")

        else:
            if pos + 1 >= len(lines):
                raise RuntimeError("Unexpected end of commit data")

            commit_meta['subject'] = lines[pos+1][4:-1]
            commit_meta['body'] = filter_body(lines[pos+2:])
            break

        pos += 1

    return commit_meta

def update_refs(meta):
    command = 'git for-each-ref --format="%(objectname) %(refname)"'
    with os.popen(command) as pipe:
        lines = pipe.readlines()

    for line in lines:
        hex_sha, ref = line[:-1].split(' ', 1)
        if ref.startswith('refs/heads/') or 'HEAD' in ref:
            continue
        meta['refs'][ref] = bytes.fromhex(hex_sha)

def repo(stored, ref):
    data = {}
    meta = stored.get('META', DEFAULT_META)

    with os.popen(f'git rev-list {ref}') as pipe:
        for hex_sha in map(str.strip, pipe.readlines()):
            sha = bytes.fromhex(hex_sha)
            if sha in meta['commits']:
                continue
            run(['git', 'checkout', hex_sha], capture_output=True, check=True)
            print(hex_sha)
            scan(data, sha)
            meta['commits'][sha] = get_meta(sha)

    merge(stored, data)
    update_refs(meta)
    stored['META'] = meta

def update_meta(stored):
    meta = stored.get('META', DEFAULT_META)
    meta['refs'] = {}
    meta['commits'] = {sha: get_meta(sha) for sha in meta['commits']}
    update_refs(meta)
    stored['META'] = meta

if __name__ == '__main__':
    with shelve.open('data') as stored:
        os.chdir('discord.py')
        if sys.argv[1] != '-m':
            repo(stored, sys.argv[1])
        else:
            update_meta(stored)
