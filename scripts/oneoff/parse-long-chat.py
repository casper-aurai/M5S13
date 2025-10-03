import re

def parse_long_chat(html):
    """Parses the html file in docs and processes it to markdown"""
    # remove all html tags
    text = re.sub('<[^<]+?>', '', html)
    # replace all occurrences of multiple whitespace with a single space
    text = re.sub('\s+', ' ', text)
    # replace all occurrences of newline with two newlines
    text = text.replace('\n', '\n\n')
    # replace all occurrences of double newlines with triple newlines
    text = text.replace('\n\n\n', '\n\n\n\n')
    return text
