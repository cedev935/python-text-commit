#!/usr/bin/env python3

from datetime import datetime, timedelta
import itertools
import json
import math
import os
from text_to_matrix import get_arial_font_matrix
try:
    # Python 3+
    from urllib.error import HTTPError, URLError
    from urllib.request import urlopen
except ImportError:
    # Python 2
    from urllib2 import HTTPError, URLError, urlopen

try:
    # Python 2
    raw_input
except NameError:
    # Python 3 (Python 2's `raw_input` was renamed to `input`)
    raw_input = input


GITHUB_BASE_URL = 'https://github.com/'
FALLBACK_IMAGE = 'kitty'


TITLE = '''
 _____         _     _____        ____                          _ _     _   _ _     _                   
|_   _|____  _| |_  |_   _|__    / ___|___  _ __ ___  _ __ ___ (_) |_  | | | (_)___| |_ ___  _ __ _   _ 
  | |/ _ \\ \\/ / __|   | |/ _ \\  | |   / _ \\| '_ ` _ \\| '_ ` _ \\| | __| | |_| | / __| __/ _ \\| '__| | | |
  | |  __/>  <| |_    | | (_) | | |__| (_) | | | | | | | | | | | | |_  |  _  | \\__ \\ || (_) | |  | |_| |
  |_|\\___/_/\\_\\\\__|   |_|\\___/   \\____\\___/|_| |_| |_|_| |_| |_|_|\\__| |_| |_|_|___/\\__\\___/|_|   \\__, |
                                                                                                  |___/

'''


KITTY = [
  [0,0,0,4,0,0,0,0,4,0,0,0],
  [0,0,4,2,4,4,4,4,2,4,0,0],
  [0,0,4,2,2,2,2,2,2,4,0,0],
  [2,2,4,2,4,2,2,4,2,4,2,2],
  [0,0,4,2,2,3,3,2,2,4,0,0],
  [2,2,4,2,2,2,2,2,2,4,2,2],
  [0,0,0,3,4,4,4,4,3,0,0,0],
]


ASCII_TO_NUMBER = {
  '_': 0,
  '_': 1,
  '~': 2,
  '=': 3,
  '*': 4,
}


def str_to_sprite(content):
    # Break out lines and filter any excess
    lines = content.split('\n')
    def is_empty_line(line):
        return len(line) != 0
    lines = filter(is_empty_line, lines)

    # Break up lines into each character
    split_lines = [list(line) for line in lines]

    # Replace each character with its numeric equivalent
    for line in split_lines:
        for index, char in enumerate(line):
            line[index] = ASCII_TO_NUMBER.get(char, 0)

    # Return the formatted str
    return split_lines


IMAGES = {
  'kitty': KITTY,
}


def retrieve_contributions_calendar(username, base_url):
    """retrieves the GitHub commit calendar data for a username"""
    base_url = base_url + 'users/' + username

    try:
        url = base_url + '/contributions'
        page = urlopen(url)
    except (HTTPError, URLError) as e:
        print('There was a problem fetching data from {0}'.format(url))
        print(e)
        raise SystemExit

    return page.read().decode('utf-8')


def parse_contributions_calendar(contributions_calendar):
    """Yield daily counts extracted from the contributions SVG."""
    for line in contributions_calendar.splitlines():
        for day in line.split():
            if 'data-count=' in day:
                commit = day.split('=')[1]
                commit = commit.strip('"')
                yield int(commit)


def find_max_daily_commits(contributions_calendar):
    """finds the highest number of commits in one day"""
    daily_counts = parse_contributions_calendar(contributions_calendar)
    return max(daily_counts)


def calculate_multiplier(max_commits):
    """calculates a multiplier to scale GitHub colors to commit history"""
    m = max_commits / 4.0

    if m == 0:
        return 1

    m = math.ceil(m)
    m = int(m)
    return m


def get_start_date():
    """returns a datetime object for the first sunday after one year ago today
    at 12:00 noon"""
    today = datetime.today()
    date = datetime(today.year - 1, today.month, today.day, 12)
    weekday = datetime.weekday(date)

    while weekday < 6:
        date = date + timedelta(1)
        weekday = datetime.weekday(date)

    return date


def generate_next_dates(start_date, offset=0):
    """generator that returns the next date, requires a datetime object as
    input. The offset is in weeks"""
    start = offset * 7
    for i in itertools.count(start):
        yield start_date + timedelta(i)


def generate_values_in_date_order(image, multiplier=1):
    height = 7
    width = len(image[0])

    for w in range(width):
        for h in range(height):
            yield image[h][w] * multiplier


def commit(commitdate):
    template = (
        '''GIT_AUTHOR_DATE={0} GIT_COMMITTER_DATE={1} '''
        '''git commit --allow-empty -m "text_to_commit_history" > /dev/null\n'''
    )
    return template.format(commitdate.isoformat(), commitdate.isoformat())


def fake_it(image, start_date, username, repo, git_url, offset=0, multiplier=1):
    template = (
        '#!/usr/bin/env bash\n'
        'REPO={0}\n'
        'git init $REPO\n'
        'cd $REPO\n'
        'touch README.md\n'
        'git add README.md\n'
        'touch text_to_commit_history\n'
        'git add text_to_commit_history\n'
        '{1}\n'
        'git remote add origin {2}:{3}/$REPO.git\n'
        'git pull origin master\n'
        'git push -u origin master\n'
    )

    strings = []
    for value, date in zip(generate_values_in_date_order(image, multiplier),
            generate_next_dates(start_date, offset)):
        for _ in range(value):
            strings.append(commit(date))

    return template.format(repo, ''.join(strings), git_url, username)


def save(output, filename):
    """Saves the list to a given filename"""
    with open(filename, 'w') as f:
        f.write(output)
    os.chmod(filename, 0o755) # add execute permissions


def request_user_input(prompt='> '):
    """Request input from the user and return what has been entered."""
    return raw_input(prompt)


def main():
    print(TITLE)

    ghe = request_user_input(
        'Enter GitHub URL (leave blank to use {}): '.format(GITHUB_BASE_URL))

    username = request_user_input('Enter your GitHub username: ')

    git_base = ghe if ghe else GITHUB_BASE_URL

    contributions_calendar = retrieve_contributions_calendar(username, git_base)

    max_daily_commits = find_max_daily_commits(contributions_calendar)

    m = calculate_multiplier(max_daily_commits)

    repo = request_user_input(
        'Enter the name of the repository to use by text_to_commit_history: ')

    offset = request_user_input(
        'Enter the number of weeks to offset the image (from the left): ')

    offset = int(offset) if offset.strip() else 0

    print((
        'By default text_to_commit_history.py matches the darkest pixel to the highest\n'
        'number of commits found in your GitHub commit/activity calendar,\n'
        '\n'
        'Currently this is: {0} commits\n'
        '\n'
        'Enter the word "text_to_commit_history" to exceed your max\n'
        '(this option generates WAY more commits)\n'
        'Any other input will cause the default matching behavior'
    ).format(max_daily_commits))
    match = request_user_input()

    match = m if (match == 'text_to_commit_history') else 1

    img_names = "".split(' ')

    print('Enter your the text you want to be shown on your profile')
    text_image = request_user_input()

    text_image_name_fallback = FALLBACK_IMAGE

    if not text_image:
        text_image = IMAGES[text_image_name_fallback]
    else:
        try:
            text_image = get_arial_font_matrix(text_image)
        except:
            text_image = IMAGES[text_image_name_fallback]

    start_date = get_start_date()
    fake_it_multiplier = m * match

    if not ghe:
        git_url = 'git@github.com'
    else:
        git_url = request_user_input('Enter Git URL like git@site.github.com: ')

    output = fake_it(text_image, start_date, username, repo, git_url, offset,
                     fake_it_multiplier)

    save(output, 'text_to_commit_history.sh')
    print('text_to_commit_history.sh saved.')
    print('Create a new(!) repo named {0} at {1} and run the script'.format(repo, git_base))


if __name__ == '__main__':
    main()
