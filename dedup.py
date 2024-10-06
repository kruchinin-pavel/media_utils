from os import pardir
from os.path import dirname

from regex import regex


def dedup(dup_log: str):
    dir = dirname(dup_log)
    line_count = 0
    with open(dup_log, "r", encoding='utf-8') as f:
        lines = sorted(f.readlines())
        last_line, last_hash = '', ''
        for line in lines:
            line_count = line_count + 1
            hash, name = regex.split('\s+', line)[:2]
            if last_hash == hash:
                print(f'rm {dir}/{name}')
            last_hash = hash
            last_line = line
    print(f'Done {line_count} lines')


if __name__ == '__main__':
    dedup('//pi.local/black/videos/dups.log')
