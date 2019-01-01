from functools import partial
import re
import shelve

START_OF_REWRITE = bytes.fromhex('044b0824e68c4dacdaf26ff52a741ca1b5118c9b')
START_OF_ASYNC = bytes.fromhex('5a666c3f0dc2ecc60ca8320e50f391c6dee19e51')
FILE_PATTERN = r'File "([^"]*)", line ([0-9]+), in'

def fix_path(path):
    path = path.replace('\\', '/')
    if 'discord' in path:
        path = path[path.rindex('discord'):]

    return path

def match_traceback(stored, trace):
    parts = []
    lines = trace.split('\n')
    pos = 0
    while pos < len(lines):
        match = re.search(FILE_PATTERN, lines[pos])
        if (
            match
            and pos + 1 < len(lines)
            # Sometimes a line is skipped
            and not re.search(FILE_PATTERN, lines[pos+1])
        ):
            path = fix_path(match[1])
            parts.append((path, int(match[2]), lines[pos+1].strip()))
            pos += 1
        pos += 1

    matched = []
    for path, line_no, line_content in parts:
        key = f'{path}:{line_no}'
        if key not in stored:
            continue

        part_matches = set()
        for stored_line, stored_commits in stored[key].items():
            if stored_line.endswith(line_content):
                part_matches |= stored_commits

        if part_matches:
            matched.append(part_matches)

    if matched:
        common = matched.pop()
        for commits in matched:
            common &= commits
        return common

    return set()

def sha_to_committer_time(meta, sha):
    return meta['commits'][sha]['committer-time']

def ref_to_committer_time(meta, ref):
    return sha_to_committer_time(meta, meta['refs'][ref])

def branches(meta, commits):
    """Infer which branchs the passed commits happened on"""
    found = []
    commits = sorted(commits, key=partial(sha_to_committer_time, meta))
    walked = set()
    while commits:
        sha = commits.pop()
        if sha in walked:
            continue

        walked.add(sha)
        if not meta['commits'][sha]['parents']:
            found.append('legacy')

        elif sha == START_OF_REWRITE:
            found.append('rewrite')

        elif sha == START_OF_ASYNC:
            found.append('async')

        else:
            commits.extend(meta['commits'][sha]['parents'])

    return found


def date_trace(trace):
    with shelve.open('data', 'r') as stored:
        commits = match_traceback(stored, trace)
        meta = stored['META']

    if not commits:
        return None

    refs = {ref for ref, sha in meta['refs'].items() if sha in commits}
    sorted_refs = sorted(refs, key=partial(ref_to_committer_time, meta))
    timestamps = [meta['commits'][sha]['committer-time'] for sha in commits]
    tags = list(map(lambda s: s[10:], filter(
        lambda s: s.startswith("refs/tags"), sorted_refs
    )))

    return {
        'tags': tags,
        'branches': branches(meta, commits),
        'time-start': min(timestamps),
        'time-end': max(timestamps),
    }


if __name__ == '__main__':
    test = open('test.txt').read()
    print(date_trace(test))
